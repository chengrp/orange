# Skill 发布操作指南

## 概述

将个人使用的 Skill 整理为可公开发布的标准流程，确保普适性和安全性。

---

## 发布前检查清单

### 1. 依赖分析

分析 Skill 的所有依赖，区分以下类型：

| 依赖类型 | 处理方式 |
|---------|---------|
| 公共 Python 包 | 保留，写入 `requirements.txt` |
| 个人 Skill 依赖 | 移除，改为通用 API 调用说明 |
| 个人 API 服务 | 移除，仅保留公开 API（如 Google AI） |
| 个人路径配置 | 清除所有绝对路径 |

### 2. 个人信息清除

检查并清除以下内容：

```bash
# 搜索检查关键词
grep -r "ProjectAI" .
grep -r "RyanCh" .
grep -r "/Users/" .
grep -r "all-image" .
grep -r "all_image" .
grep -r "demo_prompt" .
grep -r "generate\.py" .
```

### 3. 必需文件清单

```
skill-name/
├── SKILL.md             # Skill 核心文档（必需）
├── README.md            # 项目概述（必需）
├── LICENSE              # MIT 许可证（推荐）
├── requirements.txt     # Python 依赖（如有）
├── API_SETUP.md         # API 配置指南（如有需要）
├── EXAMPLES.md          # 使用示例（推荐）
├── CHANGELOG.md         # 更新日志（推荐）
├── CONTRIBUTING.md      # 贡献指南（推荐）
├── .gitignore           # Git 忽略规则（推荐）
└── [其他核心文件]
```

---

## 详细操作步骤

### Step 1: 分析原始 Skill

```bash
# 进入 skill 目录
cd path/to/your/skill

# 检查文件结构
ls -la

# 搜索依赖关系
grep -r "import" . --include="*.py" --include="*.ts"
grep -r "from" . --include="*.py" --include="*.ts"
```

### Step 2: 清除个人信息

**1. 移除个人路径引用**
```bash
# 查找所有包含个人路径的文件
grep -r "C:\\\\Users" .
grep -r "/home/" .
grep -r "ProjectAI" .

# 逐一修复文件
```

**2. 移除个人 Skill 依赖**
- 将依赖其他 Skill 的代码改为通用说明
- 在文档中说明"可以使用任何 XX 功能的 API"

**3. 清理个人输出文件**
```bash
# 删除 output/ 目录
rm -rf output/

# 删除生成的图片、缓存等
rm -rf __pycache__/
rm -f *.pyc
rm -f .env
```

### Step 3: 创建/更新必需文件

**1. README.md**
```markdown
# Skill 名称

简短描述（1-2 句话）

## 功能特点
- 特点 1
- 特点 2

## 快速开始
### 安装依赖
```bash
pip install xxx
```

### 配置
详细配置说明

## 使用示例
示例内容

## 文档
- SKILL.md - 完整文档
- EXAMPLES.md - 使用示例
- API_SETUP.md - API 配置

## 许可证
MIT License
```

**2. LICENSE（MIT）**
```bash
# 直接复制标准 MIT License
# 或使用：echo "MIT" > LICENSE 然后填写内容
```

**3. .gitignore**
```
# 个人配置
.env
.env.local

# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/

# 输出文件
output/
*.png
*.jpg
*.jpeg

# IDE
.vscode/
.idea/
*.swp
```

**4. requirements.txt**
```
# 仅包含公共 PyPI 包
package-name>=version

# 不要包含：
# - 本地路径
# - 个人依赖
```

**5. API_SETUP.md（如需要）**
```markdown
# API 配置指南

## 获取 API Key

详细步骤...

## 配置方法

**环境变量：**
```bash
export API_KEY="your_key_here"
```

**.env 文件：**
```
API_KEY=your_key_here
```

## 验证配置
测试方法...
```

**6. CHANGELOG.md**
```markdown
# Changelog

## [Unreleased]

### Added
- 新功能

## [1.0.0] - YYYY-MM-DD

### Added
- 初始发布
- 功能列表
```

### Step 4: 更新 SKILL.md

确保 SKILL.md 包含：

```markdown
---
name: skill-name
description: 简洁描述
metadata:
  trigger: 触发关键词
  last_update: YYYY-MM-DD
---

# Skill 标题

## 概述
核心功能描述

## 使用方式
清晰的使用步骤

## 编程接口
代码示例（如有）

## 更多文档
链接到其他文档
```

### Step 5: 验证清理结果

```bash
# 最终检查：确保无个人信息
grep -r "ProjectAI" . || echo "✓ 无个人路径"
grep -r "all-image" . || echo "✓ 无个人依赖"
grep -r "/Users/" . || echo "✓ 无用户路径"
```

### Step 6: 初始化 Git 并发布

**1. 初始化仓库**
```bash
cd path/to/skill
git init
```

**2. 添加所有文件**
```bash
git add .
```

**3. 创建首次提交**
```bash
git commit -m "Initial release: Skill Name

Features:
- Feature 1
- Feature 2

Documentation:
- SKILL.md - Complete documentation
- README.md - Project overview
- LICENSE - MIT License

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

**4. 添加远程仓库**
```bash
# 方式 A: 使用 GitHub CLI（如已安装）
gh repo create skill-name --public --source=. --remote=origin --push

# 方式 B: 手动添加远程
git remote add origin https://github.com/username/skill-name.git
git branch -M main
git push -u origin main
```

---

## 常见问题

### Q1: Skill 依赖其他个人 Skill 怎么办？

**A:** 有两种处理方式：

1. **内联核心功能**：将依赖的代码复制进来（注意许可证）
2. **改为通用说明**：在文档中说明"需要 XX 功能，可使用任意 XX API"

### Q2: 有多個 API 配置怎么处理？

**A:** 仅保留公开可用的 API，其他移除：

```
保留：Google AI、OpenAI、Anthropic 等公开 API
移除：自建服务、个人配置的 API
```

### Q3: 输出文件要不要保留？

**A:** 原则上不保留：

```
保留：核心逻辑文件、配置模板
移除：实际生成的文件、用户输出、缓存
```

### Q4: 目录结构要不要调整？

**A:** 按需调整，确保清晰：

```
推荐结构：
skill-name/
├── README.md          # 入口文档
├── SKILL.md           # 核心文档
├── [核心代码]/        # 代码文件
├── references/        # 参考资源
└── docs/              # 其他文档
```

---

## 快速检查命令

```bash
# 一键检查脚本
check_skill() {
    echo "=== Skill 发布检查 ==="
    echo ""
    echo "1. 检查必需文件："
    for f in README.md SKILL.md LICENSE .gitignore; do
        [ -f "$f" ] && echo "  ✓ $f" || echo "  ✗ $f (缺失)"
    done
    echo ""
    echo "2. 检查个人信息："
    grep -r "ProjectAI" . && echo "  ✗ 发现个人路径" || echo "  ✓ 无个人路径"
    grep -r "/Users/" . && echo "  ✗ 发现用户路径" || echo "  ✓ 无用户路径"
    echo ""
    echo "3. 检查 Git 状态："
    git status -s | head -5
    echo ""
}

check_skill
```

---

## 发布后维护

### 更新 Skill

```bash
# 1. 修改文件
# 2. 查看更改
git status
git diff

# 3. 提交更改
git add .
git commit -m "feat: add new feature"

# 4. 推送更新
git push
```

### 版本发布

```bash
# 创建标签
git tag -a v1.0.0 -m "Release v1.0.0"

# 推送标签
git push origin v1.0.0

# 或推送所有标签
git push origin --tags
```

---

## 示例：info-graphic Skill 发布

### 原始问题
- 依赖个人 `all-image` skill
- 包含个人 API 配置（ModelScope、Yunwu）
- 有个人输出文件和路径

### 解决方案
1. 移除 `all-image` 依赖，改为通用 API 说明
2. 仅保留 Google AI API 配置（公开可用）
3. 删除所有个人输出文件
4. 添加完整的文档和许可证

### 最终结果
```
info-graphic/
├── references/styles/   # 8 种风格模板
├── SKILL.md            # 核心文档
├── README.md           # 项目概述
├── EXAMPLES.md         # 使用示例
├── API_SETUP.md        # 仅 Google AI 配置
├── LICENSE             # MIT 许可证
├── requirements.txt    # google-generativeai
└── styles.py           # 独立风格模块
```

---

## 总结

发布 Skill 的核心原则：

1. **独立性**：不依赖其他个人 Skill
2. **普适性**：使用公开 API 和公共依赖
3. **清晰性**：完整文档和使用示例
4. **安全性**：无个人路径和敏感信息
5. **规范性**：标准的 Git 工作流和许可证

遵循本指南，可以快速将个人 Skill 转化为可公开发布的标准格式。
