# Delta SkillPack

> 🚀 智能任务执行器 - 统一入口，自动路由，实时反馈

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 为什么选择 SkillPack？

**传统方式（7个命令）：**
```bash
skill plan "任务"           # 规划
skill implement "任务"      # 实现
skill review "任务"         # 审查
skill ui "任务"             # UI 设计
skill ralph init            # 初始化 Ralph
skill ralph start           # 启动 Ralph
skill ralph status          # 查看状态
```

**SkillPack 方式（1个命令）：**
```bash
skill do "任务"             # 自动路由到最优路径 ✨
```

## 特性

- 🎯 **统一入口** - `skill do "任务"` 一个命令搞定一切
- 🧠 **智能路由** - 自动分析任务复杂度，选择最优执行路径
- 📊 **实时反馈** - Rich 终端进度追踪和状态显示
- 📚 **知识库集成** - 自动创建和查询 NotebookLM 知识库
- 🗂️ **简化输出** - 统一的 `.skillpack/current/` 和 `.skillpack/history/` 目录

## 安装

```bash
# 克隆仓库
git clone https://github.com/VictorVVedtion/delta-skillpack.git
cd delta-skillpack

# 安装（开发模式）
pip install -e .

# 可选：安装 Rich 支持更好的终端显示
pip install -e ".[rich]"
```

## 快速开始

### 1. 初始化项目

```bash
# 仅创建配置文件
skill init

# 同时创建 NotebookLM 知识库（推荐）
skill init --with-notebook
```

### 2. 执行任务

```bash
# 简单任务 → 直接执行
skill do "fix typo in README"

# 中等任务 → plan → implement → review
skill do "add user authentication"

# 复杂任务 → Ralph 自动化
skill do "build complete CMS"

# UI 任务 → UI flow
skill do "创建登录页面组件"
```

### 3. 查看状态

```bash
skill status    # 当前任务状态
skill history   # 历史任务列表
```

## 命令参考

### `skill do "任务"` - 统一入口

| 参数 | 说明 |
|------|------|
| `--quick, -q` | 跳过规划，直接实现 |
| `--deep, -d` | 强制 Ralph 自动化 |
| `--kb <id>` | 指定知识库 ID |
| `--quiet` | 静默模式 |
| `--explain, -e` | 仅显示路由决策，不执行 |

**示例：**
```bash
skill do "实现用户认证" --quick      # 跳过规划
skill do "重构整个系统" --deep       # 强制 Ralph
skill do "搜索功能" --kb notebook-123 # 指定知识库
skill do "添加按钮" --explain        # 仅显示路由
```

### `skill init` - 初始化

| 参数 | 说明 |
|------|------|
| `--with-notebook` | 自动创建 NotebookLM 知识库 |
| `--notebook-id <id>` | 使用已有的知识库 |

### `skill status` - 查看状态

```bash
skill status              # 当前任务
skill status -t abc123    # 指定任务
```

### `skill cancel` - 取消执行

```bash
skill cancel              # 取消当前任务
```

### `skill history` - 历史记录

```bash
skill history             # 最近 20 条
```

## 智能路由

SkillPack 自动分析任务描述，选择最优执行路径：

```
任务描述
   │
   ├─ 简单（typo, 重命名, 注释）────→ 直接执行
   ├─ 中等（功能实现, bug修复）────→ plan → implement → review
   ├─ 复杂（系统级, 多模块）───────→ Ralph 自动化
   └─ UI 相关（页面, 组件, 样式）──→ UI → implement → browser
```

### 复杂度判断信号

| 类型 | 关键词示例 |
|------|-----------|
| **简单** | typo, rename, comment, 修复拼写, 重命名 |
| **复杂** | system, architecture, complete, 系统, 架构, 多模块 |
| **UI** | page, component, button, style, 页面, 组件, 样式, 布局 |

## 配置

### `.skillpackrc`

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

### 知识库集成

使用 `--with-notebook` 初始化时，SkillPack 会：
1. 自动创建 NotebookLM notebook
2. 将 notebook ID 保存到配置
3. 后续任务自动查询知识库

## 输出目录

```
.skillpack/
├── current/           # 当前执行的任务输出
└── history/           # 历史任务归档
    ├── 20240117_143052_abc12345/
    └── 20240117_150123_def67890/
```

## 项目结构

```
delta-skillpack/
├── skillpack/
│   ├── __init__.py       # 包入口
│   ├── cli.py            # CLI 命令定义
│   ├── models.py         # 数据模型
│   ├── router.py         # 智能任务路由器
│   ├── executor.py       # 任务执行器（策略模式）
│   ├── knowledge.py      # NotebookLM 知识库管理
│   └── ralph/
│       ├── __init__.py
│       └── dashboard.py  # 统一进度追踪器
├── tests/
│   ├── test_router.py    # 路由器测试
│   ├── test_executor.py  # 执行器测试
│   └── test_cli.py       # CLI 测试
├── .claude/
│   └── skills/           # Claude Code skill 定义
├── pyproject.toml        # 项目配置
├── setup.py              # 兼容旧版 pip
├── CLAUDE.md             # Claude Code 文档
└── README.md
```

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev,rich]"

# 运行测试
pytest

# 类型检查
mypy skillpack

# 代码格式化
ruff check --fix skillpack
```

## 设计原则

- **KISS** - 简单的规则匹配路由，无复杂 ML
- **SOLID** - 策略模式执行器，单一职责进度追踪
- **DRY** - 复用复杂度检测和进度回调逻辑
- **YAGNI** - 仅实现当前需要的功能

## 路线图

- [x] 统一入口 `skill do`
- [x] 智能任务路由
- [x] 实时进度追踪
- [x] NotebookLM 知识库集成
- [ ] 并行任务执行
- [ ] 任务依赖管理
- [ ] Web UI 仪表盘

## License

MIT © 2024
