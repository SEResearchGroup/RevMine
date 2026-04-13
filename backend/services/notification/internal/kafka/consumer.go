package kafka

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"

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
				log.Printf("[Kafka] Consumer error: %v", err)
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
	log.Println("[Kafka] Consumer group session setup")
	return nil
}

func (h *consumerGroupHandler) Cleanup(_ sarama.ConsumerGroupSession) error {
	log.Println("[Kafka] Consumer group session cleanup")
	return nil
}

func (h *consumerGroupHandler) ConsumeClaim(session sarama.ConsumerGroupSession, claim sarama.ConsumerGroupClaim) error {
	for msg := range claim.Messages() {
		log.Printf("[Kafka] Received message from topic %s: %s", msg.Topic, string(msg.Value))

		notification := h.transformEvent(msg.Topic, msg.Value)
		if notification == nil {
			session.MarkMessage(msg, "")
			continue
		}

		// Persist to database
		if err := db.InsertNotification(h.database, notification); err != nil {
			log.Printf("[Kafka] Failed to insert notification: %v", err)
			session.MarkMessage(msg, "")
			continue
		}

		// Push to user via WebSocket
		payload, err := json.Marshal(notification)
		if err == nil {
			h.hub.SendToUser(notification.UserID, payload)
		}

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
		log.Printf("[Kafka] Failed to parse event: %v", err)
		return nil
	}

	if event.UserID == 0 {
		log.Printf("[Kafka] Skipping event with no user_id on topic %s", topic)
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
			log.Printf("[Kafka] notification.events missing type or message")
			return nil
		}
		n.Type = event.Type
		n.Title = event.Title
		n.Message = event.Message
		n.LinkURL = event.LinkURL // Pass through optional link

	default:
		log.Printf("[Kafka] Unknown topic: %s", topic)
		return nil
	}

	dataBytes, _ := json.Marshal(extraData)
	n.Data = string(dataBytes)

	return n
}
