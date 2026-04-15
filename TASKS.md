# creamcode 任务进度管理

> 最后更新：2026-04-15

---

## 任务总览

| Phase | 名称 | 任务数 | 完成数 | 状态 |
|-------|------|--------|--------|------|
| 1 | 核心框架 | 6 | 6 | ✅ 已完成 |
| 2 | 适配器 | 5 | 0 | 🔲 待开始 |
| 3 | 工具系统 | 5 | 0 | 🔲 待开始 |
| 4 | 记忆系统 | 4 | 0 | 🔲 待开始 |
| 5 | Skill + MCP | 2 | 0 | 🔲 待开始 |
| 6 | 完善 | 4 | 0 | 🔲 待开始 |

---

## Phase 1: 核心框架

| # | 任务 | 描述 | 依赖 | 状态 |
|---|------|------|------|------|
| 1.1 | 项目初始化 | 创建 `pyproject.toml`、基础目录、`__init__.py` | - | ✅ |
| 1.2 | 核心类型定义 | 定义 `Message`、`Tool`、`Response`、`Event` 等核心类型 | - | ✅ |
| 1.3 | 生命周期管理 | 实现 `LifecycleManager` 类 | 1.1 | ✅ |
| 1.4 | 事件总线 | 实现 `EventBus` 类、事件发布/订阅 | 1.1, 1.2 | ✅ |
| 1.5 | 插件管理器 | 实现 `PluginManager`、加载、卸载、依赖解析 | 1.3, 1.4 | ✅ |
| 1.6 | CLI 框架 | 实现 `CLIRegistry`、命令注册、解析、分发 | 1.4 | ✅ |

---

## Phase 2: 适配器

| # | 任务 | 描述 | 依赖 | 状态 |
|---|------|------|------|------|
| 2.1 | 适配器框架 | 实现 `BaseAdapter`、错误类型、重试机制、Token 计数 | 1.6 | 🔲 |
| 2.2 | Claude 适配器 | 实现 `AnthropicAdapter` | 2.1 | 🔲 |
| 2.3 | OpenAI 适配器 | 实现 `OpenAIAdapter` | 2.1 | 🔲 |
| 2.4 | Ollama 适配器 | 实现 `OllamaAdapter` | 2.1 | 🔲 |
| 2.5 | MiniMax 适配器 | 实现 `MiniMaxAdapter`（示例插件） | 2.1 | 🔲 |

---

## Phase 3: 工具系统

| # | 任务 | 描述 | 依赖 | 状态 |
|---|------|------|------|------|
| 3.1 | 工具注册表 | 实现 `ToolRegistry`、`@tool` 装饰器 | 1.6 | 🔲 |
| 3.2 | Bash 工具 | 实现 `BashTool` | 3.1 | 🔲 |
| 3.3 | File 工具 | 实现 `FileReadTool`、`FileWriteTool`、`FileEditTool` | 3.1 | 🔲 |
| 3.4 | Web 工具 | 实现 `WebFetchTool`、`WebSearchTool` | 3.1 | 🔲 |
| 3.5 | 内置工具集成 | 将工具注册到系统 | 3.2, 3.3, 3.4 | 🔲 |

---

## Phase 4: 记忆系统

| # | 任务 | 描述 | 依赖 | 状态 |
|---|------|------|------|------|
| 4.1 | 工作记忆 | 实现 `WorkingMemory`、Token 限制、截断 | 2.1 | 🔲 |
| 4.2 | 短期记忆 | 实现 `ShortTermMemory`、会话摘要生成 | 4.1 | 🔲 |
| 4.3 | 长期记忆 | 实现 `LongTermMemory`、三门触发、Dream 逻辑 | 4.2 | 🔲 |
| 4.4 | 上下文管理 | 实现 `ContextWindowManager`、消息准备 | 4.1, 4.2, 4.3 | 🔲 |

---

## Phase 5: Skill + MCP

| # | 任务 | 描述 | 依赖 | 状态 |
|---|------|------|------|------|
| 5.1 | Skill 系统 | 实现 Skill 加载器、解析器、触发匹配 | 3.1 | 🔲 |
| 5.2 | MCP 客户端 | 实现 `MCPClient`、Server 管理、工具转换 | 3.1 | 🔲 |

---

## Phase 6: 完善

| # | 任务 | 描述 | 依赖 | 状态 |
|---|------|------|------|------|
| 6.1 | 配置管理 | 实现配置加载、合并、持久化 | 1.6 | 🔲 |
| 6.2 | 成本追踪 | 实现 `CostTracker`、预算检查 | 2.1 | 🔲 |
| 6.3 | 测试 | 编写单元测试、集成测试 | 所有前置 | 🔲 |
| 6.4 | 文档完善 | 补充 README、API 文档 | 所有前置 | 🔲 |

---

## 任务详情

### Phase 1 详细任务

#### 1.1 项目初始化
```
文件:
- pyproject.toml
- src/creamcode/__init__.py
- src/creamcode/main.py
- src/creamcode/types.py
- src/creamcode/utils.py
- src/creamcode/core/__init__.py
- src/creamcode/plugins/__init__.py
- src/creamcode/plugins/system/__init__.py
- src/creamcode/plugins/user/__init__.py
- .gitignore
- README.md
```

#### 1.2 核心类型定义
```
类型:
- Message (role, content, name, tool_calls, etc.)
- Tool (name, description, parameters, etc.)
- Response (content, tool_calls, usage, model, stop_reason)
- ToolCall (id, name, arguments)
- TokenUsage (input_tokens, output_tokens)
- Event (name, source, data)
- PluginType (SYSTEM, USER)
- PluginMetadata (name, version, type, depends_on)
```

#### 1.3 生命周期管理
```
类:
- LifecycleManager
  - on_startup()
  - on_shutdown()
  - get_state() -> LifecycleState
```

#### 1.4 事件总线
```
类:
- EventBus
  - publish(event: Event)
  - subscribe(event_name: str, handler: Callable)
  - unsubscribe(event_name: str, handler: Callable)
- Event (name: str, source: str, data: dict)
```

#### 1.5 插件管理器
```
类:
- PluginManager
  - load_plugin(plugin_path: Path)
  - unload_plugin(name: str)
  - enable_plugin(name: str)
  - disable_plugin(name: str)
  - reload_plugin(name: str)
  - get_plugin(name: str) -> Plugin | None
  - list_plugins() -> list[PluginMetadata]
  
- Plugin (基类)
  - name, version, type, depends_on
  - on_load(), on_enable(), on_disable(), on_unload()
  - register_commands(cli: CLIRegistry)
```

#### 1.6 CLI 框架
```
类:
- CLIRegistry
  - register(namespace: str, name: str, handler: Callable, plugin: str)
  - unregister(namespace: str, name: str)
  - get_handler(namespace: str, name: str) -> Callable | None
  - list_commands() -> list[CommandInfo]
  
- CLIApp
  - parse(args: list[str])
  - execute(namespace: str, name: str, args: dict)
  - run()  # 交互模式

命令:
- 内置: --help, --version, --debug, <prompt>
- 插件注册: config/*, adapter/*, skill/*, mcp/*, plugin/*, memory/*, session/*
```

---

## 进度记录

| 日期 | 完成任务 | 说明 |
|------|----------|------|
| 2026-04-15 | - | 项目创建，设计文档完成 |
| 2026-04-15 | 1.1 - 1.6 | Phase 1 核心框架完成 |
