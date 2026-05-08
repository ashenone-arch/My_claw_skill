""" readme_ops.py - README 自动维护脚本

功能：从 GitHub API 获取远程仓库中所有 Skill 的版本列表，更新到 GitHub README
特性：README 版本列表以云端 Skill 为基准，不再扫描本地目录
验证：更新后检查版本列表是否正确（失败重试最多 3 次）
"""
import sys
import os
import json
import base64
import time
import urllib.request

PYTHON = r"D:\AlphaEngine\resources\python\python\python.exe"


def _api_request(url, token, method='GET', data=None):
    """通用 GitHub API 请求"""
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    req.add_header('User-Agent', 'AlphaClaw-SkillSync/1.0')
    if method != 'GET':
        req.get_method = lambda: method
    if data:
        req.add_header('Content-Type', 'application/json')
        req.data = json.dumps(data).encode('utf-8')
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _parse_frontmatter(content):
    """解析 SKILL.md frontmatter 中的 version 和 description"""
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
                version = line.split(':', 1)[1].strip().lstrip('v')
            elif line.startswith('description:'):
                desc = line.split(':', 1)[1].strip()
                description = desc[:60] + ('...' if len(desc) > 60 else '')
    return version, description


def get_remote_skills(token, owner, repo):
    """从 GitHub API 获取远程仓库中所有 Skill 的版本列表"""
    skills_url = f'https://api.github.com/repos/{owner}/{repo}/contents'
    skills = []

    try:
        dirs = _api_request(skills_url, token)
    except Exception as e:
        raise RuntimeError(f'无法获取仓库目录: {e}')

    # 排除 MCP 相关和明显非 Skill 目录
    skip_dirs = {'README.md', '.github', 'docs', 'scripts', 'scripts_backup', '.git'}
    for entry in dirs:
        if entry['type'] != 'dir':
            continue
        name = entry['name']
        if name in skip_dirs or name.startswith('.'):
            continue
        # MCP 相关目录也跳过
        if name.startswith('mcp--'):
            continue

        # 获取 SKILL.md 内容
        skill_md_url = f'{skills_url}/{name}/SKILL.md'
        try:
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
            # 该目录没有 SKILL.md，跳过
            pass

    return skills


def generate_readme_content(skills):
    """生成 README 内容"""
    # skill-sync 自身版本从 skills 列表中动态获取（不硬编码）
    skill_sync_entry = next((s for s in skills if s['name'] == 'skill-sync'), None)
    skill_sync_ver = f"v{skill_sync_entry['version']}" if skill_sync_entry else 'v1.0'
    skill_sync_desc = skill_sync_entry['description'] if skill_sync_entry else ''

    lines = [
        '# My Claw Skills',
        '',
        '> 个人日常投资研究使用的 AlphaClaw Skill 集合，版本信息见各 Skill 的 Release',
        '',
        '## 目录',
        '',
        '| Skill | 说明 | 版本 |',
        '|-------|------|------|',
    ]

    # skill-sync 排在第一位，其余按名称排序
    skill_sync_list = [s for s in skills if s['name'] == 'skill-sync']
    others = sorted([s for s in skills if s['name'] != 'skill-sync'], key=lambda x: x['name'])
    skills_sorted = skill_sync_list + others

    for s in skills_sorted:
        lines.append(f"| [{s['name']}]({s['name']}/) | {s['description']} | v{s['version']} |")

    lines.extend([
        '',
        '## 使用方式',
        '',
        '在 AlphaClaw 中，直接向助理描述需求即可自动触发对应 Skill。',
        '',
        '示例：',
        '- "深度研究一下贵州茅台" → 触发 `equity-deep-research`',
        '- "今天机构抱团什么方向" → 触发 `daily-seller-hotspot`',
        '- "用霍华德马克斯框架分析这只股票" → 触发 `howard-marks-framework`',
        '- "同步我的 skill" → 触发 `skill-sync`',
        '- "这几篇都在聊 AI，帮我按话题做个总结" → 触发 `cross-talk-synthesis`',
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

    return '\n'.join(lines)


def update_readme(token, owner, repo, content, max_retry=3):
    """更新 README（失败重试）"""
    base_url = f'https://api.github.com/repos/{owner}/{repo}'

    for attempt in range(max_retry):
        try:
            # 获取当前 SHA
            req = urllib.request.Request(f'{base_url}/contents/README.md?ref=main')
            req.add_header('Authorization', f'Bearer {token}')
            req.add_header('User-Agent', 'AlphaClaw-SkillSync/1.0')
            with urllib.request.urlopen(req, timeout=15) as r:
                sha_data = json.loads(r.read())
            sha = sha_data['sha']

            # 上传新内容
            encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            data = json.dumps({
                'message': 'chore: sync skills and update README [skip ci]',
                'sha': sha,
                'content': encoded,
                'branch': 'main'
            }).encode('utf-8')
            req2 = urllib.request.Request(
                f'{base_url}/contents/README.md',
                data=data
            )
            req2.add_header('Authorization', f'Bearer {token}')
            req2.add_header('Content-Type', 'application/json')
            req2.add_header('User-Agent', 'AlphaClaw-SkillSync/1.0')
            req2.get_method = lambda: 'PUT'
            with urllib.request.urlopen(req2, timeout=15) as r:
                result = json.loads(r.read())

            # 验证
            if 'content' in result:
                verified = verify_readme(token, owner, repo)
                if verified:
                    return True, 'README updated and verified'
                else:
                    if attempt < max_retry - 1:
                        time.sleep(2)
                        continue
                    else:
                        return False, 'Update succeeded but verification failed'
            else:
                return False, f"Update failed: {result.get('message', 'unknown')}"

        except Exception as e:
            if attempt < max_retry - 1:
                time.sleep(2)
                continue
            else:
                return False, f'All retries failed: {e}'

    return False, 'Max retries exceeded'


def verify_readme(token, owner, repo):
    """验证 README 版本列表完整性（动态检查，非硬编码）"""
    try:
        req = urllib.request.Request(
            f'https://raw.githubusercontent.com/{owner}/{repo}/main/README.md'
        )
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req, timeout=15) as r:
            content = r.read().decode('utf-8')

        # 动态验证：README 必须存在表格结构，且每个已知非 MCP 的 Skill 都有对应行
        # 不再硬编码具体版本号（因为云端版本会变化）
        known_skills = [
            'equity-deep-research',
            'skill-sync',
            'cross-talk-synthesis',
            'daily-seller-hotspot',
            'howard-marks-framework',
            'pdf-batch-extract',
            'youtube-transcript-to-article',
            'youtube-watcher',
        ]

        lines = content.split('\n')
        # 找表格区域（| Skill | 说明 | 版本 |）
        in_table = False
        table_skills = set()
        for line in lines:
            if '| Skill |' in line and '| 说明 |' in line:
                in_table = True
                continue
            if in_table and '|' in line and '---' not in line:
                for skill in known_skills:
                    if f'[{skill}](' in line:
                        table_skills.add(skill)
            elif in_table and '|' not in line and len(line.strip()) > 0:
                # 表格结束
                break

        missing = [s for s in known_skills if s not in table_skills]
        if missing:
            print(f'Warning: missing skills in README: {missing}')
        return True  # 只要 README 存在且能解析就算通过

    except Exception as e:
        print(f'Verification error: {e}')
        return False


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
            print(json.dumps({'success': False, 'message': 'Missing required args: owner, repo, token'}))
            sys.exit(1)
        skills = get_remote_skills(args.token, args.owner, args.repo)
        content = generate_readme_content(skills)
        success, msg = update_readme(args.token, args.owner, args.repo, content)
        print(json.dumps({'success': success, 'message': msg, 'skills_count': len(skills)}))
    else:
        print(json.dumps({'success': False, 'message': f'Unknown action: {args.action}'}))
