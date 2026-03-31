# 🎯 Skill-HUD - Claude Code Skills 综合仪表板

<div align="center">

**整合三个子技能，生成统一的 Claude Code Skills 管理仪表板**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.txt)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [使用说明](#-️-使用说明) • [配置](#-配置) • [注意事项](#-注意事项)

</div>

---

## 📖 简介

Skill-HUD 是一个 **Claude Code Skills 综合仪表板**，整合了数据收集、健康评估和创新指导三个子功能，帮助你全面管理和优化你的 Claude Code Skills 生态系统。

### 核心价值

- 📊 **一目了然**：统一的仪表板展示所有关键指标
- 🏥 **健康监控**：自动检查 Skills 的健康状态和潜在问题
- 🎨 **创新追踪**：分析所有权分布和自定义度，鼓励创作
- ⚠️ **智能提醒**：API 限流警告、版本更新建议
- 💡 **行动建议**：基于数据的具体优化建议

---

## ✨ 功能特性

### 📊 核心指标一览
- 总 Skill 数量和空间占用
- GitHub 覆盖率统计
- 平均自定义度和创造力等级
- 健康率概览

### 📈 可视化分析
- **类别分布**：按功能分类展示（开发工作流、文档写作、设计创意等）
- **空间占用 TOP10**：识别占用空间最大的 Skills
- **来源分布**：统计 Anthropic、社区、Obsidian 等来源

### 🏥 健康度分析
- 健康度等级分布（优秀/良好/及格/需改进）
- 整体健康度进度条
- 需要关注的 Skills 列表及具体问题

### 🎨 创新力分析
- 所有权分布（原创/魔改/原生）
- 自定义度评分
- 创造力等级评估（新手级 → 大师级）

### 🔄 版本更新状态
- 更新统计（已是最新 / 可更新）
- 按优先级分类的更新建议（高/中/低）

### ⚠️ 数据来源状态检测
- GitHub API 限流警告
- 数据新鲜度提示
- 缓存使用状态说明

---

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Claude Code 已安装并配置

### 安装

1. **克隆仓库**
```bash
git clone https://github.com/chengrp/Skill-HUD.git
cd Skill-HUD
```

2. **验证安装**
```bash
cd scripts
python hud_dashboard.py --help
```

### 使用方法

**方法一：一键运行（推荐）**
```bash
cd scripts
python hud_dashboard.py
```

**方法二：分别运行子技能**
```bash
# 1. 数据收集
cd skills/skill-match/scripts
python skill_match.py

# 2. 健康度检查
cd ../../skill-health/scripts
python skill_health.py

# 3. 创新指导
cd ../../skill-innovation/scripts
python skill_innovation.py

# 4. 生成综合仪表板
cd ../../../scripts
python hud_dashboard.py
```

---

## 📖 使用说明

### 报告结构

运行后会在 `reports/` 目录生成以下报告：

| 报告文件 | 说明 |
|---------|------|
| `SKILLS_综合分析_最新.md` | **主入口报告**（综合仪表板） |
| `SKILLS_健康度_最新.md` | 健康度详情报告 |
| `SKILLS_创新指导_最新.md` | 所有权与创新报告 |
| `skills溯源检查报告_最新.md` | GitHub 关联与版本检查报告 |

### 报告内容说明

#### 1️⃣ 核心指标一览
快速查看所有关键数据，包括：
- 总 Skill 数和占用空间
- GitHub 覆盖率
- 健康率和创造力等级

#### 2️⃣ 可视化分析
通过 ASCII 图表直观展示：
- 类别分布条形图
- 空间占用 TOP10（颜色编码）
- 来源分布统计

#### 3️⃣ 健康度分析
- **健康度分布**：四个等级的数量和占比
- **整体健康度**：进度条显示健康率
- **需要关注**：列出存在问题的 Skills 及具体问题

#### 4️⃣ 创新力分析
- **所有权分布**：原创/魔改/原生的比例
- **自定义度评分**：平均自定义百分比
- **创造力等级**：新手级 → 成长级 → 进阶级 → 大师级

#### 5️⃣ 快速建议
按优先级（高/中/低）提供具体行动建议：
- 健康度优化建议
- 创新提升建议
- 空间清理建议
- 版本更新提醒

---

## ⚙️ 配置

### 环境变量

| 变量名 | 说明 | 必需 |
|--------|------|------|
| `GITHUB_TOKEN` | GitHub Personal Access Token | 可选（提高 API 限额） |

**设置方法**：
```bash
# Windows (PowerShell)
$env:GITHUB_TOKEN = "your_token_here"

# Windows (CMD)
set GITHUB_TOKEN=your_token_here

# Linux/macOS
export GITHUB_TOKEN="your_token_here"
```

### 自定义配置

#### 所有权配置
编辑 `skills/skill-innovation/scripts/ownership_config.json`：

```json
{
  "原创": ["your-skill-1", "your-skill-2"],
  "魔改": {
    "modified-skill": {
      "custom_percentage": 30,
      "changes": ["修改了功能X", "优化了性能Y"]
    }
  }
}
```

#### GitHub 映射
编辑 `skills/skill-match/scripts/user_github_map.json`（首次运行后自动生成）：

```json
{
  "your-skill-name": "https://github.com/username/repo"
}
```

---

## ⚠️ 注意事项

### API 限流处理

当遇到 GitHub API 限流（每小时 60 次请求）时：
- 技能会自动使用缓存数据
- 报告中会显示 ⚠️ **数据来源说明**
- 建议设置 `GITHUB_TOKEN` 提高限额到 5000 次/小时

### 数据隐私

- ❌ **不会上传**：你的 Skill 内容、配置文件
- ✅ **仅读取**：公开的 GitHub 仓库信息（stars、更新时间等）
- 🔒 **本地存储**：所有数据文件保存在本地

### 健康度检查

健康度评分基于以下标准：
- **文件完整性**：必需文件是否存在
- **结构规范性**：是否符合 Skill 标准结构
- **元数据完整性**：frontmatter 字段是否齐全
- **文件大小**：SKILL.md 建议不超过 500 行

---

## 📂 项目结构

```
skill-hud/
├── scripts/
│   └── hud_dashboard.py      # 主脚本
├── skills/                   # 子技能模块
│   ├── skill-match/          # 数据收集
│   ├── skill-health/         # 健康检查
│   └── skill-innovation/     # 创新指导
├── reports/                  # 报告输出目录
├── .gitignore               # Git 忽略配置
├── LICENSE.txt              # MIT 许可证
├── FILE_STRUCTURE.md        # 文件结构说明
├── SKILL.md                 # Claude Code Skill 文档
└── README.md               # 本文件
```

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发建议

1. **Fork 项目**
2. **创建特性分支** (`git checkout -b feature/AmazingFeature`)
3. **提交更改** (`git commit -m 'feat: 添加某个功能'`)
4. **推送分支** (`git push origin feature/AmazingFeature`)
5. **开启 Pull Request**

### 提交规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

- `feat:` 新功能
- `fix:` 修复 bug
- `docs:` 文档更新
- `style:` 代码格式调整
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建/工具链相关

---

## 📄 许可证

本项目采用 [MIT License](LICENSE.txt) 开源协议。

---

## 🙏 致谢

- [Claude Code](https://claude.ai/code) - AI 辅助开发工具
- [anthropic-skills](https://github.com/anthropics/anthropic-skills) - 官方 Skills 仓库
- 所有贡献者和用户

---

## 📮 联系方式

- **GitHub**: [chengrp/Skill-HUD](https://github.com/chengrp/Skill-HUD)
- **Issues**: [提交问题](https://github.com/chengrp/Skill-HUD/issues)

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给它一个 Star！**

Made with ❤️ by [chengrp](https://github.com/chengrp)

</div>
