import asyncio
from typing import Callable, Awaitable

from ..types import LifecycleState

Callback = Callable[[], Awaitable[None]]
StateChangeCallback = Callable[[LifecycleState, LifecycleState], None]


class LifecycleManager:
    """
    生命周期管理器
    负责应用启动、运行、关闭的全生命周期管理
    """

    def __init__(self):
        self._state: LifecycleState = LifecycleState.STOPPED
        self._startup_callbacks: list[Callback] = []
        self._shutdown_callbacks: list[Callback] = []
        self._state_change_callbacks: list[StateChangeCallback] = []
        self._lock: asyncio.Lock | None = None

    @property
    def state(self) -> LifecycleState:
        return self._state

    async def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _set_state(self, new_state: LifecycleState) -> None:
        old_state = self._state
        if old_state != new_state:
            self._state = new_state
            for callback in self._state_change_callbacks:
                callback(old_state, new_state)

    async def on_startup(self):
        """
        应用启动时调用
        执行所有 startup 回调
        """
        lock = await self._get_lock()
        async with lock:
            if self._state in (LifecycleState.STARTING, LifecycleState.RUNNING):
                return

            self._set_state(LifecycleState.STARTING)

            for callback in self._startup_callbacks:
                try:
                    await callback()
                except Exception:
                    pass

            self._set_state(LifecycleState.RUNNING)

    async def on_shutdown(self):
        """
        应用关闭时调用
        执行所有 shutdown 回调
        """
        lock = await self._get_lock()
        async with lock:
            if self._state in (LifecycleState.STOPPING, LifecycleState.STOPPED):
                return

            self._set_state(LifecycleState.STOPPING)

            for callback in self._shutdown_callbacks:
                try:
                    await callback()
                except Exception:
                    pass

            self._set_state(LifecycleState.STOPPED)

    def register_startup(self, callback: Callback) -> None:
        """注册启动回调"""
        self._startup_callbacks.append(callback)

    def register_shutdown(self, callback: Callback) -> None:
        """注册关闭回调"""
        self._shutdown_callbacks.append(callback)

    def register_state_change(self, callback: StateChangeCallback) -> None:
        """注册状态变更回调"""
        self._state_change_callbacks.append(callback)

    def get_state(self) -> LifecycleState:
        """获取当前状态"""
        return self._state