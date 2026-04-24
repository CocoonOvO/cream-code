# creamcode

> 轻量级 AI 编程 CLI 工具，使用 Python 实现，完全插件化架构。

## 特性

- **多端支持**：通过适配器架构支持 Anthropic Claude、OpenAI、Ollama、MiniMax 等
- **完全插件化**：除核心生命周期外，所有功能均为插件
- **Skill 系统**：基于 `.md` 文件的标准 Skill 格式
- **MCP 支持**：通过 MCP 协议连接外部工具服务器
- **多级记忆**：工作记忆 → 短期记忆 → 长期记忆
- **成本控制**：Token 追踪和预算管理

## 安装

```bash
pip install -e .
```

## 快速开始

```bash
# 交互模式
creamcode

# 单次对话
creamcode "帮我写一个 Hello World"

# 调试模式
creamcode --debug "帮我分析这个代码"
```

## 架构

```
creamcode/
├── src/creamcode/
│   ├── core/           # 核心模块 (EventBus, PluginManager, CLI)
│   ├── adapters/       # AI 适配器 (Anthropic, OpenAI, Ollama, MiniMax)
│   ├── tools/          # 工具系统 (Bash, File, Web)
│   ├── memory/        # 三级记忆系统
│   ├── skills/         # Skill 加载和匹配
│   ├── mcp/           # MCP 客户端
│   ├── agent/          # Agent 协调器
│   ├── config/         # 配置管理
│   └── cost/           # 成本追踪
└── plugins/            # 插件目录
```

## 核心组件

### Application

```python
from creamcode.app import Application

app = Application()
await app.initialize()
await app.run_interactive()
```

### Agent

```python
from creamcode.agent import DefaultAgent

agent = DefaultAgent(event_bus, tool_registry, context_manager)
response = await agent.process("用户消息", system_prompt="系统提示")
```

### 工具系统

```python
from creamcode.tools.registry import ToolRegistry

registry = ToolRegistry(event_bus)
result = await registry.call_tool("Bash", {"command": "ls -la"}, "call_123")
```

### 记忆系统

```python
from creamcode.memory.working import WorkingMemory
from creamcode.memory.context import ContextWindowManager

context_manager = ContextWindowManager(working, short_term, long_term, event_bus)
messages = await context_manager.prepare_messages(system_prompt="You are a helpful assistant")
```

### 配置管理

```python
from creamcode.config import AppConfig, ConfigLoader

loader = ConfigLoader()
config = loader.load(cli_overrides={"debug": True})
```

### 成本追踪

```python
from creamcode.cost import CostTracker, DefaultPricingModel

tracker = CostTracker(monthly_budget=100.0)
tracker.record("claude-3-5-sonnet", input_tokens=1000, output_tokens=500)
print(f"Total cost: ${tracker.get_total_cost():.4f}")
```

## 开发

```bash
# 运行测试
python -m pytest tests/ -v

# 代码检查
python -m ruff check src/
python -m mypy src/
```

## 项目结构

| 目录 | 说明 |
|------|------|
| `core/` | 核心框架：生命周期、事件总线、插件管理、CLI |
| `adapters/` | AI 适配器实现 |
| `tools/` | 内置工具：Bash、File、Web |
| `memory/` | 三级记忆系统 |
| `skills/` | Skill 加载和匹配 |
| `mcp/` | MCP 客户端 |
| `agent/` | Agent 协调器 |
| `config/` | 配置管理 |
| `cost/` | 成本追踪 |

## 许可证

MIT