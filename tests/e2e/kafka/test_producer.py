"""
Copyright (c) 2023 Aiven Ltd
See LICENSE for details
"""

from __future__ import annotations

import time

import pytest
from aiokafka.errors import MessageSizeTooLargeError, UnknownTopicOrPartitionError
from confluent_kafka.admin import NewTopic

from karapace.core.kafka.producer import AsyncKafkaProducer, KafkaProducer
from karapace.core.kafka.types import Timestamp


class TestSend:
    def test_send(self, producer: KafkaProducer, new_topic: NewTopic) -> None:
        key = b"key"
        value = b"value"
        partition = 0
        timestamp = int(time.time() * 1000)
        headers = [("something", b"123"), (None, "foobar")]

        fut = producer.send(
            new_topic.topic,
            key=key,
            value=value,
            partition=partition,
            timestamp=timestamp,
            headers=headers,
        )
        producer.flush()
        message = fut.result()

        assert message.offset() == 0
        assert message.partition() == partition
        assert message.topic() == new_topic.topic
        assert message.key() == key
        assert message.value() == value
        assert message.timestamp()[0] == Timestamp.CREATE_TIME
        assert message.timestamp()[1] == timestamp

    def test_send_raises_for_unknown_topic(self, producer: KafkaProducer) -> None:
        fut = producer.send("nonexistent")
        producer.flush()

        with pytest.raises(UnknownTopicOrPartitionError):
            fut.result()

    def test_send_raises_for_unknown_partition(self, producer: KafkaProducer, new_topic: NewTopic) -> None:
        fut = producer.send(new_topic.topic, partition=99)
        producer.flush()

        with pytest.raises(UnknownTopicOrPartitionError):
            fut.result()

    def test_send_raises_for_too_large_message(self, producer: KafkaProducer, new_topic: NewTopic) -> None:
        with pytest.raises(MessageSizeTooLargeError):
            producer.send(new_topic.topic, value=b"x" * 1000001)


class TestPartitionsFor:
    def test_partitions_for_returns_empty_for_unknown_topic(self, producer: KafkaProducer) -> None:
        assert producer.partitions_for("nonexistent") == {}

    def test_partitions_for(self, producer: KafkaProducer, new_topic: NewTopic) -> None:
        partitions = producer.partitions_for(new_topic.topic)

        assert len(partitions) == 1
        assert partitions[0].id == 0
        assert partitions[0].replicas == [1]
        assert partitions[0].isrs == [1]


class TestAsyncSend:
    async def test_async_send(self, asyncproducer: AsyncKafkaProducer, new_topic: NewTopic) -> None:
        key = b"key"
        value = b"value"
        partition = 0
        timestamp = int(time.time() * 1000)
        headers = [("something", b"123"), (None, "foobar")]

        aiofut = await asyncproducer.send(
            new_topic.topic,
            key=key,
            value=value,
            partition=partition,
            timestamp=timestamp,
            headers=headers,
        )
        message = await aiofut

        assert message.offset() == 0
        assert message.partition() == partition
        assert message.topic() == new_topic.topic
        assert message.key() == key
        assert message.value() == value
        assert message.timestamp()[0] == Timestamp.CREATE_TIME
        assert message.timestamp()[1] == timestamp

    async def test_async_send_raises_for_unknown_topic(self, asyncproducer: AsyncKafkaProducer) -> None:
        aiofut = await asyncproducer.send("nonexistent")

        with pytest.raises(UnknownTopicOrPartitionError):
            _ = await aiofut

    async def test_async_send_raises_for_unknown_partition(
        self, asyncproducer: AsyncKafkaProducer, new_topic: NewTopic
    ) -> None:
        aiofut = await asyncproducer.send(new_topic.topic, partition=99)

        with pytest.raises(UnknownTopicOrPartitionError):
            _ = await aiofut

    async def test_async_send_raises_for_too_large_message(
        self, asyncproducer: AsyncKafkaProducer, new_topic: NewTopic
    ) -> None:
        with pytest.raises(MessageSizeTooLargeError):
            await asyncproducer.send(new_topic.topic, value=b"x" * 1000001)
