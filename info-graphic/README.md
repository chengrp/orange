# Info-Graphic - 高密度信息大图生成

> 将文章内容转化为**高密度信息大图**，支持 8 种专业视觉风格。适用于小红书、公众号等平台的优质配图生成。

## 功能特点

- **8 种视觉风格**：坐标蓝图、复古波普、文件夹、热敏纸、手帐、档案、色块、票据
- **高密度信息**：每张图包含 6-7 个信息模块，拒绝空白
- **智能语言保持**：自动检测内容语言，保持原始语言输出
- **多比例支持**：16:9、9:16、1:1、4:3、3:4 等
- **4K 超高清**：支持最高 4K 质量输出

## 快速开始

### 1. 安装依赖

```bash
pip install google-generativeai
```

### 2. 配置 API Key

获取 [Google AI API Key](https://ai.google.dev/) 并配置环境变量：

**Windows PowerShell:**
```powershell
$env:ALL_IMAGE_GOOGLE_API_KEY="your_api_key_here"
```

**Linux/Mac:**
```bash
export ALL_IMAGE_GOOGLE_API_KEY="your_api_key_here"
```

详细配置请参考 [API_SETUP.md](API_SETUP.md)。

### 3. 使用方式

**在 Claude Code 中使用：**

直接说："生成信息图"、"制作高密度大图" 等

**使用提示词生成图片：**

本 skill 生成高质量提示词，你可以使用任何支持文生图的 API 来生成图片。

## 8 种风格速览

| ID | 风格 | 适用场景 |
|----|------|----------|
| 1 | 坐标蓝图·波普实验室 | 技术评测、产品对比 |
| 2 | 复古波普网格 | 小红书爆款、复古风格 |
| 3 | 文件夹风格 | 文具美学、剪贴板 |
| 4 | 打印热敏纸风 | 收据/票务美学 |
| 5 | 复古手帐风 | 手账、3D图标 |
| 6 | 档案风 | 侦探证据板、拼贴 |
| 7 | 色块风 | 现代几何、扁平设计 |
| 8 | 票据风 | 真实票据、热敏印刷 |

## 文件结构

```
info-graphic/
├── references/
│   └── styles/          # 风格模板文件（8个）
├── SKILL.md             # Skill 文档
├── STYLES.md            # 风格规范说明
├── EXAMPLES.md          # 使用示例
├── API_SETUP.md         # API 配置指南
├── README.md            # 本文件
├── LICENSE              # MIT 许可证
├── requirements.txt     # 依赖声明
├── CHANGELOG.md         # 更新日志
└── CONTRIBUTING.md      # 贡献指南
```

## 使用示例

### 示例 1：生成技术对比图

```
生成一张技术对比信息图，对比 Python 和 JavaScript
```

### 示例 2：生成文章配图

```
把这篇文章生成一张信息图：[文章内容]
```

### 示例 3：指定风格

```
用复古波普风格生成一张健身指南信息图
```

## 文档

- [SKILL.md](SKILL.md) - 完整 Skill 文档
- [STYLES.md](STYLES.md) - 8 种风格详细规范
- [EXAMPLES.md](EXAMPLES.md) - 更多使用示例
- [API_SETUP.md](API_SETUP.md) - API 配置指南

## 质量检查清单

生成图片后，请检查：

- [ ] 风格一致：符合所选风格的色彩和布局
- [ ] 模块数量：包含 6-7 个独立信息块
- [ ] 数据密度：画面饱满，无空白区域
- [ ] 视觉层次：标题和内容有清晰区分
- [ ] 色彩准确：使用风格定义的指定颜色

## 常见问题

**Q: 提示认证失败？**

A: 检查 Google AI API Key 是否正确配置。

**Q: 生成图片失败？**

A: 检查 API Key 配额是否用尽，或网络连接问题。

**Q: 图片质量不满意？**

A: 在 prompt 中添加更多细节描述，或尝试不同的风格参数。

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 贡献

欢迎提交 Issue 和 Pull Request！详见 [CONTRIBUTING.md](CONTRIBUTING.md)
