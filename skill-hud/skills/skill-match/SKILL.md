---
name: skill-match
version: "1.0.0"
description: >
  Claude Code Skills 数据收集与源头追踪。

  核心功能：
  - 扫描 ~/.claude/skills/ 目录，收集所有已安装技能
  - 从 SKILL.md 中提取元数据（name、version、description）
  - 关联 GitHub 仓库（通过 user_github_map.json）
  - 检查版本更新（通过 GitHub API 获取最新版本）
  - 生成溯源检查报告

  使用场景：
  - 检查本地安装了哪些 Skills
  - 查看 Skills 的 GitHub 源头
  - 检查 Skills 是否有更新

  输出：reports/skills溯源检查报告_v{version}_{date}.md

  依赖：无（纯本地扫描 + GitHub API）

triggers:
  - "查看本地安装的 skills"
  - "检查 skill 更新"
  - "skill 溯头"
  - "扫描 skills 目录"
---

# Skill-Match 数据收集

## 功能说明

收集本地安装的 Skills 并追踪其 GitHub 源头。

## 运行方式

```bash
cd skill-match/scripts
python skill_match.py
```

或使用快捷脚本：
```bash
cd skill-match/scripts
run.bat
```

## 输出文件

- `skills_data.json` - 所有技能的基础数据
- `skills_version_check.json` - 版本检查结果
- `../reports/skills溯源检查报告_*.md` - 可读性报告

## 配置文件

- `user_github_map.json` - GitHub 用户名映射（手动配置）
- `user_github_map.template.json` - 配置模板
