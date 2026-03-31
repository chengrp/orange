# Skill-Health 参考文档

## 健康度评估流程

```
1. 读取 skill-match 生成的 skills_data.json
   ↓
2. 遍历每个 skill 目录
   ↓
3. 检查 SKILL.md 文件
   - 文件长度（字符数）
   - YAML frontmatter 完整性
   - 必填字段（name、version、description）
   ↓
4. 检查目录结构
   - 是否有 scripts/ 目录
   - 是否有 run.bat 或等效启动脚本
   - 是否有 references/ 目录
   ↓
5. 计算健康分数
   ↓
6. 生成驾驶舱报告和评分报告
```

## 数据结构

### skills_health_data.json
```json
{
  "skills": [
    {
      "name": "skill-name",
      "health_score": 85,
      "grade": "A",
      "checks": {
        "file_length": { "passed": true, "score": 20 },
        "structure": { "passed": true, "score": 28 },
        "metadata": { "passed": true, "score": 25 },
        "code_quality": { "passed": true, "score": 12 }
      },
      "issues": []
    }
  ]
}
```

## 检查标准

### SKILL.md 文件长度
- **优秀**: > 2000 字符
- **良好**: 1000-2000 字符
- **合格**: 500-1000 字符
- **不合格**: < 500 字符

### 元数据要求
```yaml
---
name: skill-name              # 必填
version: "1.0.0"              # 必填，语义化版本
description: >                # 必填，详细描述
  Multi-line description
  with use cases
triggers:                     # 可选，触发词列表
  - "keyword"
---
```

### 目录结构
```
skill-name/
├── SKILL.md          # 必须存在
├── scripts/          # 必须存在且非空
└── references/       # 可选但推荐
```
