# creamcode 任务进度管理

## 项目概述

creamcode 是一个类似 Claude Code 的轻量级 AI 编程 CLI 工具，使用 Python 实现，采用完全插件化架构。

**仓库**: https://github.com/CocoonOvO/cream-code

---

## 当前进度

### 核心架构重构 ✅ 完成

| 模块 | 事件 | CLI 命令 | 状态 |
|------|------|---------|------|
| lifecycle | `lifecycle.start`, `lifecycle.stop` | `lifecycle start/stop` | ✅ |
| plugin | `plugin.load/unload/enable/disable` | `plugin load/unload/enable/disable` | ✅ |
| cli | `cli.start`, `cli.command`, `cli.interactive` | - | ✅ |

---

## 架构设计

### 核心事件系统

```
EventBus (单例)
├── create_space("lifecycle") → EventSpace
├── create_space("plugin")   → EventSpace  
├── create_space("cli")     → EventSpace
│
├── 发射: @space.event("name") 装饰器
├── 订阅: @on("space.name", priority=N) 装饰器
└── 链式处理: handler 返回修改后的 Event
```

### 核心事件列表

| 事件 | 触发时机 |
|------|---------|
| `lifecycle.start` | `LifecycleManager.start()` 执行后 |
| `lifecycle.stop` | `LifecycleManager.stop()` 执行后 |
| `plugin.load` | `PluginManager.load_plugin()` 执行后 |
| `plugin.unload` | `PluginManager.unload_plugin()` 执行后 |
| `plugin.enable` | `PluginManager.enable_plugin()` 执行后 |
| `plugin.disable` | `PluginManager.disable_plugin()` 执行后 |
| `cli.start` | `CLIApp.initialize()` 执行后 |
| `cli.command` | `CLIApp.execute()` 执行后 |
| `cli.interactive` | `InteractiveMode.run()` 执行后 |

### 事件常量表 (CoreEvents)

位于 `creamcode/plugins/interfaces.py`

```python
class CoreEvents:
    LIFECYCLE_START = "lifecycle.start"
    LIFECYCLE_STOP = "lifecycle.stop"
    PLUGIN_LOAD = "plugin.load"
    PLUGIN_UNLOAD = "plugin.unload"
    PLUGIN_ENABLE = "plugin.enable"
    PLUGIN_DISABLE = "plugin.disable"
    CLI_START = "cli.start"
    CLI_COMMAND = "cli.command"
    CLI_INTERACTIVE = "cli.interactive"
    # ... 更多事件
```

---

## 待开发功能

### 1. Agent 系统 🔲

| 任务 | 说明 | 状态 |
|------|------|------|
| Agent 基类 | 处理消息、思考、响应 | 🔲 |
| 默认 Agent 实现 | 整合 tools + memory | 🔲 |
| Agent 事件 | `agent.thinking`, `agent.prompt`, `agent.response` | 🔲 |

### 2. 消息系统 🔲

| 任务 | 说明 | 状态 |
|------|------|------|
| 会话管理 | `session.start`, `session.end`, `session.message` | 🔲 |
| 消息管道 | `message.incoming`, `message.outgoing` 链式处理 | 🔲 |

### 3. 工具系统 🔲

| 任务 | 说明 | 状态 |
|------|------|------|
| 工具注册表 | `tool.call`, `tool.result` 事件 | 🔲 |
| 内置工具 | Bash, File, Web 工具 | 🔲 |
| 工具链式修改 | handler 可修改工具调用结果 | 🔲 |

### 4. 记忆系统 🔲

| 任务 | 说明 | 状态 |
|------|------|------|
| 工作记忆 | Token 限制管理 | 🔲 |
| 短期记忆 | 会话摘要 | 🔲 |
| 长期记忆 | Dream 机制 | 🔲 |

### 5. Skill 系统 🔲

| 任务 | 说明 | 状态 |
|------|------|------|
| Skill 加载器 | `.md` 文件解析 | 🔲 |
| Skill 匹配器 | 触发匹配 | 🔲 |

### 6. MCP 客户端 🔲

| 任务 | 说明 | 状态 |
|------|------|------|
| MCP 协议 | JSON-RPC 2.0 | 🔲 |
| MCP Client | 连接 MCP Server | 🔲 |
| 工具适配 | MCP → 内部格式 | 🔲 |

### 7. 适配器 🔲

| 任务 | 说明 | 状态 |
|------|------|------|
| BaseAdapter | 统一接口 | 🔲 |
| AnthropicAdapter | Claude | 🔲 |
| OpenAIAdapter | GPT | 🔲 |
| OllamaAdapter | Ollama | 🔲 |
| MiniMaxAdapter | MiniMax | 🔲 |

---

## 项目结构

```
creamcode/
├── src/creamcode/
│   ├── __init__.py
│   ├── main.py                 # CLI 入口
│   ├── app.py                  # Application 引导类
│   ├── types.py                # 核心类型定义
│   │
│   ├── core/                   # 核心模块（不可插件化）
│   │   ├── __init__.py
│   │   ├── lifecycle.py        # 生命周期管理
│   │   ├── plugin_manager.py   # 插件管理器
│   │   ├── event_bus.py        # 事件总线 (EventBus, EventSpace, Event)
│   │   └── cli_framework.py    # CLI 框架
│   │
│   ├── plugins/                # 插件系统
│   │   ├── interfaces.py       # Plugin 基类, CoreEvents, ServiceRegistry
│   │   └── system/             # 系统插件
│   │       ├── tool_system.py
│   │       ├── adapter_system.py
│   │       ├── memory_system.py
│   │       └── agent_system.py
│   │
│   ├── adapters/               # AI 适配器
│   ├── tools/                   # 工具系统
│   ├── memory/                  # 记忆系统
│   ├── skills/                  # Skill 系统
│   ├── mcp/                     # MCP 客户端
│   └── agent/                   # Agent 实现
│
├── plugins/                     # 用户插件目录
├── tests/                      # 测试
└── docs/                       # 文档
    ├── DESIGN.md               # 架构设计
    └── TASKS.md                # 本文件
```

---

## 插件开发指南

### 1. 事件订阅

```python
from creamcode.plugins.interfaces import Plugin
from creamcode.core import on

class MyPlugin(Plugin):
    name = "my-plugin"
    
    @on("lifecycle.start", priority=-100)
    async def on_start(self, event):
        # 插件初始化
        return event
    
    @on("message.incoming", priority=0)
    async def on_message(self, event):
        # 修改消息内容
        event.data["content"] = process(event.data["content"])
        return event
```

### 2. 事件发射

```python
from creamcode.core import event_bus

# 在需要的地方发射事件
await event_bus.publish(Event("custom.event", {"key": "value"}))
```

### 3. 服务注册

```python
class MyPlugin(Plugin):
    async def on_load(self, context):
        # 注册服务供其他插件使用
        context.services.register("my-service", MyService())
```

---

## 约定俗成

1. **核心模块**只有 3 个：`lifecycle`, `plugin_manager`, `cli_framework`
2. 其他所有功能通过**插件**实现
3. 模块间通信通过**事件**
4. 事件使用**装饰器**声明：`@space.event("name")`
5. 事件订阅使用**装饰器**：`@on("space.name")`
6. **单例模式**：`event_bus` 全局单例

---

## 后续任务优先级

1. **Agent 系统** - 核心交互闭环
2. **消息系统** - 会话和消息处理
3. **工具系统** - 工具注册和调用
4. **记忆系统** - 上下文管理
5. **Skill 系统** - 能力扩展
6. **MCP 客户端** - 外部工具集成
