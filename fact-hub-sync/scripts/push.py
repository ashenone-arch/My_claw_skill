""" push.py - 将本地 Fact Hub 增量推送到 GitHub 仓库

增量策略：SHA1 hash 对比，仅上传有变化的文件。
排除：github-config.json、__pycache__、.git
"""
import sys
import os
import json
import base64
import hashlib
import ssl
import urllib.request
from urllib.parse import quote

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
                headers={'User-Agent': 'AlphaClaw-FactHubSync/1.0'}
            )
            urllib.request.urlopen(test_req, timeout=5, context=opts)
            return opts
        except Exception:
            continue
    return None

_CTX = build_ssl_ctx()


def api_get(url, token):
    """GitHub API GET"""
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    req.add_header('User-Agent', 'AlphaClaw-FactHubSync/1.0')
    kw = {'timeout': 30}
    if _CTX:
        kw['context'] = _CTX
    with urllib.request.urlopen(req, **kw) as r:
        return json.loads(r.read())


def api_put(url, token, payload):
    """GitHub API PUT（创建/更新文件）"""
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=data)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Content-Type', 'application/json')
    req.add_header('User-Agent', 'AlphaClaw-FactHubSync/1.0')
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
    """验证 token 有效性"""
    try:
        data = api_get('https://api.github.com/user', token)
        return True, data.get('login', 'unknown')
    except Exception as e:
        return False, str(e)


def scan_local_files(local_root):
    """递归扫描本地 Fact Hub 下所有 .md 文件，返回 {rel_path: (abs_path, sha1)}"""
    files = {}
    for root, dirs, filenames in os.walk(local_root):
        # 跳过隐藏目录和 __pycache__
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for fn in filenames:
            if not fn.endswith('.md'):
                continue
            abs_path = os.path.join(root, fn)
            rel_path = os.path.relpath(abs_path, local_root).replace(os.sep, '/')
            with open(abs_path, 'rb') as f:
                content = f.read()
            sha1 = hashlib.sha1(content).hexdigest()
            files[rel_path] = (abs_path, sha1)
    return files


def get_remote_tree(owner, repo, token, branch='main'):
    """获取远程仓库文件树，返回 {path: sha}"""
    base_url = f'https://api.github.com/repos/{owner}/{repo}'
    try:
        # 获取分支最新 commit 的 tree SHA
        branch_data = api_get(f'{base_url}/branches/{branch}', token)
        tree_sha = branch_data['commit']['commit']['tree']['sha']
        tree_data = api_get(
            f'{base_url}/git/trees/{tree_sha}?recursive=1',
            token
        )
        result = {}
        for item in tree_data.get('tree', []):
            if item.get('type') == 'blob':
                result[item['path']] = item.get('sha', '')
        return result, None
    except Exception as e:
        return {}, str(e)


def get_remote_file_sha1(owner, repo, file_path, token, branch='main'):
    """获取远程单个文件的 SHA1（base64 解码后的内容 hash）"""
    base_url = f'https://api.github.com/repos/{owner}/{repo}'
    encoded_path = quote(file_path, safe='/')
    try:
        data = api_get(
            f'{base_url}/contents/{encoded_path}?ref={branch}',
            token
        )
        if 'content' in data:
            remote_b64 = data['content'].replace('\n', '')
            remote_content = base64.b64decode(remote_b64)
            return hashlib.sha1(remote_content).hexdigest()
        return None
    except Exception:
        return None


def push_file(owner, repo, file_path, content_bytes, remote_sha, token, branch='main'):
    """推送单个文件到 GitHub"""
    base_url = f'https://api.github.com/repos/{owner}/{repo}'
    encoded_path = quote(file_path, safe='/')
    encoded_content = base64.b64encode(content_bytes).decode('utf-8')

    payload = {
        'message': f'[fact-hub-sync] Update {file_path}',
        'content': encoded_content,
        'branch': branch
    }

    # 如果远程已有该文件的 blob SHA（不是内容 hash），用于冲突检测
    if remote_sha:
        payload['sha'] = remote_sha

    return api_put(f'{base_url}/contents/{encoded_path}', token, payload)


def main(local_root, owner, repo, token, branch='main'):
    """主流程"""
    print(f"=== Fact Hub Sync ===")
    print(f"Local: {local_root}")
    print(f"Remote: {owner}/{repo} ({branch})")
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

    # 3. 扫描本地文件
    local_files = scan_local_files(local_root)
    print(f"Local files: {len(local_files)}")

    # 4. 获取远程文件树（tree SHA）
    remote_tree, err = get_remote_tree(owner, repo, token, branch)
    if err:
        print(f"Warning: Could not get remote tree: {err}")
    print(f"Remote blobs: {len(remote_tree)}")

    # 5. 对比
    new_files = []       # 本地有，远程无
    changed_files = []   # 本地有，远程有，但内容不同
    skipped = []         # 内容相同，跳过
    remote_only = []     # 远程有，本地无

    for rel_path, (abs_path, local_sha1) in sorted(local_files.items()):
        if rel_path in remote_tree:
            remote_sha1 = get_remote_file_sha1(owner, repo, rel_path, token, branch)
            if remote_sha1 == local_sha1:
                skipped.append(rel_path)
            else:
                changed_files.append(rel_path)
                print(f"  CHANGED: {rel_path}")
        else:
            new_files.append(rel_path)
            print(f"  NEW: {rel_path}")

    for path in remote_tree:
        if path not in local_files:
            remote_only.append(path)

    print(f"\nSummary: {len(new_files)} new, {len(changed_files)} changed, "
          f"{len(skipped)} skipped, {len(remote_only)} remote-only")
    print()

    # 6. 推送
    to_push = new_files + changed_files
    if not to_push:
        print(json.dumps({
            'success': True,
            'message': 'All files up-to-date, nothing to push',
            'stats': {'new': 0, 'changed': 0, 'skipped': len(skipped)}
        }))
        return

    print(f"Pushing {len(to_push)} files...")
    success_count = 0
    fail_list = []

    for rel_path in to_push:
        abs_path = os.path.join(local_root, rel_path.replace('/', os.sep))
        with open(abs_path, 'rb') as f:
            content = f.read()

        remote_blob_sha = remote_tree.get(rel_path)  # tree 中的 blob SHA（用于冲突检测）
        ok, result = push_file(owner, repo, rel_path, content, remote_blob_sha, token, branch)

        if ok:
            print(f"  OK: {rel_path}")
            success_count += 1
        else:
            print(f"  FAIL: {rel_path} -> {result}")
            fail_list.append((rel_path, result))

    result = {
        'success': len(fail_list) == 0,
        'message': f'Pushed {success_count}/{len(to_push)} files',
        'stats': {
            'new': len(new_files),
            'changed': len(changed_files),
            'pushed': success_count,
            'failed': len(fail_list),
            'skipped': len(skipped),
            'remote_only': len(remote_only)
        }
    }
    if fail_list:
        result['failures'] = [{'path': p, 'error': e} for p, e in fail_list]

    print()
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Fact Hub Sync - Push')
    parser.add_argument('--local-root', required=True, help='Local Fact Hub root directory')
    parser.add_argument('--owner', required=True, help='GitHub repo owner')
    parser.add_argument('--repo', required=True, help='GitHub repo name')
    parser.add_argument('--token', required=True, help='GitHub personal access token')
    parser.add_argument('--branch', default='main', help='Target branch')
    args = parser.parse_args()

    main(args.local_root, args.owner, args.repo, args.token, args.branch)
