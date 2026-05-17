package kafka

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"log/slog"
	"time"

	"notification-service/internal/db"
	"notification-service/internal/model"
	"notification-service/internal/ws"

	"github.com/IBM/sarama"
)

// Topics to subscribe to
var subscribedTopics = []string{
	"collection.events.started",
	"collection.events.completed",
	"collection.events.failed",
	"analysis.events.requested",
	"analysis.events.completed",
	"notification.events",
}

type Consumer struct {
	group    sarama.ConsumerGroup
	database *sql.DB
	hub      *ws.Hub
	done     chan struct{}
}

func NewConsumer(brokers []string, groupID string, database *sql.DB, hub *ws.Hub) (*Consumer, error) {
	config := sarama.NewConfig()
	config.Consumer.Group.Rebalance.GroupStrategies = []sarama.BalanceStrategy{sarama.NewBalanceStrategyRoundRobin()}
	config.Consumer.Offsets.Initial = sarama.OffsetOldest
	config.Version = sarama.V3_5_0_0

	group, err := sarama.NewConsumerGroup(brokers, groupID, config)
	if err != nil {
		return nil, fmt.Errorf("failed to create consumer group: %w", err)
	}

	return &Consumer{
		group:    group,
		database: database,
		hub:      hub,
		done:     make(chan struct{}),
	}, nil
}

func (c *Consumer) Start() {
	handler := &consumerGroupHandler{
		database: c.database,
		hub:      c.hub,
	}

	for {
		select {
		case <-c.done:
			return
		default:
			if err := c.group.Consume(context.Background(), subscribedTopics, handler); err != nil {
				slog.Error("Kafka consumer error",
					"service", "notification",
					"error", err.Error(),
					"event", "kafka_consumer_error",
					"status", "error",
				)
			}
		}
	}
}

func (c *Consumer) Stop() {
	close(c.done)
	c.group.Close()
}

// consumerGroupHandler implements sarama.ConsumerGroupHandler
type consumerGroupHandler struct {
	database *sql.DB
	hub      *ws.Hub
}

func (h *consumerGroupHandler) Setup(_ sarama.ConsumerGroupSession) error {
	slog.Info("Kafka consumer group session setup",
		"service", "notification",
		"event", "kafka_session_setup",
	)
	return nil
}

func (h *consumerGroupHandler) Cleanup(_ sarama.ConsumerGroupSession) error {
	slog.Info("Kafka consumer group session cleanup",
		"service", "notification",
		"event", "kafka_session_cleanup",
	)
	return nil
}

func (h *consumerGroupHandler) ConsumeClaim(session sarama.ConsumerGroupSession, claim sarama.ConsumerGroupClaim) error {
	for msg := range claim.Messages() {
		startedAt := time.Now()
		slog.Info("Kafka message received",
			"service", "notification",
			"topic", msg.Topic,
			"partition", msg.Partition,
			"offset", msg.Offset,
			"event", "kafka_message_received",
		)

		notification := h.transformEvent(msg.Topic, msg.Value)
		if notification == nil {
			session.MarkMessage(msg, "")
			continue
		}

		// Persist to database
		if err := db.InsertNotification(h.database, notification); err != nil {
			slog.Error("Failed to insert notification",
				"service", "notification",
				"topic", msg.Topic,
				"user_id", notification.UserID,
				"error", err.Error(),
				"event", "notification_insert_failed",
				"status", "error",
			)
			session.MarkMessage(msg, "")
			continue
		}

		// Push to user via WebSocket
		payload, err := json.Marshal(notification)
		if err == nil {
			h.hub.SendToUser(notification.UserID, payload)
		}

		duration := time.Since(startedAt).Seconds()
		slog.Info("Notification processed and dispatched",
			"service", "notification",
			"topic", msg.Topic,
			"user_id", notification.UserID,
			"notification_type", notification.Type,
			"duration", duration,
			"status", "success",
			"event", "notification_dispatched",
		)

		session.MarkMessage(msg, "")
	}
	return nil
}

// kafkaEvent is the generic structure for incoming Kafka messages
type kafkaEvent struct {
	UserID       int    `json:"user_id"`
	WorkspaceID  int    `json:"workspace_id"`
	CollectionID int    `json:"collection_id"`
	RepositoryID int    `json:"repository_id"`
	Status       string `json:"status"`
	Error        string `json:"error"`
	// Generic notification fields (for notification.events topic)
	Type    string `json:"type"`
	Title   string `json:"title"`
	Message string `json:"message"`
	LinkURL string `json:"link_url"` // Optional navigation path for generic events
}

func (h *consumerGroupHandler) transformEvent(topic string, value []byte) *model.Notification {
	var event kafkaEvent
	if err := json.Unmarshal(value, &event); err != nil {
		slog.Error("Failed to parse Kafka event",
			"service", "notification",
			"topic", topic,
			"error", err.Error(),
			"event", "kafka_parse_failed",
			"status", "error",
		)
		return nil
	}

	if event.UserID == 0 {
		slog.Warn("Skipping Kafka event with no user_id",
			"service", "notification",
			"topic", topic,
			"event", "kafka_event_skipped_no_user",
		)
		return nil
	}

	n := &model.Notification{
		UserID: event.UserID,
		Read:   false,
	}

	// Build extra data context
	extraData := map[string]interface{}{
		"workspace_id":  event.WorkspaceID,
		"collection_id": event.CollectionID,
		"repository_id": event.RepositoryID,
	}

	switch topic {
	case "collection.events.started":
		n.Type = "collection_started"
		n.Title = "Collection Started"
		n.Message = fmt.Sprintf("Data collection #%d has started.", event.CollectionID)
		if event.WorkspaceID != 0 && event.RepositoryID != 0 {
			n.LinkURL = fmt.Sprintf("workspaces/%d/repositories/%d/collect", event.WorkspaceID, event.RepositoryID)
		}

	case "collection.events.completed":
		n.Type = "collection_completed"
		n.Title = "Collection Completed"
		n.Message = fmt.Sprintf("Data collection #%d completed successfully.", event.CollectionID)
		if event.WorkspaceID != 0 && event.RepositoryID != 0 {
			n.LinkURL = fmt.Sprintf("workspaces/%d/repositories/%d/collect", event.WorkspaceID, event.RepositoryID)
		}

	case "collection.events.failed":
		n.Type = "collection_failed"
		n.Title = "Collection Failed"
		n.Message = fmt.Sprintf("Data collection #%d failed: %s", event.CollectionID, event.Error)
		if event.WorkspaceID != 0 && event.RepositoryID != 0 {
			n.LinkURL = fmt.Sprintf("workspaces/%d/repositories/%d/collect", event.WorkspaceID, event.RepositoryID)
		}
		extraData["error"] = event.Error
		slog.Warn("Collection failed event received",
			"service", "notification",
			"collection_id", event.CollectionID,
			"repository_id", event.RepositoryID,
			"error", event.Error,
			"event", "collection_failed_event",
			"status", "failed",
		)

	case "analysis.events.requested":
		n.Type = "analysis_requested"
		n.Title = "Analysis Queued"
		n.Message = fmt.Sprintf("Analysis for collection #%d has been queued.", event.CollectionID)

	case "analysis.events.completed":
		n.Type = "analysis_completed"
		n.Title = "Analysis Completed"
		n.Message = fmt.Sprintf("Analysis for collection #%d is complete.", event.CollectionID)

	case "notification.events":
		// Generic notification — services can send arbitrary notifications
		if event.Type == "" || event.Message == "" {
			slog.Warn("notification.events missing type or message",
				"service", "notification",
				"event", "notification_event_incomplete",
			)
			return nil
		}
		n.Type = event.Type
		n.Title = event.Title
		n.Message = event.Message
		n.LinkURL = event.LinkURL // Pass through optional link

	default:
		slog.Warn("Unknown Kafka topic",
			"service", "notification",
			"topic", topic,
			"event", "kafka_unknown_topic",
		)
		return nil
	}

	dataBytes, _ := json.Marshal(extraData)
	n.Data = string(dataBytes)

	return n
}
