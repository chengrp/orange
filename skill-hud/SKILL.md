---
name: skill-hud
version: "1.0.0"
description: >
  Claude Code Skills 综合仪表板（HUD - Heads-Up Display）。
  整合所有子技能的功能，生成一个简明扼要、详略得当的综合报告。

  核心功能：
  - 📂 数据收集 - 扫描Skills目录，关联GitHub，检查版本更新
  - 🏥 健康度评估 - 文件长度、结构完整性、元数据验证
  - 🎨 创新指导 - 所有权追踪、自定义评分、魔改推荐
  - 📊 综合仪表板 - 一站式查看所有信息
  - 💡 快速建议 - 基于数据的具体行动建议

  使用场景：全面了解Skills状态、一站式查看所有信息、快速发现问题

  输出：reports/ 目录下的所有报告（溯源检查、健康自检、创新指导、综合分析）

  架构：调用外部独立 skill（skill-match、skill-health、skill-innovation）
---

# 🎯 Skill-HUD - Skills 综合仪表板

整合所有子技能数据，生成一个简明扼要、详略得当的综合仪表板报告。

## 🚀 快速开始

```bash
cd skill-hud/scripts
python hud_dashboard.py
# 或直接运行
run.bat
```

## 📋 功能说明

### 1. 📊 核心指标卡片

一览所有关键信息：
- 总Skill数和空间占用
- GitHub覆盖率
- 平均自定义度
- 创造力等级
- 健康率

### 2. 📈 可视化分析

**包含以下图表：**
- 📂 类别分布（条形图）
- 💾 空间占用TOP10
- 🏪 来源分布

### 3. 🏥 健康度分析

- 健康度分布统计
- 整体健康度进度条
- 需要关注的Skills列表

### 4. 🎨 创新力分析

- 所有权分布（原创/魔改/原生）
- 自定义度评分
- 创造力等级

### 5. 🔄 版本更新状态

- 更新统计（已是最新/可更新）
- 按优先级分类的更新建议

### 6. 📋 Skills清单

按类别分组的完整Skills列表，包含：
- Skill名称
- 大小
- 来源
- 健康度
- 所有权类型

### 7. 💡 快速建议

基于数据生成的具体行动建议：
- 健康度优化建议
- 创新提升建议
- 版本更新建议

## 📁 项目结构

```
skill-hud/
├── SKILL.md                  # 本文件
├── scripts/
│   ├── hud_dashboard.py      # 主脚本
│   └── run.bat               # 快速运行
├── reports/                  # 报告输出目录
│   ├── SKILLS_综合分析_v1.0.0_YYYY-MM-DD.md
│   └── SKILLS_综合分析_最新.md
└── skills/                   # 子技能目录（统一管理）
    ├── skill-match/          # 数据收集
    │   ├── SKILL.md
    │   ├── scripts/skill_match.py
    │   └── reports/
    ├── skill-health/         # 健康度评估
    │   ├── SKILL.md
    │   ├── scripts/skill_health.py
    │   └── reports/
    └── skill-innovation/     # 创新指导
        ├── SKILL.md
        ├── scripts/skill_innovation.py
        └── reports/
```

## 🔄 工作流程

```
1. 运行 skill-match       → 生成 skills_data.json
2. 运行 skill-health      → 生成 skills_health_data.json
3. 运行 skill-innovation  → 生成 ownership_config.json
4. 运行 skill-hud         → 读取所有数据，生成综合仪表板
```

## 🔄 数据整合

### 依赖关系

```
skill-match ──┐
                 ├──► skills_data.json ──┐
skill-health ────┤                        │
                 ├──► skills_health_data ─┼──► skill-hud
skill-innovation ┤                        │
                 └──► ownership_config ───┘
```

### 数据来源

| 子技能 | 数据文件 | 用途 |
|--------|----------|------|
| **skill-match** | skills_data.json | 基础信息、GitHub、版本 |
| **skill-health** | skills_health_data.json | 健康度评分、检查结果 |
| **skill-innovation** | ownership_config.json | 所有权配置、自定义度 |

## 📊 报告结构

```
SKILLS_综合分析
│
├── 📊 核心指标一览
│   ├── 总Skill数
│   ├── 总占用空间
│   ├── GitHub覆盖率
│   ├── 平均自定义度
│   ├── 创造力等级
│   └── 健康率
│
├── 📈 可视化分析
│   ├── 类别分布图表
│   ├── 空间占用TOP10
│   └── 来源分布图表
│
├── 🏥 健康度分析
│   ├── 健康度分布
│   ├── 整体健康度
│   └── 需要关注的Skills
│
├── 🎨 创新力分析
│   ├── 所有权分布
│   ├── 自定义度评分
│   └── 创造力等级
│
├── 🔄 版本更新状态
│   ├── 更新统计
│   └── 建议更新的Skills
│
├── 📋 Skills清单
│   └── 按类别分组（含健康度和所有权）
│
├── 💡 快速建议
│   └── 基于数据的具体行动建议
│
└── 📖 使用说明
```

## 🎯 使用场景

### 场景1：首次使用

**目标**：全面了解Skills状况

**步骤**：
1. 运行所有子技能收集数据
2. 运行 skill-hud 生成综合报告
3. 查看仪表板了解全貌

### 场景2：定期查看

**目标**：追踪变化趋势

**步骤**：
1. 定期运行所有子技能
2. 生成新的仪表板
3. 对比不同时期的报告

### 场景3：问题诊断

**目标**：快速发现问题

**步骤**：
1. 查看健康度分析部分
2. 查看"需要关注的Skills"
3. 根据建议采取行动

## 🔧 使用方法

### 完整流程

```bash
# 1. 数据收集（每次必做）
cd skill-match/scripts
python skill_match.py

# 2. 健康度检查（可选）
cd ../../skill-health/scripts
python skill_health.py

# 3. 创新指导（可选）
cd ../../skill-innovation/scripts
python skill_innovation.py

# 4. 生成综合仪表板（必做）
cd ../../skill-hud/scripts
python hud_dashboard.py

# 5. 查看报告
start ..\\reports\\SKILLS_综合分析_最新.md
```

### 一键运行（推荐）

直接运行 skill-hud 会自动依次执行上述步骤：
```bash
cd skill-hud/scripts
python hud_dashboard.py
# 或
run.bat
```

## 📚 相关技能

- **skill-match** - 数据收集（必需）
- **skill-health** - 健康度评估（推荐）
- **skill-innovation** - 创新指导（推荐）

---

**版本**: 1.0.0 | **作者**: Claude Code Community
