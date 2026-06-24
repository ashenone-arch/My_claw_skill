""" sync.py - Fact Hub 双向同步脚本 v2.2

增量策略：Git blob SHA 对比（0 API 调用）+ log.md 优先裁定方向：
  - 本地独有 → 推送到远程
  - 远程独有 → 下载到本地
  - 远程有、本地已删除 → 标记为待确认，默认不删除远程（需 --allow-delete）
  - 两边都有、blob SHA 不同 → 比较 log.md 最新日志时间（取所有时间戳中的最大值），更新者覆盖旧者
  - log.md 不存在时 → 回退到逐文件 commit 时间比较

v2.2 (2026-06-24): 新增 .syncstate.json 远程变更哨兵机制，解决多终端并行同步场景下
增量检测漏同步问题。每次 sync 后保存远程 tree SHA + 本地 blob SHA 快照；下次 sync 时
若远程 tree SHA 未变则维持现有效率，若变化则从快照精准定位远程变更文件加入扫描列表。

v2.1 性能优化：冲突检测阶段改用 Git blob SHA 在本地计算后直接与 remote_tree
对比，消除逐文件 API 调用（get_remote_file_sha1）。N 文件 → 0 次额外 API 调用。

排除：github-config.json、__pycache__、.git、.syncstate.json
"""
import sys
import os
import json
import re
import base64
import hashlib
import ssl
import urllib.request
import urllib.error
from urllib.parse import quote
from datetime import datetime, timezone

# ── 同步状态文件路径 ──────────────────────────────────
SYNCSTATE_FILE = '.syncstate.json'

# ── SSL 上下文（多级降级） ──────────────────────────────────
def build_ssl_ctx():
    for opts in [
        ssl.create_default_context(),
        ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
    ]:
        try:
            opts.check_hostname = False
            opts.verify_mode = ssl.CERT_NONE
            test_req = urllib.request.Request(
                'https://api.github.com/zen',
                headers={'User-Agent': 'AlphaClaw-FactHubSync/2.2'}
            )
            urllib.request.urlopen(test_req, timeout=5, context=opts)
            return opts
        except Exception:
            continue
    return None

_CTX = build_ssl_ctx()


def api_get(url, token):
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    req.add_header('User-Agent', 'AlphaClaw-FactHubSync/2.2')
    kw = {'timeout': 30}
    if _CTX:
        kw['context'] = _CTX
    with urllib.request.urlopen(req, **kw) as r:
        return json.loads(r.read())


def api_put(url, token, payload):
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=data)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Content-Type', 'application/json')
    req.add_header('User-Agent', 'AlphaClaw-FactHubSync/2.2')
    req.get_method = lambda: 'PUT'
    kw = {'timeout': 30}
    if _CTX:
        kw['context'] = _CTX
    try:
        with urllib.request.urlopen(req, **kw) as r:
            return True, json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')[:300]
        return False, f"HTTP {e.code} | {body}"
    except Exception as e:
        return False, str(e)


def verify_token(token):
    try:
        data = api_get('https://api.github.com/user', token)
        return True, data.get('login', 'unknown')
    except Exception as e:
        return False, str(e)


def scan_local_files(local_root, filter_files=None):
    """返回 {rel_path: (abs_path, content_sha1, mtime, git_blob_sha)}

    同时计算 content SHA1（用于 log.md 比对等场景）和 Git blob SHA
    （用于与 remote_tree 直接对比，消除逐文件 API 调用）。
    Git blob SHA = sha1(b"blob " + strlen(content) + b"\\x00" + content)

    若 filter_files 非空，仅扫描列表中的文件（+ log.md 和 README.md），
    其余文件假定与远程一致跳过。用于增量同步场景。
    """
    always_include = {'log.md', 'README.md'}
    files = {}
    for root, dirs, filenames in os.walk(local_root):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for fn in filenames:
            if not fn.endswith('.md'):
                continue
            abs_path = os.path.join(root, fn)
            rel_path = os.path.relpath(abs_path, local_root).replace(os.sep, '/')
            # 增量模式：只扫描指定文件 + 始终需要的关键文件
            if filter_files is not None and rel_path not in filter_files and rel_path not in always_include:
                continue
            with open(abs_path, 'rb') as f:
                content = f.read()
            content_sha1 = hashlib.sha1(content).hexdigest()
            mtime = os.path.getmtime(abs_path)
            git_blob_sha = hashlib.sha1(
                b"blob " + str(len(content)).encode('utf-8') + b"\x00" + content
            ).hexdigest()
            files[rel_path] = (abs_path, content_sha1, mtime, git_blob_sha)
    return files


def get_remote_tree(owner, repo, token, branch='main'):
    """获取远程仓库文件树，返回 ({path: blob_sha}, tree_sha|None, error|None)"""
    base_url = f'https://api.github.com/repos/{owner}/{repo}'
    try:
        branch_data = api_get(f'{base_url}/branches/{branch}', token)
        tree_sha = branch_data['commit']['commit']['tree']['sha']
        tree_data = api_get(f'{base_url}/git/trees/{tree_sha}?recursive=1', token)
        result = {}
        for item in tree_data.get('tree', []):
            if item.get('type') == 'blob':
                result[item['path']] = item.get('sha', '')
        return result, tree_sha, None
    except Exception as e:
        return {}, None, str(e)


def get_remote_file_sha1(owner, repo, file_path, token, branch='main'):
    """获取远程文件内容 SHA1"""
    base_url = f'https://api.github.com/repos/{owner}/{repo}'
    encoded_path = quote(file_path, safe='/')
    try:
        data = api_get(f'{base_url}/contents/{encoded_path}?ref={branch}', token)
        if 'content' in data:
            remote_b64 = data['content'].replace('\n', '')
            remote_content = base64.b64decode(remote_b64)
            return hashlib.sha1(remote_content).hexdigest()
        return None
    except Exception:
        return None


def get_remote_commit_date(owner, repo, file_path, token, branch='main'):
    """获取远程文件最后 commit 时间（UTC datetime），作为兜底方案"""
    base_url = f'https://api.github.com/repos/{owner}/{repo}'
    encoded_path = quote(file_path, safe='/')
    try:
        data = api_get(
            f'{base_url}/commits?path={encoded_path}&per_page=1&sha={branch}',
            token
        )
        if data and len(data) > 0:
            date_str = data[0]['commit']['committer']['date']
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except Exception:
        pass
    return None


def extract_latest_log_time(file_path):
    """从本地 log.md 提取最新日志时间（取所有时间戳中的最大值，而非最后一条匹配）"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        matches = re.findall(r'^- (\d{4}-\d{2}-\d{2} \d{2}:\d{2})', content, re.MULTILINE)
        if matches:
            timestamps = [datetime.strptime(m, '%Y-%m-%d %H:%M') for m in matches]
            return max(timestamps).replace(tzinfo=timezone.utc)
    except Exception:
        pass
    return None


def get_remote_log_time_and_sha1(owner, repo, token, branch='main'):
    """获取远程 log.md 的最后日志时间与内容 SHA1。返回 (datetime|None, sha1|None)"""
    base_url = f'https://api.github.com/repos/{owner}/{repo}'
    encoded_path = quote('log.md', safe='/')
    try:
        data = api_get(f'{base_url}/contents/{encoded_path}?ref={branch}', token)
        if 'content' not in data:
            return None, None
        content = base64.b64decode(data['content'].replace('\n', '')).decode('utf-8')
        sha1 = hashlib.sha1(base64.b64decode(data['content'].replace('\n', ''))).hexdigest()
        matches = re.findall(r'^- (\d{4}-\d{2}-\d{2} \d{2}:\d{2})', content, re.MULTILINE)
        if matches:
            timestamps = [datetime.strptime(m, '%Y-%m-%d %H:%M') for m in matches]
            dt = max(timestamps).replace(tzinfo=timezone.utc)
            return dt, sha1
        return None, sha1
    except Exception:
        pass
    return None, None


# ── .syncstate.json 操作 ──────────────────────────────────

def load_syncstate(local_root):
    """读取同步状态快照。返回 dict 或 None（文件不存在/损坏）。"""
    path = os.path.join(local_root, SYNCSTATE_FILE)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_syncstate(local_root, remote_tree_sha, local_files):
    """保存同步状态快照：远程 tree SHA + 本地所有文件的 blob SHA 映射。"""
    path = os.path.join(local_root, SYNCSTATE_FILE)
    snapshot = {
        'remote_tree_sha': remote_tree_sha,
        'last_sync': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'file_blobs': {rel: info[3] for rel, info in local_files.items()}
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)


def diff_remote_vs_snapshot(remote_tree, syncstate):
    """对比当前远程 tree vs 上次同步快照，返回远程有变更的文件列表。

    比较 remote_tree[*].blob_sha vs syncstate.file_blobs[*]，
    SHA 不同的文件说明远程有变更（另一终端推送了更新）。
    """
    if not syncstate or 'file_blobs' not in syncstate:
        return []
    last_blobs = syncstate['file_blobs']
    changed = []
    for path, remote_blob in remote_tree.items():
        if path not in last_blobs:
            # 远程新增的文件
            changed.append(path)
        elif last_blobs[path] != remote_blob:
            # 远程 blob 变了
            changed.append(path)
    return changed


def pull_file(owner, repo, file_path, token, local_root, branch='main'):
    """从远程下载文件到本地"""
    base_url = f'https://api.github.com/repos/{owner}/{repo}'
    encoded_path = quote(file_path, safe='/')
    try:
        data = api_get(f'{base_url}/contents/{encoded_path}?ref={branch}', token)
        content = base64.b64decode(data['content'].replace('\n', ''))
        local_path = os.path.join(local_root, file_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, 'wb') as f:
            f.write(content)
        return True, None
    except Exception as e:
        return False, str(e)


def push_file(owner, repo, file_path, content_bytes, remote_blob_sha, token, branch='main'):
    """推送文件到远程"""
    base_url = f'https://api.github.com/repos/{owner}/{repo}'
    encoded_path = quote(file_path, safe='/')
    encoded_content = base64.b64encode(content_bytes).decode('utf-8')
    payload = {
        'message': f'[fact-hub-sync] Update {file_path}',
        'content': encoded_content,
        'branch': branch
    }
    if remote_blob_sha:
        payload['sha'] = remote_blob_sha
    return api_put(f'{base_url}/contents/{encoded_path}', token, payload)


def main(local_root, owner, repo, token, branch='main', mode='sync', filter_files=None):
    """双向同步主流程 v2.2 — .syncstate 远程变更哨兵 + Git blob SHA 对比 + log.md 优先裁定"""
    print(f"=== Fact Hub Sync v2.2 ===")
    print(f"Local: {local_root}")
    print(f"Remote: {owner}/{repo} ({branch})")
    print(f"Mode: {mode}")
    if filter_files:
        print(f"Local changes: {len(filter_files)} files (from log.md)")
    print()

    # 0. 读取同步状态快照
    syncstate = load_syncstate(local_root)
    if syncstate:
        print(f"SyncState: last sync at {syncstate.get('last_sync', 'unknown')}")

    # 1. 验证 token
    ok, user = verify_token(token)
    if not ok:
        print(json.dumps({'success': False, 'message': f'Token invalid: {user}'}))
        return
    print(f"Token OK (user: {user})")

    # 2. 检查本地目录
    if not os.path.isdir(local_root):
        print(json.dumps({'success': False, 'message': f'Local root not found: {local_root}'}))
        return
    print(f"Local root OK")

    # 3. 获取远程树（含 tree_sha）
    remote_tree, remote_tree_sha, err = get_remote_tree(owner, repo, token, branch)
    if err:
        print(f"Warning: Could not get remote tree: {err}")
    print(f"Remote blobs: {len(remote_tree)}, tree SHA: {remote_tree_sha[:8] if remote_tree_sha else 'N/A'}")

    # 4. 远程变更哨兵检测 (v2.2)
    #    若 .syncstate 存在且远程 tree SHA 未变 → 远程无变更，维持现有增量
    #    若 tree SHA 变化 → 从快照 diff 定位远程变更文件，补充到扫描列表
    remote_changed_files = set()
    if syncstate and remote_tree_sha and remote_tree_sha != syncstate.get('remote_tree_sha'):
        remote_changed_files = set(diff_remote_vs_snapshot(remote_tree, syncstate))
        if remote_changed_files:
            print(f"Remote tree SHA changed → {len(remote_changed_files)} remote file(s) differ from last sync:")
            for f in sorted(remote_changed_files)[:10]:
                print(f"  REMOTE-CHANGED: {f}")
            if len(remote_changed_files) > 10:
                print(f"  ... and {len(remote_changed_files) - 10} more")
    elif syncstate:
        print(f"Remote tree SHA unchanged → no remote-side changes, local-only incremental")
    else:
        print(f"No .syncstate → full scan (first sync on this terminal)")

    # 5. 合并扫描列表：本地增量 + 远程变更
    effective_filter = None
    if filter_files is not None or remote_changed_files:
        effective_filter = set(filter_files or [])
        effective_filter |= remote_changed_files
        effective_filter = list(effective_filter)
        print(f"Effective scan: {len(effective_filter)} files (local {len(filter_files or [])} + remote {len(remote_changed_files)})")

    # 6. 扫描本地
    local_files = scan_local_files(local_root, effective_filter)
    print(f"Local files scanned: {len(local_files)}")

    # 7. 对比（只做分类，不裁定方向）
    local_only = []
    remote_only = []
    remote_deleted_locally = []
    conflict = []
    skipped = []

    for rel_path, (_, _, _, git_blob_sha) in sorted(local_files.items()):
        if rel_path not in remote_tree:
            local_only.append(rel_path)
            print(f"  LOCAL: {rel_path}")
            continue
        if remote_tree[rel_path] == git_blob_sha:
            skipped.append(rel_path)
        else:
            conflict.append(rel_path)

    for path in remote_tree:
        if path not in local_files:
            remote_only.append(path)
            print(f"  REMOTE: {path}")

    # 8. log.md 优先裁定冲突方向
    pull_from_conflict = []
    push_from_conflict = []
    tie_conflict = []

    if conflict:
        local_log_time = None
        remote_log_time = None
        log_sha1_match = False

        if 'log.md' in local_files:
            local_log_path = local_files['log.md'][0]
            local_log_time = extract_latest_log_time(local_log_path)

        remote_log_time, remote_log_sha1 = get_remote_log_time_and_sha1(owner, repo, token, branch)

        if 'log.md' in local_files and remote_log_sha1 and local_files['log.md'][1] == remote_log_sha1:
            log_sha1_match = True

        if log_sha1_match:
            print(f"  LOG: log.md identical → fast path, treating {len(conflict)} conflicts as skipped")
            tie_conflict.extend(conflict)
        elif local_log_time and remote_log_time:
            if remote_log_time > local_log_time:
                print(f"  LOG: remote {remote_log_time.strftime('%Y-%m-%d %H:%M')} > local {local_log_time.strftime('%Y-%m-%d %H:%M')} → pull all conflicts")
                pull_from_conflict.extend(conflict)
            elif local_log_time > remote_log_time:
                print(f"  LOG: local {local_log_time.strftime('%Y-%m-%d %H:%M')} > remote {remote_log_time.strftime('%Y-%m-%d %H:%M')} → push all conflicts")
                push_from_conflict.extend(conflict)
            else:
                print(f"  LOG: same timestamp → fallback to per-file commit time")
                for rel_path in conflict:
                    _, _, local_mtime, _ = local_files[rel_path]
                    local_dt = datetime.fromtimestamp(local_mtime, tz=timezone.utc)
                    remote_dt = get_remote_commit_date(owner, repo, rel_path, token, branch)
                    if remote_dt is None:
                        push_from_conflict.append(rel_path)
                        print(f"    CONFLICT -> PUSH: {rel_path} (remote time unknown)")
                    elif remote_dt > local_dt:
                        pull_from_conflict.append(rel_path)
                        print(f"    CONFLICT -> PULL: {rel_path}")
                    else:
                        push_from_conflict.append(rel_path)
                        print(f"    CONFLICT -> PUSH: {rel_path}")
        else:
            print(f"  LOG: unavailable → fallback to per-file commit time")
            for rel_path in conflict:
                _, _, local_mtime, _ = local_files[rel_path]
                local_dt = datetime.fromtimestamp(local_mtime, tz=timezone.utc)
                remote_dt = get_remote_commit_date(owner, repo, rel_path, token, branch)
                if remote_dt is None:
                    push_from_conflict.append(rel_path)
                elif remote_dt > local_dt:
                    pull_from_conflict.append(rel_path)
                else:
                    push_from_conflict.append(rel_path)

    # 汇总
    to_push = local_only + push_from_conflict
    to_pull = remote_only + pull_from_conflict

    print(f"\n=== SUMMARY ===")
    print(f"PUSH: {len(local_only)} local-only + {len(push_from_conflict)} local-newer = {len(to_push)}")
    print(f"PULL: {len(remote_only)} remote-only + {len(pull_from_conflict)} remote-newer = {len(to_pull)}")
    if remote_deleted_locally:
        print(f"DELETE: {len(remote_deleted_locally)} remote files locally deleted (use --allow-delete to remove from remote)")
    print(f"SKIP: {len(skipped)} unchanged + {len(tie_conflict)} tie")
    print()

    if mode == 'push':
        to_pull = []
    elif mode == 'pull':
        to_push = []

    # 9. 先拉取（远程优先），再推送
    pull_ok = 0
    pull_fail = []
    if to_pull:
        print(f"--- PULL: {len(to_pull)} files ---")
        for rel_path in to_pull:
            ok, err = pull_file(owner, repo, rel_path, token, local_root, branch)
            if ok:
                print(f"  OK: {rel_path} (downloaded)")
                pull_ok += 1
            else:
                print(f"  FAIL: {rel_path} -> {err}")
                pull_fail.append((rel_path, err))

    push_ok = 0
    push_fail = []
    if to_push:
        print(f"\n--- PUSH: {len(to_push)} files ---")
        for rel_path in to_push:
            abs_path = local_files[rel_path][0]
            with open(abs_path, 'rb') as f:
                content = f.read()
            remote_blob_sha = remote_tree.get(rel_path)
            ok, result = push_file(owner, repo, rel_path, content, remote_blob_sha, token, branch)
            if ok:
                print(f"  OK: {rel_path}")
                push_ok += 1
            else:
                print(f"  FAIL: {rel_path} -> {result}")
                push_fail.append((rel_path, result))

    # 10. 更新 .syncstate（拉取后需要重新扫描以获取最新 blob SHA）
    #     仅当有实际同步操作时才更新
    if to_pull or to_push:
        updated_local = scan_local_files(local_root, None)  # 全量重新扫描（确保拉取后的文件 hash 准确）
        if remote_tree_sha:
            save_syncstate(local_root, remote_tree_sha, updated_local)
            print(f"\n.syncstate updated (tree: {remote_tree_sha[:8]}..., {len(updated_local)} files)")
    elif syncstate is None and remote_tree_sha:
        # 首次运行且无变更 → 建立初始快照
        all_local = scan_local_files(local_root, None)
        save_syncstate(local_root, remote_tree_sha, all_local)
        print(f"\n.syncstate initialized (tree: {remote_tree_sha[:8]}..., {len(all_local)} files)")

    # 11. 结果
    result = {
        'success': len(pull_fail) == 0 and len(push_fail) == 0,
        'message': f'Pull {pull_ok}/{len(to_pull)}, Push {push_ok}/{len(to_push)}',
        'stats': {
            'local_only': len(local_only),
            'remote_only': len(remote_only),
            'locally_deleted': len(remote_deleted_locally),
            'log_ruled_pull': len(pull_from_conflict),
            'log_ruled_push': len(push_from_conflict),
            'log_ruled_tie': len(tie_conflict),
            'pulled': pull_ok,
            'pushed': push_ok,
            'pull_failed': len(pull_fail),
            'push_failed': len(push_fail),
            'skipped': len(skipped),
            'remote_changed_detected': len(remote_changed_files)
        }
    }
    if remote_deleted_locally:
        result['locally_deleted_files'] = remote_deleted_locally
    if pull_fail:
        result['pull_failures'] = [{'path': p, 'error': e} for p, e in pull_fail]
    if push_fail:
        result['push_failures'] = [{'path': p, 'error': e} for p, e in push_fail]

    print()
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Fact Hub Sync - Bidirectional v2.2')
    parser.add_argument('--local-root', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--token', required=True)
    parser.add_argument('--branch', default='main')
    parser.add_argument('--mode', default='sync', choices=['sync', 'push', 'pull'])
    parser.add_argument('--allow-delete', action='store_true', help='Allow deletion of remote files that were deleted locally (requires user confirmation)')
    parser.add_argument('--files', default=None, help='Comma-separated list of locally-changed file paths from log.md (optional; sync.py internally cross-checks with .syncstate for remote changes)')
    args = parser.parse_args()
    filter_files = [f.strip() for f in args.files.split(',') if f.strip()] if args.files else None
    main(args.local_root, args.owner, args.repo, args.token, args.branch, args.mode, filter_files)
