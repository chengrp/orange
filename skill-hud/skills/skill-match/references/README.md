# Skill-Match 参考文档

## 数据收集流程

```
1. 扫描 ~/.claude/skills/ 目录
   ↓
2. 读取每个 skill 的 SKILL.md
   ↓
3. 提取元数据（name, version, description）
   ↓
4. 从 SKILL.md 查找 GitHub URL（在 description 或引用中）
   ↓
5. 通过 user_github_map.json 补充 GitHub 关联
   ↓
6. 调用 GitHub API 检查最新版本
   ↓
7. 生成 JSON 数据和 Markdown 报告
```

## 数据结构

### skills_data.json
```json
{
  "skills": [
    {
      "name": "skill-name",
      "version": "1.0.0",
      "description": "skill 描述",
      "github_url": "https://github.com/user/repo",
      "local_path": "C:/Users/.../skill-name"
    }
  ]
}
```

### skills_version_check.json
```json
{
  "skills": [
    {
      "name": "skill-name",
      "current_version": "1.0.0",
      "latest_version": "1.2.0",
      "has_update": true,
      "github_url": "https://github.com/user/repo"
    }
  ]
}
```

## GitHub 用户映射

配置 `user_github_map.json`：

```json
{
  "skill-author-name": "github-username",
  "anthropics": "anthropics"
}
```

这样即使 SKILL.md 中没有直接写 GitHub URL，也能通过作者名找到仓库。
