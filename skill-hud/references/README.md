# 📘 Skill-HUD 使用指南

> **版本**: 1.0.0
> **更新日期**: 2026-01-23
> **适用人群**: Claude Code 用户

---

## 🎯 什么是 Skill-HUD？

Skill-HUD 是 **Claude Code Skills 综合仪表板（HUD - Heads-Up Display）**。

### 核心价值

**一站式查看** - 整合所有子技能数据，一个报告了解全部情况

**简明扼要** - 去除冗余信息，只保留关键指标

**详略得当** - 该详细的地方详细，该简略的地方简略

---

## 🚀 快速开始

### 一键运行（推荐）

直接运行 skill-hud 会自动依次执行所有子技能：

**Windows:**
```bash
cd skill-hud/scripts
run.bat
```

**Linux/Mac:**
```bash
cd skill-hud/scripts
python hud_dashboard.py
```

### 单独运行各子技能

如果只想运行特定子技能：

```bash
# 数据收集
cd skill-match/scripts && python skill_match.py

# 健康度检查
cd ../../skill-health/scripts && python skill_health.py

# 创新指导
cd ../../skill-innovation/scripts && python skill_innovation.py
```

---

## 📖 报告结构详解

### 报告组成

```
📊 核心指标一览
├── 总Skill数 / 空间占用
├── GitHub覆盖率
├── 平均自定义度
├── 创造力等级
└── 健康率

📈 可视化分析
├── 类别分布图表
├── 空间占用TOP10
└── 来源分布图表

🏥 健康度分析
├── 健康度分布
├── 整体健康度
└── 需要关注的Skills

🎨 创新力分析
├── 所有权分布
├── 自定义度评分
└── 创造力等级

🔄 版本更新状态
├── 更新统计
└── 建议更新的Skills

📋 Skills清单
└── 按类别分组（含健康度和所有权）

💡 快速建议
└── 基于数据的具体行动建议
```

---

## 📊 各部分详解

### 1️⃣ 核心指标一览

**作用**：5秒钟了解全局状况

**包含内容**：
- **总Skill数** - 已安装的Skills总数
- **总占用空间** - 磁盘占用情况
- **GitHub覆盖率** - 有明确来源的Skill比例
- **平均自定义度** - 创造力水平评分
- **创造力等级** - 大师/进阶/成长/新手
- **健康率** - 健康/良好Skills占比

### 2️⃣ 可视化分析

**作用**：直观了解Skills分布

- **类别分布图** - 按功能分类统计
- **空间占用TOP10** - 找出占用空间最大的技能
- **来源分布图** - Anthropic/社区/Obsidian/微信等

### 3️⃣ 健康度分析

**作用**：快速发现需要关注的Skills

- **健康度分布表** - 优秀/良好/及格/需改进
- **健康率进度条** - 整体健康水平
- **需要关注的Skills** - 具体问题和建议

### 4️⃣ 创新力分析

**作用**：了解创造力和自定义情况

- **所有权分布图** - 原创/魔改/原生
- **自定义度评分** - 平均自定义百分比
- **创造力等级** - 大师/进阶/成长/新手

### 5️⃣ 版本更新状态

**作用**：了解哪些Skills需要更新

- **更新统计** - 已是最新/可更新数量
- **优先级分类** - 高/中/低优先级更新
- **具体更新列表** - 需要更新的Skills

### 6️⃣ Skills清单

**作用**：按类别查看所有Skills

**包含信息**：
- Skill名称
- 大小
- 来源（Anthropic/微信/Obsidian/社区）
- 健康度（评分和等级）
- 所有权类型（原创/魔改/原生）

### 7️⃣ 快速建议

**作用**：获得具体的行动指导

**示例建议**：
```
1. 🔴 健康: 有 11 个Skills健康度需改进，建议运行 skill-health 进行优化
2. 🟡 创新: 自定义度仅 5.1%，建议尝试魔改常用Skills或创建原创Skill
3. 🟢 定期: 建议每周运行一次完整分析，保持Skills在最佳状态
```

---

## 🎯 使用场景

### 场景1：首次使用

**目标**：全面了解Skills状况

**步骤**：
```bash
cd skill-hud/scripts
python hud_dashboard.py
```

skill-hud 会自动：
1. 运行 skill-match 收集数据
2. 运行 skill-health 检查健康度
3. 运行 skill-innovation 分析创新
4. 生成综合仪表板

### 场景2：每周例行检查

**目标**：追踪变化

**步骤**：
```bash
cd skill-hud/scripts && python hud_dashboard.py
```

### 场景3：问题诊断

**目标**：快速发现问题

**步骤**：
1. 打开仪表板报告
2. 查看"健康度分析"部分
3. 查看"快速建议"部分
4. 根据建议采取行动

---

## 💡 最佳实践

### 定期运行

**推荐频率**：每周一次

### 完整流程

**数据更新顺序**：
```
1. skill-match (数据收集)
   ↓
2. skill-health (健康评估)
   ↓
3. skill-innovation (创新指导)
   ↓
4. skill-hud (综合仪表板)
   ↓
5. 查看仪表板
```

**skill-hud 会自动执行前3步，无需手动操作！**

---

## 📈 与其他子技能的关系

```
┌─────────────────────────────────────────────────────────────┐
│                   Claude Code Skills 生态                      │
└─────────────────────────────────────────────────────────────┘

    skill-match          skill-health         skill-innovation
    (独立Skill)           (独立Skill)           (独立Skill)
         │                       │                       │
         ├── skills_data.json     ├── health_data.json  ├── ownership_config.json
         │                       │                       │
         └───────────┬───────────┴───────────┬───────────┘
                     │                       │
                     ▼                       │
                    skill-hud ◄─────── 你在这里
                    (综合仪表板)
                    自动调用上面3个Skill
                         │
                         ▼
                SKILLS_综合分析_最新.md
                (一站式查看全貌)
```

---

## 📁 目录结构

```
skills/
├── skill-match/              # 数据收集（独立skill）
│   ├── SKILL.md
│   ├── scripts/skill_match.py
│   └── references/
├── skill-health/             # 健康度评估（独立skill）
│   ├── SKILL.md
│   ├── scripts/skill_health.py
│   └── references/
├── skill-innovation/         # 创新指导（独立skill）
│   ├── SKILL.md
│   ├── scripts/skill_innovation.py
│   └── references/
└── skill-hud/                # 综合仪表板（本skill）
    ├── SKILL.md
    ├── scripts/hud_dashboard.py
    └── reports/
```

---

## ❓ 常见问题

### Q1：为什么需要 4 个独立的 skill？

**A**：
- **模块化**：每个 skill 可以单独使用和维护
- **灵活性**：可以根据需要选择运行哪些 skill
- **可扩展性**：便于后续添加新的子技能

### Q2：仪表板和驾驶舱报告有什么区别？

**A**：
- **驾驶舱报告**：专注于可视化图表和空间占用（skill-health生成）
- **仪表板报告**：整合所有数据，包括健康度、所有权、版本更新等

### Q3：多长时间运行一次？

**A**：
- **最少**：每月运行一次
- **推荐**：每周运行一次
- **最佳**：每次安装新Skill后运行

### Q4：报告会覆盖旧报告吗？

**A**：
- `SKILLS_综合分析_v1.0.0_YYYY-MM-DD.md` - 带版本号的文件会被保留
- `SKILLS_综合分析_最新.md` - 每次都会被最新报告覆盖

---

## 🚀 下一步

1. **查看报告** - 了解你的Skills全貌
2. **识别问题** - 根据健康度和建议找出需要优化的地方
3. **采取行动** - 按建议执行优化
4. **定期追踪** - 每周运行查看变化

---

**版本**: 1.0.0
**更新日期**: 2026-01-23
**架构**: 调用外部独立 skill（skill-match、skill-health、skill-innovation）
