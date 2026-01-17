---
name: cancel-ralph
description: 取消当前正在运行的 Ralph 迭代循环。
---

# 取消 Ralph 循环

停止正在运行的 Ralph 自动化开发循环。

## 使用方法

```
/cancel-ralph
```

## 执行操作

1. 清除 Ralph 状态文件
2. 停止当前迭代
3. 保留已完成的工作

## 执行流程

```bash
# 清除状态
rm -f .skillpack/ralph/session.json

# 调用 CLI 取消命令
skill ralph cancel
```

## 注意事项

- 已完成的故事和 git commits 不会被撤销
- PRD 文件保留，可以稍后继续
- 进度日志保留，记录取消时间点

## 恢复执行

取消后若要继续，使用:

```
/ralph-loop "继续之前的任务"
```

Ralph 会自动检测现有 PRD 并从中断处继续。
