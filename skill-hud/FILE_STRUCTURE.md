# Skill-HUD 文件结构

```
skill-hud/
├── .gitignore                      # Git 忽略配置
├── SKILL.md                        # 技能文档
├── FILE_STRUCTURE.md               # 本文件
│
├── scripts/                        # 主脚本目录
│   ├── hud_dashboard.py           # 综合仪表板生成脚本
│   ├── run.bat                     # 快速运行脚本
│   ├── test_stdin.py               # 测试脚本
│   └── test_visualization.py       # 可视化测试
│
├── reports/                        # 报告输出目录（已清空）
│   └── (生成时自动创建)
│
├── references/                     # 参考文档
│   └── README.md
│
└── skills/                         # 子技能模块
    ├── skill-match/                # 数据收集
    │   ├── SKILL.md
    │   ├── references/
    │   │   └── README.md
    │   ├── docs/
    │   │   └── v2_vs_v1.md
    │   ├── scripts/
    │   │   ├── skill_match.py              # 主脚本
    │   │   ├── skill_match_v2.py           # V2 版本
    │   │   ├── skill_match_v2_enhanced.py  # V2 增强版
    │   │   ├── skill_match_v2_fixed.py     # V2 修复版
    │   │   ├── skill_match_v3_optimized.py # V3 优化版（支持 API 限流检测）
    │   │   ├── generate_labeled_report.py  # 报告生成
    │   │   ├── evaluate_all_matches.py     # 评估工具
    │   │   ├── evaluate_all_matches_v2.py  # 评估工具 V2
    │   │   ├── run.bat
    │   │   └── run_v2.bat
    │   ├── config/                  # 配置目录
    │   └── reports/                 # 报告输出（已清空）
    │
    ├── skill-health/               # 健康度检查
    │   ├── SKILL.md
    │   ├── references/
    │   │   └── README.md
    │   ├── scripts/
    │   │   ├── skill_health.py
    │   │   └── run.bat
    │   └── reports/                 # 报告输出（已清空）
    │
    └── skill-innovation/           # 创新指导
        ├── SKILL.md
        ├── references/
        │   └── README.md
        ├── scripts/
        │   ├── skill_innovation.py
        │   ├── skill_innovation_v3.0_backup.py
        │   └── run.bat
        └── reports/                 # 报告输出（已清空）
```

## 主要文件说明

### 核心脚本
- **hud_dashboard.py**: 综合仪表板生成主脚本，整合所有子技能数据
- **skill_match.py/skill_match_v3_optimized.py**: 数据收集脚本
- **skill_health.py**: 健康度检查脚本
- **skill_innovation.py**: 创新指导脚本

### 数据文件（运行时生成）
- `skills_data.json`: 基础技能数据
- `skills_health_data.json`: 健康度数据
- `skills_innovation_data.json`: 所有权配置数据
- `skills_version_check.json`: 版本检查数据

### 报告文件（输出到 reports/）
- `SKILLS_综合分析_v{版本}_{日期}.md`: 综合仪表板报告
- `SKILLS_健康度_v{版本}_{日期}.md`: 健康度报告
- `SKILLS_创新指导_v{版本}_{日期}.md`: 创新指导报告

## GitHub 上传清单

- ✅ 已添加 `.gitignore` 文件
- ✅ 已添加 `LICENSE.txt` 文件（MIT License）
- ✅ 已清除所有报告文件
- ✅ 已检查文件结构
- ⚠️ 上传前请确认：
  1. 是否包含敏感信息（如 GITHUB_TOKEN）
  2. config/user_github_map.json 已被 .gitignore 忽略
