""" readme_ops.py - README 自动维护脚本

功能：生成当前本地所有 Skill 的版本列表，更新到 GitHub README
验证：更新后检查版本列表是否正确（失败重试最多 3 次）
"""
import sys, os, json, base64, time, urllib.request

def get_local_skills():
    """扫描本地 Skill 目录，生成版本列表"""
    skills_dir = os.path.expanduser('~/.alphaclaw/skills')
    result = []

    for name in os.listdir(skills_dir):
        skill_path = os.path.join(skills_dir, name, 'SKILL.md')
        if not os.path.isfile(skill_path):
            continue
        if name.startswith('mcp--') or name in ['skill-sync']:  # skill-sync 自己跳过（后面单独处理）
            if name == 'skill-sync':
                pass  # 仍收录
            else:
                continue  # MCP 相关跳过

        try:
            with open(skill_path, 'r', encoding='utf-8') as f:
                content = f.read()
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
                        version = line.split(':')[1].strip().lstrip('v')
                    elif line.startswith('description:'):
                        desc = line.split(':', 1)[1].strip()
                        description = desc[:50] + ('...' if len(desc) > 50 else '')
            result.append({
                'name': name,
                'version': version,
                'description': description
            })
        except:
            pass

    # 添加 skill-sync（它也在 ~/.alphaclaw/skills 下，但描述需要单独处理）
    return result

def generate_readme_content(skills):
    """生成 README 内容"""
    skill_sync_ver = 'v1.2'  # 当前版本，硬编码或从文件读取
    skill_sync_desc = 'GitHub Skill 同步工具，支持本地→云端推送，自动维护 README 版本列表'

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

    # 按名称排序
    skills_sorted = sorted(skills, key=lambda x: x['name'])
    for s in skills_sorted:
        lines.append(f"| [{s['name']}]({s['name']}/) | {s['description']} | {s['version']} |")

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
            req = urllib.request.Request(
                f'{base_url}/contents/README.md?ref=main'
            )
            req.add_header('Authorization', f'Bearer {token}')
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
    """验证 README 版本列表正确性"""
    try:
        req = urllib.request.Request(
            f'https://raw.githubusercontent.com/{owner}/{repo}/main/README.md'
        )
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req, timeout=15) as r:
            content = r.read().decode('utf-8')

        # 检查 equity-deep-research 和 skill-sync 版本（已知的关键版本）
        checks = [
            ('equity-deep-research', 'v2.1'),
            ('skill-sync', 'v1.2'),
            ('cross-talk-synthesis', 'v1.1'),
            ('pdf-batch-extract', 'v1.1'),
        ]

        for skill, ver in checks:
            skill_line = [l for l in content.split('\n') if f'[{skill}](' in l]
            if skill_line and f'| {ver} |' not in skill_line[0]:
                return False
        return True
    except Exception as e:
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
        skills = get_local_skills()
        content = generate_readme_content(skills)
        success, msg = update_readme(args.token, args.owner, args.repo, content)
        print(json.dumps({'success': success, 'message': msg, 'skills_count': len(skills)}))
    else:
        print(json.dumps({'success': False, 'message': f'Unknown action: {args.action}'}))
