from __future__ import annotations

import asyncio
import pytest
from creamcode.core.lifecycle import LifecycleManager
from creamcode.types import LifecycleState


class TestLifecycleManagerBasic:
    def test_initial_state_is_stopped(self):
        manager = LifecycleManager()
        assert manager.state == LifecycleState.STOPPED
        assert manager.get_state() == LifecycleState.STOPPED

    @pytest.mark.asyncio
    async def test_on_startup_changes_state_to_running(self):
        manager = LifecycleManager()
        await manager.on_startup()
        assert manager.state == LifecycleState.RUNNING

    @pytest.mark.asyncio
    async def test_on_shutdown_changes_state_to_stopped(self):
        manager = LifecycleManager()
        await manager.on_startup()
        await manager.on_shutdown()
        assert manager.state == LifecycleState.STOPPED

    @pytest.mark.asyncio
    async def test_startup_then_shutdown_flow(self):
        manager = LifecycleManager()
        assert manager.state == LifecycleState.STOPPED
        await manager.on_startup()
        assert manager.state == LifecycleState.RUNNING
        await manager.on_shutdown()
        assert manager.state == LifecycleState.STOPPED


class TestLifecycleManagerCallbacks:
    @pytest.mark.asyncio
    async def test_startup_callbacks_executed_in_order(self):
        manager = LifecycleManager()
        execution_order = []

        async def callback1():
            execution_order.append(1)

        async def callback2():
            execution_order.append(2)

        async def callback3():
            execution_order.append(3)

        manager.register_startup(callback1)
        manager.register_startup(callback2)
        manager.register_startup(callback3)
        await manager.on_startup()

        assert execution_order == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_shutdown_callbacks_executed_in_order(self):
        manager = LifecycleManager()
        execution_order = []

        async def callback1():
            execution_order.append(1)

        async def callback2():
            execution_order.append(2)

        async def callback3():
            execution_order.append(3)

        manager.register_shutdown(callback1)
        manager.register_shutdown(callback2)
        manager.register_shutdown(callback3)
        await manager.on_startup()
        await manager.on_shutdown()

        assert execution_order == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_callback_failure_does_not_affect_others(self):
        manager = LifecycleManager()
        execution_order = []

        async def failing_callback():
            execution_order.append(1)
            raise RuntimeError("Callback failed")

        async def success_callback():
            execution_order.append(2)

        manager.register_startup(failing_callback)
        manager.register_startup(success_callback)
        await manager.on_startup()

        assert execution_order == [1, 2]
        assert manager.state == LifecycleState.RUNNING


class TestLifecycleManagerStateChange:
    @pytest.mark.asyncio
    async def test_state_change_callback_receives_old_and_new_state(self):
        manager = LifecycleManager()
        state_changes = []

        def state_change_listener(old_state: LifecycleState, new_state: LifecycleState):
            state_changes.append((old_state, new_state))

        manager.register_state_change(state_change_listener)
        await manager.on_startup()

        assert (LifecycleState.STOPPED, LifecycleState.STARTING) in state_changes
        assert (LifecycleState.STARTING, LifecycleState.RUNNING) in state_changes

    @pytest.mark.asyncio
    async def test_state_change_callback_on_shutdown(self):
        manager = LifecycleManager()
        state_changes = []

        def state_change_listener(old_state: LifecycleState, new_state: LifecycleState):
            state_changes.append((old_state, new_state))

        manager.register_state_change(state_change_listener)
        await manager.on_startup()
        await manager.on_shutdown()

        assert (LifecycleState.RUNNING, LifecycleState.STOPPING) in state_changes
        assert (LifecycleState.STOPPING, LifecycleState.STOPPED) in state_changes


class TestLifecycleManagerConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_on_startup_calls(self):
        manager = LifecycleManager()

        async def startup_task():
            await manager.on_startup()

        await asyncio.gather(startup_task(), startup_task(), startup_task())
        assert manager.state == LifecycleState.RUNNING

    @pytest.mark.asyncio
    async def test_repeated_startup_shutdown(self):
        manager = LifecycleManager()

        for _ in range(3):
            await manager.on_startup()
            assert manager.state == LifecycleState.RUNNING
            await manager.on_shutdown()
            assert manager.state == LifecycleState.STOPPED


class TestLifecycleManagerEdgeCases:
    @pytest.mark.asyncio
    async def test_shutdown_without_startup(self):
        manager = LifecycleManager()
        await manager.on_shutdown()
        assert manager.state == LifecycleState.STOPPED

    @pytest.mark.asyncio
    async def test_repeated_on_startup(self):
        manager = LifecycleManager()
        await manager.on_startup()
        await manager.on_startup()
        await manager.on_startup()
        assert manager.state == LifecycleState.RUNNING

    @pytest.mark.asyncio
    async def test_repeated_on_shutdown(self):
        manager = LifecycleManager()
        await manager.on_startup()
        await manager.on_shutdown()
        await manager.on_shutdown()
        await manager.on_shutdown()
        assert manager.state == LifecycleState.STOPPED
