# Delta SkillPack

智能任务执行器 - 统一入口，自动路由，实时反馈

## 快速开始

```bash
# 安装
pip install -e .

# 基本用法 - 一个命令搞定一切
skill do "实现用户认证系统"
```

## 命令参考

### `skill do "任务"` - 统一入口

智能分析任务复杂度，自动选择最优执行路径：

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

**可选参数：**

| 参数 | 说明 |
|------|------|
| `--quick, -q` | 跳过规划，直接实现 |
| `--deep, -d` | 强制 Ralph 自动化 |
| `--kb <id>` | 指定知识库 |
| `--quiet` | 静默模式 |
| `--explain, -e` | 仅显示路由决策 |

### `skill status` - 查看状态

```bash
skill status              # 查看当前任务
skill status -t abc123    # 查看指定任务
```

### `skill cancel` - 取消执行

```bash
skill cancel              # 取消当前任务
skill cancel -t abc123    # 取消指定任务
```

### `skill init` - 初始化配置

```bash
skill init    # 创建 .skillpackrc 配置文件
```

### `skill history` - 查看历史

```bash
skill history    # 显示最近执行的任务
```

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

## 智能路由逻辑

```
任务描述
   │
   ├─ 简单（单文件修改）──────→ 直接执行
   ├─ 中等（2-5 文件）───────→ plan → implement → review
   ├─ 复杂（多模块/系统级）──→ Ralph 自动化
   └─ UI 相关 ─────────────→ UI → implement → browser
```

**复杂度判断信号：**

- **简单**: typo, 注释, 重命名, 单文件修改
- **中等**: 新功能, bug 修复, 小重构
- **复杂**: 系统, 架构, 多模块, 从零构建
- **UI**: 页面, 组件, 样式, 布局, 前端

## 输出目录

- **当前执行**: `.skillpack/current/`
- **历史记录**: `.skillpack/history/<timestamp>/`

## 项目结构

```
skillpack/
├── __init__.py       # 包入口
├── cli.py            # CLI 命令定义
├── models.py         # 数据模型
├── router.py         # 任务路由器
├── executor.py       # 任务执行器
└── ralph/
    ├── __init__.py
    └── dashboard.py  # 进度追踪器
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
