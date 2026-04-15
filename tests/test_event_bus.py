from __future__ import annotations

import asyncio
import pytest
from creamcode.core.event_bus import EventBus, Event


class TestEventBusBasic:
    def test_initial_state(self):
        bus = EventBus()
        assert bus.list_subscriptions() == []

    @pytest.mark.asyncio
    async def test_subscribe_receives_event(self):
        bus = EventBus()
        received = []

        async def handler(event: Event):
            received.append(event)

        await bus.subscribe("test_event", handler)
        await bus.publish(Event(name="test_event", source="test"))

        assert len(received) == 1
        assert received[0].name == "test_event"
        assert received[0].source == "test"

    @pytest.mark.asyncio
    async def test_multiple_subscribers_all_receive(self):
        bus = EventBus()
        received1 = []
        received2 = []

        async def handler1(event: Event):
            received1.append(event)

        async def handler2(event: Event):
            received2.append(event)

        await bus.subscribe("test_event", handler1)
        await bus.subscribe("test_event", handler2)
        await bus.publish(Event(name="test_event", source="test"))

        assert len(received1) == 1
        assert len(received2) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe_stops_receiving(self):
        bus = EventBus()
        received = []

        async def handler(event: Event):
            received.append(event)

        await bus.subscribe("test_event", handler)
        await bus.publish(Event(name="test_event", source="test"))
        assert len(received) == 1

        await bus.unsubscribe("test_event", handler)
        await bus.publish(Event(name="test_event", source="test"))
        assert len(received) == 1


class TestEventBusPublishSubscribe:
    @pytest.mark.asyncio
    async def test_publish_event_has_correct_name(self):
        bus = EventBus()
        received = []

        async def handler(event: Event):
            received.append(event)

        await bus.subscribe("my_event", handler)
        await bus.publish(Event(name="my_event", source="plugin_a"))

        assert received[0].name == "my_event"

    @pytest.mark.asyncio
    async def test_publish_event_has_correct_source(self):
        bus = EventBus()
        received = []

        async def handler(event: Event):
            received.append(event)

        await bus.subscribe("my_event", handler)
        await bus.publish(Event(name="my_event", source="plugin_b"))

        assert received[0].source == "plugin_b"

    @pytest.mark.asyncio
    async def test_publish_event_has_correct_data(self):
        bus = EventBus()
        received = []

        async def handler(event: Event):
            received.append(event)

        await bus.subscribe("my_event", handler)
        await bus.publish(Event(name="my_event", source="plugin", data={"key": "value"}))

        assert received[0].data == {"key": "value"}

    @pytest.mark.asyncio
    async def test_handler_receives_correct_event_object(self):
        bus = EventBus()
        received = []

        async def handler(event: Event):
            received.append(event)

        await bus.subscribe("evt", handler)
        event = Event(name="evt", source="src", data={"foo": "bar"})
        await bus.publish(event)

        assert received[0] is event


class TestEventBusConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_publish(self):
        bus = EventBus()
        received = []

        async def handler(event: Event):
            received.append(event)

        await bus.subscribe("concurrent_event", handler)

        async def publish():
            await bus.publish(Event(name="concurrent_event", source="test"))

        await asyncio.gather(*[publish() for _ in range(10)])
        assert len(received) == 10

    @pytest.mark.asyncio
    async def test_concurrent_subscribe(self):
        bus = EventBus()

        async def make_handler(i: int):
            async def handler(event: Event):
                pass
            return handler

        handlers = [await make_handler(i) for i in range(5)]

        async def subscribe(h):
            await bus.subscribe("concurrent_sub", h)

        await asyncio.gather(*[subscribe(h) for h in handlers])
        result = bus.get_handlers("concurrent_sub")
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_concurrent_unsubscribe(self):
        bus = EventBus()

        async def handler(event: Event):
            pass

        await bus.subscribe("concurrent_unsub", handler)
        await bus.subscribe("concurrent_unsub", handler)

        async def unsubscribe():
            await bus.unsubscribe("concurrent_unsub", handler)

        await asyncio.gather(*[unsubscribe() for _ in range(2)])
        handlers = bus.get_handlers("concurrent_unsub")
        assert len(handlers) == 0


class TestEventBusExceptionHandling:
    @pytest.mark.asyncio
    async def test_handler_exception_does_not_affect_others(self):
        bus = EventBus()
        received = []

        async def failing_handler(event: Event):
            raise RuntimeError("Handler failed")

        async def success_handler(event: Event):
            received.append(event)

        await bus.subscribe("error_test", failing_handler)
        await bus.subscribe("error_test", success_handler)
        await bus.publish(Event(name="error_test", source="test"))

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_handler_exception_does_not_affect_publish(self):
        bus = EventBus()

        async def failing_handler(event: Event):
            raise RuntimeError("Handler failed")

        await bus.subscribe("error_test", failing_handler)
        await bus.publish(Event(name="error_test", source="test"))

    @pytest.mark.asyncio
    async def test_multiple_handler_exceptions(self):
        bus = EventBus()
        received = []

        async def failing_handler1(event: Event):
            raise RuntimeError("Handler 1 failed")

        async def failing_handler2(event: Event):
            raise RuntimeError("Handler 2 failed")

        async def success_handler(event: Event):
            received.append(event)

        await bus.subscribe("multi_error", failing_handler1)
        await bus.subscribe("multi_error", failing_handler2)
        await bus.subscribe("multi_error", success_handler)
        await bus.publish(Event(name="multi_error", source="test"))

        assert len(received) == 1


class TestEventBusWildcard:
    @pytest.mark.asyncio
    async def test_wildcard_subscription_receives_all_events(self):
        bus = EventBus()
        received = []

        async def wildcard_handler(event: Event):
            received.append(event)

        await bus.subscribe("*", wildcard_handler)
        await bus.publish(Event(name="event_a", source="src"))
        await bus.publish(Event(name="event_b", source="src"))

        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_wildcard_with_named_subscription(self):
        bus = EventBus()
        received_wildcard = []
        received_named = []

        async def wildcard_handler(event: Event):
            received_wildcard.append(event)

        async def named_handler(event: Event):
            received_named.append(event)

        await bus.subscribe("*", wildcard_handler)
        await bus.subscribe("specific", named_handler)
        await bus.publish(Event(name="specific", source="src"))

        assert len(received_wildcard) == 1
        assert len(received_named) == 1


class TestEventBusEdgeCases:
    @pytest.mark.asyncio
    async def test_subscribe_to_nonexistent_event(self):
        bus = EventBus()

        async def handler(event: Event):
            pass

        await bus.subscribe("nonexistent", handler)
        assert bus.get_handlers("nonexistent") == [handler]

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_handler(self):
        bus = EventBus()

        async def handler(event: Event):
            pass

        async def other_handler(event: Event):
            pass

        await bus.subscribe("test", handler)
        await bus.unsubscribe("test", other_handler)
        assert bus.get_handlers("test") == [handler]

    @pytest.mark.asyncio
    async def test_publish_to_no_subscribers(self):
        bus = EventBus()
        await bus.publish(Event(name="no_subscribers", source="test"))

    @pytest.mark.asyncio
    async def test_duplicate_subscribe_same_handler(self):
        bus = EventBus()
        received = []

        async def handler(event: Event):
            received.append(event)

        await bus.subscribe("dup", handler)
        await bus.subscribe("dup", handler)
        await bus.publish(Event(name="dup", source="test"))

        assert len(received) == 1
        assert len(bus.get_handlers("dup")) == 1
