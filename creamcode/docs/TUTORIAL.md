# creamcode 教程

> 轻量级 AI 编程 CLI 工具，完全插件化架构。

## 安装

```bash
# 克隆项目
git clone https://github.com/CocoonOvO/cream-code.git
cd cream-code

# 安装依赖
pip install -e .

# 或使用 poetry
poetry install
```

## 快速开始

### 命令行模式

```bash
# 显示版本
creamcode --version

# 显示帮助
creamcode --help

# 交互模式
creamcode

# 单次对话
creamcode "帮我写一个 Hello World"

# 调试模式
creamcode --debug "分析这个代码"
```

### Python API 模式

```python
import asyncio
from creamcode.app import Application

async def main():
    # 创建应用
    app = Application()
    
    # 初始化
    await app.initialize()
    
    # 使用组件
    print(f"EventBus: {app.event_bus}")
    print(f"ToolRegistry: {app.tool_registry}")
    print(f"Agent: {app.agent}")
    
    # 关闭
    await app.shutdown()

asyncio.run(main())
```

---

## 核心概念

### 1. Application 引导类

Application 是整个系统的入口，负责初始化和协调所有子系统：

```python
from creamcode.app import Application

app = Application(config={"debug": True})
await app.initialize()
```

**子系统**：
- `event_bus` - 事件总线
- `tool_registry` - 工具注册表
- `cli_registry` - CLI 命令注册
- `plugin_manager` - 插件管理器
- `adapter_registry` - AI 适配器管理
- `agent` - Agent 协调器
- `working_memory` / `short_term_memory` / `long_term_memory` - 三级记忆

### 2. 工具系统

creamcode 内置多种工具：

```python
from creamcode.tools.registry import ToolRegistry
from creamcode.tools.builtins import register_builtins

registry = ToolRegistry(event_bus)
register_builtins(registry)

# 列出所有工具
tools = registry.list_tools()
for tool in tools:
    print(f"{tool.name}: {tool.description}")

# 调用工具
result = await registry.call_tool(
    "Bash",
    {"command": "ls -la"},
    tool_call_id="call_001"
)
print(result.content)
```

**内置工具**：
| 工具 | 用途 | 示例 |
|------|------|------|
| `Bash` | 执行 shell 命令 | `{"command": "echo hello"}` |
| `FileRead` | 读取文件 | `{"path": "./README.md"}` |
| `FileWrite` | 写入文件 | `{"path": "./output.txt", "content": "Hello"}` |
| `FileEdit` | 编辑文件 | `{"path": "./file.py", "old": "foo", "new": "bar"}` |
| `WebFetch` | 获取网页 | `{"url": "https://example.com"}` |
| `WebSearch` | 搜索网络 | `{"query": "python tutorial"}` |

### 3. 记忆系统

三级记忆系统：

```python
from creamcode.memory.working import WorkingMemory
from creamcode.memory.short_term import ShortTermMemory
from creamcode.memory.long_term import LongTermMemory
from creamcode.memory.context import ContextWindowManager
from creamcode.types import Message, MessageRole

# 工作记忆 - Token 限制
wm = WorkingMemory(max_tokens=100000, reserved_tokens=4096)
wm.add(Message(role=MessageRole.SYSTEM, content="You are helpful."))
wm.add(Message(role=MessageRole.USER, content="Hello!"))

# 短期记忆 - 会话摘要
stm = ShortTermMemory(storage_dir="./memory", max_summaries=10)

# 长期记忆 - 三门触发
ltm = LongTermMemory(storage_dir="./memory/long_term")

# 上下文管理器 - 整合所有记忆
context = ContextWindowManager(
    working_memory=wm,
    short_term_memory=stm,
    long_term_memory=ltm,
    event_bus=event_bus
)

# 准备消息
messages = await context.prepare_messages(
    system_prompt="You are a helpful assistant.",
    query="Say hello"
)
```

### 4. 适配器系统

支持多种 AI 提供商：

```python
from creamcode.adapters.anthropic import AnthropicAdapter
from creamcode.adapters.openai import OpenAIAdapter
from creamcode.adapters.ollama import OllamaAdapter
from creamcode.adapters.minimax import MiniMaxAdapter

# Anthropic (Claude)
adapter = AnthropicAdapter(
    api_key="sk-ant-...",
    model="claude-3-5-sonnet-20241022"
)

# 发送消息
response = await adapter.send_messages(messages, tools)
print(response.content)
```

### 5. Agent 系统

Agent 协调工具调用和记忆：

```python
from creamcode.agent import DefaultAgent

agent = DefaultAgent(
    event_bus=event_bus,
    tool_registry=tool_registry,
    context_manager=context_manager
)

# 设置适配器
agent.set_adapter(adapter)

# 处理用户消息
response = await agent.process(
    user_message="帮我分析这个代码",
    system_prompt="你是一个代码助手"
)
print(response.content)
```

### 6. 配置管理

```python
from creamcode.config import AppConfig, ConfigLoader

# 加载配置（合并多层）
loader = ConfigLoader()
config = loader.load(cli_overrides={"debug": True})

# 直接创建
config = AppConfig(
    debug=False,
    max_tokens=100000,
    monthly_budget=100.0,
    default_adapter="anthropic"
)
```

**配置优先级**：命令行 > 项目配置 > 全局配置

### 7. 成本追踪

```python
from creamcode.cost import CostTracker, DefaultPricingModel

# 创建追踪器
tracker = CostTracker(
    monthly_budget=100.0,
    session_budget=10.0
)

# 记录 API 调用
tracker.record(
    model="claude-3-5-sonnet",
    input_tokens=1000,
    output_tokens=500
)

# 检查预算
allowed, reason = tracker.check_budget()
if not allowed:
    print(f"预算超限: {reason}")

# 获取使用摘要
summary = tracker.get_usage_summary()
print(f"总成本: ${summary['total_cost']:.4f}")
print(f"输入 tokens: {summary['total_input_tokens']}")
print(f"输出 tokens: {summary['total_output_tokens']}")
```

### 8. Skill 系统

Skill 是基于 Markdown 的任务扩展：

```python
from creamcode.skills import SkillRegistry

registry = SkillRegistry(skills_dir="./skills")

# 加载所有 skills
registry.load_all()

# 查找匹配的 skills
matches = registry.find_matching_skills(
    "我需要分析代码质量",
    top_k=3
)

for skill, score in matches:
    print(f"{skill.name} (score: {score:.2f})")
    print(f"  {skill.description}")
```

### 9. MCP 客户端

连接 MCP 外部工具服务器：

```python
from creamcode.mcp import MCPServerManager, MCPServerConfig

manager = MCPServerManager()

# 添加 MCP Server
config = MCPServerConfig(
    name="chrome-devtools",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-chrome-devtools"]
)
manager.add_server(config)

# 启动 server
await manager.start_server("chrome-devtools")

# 注册工具到 registry
await manager.register_tools_to_registry(tool_registry)

# 获取所有工具
tools = await manager.get_all_tools_async()
```

### 10. 插件系统

```python
from creamcode.core.plugin_manager import Plugin, PluginManager
from creamcode.types import PluginType

class MyPlugin(Plugin):
    name = "my-plugin"
    version = "0.1.0"
    type = PluginType.USER
    depends_on = []
    description = "A custom plugin"
    
    async def on_load(self):
        print(f"Plugin {self.name} loaded")
    
    def register_commands(self, cli):
        cli.register("my-plugin", "hello", self.hello_command)

# 加载插件
manager = PluginManager(event_bus)
plugin = await manager.load_plugin(Path("./plugins/my_plugin.py"))

# 启用插件
await manager.enable_plugin("my-plugin")
```

---

## 事件系统

事件总线用于模块间解耦通信：

```python
# 订阅事件
await event_bus.subscribe("tool.executed", my_handler)

# 发布事件
await event_bus.publish(Event(
    name="tool.executed",
    source="my-plugin",
    data={"tool": "Bash", "result": "success"}
))

# 取消订阅
await event_bus.unsubscribe("tool.executed", my_handler)
```

---

## 完整示例

```python
import asyncio
from creamcode.app import Application
from creamcode.types import Message, MessageRole

async def main():
    # 1. 创建应用
    app = Application({"debug": True})
    await app.initialize()
    
    print(f"Initialized: {app.is_initialized}")
    print(f"Tools: {[t.name for t in app.tool_registry.list_tools()]}")
    
    # 2. 注册 MCP 服务器（可选）
    # await app.mcp_manager.add_server(config)
    # await app.mcp_manager.start_all()
    
    # 3. 设置适配器
    from creamcode.adapters.anthropic import AnthropicAdapter
    adapter = AnthropicAdapter(api_key="your-key", model="claude-3-5-sonnet-20241022")
    app.agent.set_adapter(adapter)
    
    # 4. 处理对话
    response = await app.agent.process(
        user_message="帮我写一个快速排序",
        system_prompt="你是一个专业的程序员助手。"
    )
    
    print(f"Response: {response.content}")
    
    # 5. 检查成本
    from creamcode.cost import CostTracker
    tracker = CostTracker(monthly_budget=100)
    tracker.record("claude-3-5-sonnet", 1000, 500)
    print(f"Cost: ${tracker.get_total_cost():.4f}")
    
    # 6. 关闭
    await app.shutdown()

asyncio.run(main())
```

---

## 目录结构

```
creamcode/
├── src/creamcode/
│   ├── core/          # 核心：EventBus, PluginManager, CLI
│   ├── adapters/      # AI 适配器
│   ├── tools/         # 工具系统
│   ├── memory/        # 记忆系统
│   ├── skills/         # Skill 系统
│   ├── mcp/           # MCP 客户端
│   ├── agent/          # Agent
│   ├── config/         # 配置
│   └── cost/          # 成本追踪
├── plugins/           # 插件
├── skills/            # Skill 文件
└── tests/             # 测试
```

---

## 测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定模块测试
python -m pytest tests/test_tools/ -v

# 带覆盖率
python -m pytest tests/ --cov=creamcode --cov-report=html
```

---

## 下一步

- 查看 [DESIGN.md](./docs/DESIGN.md) 了解架构设计
- 查看 [TASKS.md](./TASKS.md) 了解开发进度
- 查看示例代码 [examples/](./examples/)