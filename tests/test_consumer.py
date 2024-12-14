import asyncio

from aioworkers_kafka.consumer import KafkaConsumer
from aioworkers_kafka.producer import KafkaProducer


async def test_get(bootstrap_servers, topic):
    data = {"test": 1}
    ct = "application/json"
    async with KafkaConsumer(
        bootstrap_servers=bootstrap_servers, group_id="test", topics=[topic], content_type=ct
    ) as c:
        result = await c.get(timeout=0.1)

        async def produce():
            async with KafkaProducer(content_type=ct) as p:
                for _ in range(3):
                    await asyncio.sleep(1)
                    await p.put(data, topic=topic)

        task = asyncio.create_task(produce())
        result = await c.get()

        await task
    assert result == data
