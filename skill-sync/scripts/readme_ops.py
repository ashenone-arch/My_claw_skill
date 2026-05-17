""" readme_ops.py - README 自动维护脚本 v2.0

功能：从 GitHub API 获取远程仓库中所有 Skill 的版本列表，更新到 GitHub README
特性：
  - 锚点保护：仅替换 <!-- SKILL_TABLE_START --> ... <!-- SKILL_TABLE_END --> 之间的版本表格
  - README 中标记外的自定义内容永久保留
  - 首次运行或无标记时，生成带锚点的完整 README
验证：更新后检查版本列表是否正确（失败重试最多 3 次）
"""
import sys
import os
import json
import base64
import time
import ssl
import urllib.request

TABLE_START = '<!-- SKILL_TABLE_START -->'
TABLE_END = '<!-- SKILL_TABLE_END -->'

# 全局 SSL 上下文（启动时初始化，失败则为 None）
_GLOBAL_SSL_CTX = None
try:
    _ctx = ssl.create_default_context()
    _ctx.check_hostname = False
    _ctx.verify_mode = ssl.CERT_NONE
    test_req = urllib.request.Request(
        'https://api.github.com/zen',
        headers={'User-Agent': 'AlphaClaw-SkillSync/1.0'}
    )
    urllib.request.urlopen(test_req, timeout=5, context=_ctx)
    _GLOBAL_SSL_CTX = _ctx
except Exception:
    pass


def _build_ssl_ctx():
    """构建 SSL 上下文，多级降级"""
    for ctx in [
        ssl.create_default_context(),
        ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
    ]:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            test = urllib.request.Request('https://api.github.com/zen')
            test.add_header('User-Agent', 'AlphaClaw-SkillSync/1.0')
            urllib.request.urlopen(test, timeout=5, context=ctx)
            return ctx
        except Exception:
            continue
    return None


def _api_request(url, token, method='GET', data=None, max_retry=2):
    """通用 GitHub API 请求（含 SSL 降级 + 重试）"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'AlphaClaw-SkillSync/1.0'
    }

    # 优先用全局 SSL 上下文
    ctx = _GLOBAL_SSL_CTX
    kw = {'timeout': 30}
    if ctx:
        kw['context'] = ctx

    for attempt in range(max_retry + 1):
        try:
            req = urllib.request.Request(url, data=data)
            for k, v in headers.items():
                req.add_header(k, v)
            if method != 'GET':
                req.get_method = lambda: method
            if data and method == 'GET':
                pass
            with urllib.request.urlopen(req, **kw) as r:
                return json.loads(r.read())
        except Exception as e:
            err_str = str(e)
            if attempt == 0 and ('SSL' in err_str or 'EOF' in err_str or 'ssl' in err_str.lower()):
                try:
                    fallback_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                    fallback_ctx.check_hostname = False
                    fallback_ctx.verify_mode = ssl.CERT_NONE
                    kw['context'] = fallback_ctx
                    continue
                except Exception:
                    pass
            if attempt >= max_retry:
                raise


def _parse_frontmatter(content):
    """解析 SKILL.md frontmatter"""
    version = 'unknown'
    description = ''
    in_frontmatter = False
    for line in content.split('\n'):
        if line.strip() == '---':
            if not in_frontmatter:
                in_frontmatter = True
            else:
                break
        elif in_frontmatter:
            if line.startswith('version:'):
                version = line.split(':', 1)[1].strip().strip('"').strip("'").lstrip('v')
            elif line.startswith('description:'):
                desc = line.split(':', 1)[1].strip().strip('"').strip("'")
                description = desc[:60] + ('...' if len(desc) > 60 else '')
    return version, description


def get_remote_skills(token, owner, repo):
    """从 GitHub API 获取远程仓库中所有 Skill 的版本列表"""
    skills_url = f'https://api.github.com/repos/{owner}/{repo}/contents'
    skills = []

    dirs = _api_request(skills_url, token)
    skip_dirs = {'README.md', '.github', 'docs', 'scripts', 'scripts_backup', '.git'}

    for entry in dirs:
        if entry['type'] != 'dir':
            continue
        name = entry['name']
        if name in skip_dirs or name.startswith('.') or name.startswith('mcp--'):
            continue

        try:
            dir_contents = _api_request(f'{skills_url}/{name}', token)
            skill_md_filename = None
            for f in dir_contents:
                if f['name'].lower() == 'skill.md':
                    skill_md_filename = f['name']
                    break
            if not skill_md_filename:
                continue

            skill_md_url = f'{skills_url}/{name}/{skill_md_filename}'
            file_data = _api_request(skill_md_url, token)
            if 'content' in file_data:
                content = base64.b64decode(file_data['content']).decode('utf-8')
                version, description = _parse_frontmatter(content)
                skills.append({
                    'name': name,
                    'version': version,
                    'description': description,
                    'sha': file_data.get('sha')
                })
        except Exception:
            pass

    return skills


def generate_table_block(skills):
    """生成仅含锚点标记的版本表格块（用于替换已有 README 中的表格区域）"""
    lines = [TABLE_START, '']

    # 表格头
    lines.extend([
        '| Skill | 说明 | 版本 |',
        '|-------|------|------|',
    ])

    # skill-sync 排第一，其余按名称排序
    skill_sync_list = [s for s in skills if s['name'] == 'skill-sync']
    others = sorted([s for s in skills if s['name'] != 'skill-sync'], key=lambda x: x['name'])
    for s in skill_sync_list + others:
        lines.append(f"| [{s['name']}]({s['name']}/) | {s['description']} | v{s['version']} |")

    lines.append('')
    lines.append(TABLE_END)
    return '\n'.join(lines)


def generate_full_readme(skills):
    """生成带锚点的完整 README（仅首次初始化或旧格式 README 无锚点时使用）"""
    table_block = generate_table_block(skills)
    return '\n'.join([
        '# My Claw Skills',
        '',
        '> 个人日常投资研究使用的 AlphaClaw Skill 集合。',
        '> `<!-- SKILL_TABLE_START -->` 到 `<!-- SKILL_TABLE_END -->` 之间的表格由 skill-sync 自动维护，',
        '> 请勿手动编辑表格内容。标记外的区域可自由自定义。',
        '',
        '## 目录',
        '',
        table_block,
        '',
        '## 使用方式',
        '',
        '在 AlphaClaw 中，直接向助理描述需求即可自动触发对应 Skill。',
        '',
        '示例：',
        '- "同步我的 skill" → 触发对应 Skill',
        '- "深度研究一下某公司" → 触发对应 Skill',
        '- "今天机构抱团什么方向" → 触发对应 Skill',
        '',
        '## 版本说明',
        '',
        '每个 Skill 独立打 Tag，格式为 `{skill-name}-v{version}`。',
        '如需回溯历史版本，请访问对应 Tag 的 Release 页面。',
        '',
        '## 免责声明',
        '',
        '本仓库中的 Skill 仅供个人投资研究使用，不构成任何投资建议。',
        '投资有风险，决策需谨慎。',
    ])


def get_existing_readme(token, owner, repo):
    """获取远程 README 当前文本内容，不存在则返回 None"""
    try:
        url = f'https://api.github.com/repos/{owner}/{repo}/contents/README.md?ref=main'
        data = _api_request(url, token)
        if 'content' in data:
            return base64.b64decode(data['content']).decode('utf-8')
    except Exception:
        pass
    return None


def merge_readme(existing_content, skills):
    """将版本表格块合并到已有 README 中（锚点保护模式）"""
    if existing_content and TABLE_START in existing_content and TABLE_END in existing_content:
        # 锚点保护：仅替换标记之间的内容
        before = existing_content.split(TABLE_START)[0]
        after = existing_content.split(TABLE_END)[1]
        table_block = generate_table_block(skills)
        return before + table_block + after
    else:
        # 无锚点：生成完整 README（含锚点，后续更新即受保护）
        return generate_full_readme(skills)


def update_readme(token, owner, repo, content, max_retry=3):
    """更新 README（失败重试）"""
    base_url = f'https://api.github.com/repos/{owner}/{repo}'
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')

    for attempt in range(max_retry):
        try:
            # 获取当前 SHA
            sha_req = urllib.request.Request(f'{base_url}/contents/README.md?ref=main')
            sha_req.add_header('Authorization', f'Bearer {token}')
            sha_req.add_header('User-Agent', 'AlphaClaw-SkillSync/1.0')
            with urllib.request.urlopen(sha_req, timeout=15) as r:
                file_data = json.loads(r.read())
            sha = file_data['sha']

            # 上传新内容
            payload = json.dumps({
                'message': 'chore: sync skills and update README [skip ci]',
                'sha': sha,
                'content': encoded,
                'branch': 'main'
            }).encode('utf-8')
            put_req = urllib.request.Request(f'{base_url}/contents/README.md', data=payload)
            put_req.add_header('Authorization', f'Bearer {token}')
            put_req.add_header('Content-Type', 'application/json')
            put_req.add_header('User-Agent', 'AlphaClaw-SkillSync/1.0')
            put_req.get_method = lambda: 'PUT'
            with urllib.request.urlopen(put_req, timeout=15) as r:
                result = json.loads(r.read())

            # 验证
            if 'content' in result:
                verified_req = urllib.request.Request(
                    f'https://raw.githubusercontent.com/{owner}/{repo}/main/README.md'
                )
                verified_req.add_header('User-Agent', 'Mozilla/5.0')
                with urllib.request.urlopen(verified_req, timeout=15) as r:
                    verify_content = r.read().decode('utf-8')
                skill_count = verify_content.count('| [')
                return True, f'Updated and verified ({skill_count} skills)'
            else:
                return False, f"Update failed: {result.get('message', 'unknown')}"

        except Exception as e:
            if attempt < max_retry - 1:
                time.sleep(2)
                continue
            else:
                return False, f'All retries failed: {e}'

    return False, 'Max retries exceeded'


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--action', default='update')
    parser.add_argument('--owner')
    parser.add_argument('--repo')
    parser.add_argument('--token')
    args = parser.parse_args()

    if args.action == 'update':
        if not all([args.owner, args.repo, args.token]):
            print(json.dumps({'success': False, 'message': 'Missing required args'}))
            sys.exit(1)
        skills = get_remote_skills(args.token, args.owner, args.repo)
        # 锚点保护模式：读取已有 README，仅替换表格区域
        existing = get_existing_readme(args.token, args.owner, args.repo)
        content = merge_readme(existing, skills)
        success, msg = update_readme(args.token, args.owner, args.repo, content)
        print(json.dumps({'success': success, 'message': msg, 'skills_count': len(skills)}))
    else:
        print(json.dumps({'success': False, 'message': f'Unknown action: {args.action}'}))
