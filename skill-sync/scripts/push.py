""" push.py - 推送 Skill 到 GitHub 支持 git clone 路径（首选）和 GitHub API 路径（备选） """
import sys, os, json, base64, time, subprocess, urllib.request, ssl

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
        pre_req = urllib.request.Request(
            'https://api.github.com/user',
            headers={'Authorization': f'Bearer {token}'}
        )
        with urllib.request.urlopen(pre_req, timeout=10) as r:
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

def _build_ctx():
    """构建 SSL 上下文，优先 TLSv1.3，降级到不验证"""
    for opts in [
        ssl.create_default_context(),
        ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
    ]:
        try:
            opts.check_hostname = False
            opts.verify_mode = ssl.CERT_NONE
            test_req = urllib.request.Request(
                'https://api.github.com/zen',
                headers={'User-Agent': 'AlphaClaw-SkillSync/1.0'}
            )
            urllib.request.urlopen(test_req, timeout=5, context=opts)
            return opts
        except Exception:
            continue
    return None


def _api_get(url, token, timeout=15, ctx=None):
    """GET 请求"""
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    req.add_header('User-Agent', 'AlphaClaw-SkillSync/1.0')
    kw = {'timeout': timeout}
    if ctx:
        kw['context'] = ctx
    with urllib.request.urlopen(req, **kw) as r:
        return json.loads(r.read())


def push_api(skill_name, owner, repo, token, branch='main'):
    """GitHub API 路径推送（直接 PUT，每个文件独立检测变化）"""
    base_url = f'https://api.github.com/repos/{owner}/{repo}'
    skill_src = os.path.expanduser(f'~/.alphaclaw/skills/{skill_name}')
    if not os.path.exists(skill_src):
        return False, f'Skill source not found: {skill_src}'

    ctx = _build_ctx()

    # 收集所有文件（同时计算本地内容 hash）
    import hashlib
    files = []
    for root, dirs, filenames in os.walk(skill_src):
        if 'github-config.json' in filenames:
            filenames.remove('github-config.json')
        for fn in filenames:
            full_path = os.path.join(root, fn)
            rel_path = os.path.relpath(full_path, skill_src).replace(os.sep, '/')
            with open(full_path, 'rb') as f:
                content = f.read()
            local_hash = hashlib.sha1(content).hexdigest()
            files.append((rel_path, content, local_hash))

    if not files:
        return False, 'No files to push'

    pushed = 0
    skipped = 0
    errors = []

    for rel_path, content, local_hash in files:
        remote_path = f'{skill_name}/{rel_path}'
        file_url = f'{base_url}/contents/{remote_path}'

        try:
            # 获取远程文件 SHA（如果存在）
            remote_sha = None
            try:
                dir_url = f'{base_url}/contents/{skill_name}?ref={branch}'
                tree = _api_get(dir_url, token, ctx=ctx)
                for item in tree:
                    if item['path'] == rel_path and item['sha']:
                        remote_sha = item['sha']
                        break
            except Exception:
                pass

            # 计算远程内容 hash 确认是否真的变化
            if remote_sha:
                try:
                    remote_data = _api_get(file_url + f'?ref={branch}', token, ctx=ctx)
                    remote_b64 = remote_data.get('content', '').encode()
                    import base64 as b64mod
                    remote_content = b64mod.b64decode(remote_b64)
                    remote_hash = hashlib.sha1(remote_content).hexdigest()
                    if remote_hash == local_hash:
                        skipped += 1
                        continue
                except Exception:
                    pass

            # 上传（create 或 update）
            encoded = base64.b64encode(content).decode('utf-8')
            payload = {
                'message': f'Update {skill_name}/{rel_path}',
                'content': encoded,
                'branch': branch
            }
            if remote_sha:
                payload['sha'] = remote_sha

            put_data = json.dumps(payload).encode('utf-8')
            put_req = urllib.request.Request(file_url, data=put_data)
            put_req.add_header('Authorization', f'Bearer {token}')
            put_req.add_header('Content-Type', 'application/json')
            put_req.add_header('User-Agent', 'AlphaClaw-SkillSync/1.0')
            put_req.get_method = lambda: 'PUT'
            kw = {'timeout': 30}
            if ctx:
                kw['context'] = ctx
            with urllib.request.urlopen(put_req, **kw) as r:
                json.loads(r.read())
            pushed += 1

        except Exception as e:
            errors.append(f'{rel_path}: {e}')

    if errors and pushed == 0:
        return False, f'All files failed: {errors[:2]}'

    msg = f'Pushed {pushed} files, skipped {skipped} unchanged'
    if errors:
        msg += f', {len(errors)} errors'
    return True, msg

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
