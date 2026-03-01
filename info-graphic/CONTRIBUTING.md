# Contributing to Info-Graphic

感谢你考虑为 Info-Graphic 贡献！

## 如何贡献

### 报告问题

如果你发现了 bug 或有功能建议：

1. 检查 [Issues](https://github.com/yourusername/info-graphic/issues) 是否已存在相同问题
2. 如果没有，创建新的 Issue，详细描述：
   - 问题和复现步骤
   - 预期行为
   - 实际行为
   - 环境信息（操作系统、Python 版本等）

### 提交代码

1. **Fork 项目**
   ```bash
   git clone https://github.com/yourusername/info-graphic.git
   cd info-graphic
   ```

2. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **做出修改**
   - 遵循现有代码风格
   - 添加必要的文档
   - 确保代码通过测试

4. **提交更改**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **推送到 Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **创建 Pull Request**
   - 在 PR 描述中清楚说明你的更改
   - 关联相关的 Issue

### 添加新风格

如果你想添加新的视觉风格：

1. 在 `references/styles/` 创建新的风格文件
2. 遵循现有风格文件的格式
3. 在 `SKILL.md` 和 `STYLES.md` 中更新风格列表
4. 提供示例图片

### 代码规范

- 使用 4 空格缩进
- 遵循 PEP 8 风格指南
- 添加有意义的注释
- 保持函数简洁和单一职责

### 文档

- 更新相关文档（SKILL.md、README.md 等）
- 在 CHANGELOG.md 中记录更改

## 许可证

通过贡献，你同意你的代码将在 MIT 许可证下发布。

## 联系方式

- 提交 Issue 进行讨论
- Pull Request 欢迎审查

再次感谢你的贡献！
