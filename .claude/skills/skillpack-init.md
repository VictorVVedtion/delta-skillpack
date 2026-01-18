# SkillPack 初始化 Skill

当用户运行 `skill init --with-notebook` 时，此 skill 自动创建 NotebookLM 知识库。

## 触发条件

检测到输出中包含 `SKILLPACK_CREATE_NOTEBOOK` 标记。

## 执行流程

1. **解析参数**
   - 从输出中提取 `PROJECT_NAME` 和 `CONFIG_PATH`

2. **创建 NotebookLM Notebook**
   ```
   使用 mcp__notebooklm-mcp__notebook_create 工具
   title: "SkillPack: {PROJECT_NAME}"
   ```

3. **更新配置文件**
   - 将返回的 notebook_id 写入 CONFIG_PATH 的 `knowledge.default_notebook` 字段

4. **确认完成**
   - 输出成功消息和 notebook ID

## 示例

用户运行:
```bash
skill init --with-notebook
```

Claude Code 检测到:
```
📚 SKILLPACK_CREATE_NOTEBOOK
PROJECT_NAME=my-project
CONFIG_PATH=/path/to/.skillpackrc
```

Claude Code 执行:
1. 调用 `mcp__notebooklm-mcp__notebook_create` 创建 notebook
2. 更新 `.skillpackrc` 配置
3. 输出: "✅ 知识库已创建: {notebook_id}"
