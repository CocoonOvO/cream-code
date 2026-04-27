# creamcode 设计文档

> 轻量级 AI 编程 CLI 工具
> 版本：0.1.0

---

## 1. 架构总览

### 1.1 核心与插件分离

```
┌─────────────────────────────────────────────────────────────┐
│                      creamcode (核心)                        │
├─────────────────────────────────────────────────────────────┤
│  core/                                                    │
│    lifecycle.py      - 生命周期管理 (生命周期事件)            │
│    event_bus.py     - 事件总线 (EventBus, EventSpace)        │
│    plugin_manager.py - 插件管理器 (插件事件)                  │
│    cli_framework.py - CLI 框架 (CLI 事件)                   │
├─────────────────────────────────────────────────────────────┤
│  plugins/                                                 │
│    interfaces.py   - Plugin 基类, CoreEvents 常量表         │
│    system/         - 系统插件 (tool, adapter, memory, agent) │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 设计原则

1. **核心模块最小化**：只有 3 个核心模块（lifecycle, plugin_manager, cli_framework）
2. **一切皆事件**：模块间通信通过事件总线
3. **装饰器声明**：使用 `@space.event("name")` 声明事件发射
4. **插件自由扩展**：任何功能都可以通过插件实现

---

## 2. 事件系统

### 2.1 核心概念

```
EventBus (单例)
├── event_spaces: dict[str, EventSpace]
├── _handlers: dict[str, list[tuple[int, EventHandler]]]
│
├── create_space("name") → EventSpace
├── on("event.path", priority) → 订阅装饰器
└── publish(Event) → Event | None
```

### 2.2 事件发射

```python
# 1. 创建 EventSpace
_lifecycle = event_bus.create_space("lifecycle")

# 2. 使用装饰器声明事件
class LifecycleManager:
    @_lifecycle.event("start")
    async def start(self):
        # 方法执行后自动发布 lifecycle.start 事件
        pass
```

### 2.3 事件订阅

```python
# 1. 使用 @on 装饰器订阅
@on("lifecycle.start", priority=-100)
async def on_start(event):
    return event

# 2. 链式处理 - handler 可修改 event.data 并返回
@on("message.incoming", priority=0)
async def process_message(event):
    event.data["content"] = filter_content(event.data["content"])
    return event
```

### 2.4 核心事件列表

| 事件 | 发射方法 | 说明 |
|------|---------|------|
| `lifecycle.start` | `LifecycleManager.start()` | 应用启动 |
| `lifecycle.stop` | `LifecycleManager.stop()` | 应用关闭 |
| `plugin.load` | `PluginManager.load_plugin()` | 插件加载 |
| `plugin.unload` | `PluginManager.unload_plugin()` | 插件卸载 |
| `plugin.enable` | `PluginManager.enable_plugin()` | 插件启用 |
| `plugin.disable` | `PluginManager.disable_plugin()` | 插件禁用 |
| `cli.start` | `CLIApp.initialize()` | CLI 初始化 |
| `cli.command` | `CLIApp.execute()` | 命令执行 |
| `cli.interactive` | `InteractiveMode.run()` | 交互模式 |

### 2.5 事件常量表

位于 `creamcode/plugins/interfaces.py` 的 `CoreEvents` 类，仅供开发参考：

```python
class CoreEvents:
    LIFECYCLE_START = "lifecycle.start"
    LIFECYCLE_STOP = "lifecycle.stop"
    PLUGIN_LOAD = "plugin.load"
    # ... 更多常量
```

---

## 3. 目录结构

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
│   │   ├── event_bus.py        # 事件总线
│   │   └── cli_framework.py    # CLI 框架
│   │
│   ├── plugins/                # 插件系统
│   │   ├── interfaces.py       # Plugin 基类, CoreEvents
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
```

---

## 4. 插件开发

### 4.1 插件基类

```python
from creamcode.plugins.interfaces import Plugin

class MyPlugin(Plugin):
    name = "my-plugin"
    version = "1.0.0"
    depends_on = []
    
    async def on_load(self, context):
        """插件加载时调用"""
        pass
    
    async def on_enable(self):
        """插件启用时调用"""
        pass
```

### 4.2 事件订阅

```python
from creamcode.core import on

class MyPlugin(Plugin):
    @on("lifecycle.start", priority=-100)
    async def on_start(self, event):
        """应用启动时执行"""
        return event
    
    @on("message.incoming", priority=0)
    async def on_message(self, event):
        """处理收到的消息"""
        return event
```

### 4.3 CLI 命令注册

```python
class MyPlugin(Plugin):
    def register_commands(self, cli_registry):
        cli_registry.register("myns", "cmd", self.handle_cmd, self.name)

    async def handle_cmd(self, args):
        """处理命令"""
        pass
```

---

## 5. 系统插件

### 5.1 系统插件列表

| 插件 | 职责 |
|------|------|
| tool-system | 工具注册表和内置工具 |
| adapter-system | AI 适配器注册 |
| memory-system | 三级记忆系统 |
| agent-system | 默认 Agent 实现 |

### 5.2 系统插件加载

在 `Application` 初始化时从 `creamcode.plugins.system.*` 模块加载。

---

## 6. CLI 命令

### 6.1 内置命令

```bash
creamcode                     # 交互模式
creamcode --help             # 帮助
creamcode --version          # 版本
creamcode --debug            # 调试模式
```

### 6.2 核心模块命令

| 命名空间 | 命令 | 说明 |
|----------|------|------|
| lifecycle | start, stop | 生命周期管理 |
| plugin | load, unload, enable, disable | 插件管理 |

---

## 7. 待开发功能

- [ ] Agent 系统
- [ ] 消息系统 (session, message)
- [ ] 工具系统
- [ ] 记忆系统
- [ ] Skill 系统
- [ ] MCP 客户端

详见 [TASKS.md](./TASKS.md)
