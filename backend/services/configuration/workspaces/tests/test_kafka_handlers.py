"""Unit tests for Kafka message handlers (infrastructure/messaging layer)."""
import pytest
from unittest.mock import patch, MagicMock, call

from workspaces.infrastructure.messaging.kafka_handlers import (
    handle_token_request,
    start_kafka_consumers,
)


@pytest.mark.django_db
class TestHandleTokenRequest:
    """Tests for handle_token_request Kafka handler."""

    @patch("workspaces.infrastructure.messaging.kafka_handlers.KafkaClient")
    def test_publishes_error_when_user_id_missing(self, mock_kafka):
        handle_token_request(
            {"workspace_id": "1", "correlation_id": "corr-1"}, "topic"
        )
        mock_kafka.publish.assert_called_once()
        _, published = mock_kafka.publish.call_args[0]
        assert published["status"] == "error"
        assert "user_id" in published["error"]

    @patch("workspaces.infrastructure.messaging.kafka_handlers.KafkaClient")
    def test_publishes_error_when_workspace_id_missing(self, mock_kafka):
        handle_token_request(
            {"user_id": "1", "correlation_id": "corr-2"}, "topic"
        )
        mock_kafka.publish.assert_called_once()
        _, published = mock_kafka.publish.call_args[0]
        assert published["status"] == "error"

    @patch("workspaces.infrastructure.messaging.kafka_handlers.KafkaClient")
    def test_publishes_token_on_success(self, mock_kafka, create_workspace):
        ws = create_workspace(user_id=7, name="Kafka WS")
        handle_token_request(
            {
                "user_id": 7,
                "workspace_id": ws.id,
                "correlation_id": "corr-ok",
            },
            "topic",
        )
        mock_kafka.publish.assert_called_once()
        _, published = mock_kafka.publish.call_args[0]
        assert published["status"] == "ok"
        assert published["token"] == ws.get_token()
        assert published["platform"] == ws.platform

    @patch("workspaces.infrastructure.messaging.kafka_handlers.KafkaClient")
    def test_publishes_error_on_workspace_not_found(self, mock_kafka):
        handle_token_request(
            {"user_id": 1, "workspace_id": 99999, "correlation_id": "corr-nf"},
            "topic",
        )
        mock_kafka.publish.assert_called_once()
        _, published = mock_kafka.publish.call_args[0]
        assert published["status"] == "error"
        assert "not found" in published["error"].lower()


class TestStartKafkaConsumers:
    """Tests for start_kafka_consumers."""

    @patch("workspaces.infrastructure.messaging.kafka_handlers.KafkaClient")
    def test_starts_consumer_with_correct_topic(self, mock_kafka):
        from kafka_utils.topics import Topics

        start_kafka_consumers()
        mock_kafka.start_consumer.assert_called_once()
        kwargs = mock_kafka.start_consumer.call_args[1]
        assert Topics.TOKENS_REQUEST in kwargs.get("topics", [])
        assert kwargs.get("group_id") == "configuration-service"
