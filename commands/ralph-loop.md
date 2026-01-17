---
name: ralph-loop
description: 启动 Ralph 迭代循环 - 持续开发直到任务完成。 灵感来自 Anthropic 官方的 ralph-wiggum 插件。
---

# Ralph 自动化开发循环

启动 PRD 驱动的自主开发循环，持续迭代直到所有故事完成。

## 使用方法

```
/ralph-loop "任务描述"
```

## 执行流程

1. **初始化 PRD**
   - 检查 `.skillpack/ralph/prd.json` 是否存在
   - 若不存在，执行 `skill ralph init "任务描述"` 生成 PRD
   - 若存在，继续未完成的工作

2. **启动循环**
   - 执行 `skill ralph start`
   - 按优先级依次处理故事
   - 每个故事执行对应的技能管道

3. **故事管道**
   - **feature**: plan → implement → review → verify
   - **ui**: ui → implement → review → browser
   - **refactor**: plan → implement → review → verify
   - **test**: implement → review → verify
   - **docs**: plan → implement → review

4. **完成信号**
   - 所有故事通过时输出: `<promise>COMPLETE</promise>`
   - Stop Hook 检测到信号后终止循环

## 参数

- `任务描述`: 要完成的开发任务（必填）

## 示例

```
/ralph-loop "实现用户认证系统，包括登录、注册、JWT token 管理"
```

```
/ralph-loop "重构数据库访问层，使用 Repository 模式"
```

## 中断循环

使用 `/cancel-ralph` 命令取消正在运行的循环。

## 输出位置

- PRD: `.skillpack/ralph/prd.json`
- 进度日志: `.skillpack/ralph/progress.txt`
- 知识库: `.skillpack/ralph/AGENTS.md`
- 迭代输出: `.skillpack/ralph/iterations/`

## 注意事项

- 循环最多执行 100 次迭代
- 每个故事最多重试 3 次
- 失败的故事会记录错误并继续下一个
- 所有成功的故事会自动 git commit
