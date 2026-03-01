# API 配置指南

## 概述

本 skill 使用 Google AI 生成高质量图片。你需要获取 Google AI API Key 才能使用。

---

## 获取 Google AI API Key

1. 访问 [Google AI Studio](https://ai.google.dev/)
2. 点击 **"Get API Key"** 或 **"获取 API Key"**
3. 使用 Google 账号登录
4. 创建新项目或选择现有项目
5. 复制生成的 API Key

**免费额度：**
- 每月 15 次/分钟请求限制
- 每天 1500 次生成限制
- 足够个人使用

---

## 配置 API Key

### 方法一：环境变量（推荐）

**Windows PowerShell:**
```powershell
$env:ALL_IMAGE_GOOGLE_API_KEY="your_api_key_here"
```

**Windows CMD:**
```cmd
set ALL_IMAGE_GOOGLE_API_KEY=your_api_key_here
```

**Linux/Mac:**
```bash
export ALL_IMAGE_GOOGLE_API_KEY="your_api_key_here"
```

### 方法二：.env 文件

在 skill 目录下创建 `.env` 文件：

```bash
ALL_IMAGE_GOOGLE_API_KEY=your_api_key_here
```

⚠️ **重要：** `.env` 文件已被 `.gitignore` 忽略，不会提交到 Git 仓库。

---

## 验证配置

在 Claude Code 中测试：

```
测试一下 info-graphic skill，生成一个简单的测试图片
```

如果成功生成图片，说明配置正确。

---

## 常见问题

### Q1: 提示 "AuthenticationError" 或认证失败

**A:** 检查 API Key 是否正确，是否有多余的空格或引号。

### Q2: 提示配额用尽

**A:** Google AI 免费版有每日限制，可以：
- 等待第二天重置
- 使用不同的 Google 账号获取新的 API Key

### Q3: 生成图片失败

**A:** 可能原因：
- API Key 配额用尽
- 网络连接问题
- Prompt 包含敏感内容被拒绝

### Q4: 图片质量不满意

**A:** 尝试以下方法：
- 在 prompt 中添加更多细节描述
- 尝试不同的风格参数
- 调整质量参数（standard/high/4k）

---

## 安全提示

⚠️ **重要：**
- 不要将 API Key 提交到 Git 仓库
- 不要在公开代码中硬编码 API Key
- 定期轮换 API Key
- 使用 `.gitignore` 忽略 `.env` 文件

---

## 支持

如有问题，请：
1. 查看 [SKILL.md](SKILL.md) 了解详细用法
2. 查看 [EXAMPLES.md](EXAMPLES.md) 查看示例
3. 提交 Issue 到 GitHub 仓库
