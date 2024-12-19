import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional

import confluent_kafka
from aioworkers.core.base import AbstractConnector, AbstractReader, ExecutorEntity
from aioworkers.core.context import Context
from aioworkers.core.formatter import FormattedEntity
from confluent_kafka import KafkaError

from aioworkers_kafka.utils import flat_conf


@dataclass
class IncommingMessage(Mapping):
    value: Any
    topic: str
    key: Optional[bytes]
    headers: Mapping[str, bytes]

    def __getitem__(self, key: str) -> bytes:
        return self.headers[key]

    def __iter__(self):
        return iter(())

    def __len__(self) -> int:
        return 0


@dataclass
class RawMessage(IncommingMessage):
    value: bytes
    topic: str
    key: Optional[bytes]
    headers: Mapping[str, bytes]


@dataclass
class MappingMessage(IncommingMessage):
    value: Mapping[str, Any]
    topic: str
    key: Optional[bytes]
    headers: Mapping[str, bytes]

    def __getitem__(self, key: str) -> Any:
        try:
            return self.value[key]
        except KeyError:
            if v := self.headers.get(key):
                return v
            else:
                raise

    def __iter__(self):
        return iter(self.value)

    def __len__(self) -> int:
        return len(self.value)


class KafkaConsumer(AbstractReader, FormattedEntity, ExecutorEntity, AbstractConnector):
    def __init__(
        self,
        *args,
        bootstrap_servers: Optional[str] = "localhost:9092",
        group_id: Optional[str] = None,
        topics: Optional[List[str]] = None,
        content_type: Optional[str] = None,
        **kwargs,
    ):
        self.topics = topics
        self._kafka_config: Dict = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
        }
        if content_type:
            kwargs["format"] = content_type
        kwargs["executor"] = 1
        super().__init__(*args, **kwargs)

    def set_config(self, config):
        super().set_config(config)
        if cfg := self.config.get("kafka"):
            self._kafka_config.update(flat_conf(cfg))
        if topics := self.config.get("topics"):
            self.topics = topics

    async def init(self):
        await super().init()
        self.consumer = confluent_kafka.Consumer(
            self._kafka_config,
            logger=self.logger,
        )

    async def connect(self):
        if self.topics:
            self.consumer.subscribe(self.topics)

    async def disconnect(self):
        await self.run_in_executor(self.consumer.close)

    async def get(self, timeout: Optional[float] = None) -> Optional[IncommingMessage]:
        poll_timeout = timeout or 1.0
        while True:
            msg = await self.run_in_executor(self.consumer.poll, poll_timeout)
            if msg is None:
                if timeout is not None:
                    return None
            elif msg.error():
                if msg.error().code() not in {KafkaError._PARTITION_EOF}:
                    self.logger.error("Consume with error %s", msg.error())
                await asyncio.sleep(1)
            else:
                return self.decode_msg(msg)

    def decode_msg(self, msg: confluent_kafka.Message) -> IncommingMessage:
        if h := msg.headers():
            headers = dict(h)
        else:
            headers = {}

        raw_value = msg.value()
        if ct := headers.get("content-type"):
            f = self.registry.get(ct)
            value = f.decode(msg.value())
        else:
            value = self.decode(msg.value())

        if type(value) is bytes:
            return RawMessage(value=raw_value, topic=msg.topic(), key=msg.key(), headers=headers)
        else:
            return MappingMessage(value=value, topic=msg.topic(), key=msg.key(), headers=headers)

    async def __aenter__(self):
        self.set_context(Context())
        self.set_config(
            self.config.new_child(
                name="kafka_consumer",
                kafka=self._kafka_config,
            )
        )
        await self.init()
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.disconnect()
