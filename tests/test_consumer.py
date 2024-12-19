import asyncio
import json

from aioworkers_kafka.consumer import KafkaConsumer, MappingMessage, RawMessage
from aioworkers_kafka.producer import KafkaProducer

CONTENT_TYPE = "application/json"


def test_decode_message_header_ct(mocker):
    data = {"test": 1}
    msg = mocker.Mock(
        value=lambda: json.dumps(data).encode(),
        headers=lambda: {"content-type": CONTENT_TYPE.encode()},
        key=lambda: None,
        topic=lambda: "test",
    )
    c = KafkaConsumer()
    result = c.decode_msg(msg)
    assert isinstance(result, MappingMessage)
    assert dict(result) == data
    assert result.value == data
    assert result["content-type"] == CONTENT_TYPE.encode()


def test_decode_message_formatted(mocker):
    data = {"test": 1}
    msg = mocker.Mock(
        value=lambda: json.dumps(data).encode(),
        headers=lambda: None,
        key=lambda: None,
        topic=lambda: "test",
    )
    c = KafkaConsumer(content_type=CONTENT_TYPE)
    result = c.decode_msg(msg)
    assert isinstance(result, MappingMessage)
    assert dict(result) == data
    assert result.value == data


def test_decode_message_bytes(mocker):
    data = {"test": 1}
    b = json.dumps(data).encode()
    msg = mocker.Mock(
        value=lambda: b,
        headers=lambda: {"a": b"b"},
        key=lambda: None,
        topic=lambda: "test",
    )
    c = KafkaConsumer()
    result = c.decode_msg(msg)
    assert isinstance(result, RawMessage)
    assert result.value == b
    assert result["a"] == b"b"


async def test_get(bootstrap_servers, topic, mocker):
    data = {"test": 1}
    async with KafkaConsumer(
        bootstrap_servers=bootstrap_servers, group_id="test", topics=[topic], content_type=CONTENT_TYPE
    ) as c:
        m = mocker.patch.object(c, "consumer")
        m.poll.return_value = None

        result = await c.get(timeout=0.1)

        msg = m.poll.return_value = mocker.Mock()
        msg.error.return_value = None
        msg.value.return_value = json.dumps(data).encode()
        msg.headers.return_value = {"content-type": CONTENT_TYPE.encode()}

        async def produce():
            async with KafkaProducer(content_type=CONTENT_TYPE) as p:
                for _ in range(2):
                    await asyncio.sleep(0.3)
                    await p.put(data, topic=topic)

        task = asyncio.create_task(produce())
        result = await c.get()

        msg.headers.return_value = {}
        result = await c.get()

        await task
    assert dict(result) == data
