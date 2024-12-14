from aioworkers_kafka.producer import KafkaProducer


async def test_produce(bootstrap_servers, topic):
    data = b'{"test": 1}'
    async with KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        topic=topic,
    ) as p:
        msg = await p.put(data)
    assert msg.value() == data
    assert msg.topic() == topic


async def test_produce_json(bootstrap_servers, topic):
    data = {"test": 1}
    async with KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        content_type="application/json",
    ) as p:
        await p.put(data, topic=topic)
