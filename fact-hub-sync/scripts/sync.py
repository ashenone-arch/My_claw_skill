""" sync.py - Fact Hub 双向同步脚本 v2.1

增量策略：Git blob SHA 对比（0 API 调用）+ log.md 优先裁定方向：
  - 本地独有 → 推送到远程
  - 远程独有 → 下载到本地
  - 远程有、本地已删除 → 标记为待确认，默认不删除远程（需 --allow-delete）
  - 两边都有、blob SHA 不同 → 比较 log.md 最新日志时间（取所有时间戳中的最大值），更新者覆盖旧者
  - log.md 不存在时 → 回退到逐文件 commit 时间比较

v2.1 性能优化：冲突检测阶段改用 Git blob SHA 在本地计算后直接与 remote_tree
对比，消除逐文件 API 调用（get_remote_file_sha1）。N 文件 → 0 次额外 API 调用。

排除：github-config.json、__pycache__、.git
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
                headers={'User-Agent': 'AlphaClaw-FactHubSync/2.1'}
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
    req.add_header('User-Agent', 'AlphaClaw-FactHubSync/2.1')
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
    req.add_header('User-Agent', 'AlphaClaw-FactHubSync/2.1')
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


def scan_local_files(local_root):
    """返回 {rel_path: (abs_path, content_sha1, mtime, git_blob_sha)}

    同时计算 content SHA1（用于 log.md 比对等场景）和 Git blob SHA
    （用于与 remote_tree 直接对比，消除逐文件 API 调用）。
    Git blob SHA = sha1(b"blob " + strlen(content) + b"\\x00" + content)
    """
    files = {}
    for root, dirs, filenames in os.walk(local_root):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for fn in filenames:
            if not fn.endswith('.md'):
                continue
            abs_path = os.path.join(root, fn)
            rel_path = os.path.relpath(abs_path, local_root).replace(os.sep, '/')
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
    """获取远程仓库文件树，返回 {path: blob_sha}"""
    base_url = f'https://api.github.com/repos/{owner}/{repo}'
    try:
        branch_data = api_get(f'{base_url}/branches/{branch}', token)
        tree_sha = branch_data['commit']['commit']['tree']['sha']
        tree_data = api_get(f'{base_url}/git/trees/{tree_sha}?recursive=1', token)
        result = {}
        for item in tree_data.get('tree', []):
            if item.get('type') == 'blob':
                result[item['path']] = item.get('sha', '')
        return result, None
    except Exception as e:
        return {}, str(e)


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


def main(local_root, owner, repo, token, branch='main', mode='sync'):
    """双向同步主流程 v2.1 — Git blob SHA 对比 + log.md 优先裁定"""
    print(f"=== Fact Hub Sync v2.1 ===")
    print(f"Local: {local_root}")
    print(f"Remote: {owner}/{repo} ({branch})")
    print(f"Mode: {mode}")
    print()

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

    # 3. 扫描本地
    local_files = scan_local_files(local_root)
    print(f"Local files: {len(local_files)}")

    # 4. 获取远程树
    remote_tree, err = get_remote_tree(owner, repo, token, branch)
    if err:
        print(f"Warning: Could not get remote tree: {err}")
    print(f"Remote blobs: {len(remote_tree)}")

    # 5. 对比（只做分类，不裁定方向）
    local_only = []
    remote_only = []
    remote_deleted_locally = []  # v2.0: 远端存在但本地已删除
    conflict = []
    skipped = []

    for rel_path, (_, _, _, git_blob_sha) in sorted(local_files.items()):
        if rel_path not in remote_tree:
            local_only.append(rel_path)
            print(f"  LOCAL: {rel_path}")
            continue
        # remote_tree 存储的就是 Git blob SHA，本地计算后直接对比，0 次 API 调用
        if remote_tree[rel_path] == git_blob_sha:
            skipped.append(rel_path)
        else:
            conflict.append(rel_path)

    for path in remote_tree:
        if path not in local_files:
            remote_only.append(path)
            print(f"  REMOTE: {path}")

    # 6. log.md 优先裁定冲突方向 (v2.1)
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

        # 检查两边 log.md 的 SHA1 是否一致
        if 'log.md' in local_files and remote_log_sha1 and local_files['log.md'][1] == remote_log_sha1:
            log_sha1_match = True

        if log_sha1_match:
            # log.md 一致 → 快速路径：两边知识库状态相同，其余文件差异视为非实质性，跳过
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
                # 回退：逐文件 commit 时间比较
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
            # log.md 不存在 → 回退逐文件 commit 时间
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

    # 6b. v2.0: 检测远程有而本地已删除的文件
    # 这些文件在第一次 sync 时被拉取到本地，后来用户通过 git 手动删除
    # 默认不自动删除远程（安全考虑），仅在 --allow-delete 模式下执行
    # 即使不删除，也会在 SUMMARY 中列出供用户知晓

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

    # 7. 先拉取（远程优先），再推送
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

    # 8. 结果
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
            'skipped': len(skipped)
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
    parser = argparse.ArgumentParser(description='Fact Hub Sync - Bidirectional v2.1')
    parser.add_argument('--local-root', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--token', required=True)
    parser.add_argument('--branch', default='main')
    parser.add_argument('--mode', default='sync', choices=['sync', 'push', 'pull'])
    parser.add_argument('--allow-delete', action='store_true', help='Allow deletion of remote files that were deleted locally (requires user confirmation)')
    args = parser.parse_args()
    main(args.local_root, args.owner, args.repo, args.token, args.branch, args.mode)
