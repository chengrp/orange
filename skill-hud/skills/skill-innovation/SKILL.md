---
name: skill-innovation
version: "3.0.0"
description: >
  Claude Code Skills 创新指导系统 v3.0（多因子评分版）。

  核心功能：
  - 所有权追踪（原创、魔改、原生）
  - 自定义评分系统
  - 魔改推荐
  - 创新价值评估

  v3.0 新特性：
  - **多因子评分系统**（不依赖白名单）
  - 官方特征识别（triggers、Use when、版本号等）
  - 原创特征识别（中文内容、复杂 scripts、自定义目录等）
  - 智能分类判定（基于评分而非硬编码规则）

  v2.1 新特性：
  - Git 命令性能优化（缓存机制）
  - 类别推断优化（减少关键词重叠）
  - 详细日志系统（verbose 模式）
  - 改进的文件过滤规则

  使用场景：
  - 了解自己的 skill 创造活动
  - 发现有魔改潜力的 skills
  - 评估 skill 的独特价值
  - 获取个性化的改进建议

  输出：reports/SKILLS_创新指导_*.md

  依赖：读取 skill-match 生成的 skills_data.json

triggers:
  - "skill 创新"
  "魔改推荐"
  "skill 所有权"
  "skill 评分"
---

# Skill-Innovation 创新指导 v2.1

## 功能说明

分析每个 Skill 的所有权类型和创新价值，提供魔改建议。

## 运行方式

```bash
cd skill-innovation/scripts
python skill_innovation.py
```

### 命令行参数

```bash
python skill_innovation.py              # 默认运行（使用缓存）
python skill_innovation.py -v           # 详细输出模式
python skill_innovation.py --no-cache   # 禁用缓存重新分析
python skill_innovation.py --clear-cache  # 清空缓存后退出
```

## 输出文件

- `../reports/SKILLS_创新指导_*.md` - 创新指导报告
- `.cache/git_*.json` - Git 信息缓存（可清空）

## 所有权类型

| 类型 | 说明 | 标记 |
|------|------|------|
| 原创 | 自己创建的 skill | 原创 |
| 魔改 | 基于他人 skill 修改 | 魔改 |
| 原生 | 直接使用，无修改 | 原生 |

## 创新评分维度

| 维度 | 权重 | 说明 |
|------|------|------|
| 独特性 | 30% | 功能是否独特 |
| 实用性 | 30% | 是否解决实际问题 |
| 完整性 | 20% | 文档和代码是否完整 |
| 活跃度 | 20% | 是否有更新维护 |

## 配置文件

### ownership_config.json
```json
{
  "原创": [],
  "魔改": {},
  "说明": "手动配置技能所有权（可选，系统会自动检测）",
  "auto_detection": {
    "enabled": true,
    "users": ["你的用户名"],
    "user_aliases": [],
    "说明": {
      "enabled": "是否启用自动检测",
      "users": "你的用户名列表（用于识别你的仓库）",
      "user_aliases": "用户别名/昵称列表"
    }
  }
}
```

## v2.1 优化详情

### 性能优化
- Git 命令合并调用（5+ 次减少到 2-3 次）
- 智能缓存机制（1 小时有效期）
- 相似度计算提前终止优化

### 精度提升
- 改进的文件过滤规则（忽略配置文件、临时文件）
- 类别推断减少重叠（添加排除词机制）
- 更完善的所有权检测算法

### 用户体验
- 详细日志模式（`-v` 参数）
- 缓存管理命令（`--clear-cache`）
- 更好的错误处理和提示
