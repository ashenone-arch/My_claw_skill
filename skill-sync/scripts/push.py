""" push.py - 推送 Skill 到 GitHub 支持 git clone 路径（首选）和 GitHub API 路径（备选） """
import sys, os, json, base64, time, subprocess, urllib.request

def precheck_git():
    try:
        r = subprocess.run(['git', '--version'], capture_output=True, timeout=5)
        if r.returncode != 0:
            return False
        r2 = subprocess.run(['git', 'config', '--global', 'user.email'], capture_output=True, timeout=5)
        return r2.returncode == 0 and len(r2.stdout.strip()) > 0
    except:
        return False

def precheck_api(token):
    try:
        req = urllib.request.Request(
            'https://api.github.com/user',
            headers={'Authorization': f'Bearer {token}'}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except:
        return False

def push_git_clone(skill_name, owner, repo, token, branch='main'):
    """git clone 路径推送"""
    import tempfile, shutil

    tmp = tempfile.mkdtemp(prefix='skill_push_')
    try:
        # 克隆仓库
        clone_url = f'https://{token}@github.com/{owner}/{repo}.git'
        r = subprocess.run(
            ['git', 'clone', '--depth=1', '--branch', branch, clone_url, tmp],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'}
        )
        if r.returncode != 0:
            return False, f'Clone failed: {r.stderr}'

        # 复制 Skill 文件
        skill_src = os.path.expanduser(f'~/.alphaclaw/skills/{skill_name}')
        if not os.path.exists(skill_src):
            return False, f'Skill source not found: {skill_src}'

        skill_dest = os.path.join(tmp, skill_name)
        if os.path.exists(skill_dest):
            shutil.rmtree(skill_dest)
        shutil.copytree(skill_src, skill_dest)

        # 排除敏感文件
        config_file = os.path.join(skill_dest, 'github-config.json')
        if os.path.exists(config_file):
            os.remove(config_file)

        # 提交
        subprocess.run(['git', 'add', '-A'], cwd=tmp, capture_output=True)
        commit_msg = f'Update {skill_name} to v{get_local_version(skill_name)}'
        r = subprocess.run(
            ['git', 'commit', '-m', commit_msg],
            cwd=tmp, capture_output=True, text=True,
            env={**os.environ, 'GIT_TERMINAL_PROMPT': '0',
                 'GIT_AUTHOR_NAME': 'AlphaClaw',
                 'GIT_AUTHOR_EMAIL': 'agent@alphaclaw'}
        )
        if r.returncode != 0 and 'nothing to commit' not in r.stdout:
            return False, f'Commit failed: {r.stdout} {r.stderr}'

        # 推送
        r = subprocess.run(
            ['git', 'push', 'origin', branch],
            cwd=tmp, capture_output=True, text=True, timeout=60,
            env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'}
        )
        if 'main -> main' in r.stdout or r.returncode == 0:
            return True, 'Push successful'
        else:
            # 重试一次
            r = subprocess.run(
                ['git', 'push', 'origin', branch],
                cwd=tmp, capture_output=True, text=True, timeout=60,
                env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'}
            )
            if 'main -> main' in r.stdout or r.returncode == 0:
                return True, 'Push successful (retry)'
            return False, f'Push failed after retry: {r.stdout} {r.stderr}'

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def get_local_version(skill_name):
    skill_file = os.path.expanduser(f'~/.alphaclaw/skills/{skill_name}/SKILL.md')
    try:
        with open(skill_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('version:'):
                    return line.split(':')[1].strip().lstrip('v')
    except:
        pass
    return 'unknown'

def push_api(skill_name, owner, repo, token, branch='main'):
    """GitHub API 路径推送"""
    base_url = f'https://api.github.com/repos/{owner}/{repo}'

    skill_src = os.path.expanduser(f'~/.alphaclaw/skills/{skill_name}')
    if not os.path.exists(skill_src):
        return False, f'Skill source not found: {skill_src}'

    # 收集所有文件
    files = []
    for root, dirs, filenames in os.walk(skill_src):
        # 排除 github-config.json
        if 'github-config.json' in filenames:
            filenames.remove('github-config.json')
        for fn in filenames:
            full_path = os.path.join(root, fn)
            rel_path = os.path.relpath(full_path, skill_src).replace(os.sep, '/')
            with open(full_path, 'rb') as f:
                content = f.read()
            files.append((rel_path, content))

    if not files:
        return False, 'No files to push'

    # 获取当前 commit SHA（用于创建新 commit）
    req = urllib.request.Request(f'{base_url}/git/ref/heads/{branch}')
    req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=15) as r:
        ref_data = json.loads(r.read())
    commit_sha = ref_data['object']['sha']

    # 获取当前 tree SHA
    req = urllib.request.Request(f'{base_url}/git/commits/{commit_sha}')
    req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=15) as r:
        commit_data = json.loads(r.read())
    base_tree_sha = commit_data['tree']['sha']

    # 上传每个文件并获取 blob SHA
    tree_items = []
    for path, content in files:
        # 创建 blob
        blob_data = json.dumps({
            'content': base64.b64encode(content).decode('utf-8'),
            'encoding': 'base64'
        }).encode('utf-8')
        req = urllib.request.Request(f'{base_url}/git/blobs', data=blob_data)
        req.add_header('Authorization', f'Bearer {token}')
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=15) as r:
            blob = json.loads(r.read())
        tree_items.append({
            'path': f'{skill_name}/{path}',
            'mode': '100644',
            'type': 'blob',
            'sha': blob['sha']
        })

    # 创建新 tree
    tree_data = json.dumps({
        'base_tree': base_tree_sha,
        'tree': tree_items
    }).encode('utf-8')
    req = urllib.request.Request(f'{base_url}/git/trees', data=tree_data)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=15) as r:
        new_tree = json.loads(r.read())

    # 创建 commit
    ver = get_local_version(skill_name)
    commit_data = json.dumps({
        'message': f'Update {skill_name} to v{ver}',
        'tree': new_tree['sha'],
        'parents': [commit_sha]
    }).encode('utf-8')
    req = urllib.request.Request(f'{base_url}/git/commits', data=commit_data)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=15) as r:
        new_commit = json.loads(r.read())

    # 更新 ref
    update_data = json.dumps({
        'sha': new_commit['sha'],
        'force': False
    }).encode('utf-8')
    req = urllib.request.Request(f'{base_url}/git/refs/heads/{branch}', data=update_data)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Content-Type', 'application/json')
    req.get_method = lambda: 'PATCH'
    with urllib.request.urlopen(req, timeout=15) as r:
        json.loads(r.read())

    return True, f'Pushed {len(files)} files'

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--skill')
    parser.add_argument('--owner')
    parser.add_argument('--repo')
    parser.add_argument('--token')
    parser.add_argument('--branch', default='main')
    args = parser.parse_args()

    git_ok = precheck_git()
    api_ok = precheck_api(args.token)

    if git_ok:
        success, msg = push_git_clone(args.skill, args.owner, args.repo, args.token, args.branch)
    else:
        success, msg = push_api(args.skill, args.owner, args.repo, args.token, args.branch)

    print(json.dumps({'success': success, 'message': msg}))
