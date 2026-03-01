---
name: info-graphic
description: 高密度信息大图生成 - 支持 8 种视觉风格。使用 Nano Banana Pro 4K 生图 API，将文章/内容转化为视觉坐标系统。触发场景：用户说"生成信息图"、"制作高密度大图"、"信息可视化"或提供文章要求生成配图时。
metadata:
  trigger: 信息图、高密度大图、小红书配图、坐标蓝图、复古波普、文件夹风格、热敏纸风、复古手帐、档案风、色块风、票据风
  source: https://waytoagi.feishu.cn/wiki/YG0zwalijihRREkgmPzcWRInnUg (持续更新)
  model: nano-banana-pro-4k
  styles: 8种风格可选（可扩展）
  last_update: 2026-02-28
---

# 高密度信息大图生成

## 概述

将文章内容转化为**高密度信息大图**，支持 8 种专业视觉风格。适用于小红书、公众号等平台的优质配图生成。

**视觉哲学**：拒绝平庸的手账，追求"数据可视化"的极致美感。

---

## 8 种风格速览

| ID | 风格 | 适用场景 |
|----|------|----------|
| 1 | 坐标蓝图·波普实验室 | 技术评测、产品对比、数据分析 |
| 2 | 复古波普网格 | 小红书爆款、70年代复古风格、粗描边平涂 |
| 3 | 文件夹风格 | 文具美学、3D剪贴板、索引标签 |
| 4 | 打印热敏纸风 | 收据/票务美学、现代拟物设计、穿孔边缘 |
| 5 | 复古手帐风 | 现代3D图标、手绘细节、双语分层 |
| 6 | 档案风 | 侦探证据板、混合媒体剪贴簿、复古美学 |
| 7 | 色块风 | 现代几何、高对比度色块、扁平设计 |
| 8 | 票据风 | 真实票据、热敏印刷、票据编号 |

> 详细风格规范：见 [STYLES.md](STYLES.md)

---

## 快速工作流

```
启动询问 → 风格选择 → 搜索/提炼 → 生成 Prompt（自动保持语言） → 确认 → 生图
```

### 1️⃣ 启动询问

确认：主题/内容、目标平台、特殊要求

### 2️⃣ 风格选择 ⛔ **强制停止点**

根据内容分析推荐风格，**必须等待用户选择**。

**推荐规则**：
- 技术评测/产品对比 → 坐标蓝图·波普实验室 (1)
- 小红书爆款/复古 → 复古波普网格 (2)
- 文具美学/剪贴板 → 文件夹风格 (3)
- 收据/票务美学 → 打印热敏纸风 (4)
- 手账/3D图标 → 复古手帐风 (5)
- 侦探/档案/拼贴 → 档案风 (6)
- 现代几何/色块 → 色块风 (7)
- 真实票据/印刷 → 票据风 (8)

### 3️⃣ 搜索提炼

如需要，使用 `WebSearch` 搜索最新信息，提炼 6-7 个核心价值模块。

### 4️⃣ 生成 Prompt ⭐ **自动语言保持**

使用风格文件生成指定风格的 Prompt。

**语言检测规则**：
- 中文占比 > 30% → 保持中文（添加 "ALL TEXT MUST BE IN CHINESE"）
- 英文占比 > 70% → 保持英文
- 混合内容 → 保持原始混合

### 5️⃣ 确认生图

向用户展示内容规划，确认后使用 Google AI API 或其他文生图服务生成图片。

---

## 编程接口

本 skill 生成高质量的提示词，你可以使用任何支持文生图的 API 来生成图片。

### 使用 Google Generative AI

```python
import google.generativeai as genai
import os

# 配置 API Key
api_key = os.environ.get("ALL_IMAGE_GOOGLE_API_KEY")
genai.configure(api_key=api_key)

# 生成图片
model = genai.GenerativeModel("gemini-2.0-flash-exp-image-generation")
response = model.generate_content("[生成的 Prompt]")

# 保存图片
with open("output.png", "wb") as f:
    f.write(response.data)
```

---

## 风格模板文件

风格定义存储在 `references/styles/` 文件夹中，便于直接修改：

```bash
# 查看风格定义
ls references/styles/
```

---

## 质量检查清单

- [ ] 风格一致：符合所选风格的色彩和布局
- [ ] 模块数量：包含 6-7 个独立信息块
- [ ] 数据密度：画面饱满，无空白区域
- [ ] 视觉层次：标题和内容有清晰区分
- [ ] 色彩准确：使用风格定义的指定颜色

---

## 更多文档

- [STYLES.md](STYLES.md) - 8 种风格详细规范
- [EXAMPLES.md](EXAMPLES.md) - 使用示例和交互流程
- [references/styles/](references/styles/) - **8 种风格模板文件（可编辑）**

---

风格定义存储在 `references/styles/` 文件夹中，便于直接修改：

```
references/styles/
├── 01_坐标蓝图_波普实验室.md    # 技术评测、产品对比
├── 02_复古波普网格.md            # 小红书爆款、70年代复古
├── 03_文件夹风格.md            # 文具美学、3D剪贴板
├── 04_打印热敏纸风.md          # 收据/票务美学
├── 05_复古手帐风.md            # 现代3D图标、手绘细节
├── 06_档案风.md                # 侦探证据板、混合媒体
├── 07_色块风.md                # 现代几何、高对比度
└── 08_票据风.md                # 真实票据、热敏印刷
```

**修改风格**：直接编辑 `references/styles/` 中对应的 `.md` 文件。

---

## 环境配置

确保已配置 Google AI Studio API Key：

**方法一：环境变量**
```bash
# Windows PowerShell
$env:ALL_IMAGE_GOOGLE_API_KEY="your_google_api_key_here"

# Linux/Mac
export ALL_IMAGE_GOOGLE_API_KEY="your_google_api_key_here"
```

**方法二：.env 文件**
```bash
# 在 skill 目录创建 .env 文件
ALL_IMAGE_GOOGLE_API_KEY=your_google_api_key_here
```

详细配置请参考 [API_SETUP.md](API_SETUP.md)。
