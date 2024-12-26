aioworkers-kafka
================

.. image:: https://img.shields.io/pypi/v/aioworkers-kafka.svg
  :target: https://pypi.org/project/aioworkers-kafka

.. image:: https://github.com/aioworkers/aioworkers-kafka/workflows/Tests/badge.svg
  :target: https://github.com/aioworkers/aioworkers-kafka/actions?query=workflow%3ATests

.. image:: https://codecov.io/gh/aioworkers/aioworkers-kafka/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/aioworkers/aioworkers-kafka
  :alt: Coverage

.. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v0.json
  :target: https://github.com/charliermarsh/ruff
  :alt: Code style: ruff

.. image:: https://img.shields.io/badge/types-Mypy-blue.svg
  :target: https://github.com/python/mypy
  :alt: Code style: Mypy

.. image:: https://readthedocs.org/projects/aioworkers-kafka/badge/?version=latest
  :target: https://github.com/aioworkers/aioworkers-kafka#readme
  :alt: Documentation Status

.. image:: https://img.shields.io/pypi/pyversions/aioworkers-kafka.svg
  :target: https://pypi.org/project/aioworkers-kafka
  :alt: Python versions

.. image:: https://img.shields.io/pypi/dm/aioworkers-kafka.svg
  :target: https://pypistats.org/packages/aioworkers-kafka

.. image:: https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg
  :alt: Hatch project
  :target: https://github.com/pypa/hatch


Usage
-----

config.yaml:

.. code-block:: yaml

    producer:
      cls: aioworkers_kafka.producer.KafkaProducer
      format: json
      kafka:
        bootstrap.servers: kafka:9092
      topic: test

    consumer:
      cls: aioworkers_kafka.consumer.KafkaConsumer
      format: json  # default format is json
      kafka:
        bootstrap.servers: kafka:9092
        group.id: test
      topics:
        - test

    worker:
      cls: mymodule.MyWorker
      input: .consumer
      output: .producer
      autorun: true


mymodule.py:

.. code-block:: python

    from aioworkers.worker.base import Worker

    class MyWorker(Worker):
        async def run(self, value):  # consume value from input
            assert isinstance(value, Mapping)

            out = dict(value)

            value["ts"] = time()

            return value  # produce value to output


.. code-block:: shell

    $ aioworkers -c config.yaml


Development
-----------

Check code:

.. code-block:: shell

    hatch run lint:all


Format code:

.. code-block:: shell

    hatch run lint:fmt


Run tests:

.. code-block:: shell

    hatch run pytest


Run tests with coverage:

.. code-block:: shell

    hatch run cov
