import asyncio
import json

from aioworkers_kafka.consumer import KafkaConsumer
from aioworkers_kafka.producer import KafkaProducer


async def test_get(bootstrap_servers, topic, mocker):
    data = {"test": 1}
    ct = "application/json"
    async with KafkaConsumer(
        bootstrap_servers=bootstrap_servers, group_id="test", topics=[topic], content_type=ct
    ) as c:
        m = mocker.patch.object(c, "consumer")
        m.poll.return_value = None

        result = await c.get(timeout=0.1)

        msg = m.poll.return_value = mocker.Mock()
        msg.error.return_value = None
        msg.value.return_value = json.dumps(data).encode()
        msg.headers.return_value = {"content-type": ct}

        async def produce():
            async with KafkaProducer(content_type=ct) as p:
                for _ in range(2):
                    await asyncio.sleep(0.3)
                    await p.put(data, topic=topic)

        task = asyncio.create_task(produce())
        result = await c.get()

        msg.headers.return_value = {}
        result = await c.get()

        await task
    assert result == data
