import os

import pytest


@pytest.fixture
def bootstrap_servers():
    return os.getenv("KAFKA_BOOTSTRAP_SERVERS") or "localhost:9092"


@pytest.fixture
def topic():
    return os.getenv("KAFKA_TOPIC") or "test"
