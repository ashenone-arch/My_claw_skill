# 版本比较逻辑

## 语义化版本比较

版本比较使用语义化版本比较，禁止纯字符串比较。

```python
def compare_versions(v1, v2):
    """比较两个版本号，返回 1(v1>v2), 0(相等), -1(v1<v2)"""
    def parse(v):
        return [int(x) for x in v.lstrip('v').split('.')]
    n1, n2 = parse(v1), parse(v2)
    for i in range(max(len(n1), len(n2))):
        i1 = n1[i] if i < len(n1) else 0
        i2 = n2[i] if i < len(n2) else 0
        if i1 > i2:
            return 1
        elif i1 < i2:
            return -1
    return 0
```

**示例**：`compare_versions("v2.1", "v2.10")` → -1（因为 v2.1 = [2,1]，v2.10 = [2,10]，9>1）

## 版本对比表模板

```
| Skill | 说明 | 本地版本 | 远程版本 | 状态 |
|-------|------|---------|---------|------|
```

**状态枚举**：

| 条件 | 状态标签 |
|------|---------|
| 本地 == 远程 | `已同步` |
| 远程 > 本地 | `可更新（远程 > 本地）` |
| 本地 > 远程 | `可推送（本地 > 远程）` |
| 本地不存在 | `新增` |
| 远程不存在 | `本地独有` |

**版本来源**：

- 远程版本：从 GitHub API 获取 `SKILL.md` frontmatter 的 `version` 字段
- 本地版本：扫描 `~/.alphaclaw/skills/{skill}/SKILL.md` frontmatter

**frontmatter 解析**：

```python
def parse_frontmatter(content):
    version = 'unknown'
    description = ''
    in_frontmatter = False
    for line in content.split('\n'):
        if line.strip() == '---':
            in_frontmatter = not in_frontmatter
            continue
        if not in_frontmatter:
            continue
        if line.startswith('version:'):
            version = line.split(':', 1)[1].strip().strip('"').strip("'").lstrip('v')
        elif line.startswith('description:'):
            desc = line.split(':', 1)[1].strip().strip('"').strip("'")
            description = desc[:50] + ('...' if len(desc) > 50 else '')
    return version, description
```

## Skip 规则

以下情况跳过对比和同步：

- 本地目录名以 `mcp--` 开头（MCP 相关）
- 本地目录为 `skill-sync` 自身（同步自身时注意）
- 目录中无 `SKILL.md` 文件
