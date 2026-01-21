# 安装与配置指南 (Setup Guide) v5.4

## 概述

本指南提供 Skillpack v5.4 的完整安装和配置说明，包括 CLI 工具安装、API 密钥配置、环境验证和故障排查。

---

## 前置条件

### 系统要求

| 要求 | 最低版本 | 推荐版本 | 验证命令 |
|------|----------|----------|----------|
| Node.js | 16.0.0 | 20+ (LTS) | `node --version` |
| npm | 8.0.0 | 10+ | `npm --version` |
| Claude Code | 最新版 | 最新版 | `claude --version` |
| Git | 2.0.0 | 最新版 | `git --version` |

### 网络要求

- 可访问 OpenAI API (api.openai.com)
- 可访问 Google AI API (generativelanguage.googleapis.com)
- 可访问 NotebookLM (notebooklm.google.com)

---

## Phase 1: Codex CLI 安装

### 1.1 安装 Codex CLI

```bash
# 全局安装 Codex CLI
npm install -g @openai/codex

# 验证安装
codex --version
```

### 1.2 获取 OpenAI API Key

1. 访问 [OpenAI Platform](https://platform.openai.com/api-keys)
2. 登录或注册账户
3. 点击 "Create new secret key"
4. 复制生成的 API Key（格式：`sk-...`）

### 1.3 配置 Codex

创建或编辑 `~/.codex/config.toml`：

```toml
# Codex 配置
model = "gpt-5.2-codex"
model_reasoning_effort = "xhigh"

# 可选配置
# approval_policy = "on-failure"
# sandbox = "workspace-write"
```

### 1.4 设置环境变量

```bash
# 方式 1: 临时设置
export OPENAI_API_KEY="sk-your-api-key-here"

# 方式 2: 永久设置 (添加到 ~/.bashrc 或 ~/.zshrc)
echo 'export OPENAI_API_KEY="sk-your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### 1.5 验证 Codex 安装

```bash
# 测试 Codex 是否正常工作
codex exec "print hello world"
```

预期输出：应该看到 Codex 执行 Python 或其他语言打印 "hello world"。

---

## Phase 2: Gemini CLI 安装

### 2.1 安装 Gemini CLI

```bash
# 全局安装 Gemini CLI
npm install -g @google/gemini-cli

# 或使用 npx 直接运行（无需全局安装）
npx gemini-mcp-tool
```

### 2.2 获取 Gemini API Key

1. 访问 [Google AI Studio](https://aistudio.google.com/apikey)
2. 登录 Google 账户
3. 点击 "Create API Key"
4. 选择项目（或创建新项目）
5. 复制生成的 API Key

### 2.3 配置 Gemini

创建或编辑 `~/.gemini/settings.json`：

```json
{
  "model": "gemini-3-pro-preview",
  "temperature": 0.7,
  "maxOutputTokens": 8192
}
```

### 2.4 设置环境变量

```bash
# 方式 1: 临时设置
export GEMINI_API_KEY="your-gemini-api-key-here"

# 方式 2: 永久设置
echo 'export GEMINI_API_KEY="your-gemini-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### 2.5 验证 Gemini 安装

```bash
# 测试 Gemini CLI
gemini "explain what is 2+2"
```

预期输出：应该看到 Gemini 返回对 2+2=4 的解释。

---

## Phase 3: NotebookLM MCP 安装

### 3.1 安装 NotebookLM MCP

```bash
# 全局安装
npm install -g notebooklm-mcp
```

### 3.2 认证 NotebookLM

```bash
# 运行认证命令（会打开浏览器）
notebooklm-mcp-auth
```

这将：
1. 打开浏览器
2. 引导您登录 Google 账户
3. 授权 NotebookLM MCP 访问
4. 保存认证令牌到本地

### 3.3 验证认证

```bash
# 测试认证状态
notebooklm-mcp --test-auth
```

---

## Phase 4: MCP 服务器配置

### 4.1 项目级配置

在项目根目录创建或编辑 `.mcp.json`：

```json
{
  "$schema": "https://raw.githubusercontent.com/anthropics/claude-code/main/schemas/mcp.schema.json",
  "mcpServers": {
    "notebooklm-mcp": {
      "type": "stdio",
      "command": "notebooklm-mcp",
      "args": [],
      "env": {}
    },
    "codex-cli": {
      "type": "stdio",
      "command": "codex",
      "args": ["mcp-server"],
      "env": {}
    },
    "gemini-cli": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "gemini-mcp-tool"],
      "env": {}
    }
  }
}
```

### 4.2 全局配置（可选）

如果希望在所有项目中使用，编辑 `~/.claude/settings.json`：

```json
{
  "mcpServers": {
    "codex-cli": {
      "type": "stdio",
      "command": "codex",
      "args": ["mcp-server"]
    },
    "gemini-cli": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "gemini-mcp-tool"]
    },
    "notebooklm-mcp": {
      "type": "stdio",
      "command": "notebooklm-mcp"
    }
  }
}
```

---

## Phase 5: Skillpack 配置

### 5.1 创建 .skillpackrc

在项目根目录创建 `.skillpackrc`：

```json
{
  "version": "3.0",
  "knowledge": {
    "default_notebook": null,
    "auto_query": false
  },
  "routing": {
    "weights": {
      "scope": 25,
      "dependency": 20,
      "technical": 20,
      "risk": 15,
      "time": 10,
      "ui": 10
    },
    "thresholds": {
      "direct": 20,
      "planned": 45,
      "ralph": 70,
      "architect": 100
    }
  },
  "checkpoint": {
    "auto_save": true,
    "atomic_writes": true,
    "backup_count": 3,
    "save_interval_minutes": 5
  },
  "mcp": {
    "timeout_seconds": 180,
    "auto_chunk_large_tasks": true,
    "chunk_max_tokens": 4000,
    "auto_fallback_to_cli": true
  },
  "cli": {
    "codex_path": "codex",
    "gemini_path": "gemini",
    "prefer_cli_over_mcp": false,
    "cli_timeout_seconds": 300
  }
}
```

### 5.2 配置说明

| 配置项 | 说明 | 推荐值 |
|--------|------|--------|
| `mcp.timeout_seconds` | MCP 调用超时时间 | 180 |
| `mcp.auto_chunk_large_tasks` | 自动拆分大任务 | true |
| `mcp.auto_fallback_to_cli` | MCP 失败时自动降级到 CLI | true |
| `cli.prefer_cli_over_mcp` | 优先使用 CLI 而非 MCP | false |
| `cli.cli_timeout_seconds` | CLI 命令超时时间 | 300 |

---

## Phase 6: 快速验证

### 6.1 验证路由决策

```bash
# 测试 DIRECT_TEXT 路由
/do "fix typo in README" --explain

# 测试 DIRECT_CODE 路由
/do "fix bug in auth.ts" --explain

# 测试 UI_FLOW 路由
/do "create login page component" --explain
```

预期输出：应该看到复杂度评分和推荐路由。

### 6.2 验证 MCP 调用

```bash
# 测试 Codex MCP
/do "add console.log to main.ts" --quick

# 测试 Gemini MCP
/do "design a simple button component"
```

### 6.3 验证 CLI 直接调用

```bash
# 测试 Codex CLI 直接调用
/cli-codex "add a hello world function"

# 测试 Gemini CLI 直接调用
/cli-gemini "analyze project structure"
```

---

## 故障排查

### 常见问题

#### 1. Codex 认证失败

**症状**: `Error: Invalid API key` 或 `401 Unauthorized`

**解决方案**:
```bash
# 检查 API Key 是否正确设置
echo $OPENAI_API_KEY

# 重新设置
export OPENAI_API_KEY="sk-your-correct-key"

# 验证
codex exec "print hello"
```

#### 2. Gemini 连接超时

**症状**: `ETIMEDOUT` 或 `ECONNREFUSED`

**解决方案**:
```bash
# 检查网络连接
curl -I https://generativelanguage.googleapis.com

# 检查 API Key
echo $GEMINI_API_KEY

# 尝试直接调用
curl -X POST "https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key=$GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
```

#### 3. NotebookLM 认证过期

**症状**: `Authentication expired` 或 `401`

**解决方案**:
```bash
# 重新认证
notebooklm-mcp-auth

# 刷新令牌
notebooklm-mcp --refresh-auth
```

#### 4. MCP 服务器无响应

**症状**: MCP 调用挂起，无输出

**解决方案**:
```bash
# 检查 MCP 服务器进程
ps aux | grep -E "codex|gemini|notebooklm"

# 重启 Claude Code
# 或使用 CLI 直接调用作为后备
/cli-codex "your task"
```

#### 5. 权限错误

**症状**: `EACCES` 或 `Permission denied`

**解决方案**:
```bash
# 修复 npm 全局目录权限
sudo chown -R $(whoami) $(npm config get prefix)/{lib/node_modules,bin,share}

# 或使用 nvm 管理 Node.js
```

---

## 环境变量汇总

| 变量名 | 用途 | 示例 |
|--------|------|------|
| `OPENAI_API_KEY` | Codex 认证 | `sk-...` |
| `GEMINI_API_KEY` | Gemini 认证 | `AIza...` |
| `NOTEBOOKLM_COOKIES` | NotebookLM 认证（备用） | Cookie 字符串 |

---

## 完整安装检查清单

```
[ ] Node.js >= 16 已安装
[ ] npm >= 8 已安装
[ ] Claude Code 已安装
[ ] Codex CLI 已安装 (npm install -g @openai/codex)
[ ] OPENAI_API_KEY 已设置
[ ] ~/.codex/config.toml 已配置
[ ] Gemini CLI 已安装或可通过 npx 运行
[ ] GEMINI_API_KEY 已设置
[ ] NotebookLM MCP 已安装 (npm install -g notebooklm-mcp)
[ ] NotebookLM 已认证 (notebooklm-mcp-auth)
[ ] .mcp.json 已配置
[ ] .skillpackrc 已创建
[ ] 验证测试通过
```

---

## 升级指南

### 从 v5.0 升级到 v5.1

1. **更新 .skillpackrc**:
   ```json
   {
     "mcp": {
       "auto_fallback_to_cli": true
     },
     "cli": {
       "codex_path": "codex",
       "gemini_path": "gemini",
       "prefer_cli_over_mcp": false,
       "cli_timeout_seconds": 300
     }
   }
   ```

2. **安装 CLI Skills**:
   ```bash
   # CLI Skills 已内置，无需额外安装
   ```

3. **验证 CLI 功能**:
   ```bash
   /cli-codex "test"
   /cli-gemini "test"
   ```

---

## 参考链接

- [OpenAI API 文档](https://platform.openai.com/docs)
- [Google AI Studio](https://aistudio.google.com)
- [Claude Code 文档](https://docs.anthropic.com/claude-code)
- [NotebookLM](https://notebooklm.google.com)
