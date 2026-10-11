"""Asynchronous Event Bus for real-time WebSocket dispatch and decoupling.

Broadcaster handles tick updates, prediction events, order executions,
risk notifications, and system health status.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Set


class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, Set[Callable]] = {}
        self._ws_queues: Set[asyncio.Queue] = set()

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = set()
        self._subscribers[event_type].add(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        if event_type in self._subscribers and callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    def register_ws_queue(self, queue: asyncio.Queue):
        self._ws_queues.add(queue)

    def unregister_ws_queue(self, queue: asyncio.Queue):
        self._ws_queues.discard(queue)

    async def emit(self, event_type: str, data: Dict[str, Any]):
        payload = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Dispatch to synchronous or asynchronous registered callbacks
        if event_type in self._subscribers:
            for callback in list(self._subscribers[event_type]):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(payload))
                    else:
                        callback(payload)
                except Exception as e:
                    print(f"Error executing callback for {event_type}: {e}")

        # Broadcast to connected WebSocket clients
        dead_queues = []
        for queue in list(self._ws_queues):
            try:
                if queue.full():
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                queue.put_nowait(payload)
            except Exception:
                dead_queues.append(queue)

        for dead in dead_queues:
            self._ws_queues.discard(dead)


event_bus = EventBus()
