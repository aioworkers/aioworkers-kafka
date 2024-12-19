import asyncio
import logging
from threading import Thread
from typing import Dict, Mapping, Optional

import confluent_kafka
from aioworkers.core.base import AbstractConnector, AbstractWriter
from aioworkers.core.context import Context
from aioworkers.core.formatter import FormattedEntity
from confluent_kafka import KafkaException

from aioworkers_kafka.utils import flat_conf

logger = logging.getLogger(__name__)


class InnerProducer:
    _producer: confluent_kafka.Producer

    def __init__(
        self,
        configs: Mapping,
        *,
        logger: logging.Logger = logger,
        loop=None,
    ):
        self._loop = loop or asyncio.get_running_loop()
        self._producer = confluent_kafka.Producer(configs, logger=logger)
        self._cancelled = False
        self._poll_thread = Thread(target=self._poll_loop)
        self._running = asyncio.Event()
        self._logger = logger

    async def start(self):
        self._poll_thread.start()

    def _poll_loop(self):
        self._loop.call_soon_threadsafe(self._running.set)
        try:
            while not self._cancelled:
                self._producer.poll(0.1)
        finally:
            self._loop.call_soon_threadsafe(self._running.clear)

    async def stop(self):
        if not self._cancelled:
            self._cancelled = True
            await self._running.wait()
            self._poll_thread.join()

    async def produce(
        self,
        value: bytes,
        *,
        topic: Optional[str] = None,
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> asyncio.Future[confluent_kafka.Message]:
        result = self._loop.create_future()

        def ack(err, msg):
            if err:
                e = KafkaException(err)
                self._loop.call_soon_threadsafe(result.set_exception, e)
            else:
                self._loop.call_soon_threadsafe(result.set_result, msg)

        while True:
            try:
                self._producer.produce(
                    topic=topic,
                    value=value,
                    key=key,
                    headers=headers,
                    on_delivery=ack,
                )
            except BufferError:
                self._logger.warning("Producer queue is full")
                if self._running.is_set():
                    await asyncio.sleep(1)
                else:
                    raise
            else:
                return await result


class KafkaProducer(AbstractWriter, FormattedEntity, AbstractConnector):
    def __init__(
        self,
        *args,
        bootstrap_servers: Optional[str] = "localhost:9092",
        topic: Optional[str] = None,
        content_type: Optional[str] = None,
        **kwargs,
    ):
        self.topic: Optional[str] = topic
        self._headers = {}
        if content_type:
            self._headers["content-type"] = content_type
            kwargs["format"] = content_type
        self._kafka_config: Dict = {
            "bootstrap.servers": bootstrap_servers,
        }
        super().__init__(*args, **kwargs)

    def set_config(self, config):
        super().set_config(config)
        if cfg := self.config.get("kafka"):
            self._kafka_config.update(flat_conf(cfg))
        self.topic = self.config.get("topic") or self.topic
        if headers := self.config.get("headers"):
            self._headers.update(headers)
        if f := self.config.get("format"):
            self._headers.setdefault("content-type", f)

    async def init(self):
        await super().init()
        self.producer = InnerProducer(
            self._kafka_config,
            logger=self.logger,
        )

    async def connect(self):
        await self.producer.start()

    async def disconnect(self):
        await self.producer.stop()

    async def put(
        self,
        message,
        *,
        topic: Optional[str] = None,
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> confluent_kafka.Message:
        data = self.encode(message)
        return await self.producer.produce(
            data,
            key=key,
            topic=topic or self.topic,
            headers=headers or self._headers,
        )

    async def __aenter__(self):
        self.set_context(Context())
        self.set_config(
            self.config.new_child(
                name="kafka_producer",
                kafka=self._kafka_config,
            )
        )
        await self.init()
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.disconnect()
