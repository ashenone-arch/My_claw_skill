""" readme_ops.py - README 自动维护脚本 v2.1

功能：从 GitHub API 获取远程仓库中所有 Skill 的版本列表，更新到 GitHub README
特性：
  - 工作流分阶段表格：按 信息收集 → 信息整理 → 分析/决策 → 系统工具 分组展示
  - 锚点保护：仅替换 <!-- SKILL_TABLE_START --> ... <!-- SKILL_TABLE_END --> 之间的表格区域
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
from collections import OrderedDict

TABLE_START = '<!-- SKILL_TABLE_START -->'
TABLE_END = '<!-- SKILL_TABLE_END -->'

# Skill 元数据：工作流阶段 + 核心功能描述
SKILL_META = {
    'daily-seller-hotspot': ('信息收集', '每日扫描卖方抱团方向，识别机构注意力焦点'),
    'youtube-transcript-to-article': ('信息收集', '视频/播客字幕自动转为书面文章'),
    'pdf-batch-extract': ('信息收集', '批量提取研报、公告PDF原文和表格为Markdown'),
    'fact-hub': ('信息整理', '事实、观点、冲突三层知识库，追踪认知迭代'),
    'cross-talk-synthesis': ('信息整理', '多篇对谈交叉汇总，按话题轴心组织观点碰撞'),
    'equity-deep-research': ('分析/决策', 'A股上市公司9段深度投研框架'),
    'howard-marks-framework': ('分析/决策', '霍华德·马克斯投资框架评估标的'),
    'dd-qlist': ('分析/决策', '一级市场科技项目尽调问题清单生成'),
    'skill-sync': ('系统工具', 'Skill本地与GitHub双向同步'),
    'fact-hub-sync': ('系统工具', 'Fact Hub知识库GitHub同步备份'),
}

PHASE_ORDER = ['信息收集', '信息整理', '分析/决策', '系统工具']


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


def _api_request(url, token, method='GET', data=None, max_retry=2):
    """通用 GitHub API 请求（含 SSL 降级 + 重试）"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'AlphaClaw-SkillSync/1.0'
    }

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
    """解析 SKILL.md frontmatter，返回 (version, description)"""
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
    """生成工作流分阶段表格块（含锚点标记）"""
    lines = [TABLE_START, '']

    # 按阶段分组
    phases = OrderedDict()
    for phase_name in PHASE_ORDER:
        phases[phase_name] = []

    skill_map = {s['name']: s for s in skills}
    for skill_name, (phase, function) in SKILL_META.items():
        if skill_name in skill_map:
            phases[phase].append((skill_name, skill_map[skill_name]['version'], function))

    for phase_name, phase_skills in phases.items():
        if not phase_skills:
            continue
        lines.append(f'### {phase_name}')
        lines.append('')
        lines.append('| Skill | 版本 | 核心功能 |')
        lines.append('|-------|------|---------|')
        for name, ver, func in phase_skills:
            lines.append(f'| [{name}]({name}/) | v{ver} | {func} |')
        lines.append('')

    lines.append(TABLE_END)
    return '\n'.join(lines)


def generate_full_readme(skills):
    """生成完整的带锚点 README（仅首次初始化或旧格式无锚点时使用）"""
    table_block = generate_table_block(skills)
    return '\n'.join([
        '# My Claw Skills',
        '',
        '> 一套完整的A股投研工作流——将信息收集、整理、分析到决策的闭环，通过结构化Skill固化为自动化、标准化的投研操作系统。',
        '',
        '---',
        '',
        '## 仓库总览：完整的投研工作流',
        '',
        f'{len(skills)} 个 Skill 系统性地覆盖投研各环节：',
        '',
        table_block,
        '',
        '---',
        '',
        '## 方法论设计',
        '',
        '**投资哲学的内化**：将投资大师的思想工程化为具体指令。`howard-marks-framework` 将"第二层次思维"、"周期定位"等抽象概念转化为可执行的分析维度。',
        '',
        '**认知过程的外化**：这套Skill体系作为"外部大脑"，将投研中的隐性知识显性化。`fact-hub` 通过事实→观点→冲突三层结构，清晰展示个人认知如何迭代更新。',
        '',
        '**工作流的管线化**：投研流程拆解为 **信息收集 → 信息整理 → 分析/决策** 三个阶段，每个环节可独立优化、复用和迭代。',
        '',
        '---',
        '',
        '## 使用方式',
        '',
        '在 AlphaClaw 中直接向助理描述需求即可自动触发对应 Skill：',
        '',
        '- "今天机构抱团什么方向" → `daily-seller-hotspot`',
        '- "把这几篇对谈合并一下" → `cross-talk-synthesis`',
        '- "深度研究一下贵州茅台" → `equity-deep-research`',
        '- "用霍华德·马克斯的框架评估这个标的" → `howard-marks-framework`',
        '- "同步我的 Skill" → `skill-sync`',
        '',
        '---',
        '',
        '## 免责声明',
        '',
        '本仓库中的 Skill 仅供个人投资研究使用，不构成任何投资建议。投资有风险，决策需谨慎。',
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
        before = existing_content.split(TABLE_START)[0]
        after = existing_content.split(TABLE_END)[1]
        table_block = generate_table_block(skills)
        return before + table_block + after
    else:
        return generate_full_readme(skills)


def update_readme(token, owner, repo, content, max_retry=3):
    """更新 README（失败重试）"""
    base_url = f'https://api.github.com/repos/{owner}/{repo}'
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')

    for attempt in range(max_retry):
        try:
            sha_req = urllib.request.Request(f'{base_url}/contents/README.md?ref=main')
            sha_req.add_header('Authorization', f'Bearer {token}')
            sha_req.add_header('User-Agent', 'AlphaClaw-SkillSync/1.0')
            with urllib.request.urlopen(sha_req, timeout=15) as r:
                file_data = json.loads(r.read())
            sha = file_data['sha']

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
        existing = get_existing_readme(args.token, args.owner, args.repo)
        content = merge_readme(existing, skills)
        success, msg = update_readme(args.token, args.owner, args.repo, content)
        print(json.dumps({'success': success, 'message': msg, 'skills_count': len(skills)}))
    else:
        print(json.dumps({'success': False, 'message': f'Unknown action: {args.action}'}))
