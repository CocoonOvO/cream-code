# creamcode 设计文档

> 轻量级 AI 编程 CLI 工具
> 版本：0.1.0
> 日期：2026-04-15

---

## 1. 概述

### 1.1 目标定位

creamcode 是一个类似 Claude Code 的轻量级 AI 编程 CLI 工具，使用 Python 实现，易于扩展。

### 1.2 核心特性

- **多端支持**：通过插件架构支持 Anthropic Claude、OpenAI、Ollama、MiniMax 等
- **Skill 系统**：基于 `.md` 文件的标准 Skill 格式
- **MCP 支持**：工具调用模式连接外部 MCP 服务器
- **多级记忆**：工作记忆 → 短期记忆 → 长期记忆
- **完全插件化**：除核心生命周期外，所有功能均为插件

---

## 2. 架构总览

### 2.1 核心与插件分离

```
┌─────────────────────────────────────────────────────────────┐
│                      creamcode (核心)                        │
├─────────────────────────────────────────────────────────────┤
│  核心生命周期管理                                             │
│  插件管理器                                                  │
│  事件总线                                                    │
│  CLI 框架                                                    │
│  适配器框架（不包含具体适配器实现）                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       系统插件                                │
│  event-bus | adapter-core | cli-core | tool-system          │
│  memory-system | skill-system | mcp-client                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       用户插件                                │
│  adapter-anthropic | adapter-openai | adapter-ollama        │
│  adapter-minimax | 其他扩展                                  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 目录结构

```
creamcode/
├── src/creamcode/
│   ├── __init__.py
│   ├── main.py                 # 入口
│   ├── core/                   # 核心模块
│   │   ├── __init__.py
│   │   ├── lifecycle.py        # 生命周期管理
│   │   ├── plugin_manager.py   # 插件管理器
│   │   ├── event_bus.py        # 事件总线
│   │   ├── cli_framework.py    # CLI 框架
│   │   └── adapter_framework.py # 适配器框架
│   ├── types.py                # 核心类型定义
│   └── utils.py                # 工具函数
│
├── plugins/
│   ├── system/                 # 系统插件（必有）
│   │   ├── __init__.py
│   │   ├── event_bus.py        # (核心内置)
│   │   ├── adapter_core.py     # 适配器框架
│   │   ├── cli_core.py         # CLI 框架
│   │   ├── tool_system.py      # 工具系统
│   │   ├── memory_system.py    # 记忆系统
│   │   ├── skill_system.py     # Skill 系统
│   │   └── mcp_client.py       # MCP 客户端
│   │
│   └── user/                   # 用户插件（可选）
│       └── __init__.py
│
├── adapters/                   # 适配器插件（用户插件）
│   ├── __init__.py
│   ├── anthropic.py            # Claude 适配器
│   ├── openai.py              # GPT 适配器
│   ├── ollama.py              # Ollama 适配器
│   └── minimax.py             # MiniMax 适配器（示例）
│
├── skills/                     # Skill 文件目录
│   └── README.md
│
├── docs/                       # 文档
│   └── DESIGN.md              # 本文档
│
├── tests/                      # 测试
│
└── examples/                   # 示例
    ├── plugin_example/        # 插件示例
    └── skill_example/         # Skill 示例
```

---

## 3. 核心模块

### 3.1 生命周期管理

```python
class Lifecycle:
    """生命周期状态"""
    
    async def on_startup(self):
        """启动时调用"""
        pass
    
    async def on_shutdown(self):
        """关闭时调用"""
        pass
```

### 3.2 插件管理器

```python
class Plugin:
    """插件基类"""
    
    name: str
    version: str
    type: PluginType  # SYSTEM | USER
    
    # 生命周期
    def on_load(self): ...
    def on_enable(self): ...
    def on_disable(self): ...
    def on_unload(self): ...
    
    # 依赖声明
    depends_on: list[str] = []
    
    # CLI 命令注册
    def register_commands(self, cli: CLIRegistry): ...
    
    # 钩子装饰器
    @hook("event_name")
    def handler(self, event): ...
```

### 3.3 事件总线

```python
class Event:
    """事件格式 - 最灵活轻量"""
    name: str
    source: str  # 插件名
    data: dict   # 任意结构

class EventBus:
    def publish(self, event: Event): ...
    def subscribe(self, event_name: str, handler: Callable): ...
    def unsubscribe(self, event_name: str, handler: Callable): ...
```

### 3.4 CLI 框架

```python
class CLIRegistry:
    """CLI 命令注册表"""
    
    def register(self, namespace: str, name: str, handler: Callable, plugin: str): ...
    def unregister(self, namespace: str, name: str): ...
    def get_handler(self, namespace: str, name: str) -> Callable | None: ...
```

命令格式：`creamcode <namespace> <command> [args]`

---

## 4. 系统插件

### 4.1 加载顺序

系统插件按以下顺序加载：

| 顺序 | 插件 | 职责 |
|------|------|------|
| 1 | event-bus | 事件总线（核心基础设施） |
| 2 | adapter-core | 适配器框架 |
| 3 | cli-core | CLI 框架 |
| 4 | tool-system | 工具系统 |
| 5 | memory-system | 记忆系统 |
| 6 | skill-system | Skill 系统 |
| 7 | mcp-client | MCP 客户端 |

### 4.2 系统插件详情

#### event-bus
- 提供事件发布/订阅
- 所有其他插件的基础

#### adapter-core
- 定义适配器基类 `BaseAdapter`
- 工具格式转换（注册时转换 + 适配器兜底）
- 错误标准化

#### cli-core
- CLI 命令解析
- 帮助信息生成
- 交互模式管理

#### tool-system
- 工具注册表
- 内置工具（Bash、File、WebFetch）
- 工具调用管理

#### memory-system
- 工作记忆（Token 限制，智能截断）
- 短期记忆（会话摘要）
- 长期记忆（三门触发 Dream）

#### skill-system
- Skill 加载器
- Skill 注册表
- 触发匹配

#### mcp-client
- MCP Server 管理
- 工具格式转换
- 连接生命周期

---

## 5. 适配器插件

### 5.1 适配器接口

```python
class BaseAdapter(ABC):
    """统一适配器接口"""
    
    @abstractmethod
    async def send_messages(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        model: str | None = None,
    ) -> Response:
        """发送消息，获取响应"""
        pass
    
    @abstractmethod
    async def stream_messages(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        model: str | None = None,
    ) -> AsyncIterator[ResponseChunk]:
        """流式响应"""
        pass

class Response(TypedDict):
    content: str
    tool_calls: list[ToolCall] | None
    usage: TokenUsage
    model: str
    stop_reason: str

class ToolCall(TypedDict):
    id: str
    name: str
    arguments: dict
```

### 5.2 工具格式转换

工具注册时同时提供统一格式和厂商格式：

```python
class Tool:
    name: str
    description: str
    parameters: dict  # JSON Schema，统一格式
    
    # 厂商特定格式（可选）
    anthropic_schema: dict | None = None
    openai_function: dict | None = None
```

转换优先级：
1. 优先使用注册的厂商格式
2. 没有则适配器尝试转换

### 5.3 错误类型

```python
class AdapterError(Exception):
    code: str
    message: str
    retryable: bool  # 是否可重试

class RateLimitError(AdapterError): ...
class AuthError(AdapterError): ...
class ContextLengthError(AdapterError): ...
class ModelNotFoundError(AdapterError): ...
```

### 5.4 重试机制

```python
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    retryable_codes: set[str] = {"rate_limit", "timeout", "server_error"}
```

### 5.5 自适应限流

根据 API 响应自动调整请求速率：

```python
class AdaptiveRateLimiter:
    """自适应限流"""
    
    current_rate: float = 10.0  # 请求/秒
    backoff_factor: float = 0.5
    
    def on_rate_limit_hit(self):
        self.current_rate *= self.backoff_factor
    
    def on_success(self):
        self.current_rate = min(self.current_rate * 1.1, self.max_rate)
```

---

## 6. 工具系统

### 6.1 工具注册

```python
@tool(name="Bash", description="Execute shell command")
def bash(command: str) -> ToolResult:
    ...
```

### 6.2 内置工具

| 工具 | 说明 |
|------|------|
| Bash | 执行 Shell 命令 |
| FileRead | 读取文件 |
| FileWrite | 写入文件 |
| FileEdit | 编辑文件（基于 diff） |
| Glob | 文件搜索 |
| Grep | 内容搜索 |
| WebFetch | 获取网页内容 |
| WebSearch | 搜索网页 |

---

## 7. 记忆系统

### 7.1 三级记忆架构

```
工作记忆 ──→ 短期记忆 ──→ 长期记忆
(会话内)    (会话摘要)   (Dream整理)
```

### 7.2 工作记忆

```python
class WorkingMemory:
    """工作记忆：当前会话消息"""
    
    max_tokens: int = 100000  # 可配置
    
    def add(self, message: Message): ...
    def get_context(self) -> list[Message]: ...
    
    def truncate(self, max_tokens: int):
        """Token 超限时：
        1. 触发短期记忆更新（生成会话摘要）
        2. 清理已摘要内容
        3. 若仍超限，截断（保留系统提示 + 最近消息）
        """
```

### 7.3 短期记忆

```python
class ShortTermMemory:
    """短期记忆：最近对话的摘要"""
    
    max_summaries: int = 10
    
    def add_summary(self, summary: ConversationSummary): ...
    def get_recent_context(self) -> str: ...
```

触发时机：会话结束时

### 7.4 长期记忆

```python
class LongTermMemory:
    """长期记忆：通过 Dream 整理的持久化记忆"""
    
    memory_dir: Path
    topics: dict[str, MemoryTopic]
    
    async def dream(self, context: MemoryContext): ...
```

### 7.5 三门触发机制

| 门 | 条件 |
|----|------|
| 时间门 | 24 小时未执行 Dream |
| 会话数门 | 至少 5 个新会话 |
| 锁门 | 获得整理锁（防止并发） |

三个都满足时触发 Dream。

### 7.6 上下文窗口管理

```python
class ContextWindowManager:
    async def prepare_messages(
        self,
        working: WorkingMemory,
        short_term: ShortTermMemory,
        long_term: LongTermMemory,
        max_tokens: int,
    ) -> list[Message]:
        """
        1. 从长期记忆获取相关主题记忆
        2. 拼接短期记忆摘要
        3. 拼接工作记忆消息
        4. 按 token 限制截断
        """
```

截断优先级：系统提示 > 最近消息 > 早期消息

---

## 8. Skill 系统

### 8.1 Skill 文件格式

```markdown
---
name: react-developer
description: React 开发助手
version: 1.0.0
author: your-name
trigger:
  patterns:
    - "react"
    - "component"
  type: keyword
---

# Skill 系统提示词
你是一个专业的 React 开发助手...

## 可用工具
- file_read
- file_write
- bash
```

### 8.2 触发类型

| 类型 | 说明 |
|------|------|
| keyword | 消息内容匹配关键词 |
| regex | 正则匹配 |
| always | 始终激活 |

---

## 9. MCP 支持

### 9.1 架构

```
creamcode ──→ MCP Client ──→ MCP Server ──→ 外部服务
                    │
                    └── 工具注册到 Agent
```

### 9.2 配置格式

```json
// ~/.config/creamcode/mcp.json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
    }
  }
}
```

### 9.3 工具转换

MCP Client 模块统一处理各 Server 的工具格式转换，转换为内部 `Tool` 格式。

---

## 10. 插件系统

### 10.1 目录结构

```
~/.config/creamcode/
├── plugins/
│   ├── system/           # 系统插件
│   └── user/            # 用户插件
├── skills/              # Skill 文件
├── memory/              # 记忆存储
├── sessions/            # 会话历史
├── config.json
└── mcp.json
```

### 10.2 插件元数据

```python
# plugins/system/my_plugin/__init__.py
class MyPlugin(Plugin):
    name = "my-plugin"
    version = "1.0.0"
    type = PluginType.SYSTEM
    depends_on = ["event-bus"]
```

### 10.3 钩子系统

```python
# 可用钩子
BEFORE_SEND_MESSAGES = "before_send_messages"
AFTER_RECEIVE_RESPONSE = "after_receive_response"
BEFORE_TOOL_CALL = "before_tool_call"
AFTER_TOOL_RESULT = "after_tool_result"
SESSION_START = "session_start"
SESSION_END = "session_end"
MEMORY_CONSOLIDATE = "memory_consolidate"
MEMORY_RETRIEVE = "memory_retrieve"
COMMAND_REGISTERED = "command_registered"
COMMAND_EXECUTED = "command_executed"
PLUGIN_LOADED = "plugin_loaded"
PLUGIN_UNLOADED = "plugin_unloaded"
ERROR = "error"
```

### 10.4 装饰器注册

```python
class MyPlugin(Plugin):
    @hook("before_send_messages")
    async def on_before_send(self, event):
        # 处理逻辑
        pass
```

---

## 11. 配置管理

### 11.1 配置层级

| 层级 | 路径 | 说明 |
|------|------|------|
| 全局 | `~/.config/creamcode/config.json` | 所有项目共享 |
| 项目 | `.creamcode.json` | 当前项目 |
| 命令行 | `--key value` | 运行时参数 |

### 11.2 优先级

命令行 > 项目配置 > 全局配置

---

## 12. CLI 命令

### 12.1 内置命令

```bash
creamcode                     # 交互模式
creamcode "单次对话"          # 单次对话
creamcode --help              # 帮助
creamcode --version           # 版本
creamcode --debug             # 调试模式
```

### 12.2 插件注册命令

| 命名空间 | 命令 | 说明 |
|----------|------|------|
| config | show, edit, get, set, reset | 配置管理 |
| adapter | list, info, test, set-default | 适配器管理 |
| skill | list, info, enable, disable, install, uninstall | Skill 管理 |
| mcp | list, add, remove, start, stop, restart, test | MCP 管理 |
| plugin | list, info, enable, disable, reload, install, uninstall | 插件管理 |
| memory | status, working, short-term, long-term, clear, dream, consolidate | 记忆管理 |
| session | list, show, resume, delete | 会话管理 |

---

## 13. 成本控制

### 13.1 Token 追踪

```python
class CostTracker:
    session_usage: dict[str, int]
    total_usage: dict[str, int]
    
    def record(self, model: str, usage: TokenUsage): ...
    def get_cost(self) -> float: ...
```

### 13.2 预算策略

| 策略 | 行为 |
|------|------|
| reject | 预算用完停止请求 |
| warn | 超支警告但继续 |
| downgrade | 自动切换便宜模型 |

默认：reject

---

## 14. 错误处理

### 14.1 错误恢复

- 适配器错误统一转换为 `AdapterError`
- 可重试错误自动指数退避重试
- 不可重试错误立即抛出

### 14.2 插件隔离

- 插件加载失败不影响其他插件
- 失败插件标记为 unavailable
- 事件总线错误不影响主流程

---

## 15. 实现计划

### Phase 1: 核心框架
- [ ] 项目结构
- [ ] 核心生命周期
- [ ] 插件管理器
- [ ] 事件总线
- [ ] CLI 框架

### Phase 2: 适配器
- [ ] 适配器框架
- [ ] Claude 适配器
- [ ] OpenAI 适配器
- [ ] Ollama 适配器
- [ ] MiniMax 适配器（示例）

### Phase 3: 工具系统
- [ ] 工具注册表
- [ ] Bash 工具
- [ ] File 工具
- [ ] Web 工具

### Phase 4: 记忆系统
- [ ] 工作记忆
- [ ] 短期记忆
- [ ] 长期记忆（Dream）

### Phase 5: Skill + MCP
- [ ] Skill 系统
- [ ] MCP 客户端

### Phase 6: 完善
- [ ] 配置管理
- [ ] 成本追踪
- [ ] 测试
- [ ] 文档
