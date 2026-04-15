from typing import Callable, Any


class CommandHandler(Callable):
    """CLI command handler"""
    pass


class CLIRegistry:
    """
    CLI命令注册表
    负责命令的注册、注销和调用
    """

    def __init__(self):
        self._namespaces: dict[str, dict[str, CommandHandler]] = {}

    def register(self, namespace: str, name: str, handler: CommandHandler) -> None:
        """注册命令"""
        if namespace not in self._namespaces:
            self._namespaces[namespace] = {}
        self._namespaces[namespace][name] = handler

    def unregister_namespace(self, namespace: str) -> None:
        """注销命名空间下的所有命令"""
        if namespace in self._namespaces:
            del self._namespaces[namespace]

    def get_command(self, namespace: str, name: str) -> CommandHandler | None:
        """获取命令处理器"""
        return self._namespaces.get(namespace, {}).get(name)

    def list_commands(self, namespace: str | None = None) -> list[tuple[str, str]]:
        """列出命令"""
        if namespace:
            return [(namespace, name) for name in self._namespaces.get(namespace, {})]
        return [(ns, name) for ns, commands in self._namespaces.items() for name in commands]
