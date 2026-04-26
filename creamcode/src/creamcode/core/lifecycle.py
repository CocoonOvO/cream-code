from __future__ import annotations

from typing import TYPE_CHECKING

from ..types import LifecycleState
from .event_bus import event_bus


class LifecycleManager:
    """生命周期管理器"""

    _lifecycle = event_bus.create_space("lifecycle")

    def __init__(self):
        self._state: LifecycleState = LifecycleState.STOPPED

    @property
    def state(self) -> LifecycleState:
        return self._state

    def _set_state(self, new_state: LifecycleState) -> None:
        self._state = new_state

    @_lifecycle.event("start")
    async def start(self):
        """应用启动"""
        self._set_state(LifecycleState.STARTING)
        self._set_state(LifecycleState.RUNNING)

    @_lifecycle.event("stop")
    async def stop(self):
        """应用关闭"""
        self._set_state(LifecycleState.STOPPING)
        self._set_state(LifecycleState.STOPPED)

    def get_state(self) -> LifecycleState:
        return self._state
