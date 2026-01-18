# OpenAlpha

智能任务执行器 - 统一入口，自动路由，实时反馈

## 快速开始

```
# 基本用法 - 一个命令搞定一切
/skill-do "实现用户认证系统"
```

## 命令参考

### `/skill-do "任务"` - 统一入口

智能分析任务复杂度，自动选择最优执行路径：

```
# 简单任务 → 直接执行
/skill-do "fix typo in README"

# 中等任务 → plan → implement → review
/skill-do "add user authentication"

# 复杂任务 → Ralph 自动化
/skill-do "build complete CMS"

# UI 任务 → UI flow
/skill-do "创建登录页面组件"
```

**可选参数：**

| 参数 | 说明 |
|------|------|
| `-q, --quick` | 跳过规划，直接实现 |
| `-d, --deep` | 强制 Ralph 自动化 |
| `-e, --explain` | 仅显示路由决策 |

## 智能路由逻辑

```
任务描述
   │
   ├─ 简单（单文件修改）──────→ 直接执行
   ├─ 中等（2-5 文件）───────→ plan → implement → review
   ├─ 复杂（多模块/系统级）──→ Ralph 自动化
   └─ UI 相关 ─────────────→ UI → implement → preview
```

**复杂度判断信号：**

- **简单**: typo, 注释, 重命名, 单文件修改
- **中等**: 新功能, bug 修复, 小重构
- **复杂**: 系统, 架构, 多模块, 从零构建
- **UI**: 页面, 组件, 样式, 布局, 前端

## 输出目录

- **当前执行**: `.skillpack/current/`
- **历史记录**: `.skillpack/history/<timestamp>/`

## 配置文件

创建 `.skillpackrc` 配置默认行为：

```json
{
  "knowledge": {
    "default_notebook": "your-notebook-id",
    "auto_query": true
  },
  "output": {
    "current_dir": ".skillpack/current",
    "history_dir": ".skillpack/history"
  }
}
```

## 项目结构

```
openalpha/
├── .claude/
│   └── skills/
│       ├── skill-do.md       # 主 Skill - 智能任务执行
│       └── skillpack-init.md # 初始化 Skill
├── .skillpack/
│   ├── current/              # 当前执行输出
│   └── history/              # 历史记录
├── .skillpackrc              # 配置文件（可选）
├── CLAUDE.md                 # 项目说明
└── pyproject.toml            # 项目配置
```
