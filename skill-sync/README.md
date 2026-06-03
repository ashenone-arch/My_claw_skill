# skill-sync

> GitHub Skill 同步工具 | 版本: v2.0

## 概述

自动检测并同步本地 Skill 与 GitHub 仓库中的版本。支持**双向同步**：远程优先拉取，本地领先时推送到云端。

## 首次使用

首次使用时，告诉 AI 你的 GitHub 仓库地址和 Token：
> "我的仓库是 owner/repo，token 是 ghp_xxx"

AI 会自动保存配置，后续同步无需重复输入。

> **隐私提示**：Token 保存在本地的 `github-config.json`，该文件已被 `.gitignore` 和 `push.py` 双重保护，不会被上传到 GitHub。

## 使用场景

- "同步我的 skill"
- "检查 skill 版本"
- "更新本地 skill"
