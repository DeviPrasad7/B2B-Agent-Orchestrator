import asyncio
from typing import Dict, Set, Any
from collections import defaultdict

class PubSub:
    def __init__(self):
        # Maps topic (e.g. prospect_id) to a set of queues
        self.subscribers: Dict[str, Set[asyncio.Queue]] = defaultdict(set)

    async def publish(self, topic: str, message: Any):
        if topic in self.subscribers:
            for queue in list(self.subscribers[topic]):
                await queue.put(message)

    async def subscribe(self, topic: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        self.subscribers[topic].add(queue)
        return queue

    def unsubscribe(self, topic: str, queue: asyncio.Queue):
        if topic in self.subscribers:
            self.subscribers[topic].discard(queue)
            if not self.subscribers[topic]:
                del self.subscribers[topic]

pubsub_broker = PubSub()
