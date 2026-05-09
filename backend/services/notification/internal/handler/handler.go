package handler

import (
	"database/sql"
	"log/slog"
	"strconv"

	dbpkg "notification-service/internal/db"
	"notification-service/internal/model"
	"notification-service/internal/ws"

	"github.com/gofiber/contrib/websocket"
	"github.com/gofiber/fiber/v2"
)

type Handler struct {
	database *sql.DB
	hub      *ws.Hub
}

func New(database *sql.DB, hub *ws.Hub) *Handler {
	return &Handler{database: database, hub: hub}
}

// extractUserID gets user_id from X-User-ID header (set by api-gateway proxy)
func extractUserID(c *fiber.Ctx) (int, error) {
	userIDStr := c.Get("X-User-ID")
	if userIDStr == "" {
		return 0, fiber.NewError(fiber.StatusUnauthorized, "Missing X-User-ID header")
	}
	return strconv.Atoi(userIDStr)
}

// WebSocketUpgrade is middleware that checks if the request is a WebSocket upgrade
func (h *Handler) WebSocketUpgrade() fiber.Handler {
	return func(c *fiber.Ctx) error {
		if websocket.IsWebSocketUpgrade(c) {
			return c.Next()
		}
		return fiber.ErrUpgradeRequired
	}
}

// WebSocket handles WebSocket connections
func (h *Handler) WebSocket() fiber.Handler {
	return websocket.New(func(c *websocket.Conn) {
		// Get user_id from query param (WebSocket can't use headers easily)
		userIDStr := c.Query("user_id")
		userID, err := strconv.Atoi(userIDStr)
		if err != nil || userID == 0 {
			slog.Warn("WebSocket rejected: invalid user_id",
				"service", "notification",
				"user_id_raw", userIDStr,
				"event", "ws_rejected",
			)
			c.Close()
			return
		}

		slog.Info("WebSocket client connected",
			"service", "notification",
			"user_id", userID,
			"event", "ws_connected",
		)
		h.hub.Register(userID, c)
		defer func() {
			h.hub.Unregister(userID, c)
			slog.Info("WebSocket client disconnected",
				"service", "notification",
				"user_id", userID,
				"event", "ws_disconnected",
			)
		}()

		// Read loop to keep the connection alive and detect disconnects
		for {
			_, _, err := c.ReadMessage()
			if err != nil {
				break
			}
		}
	})
}

// ListNotifications returns paginated notifications for the user
func (h *Handler) ListNotifications(c *fiber.Ctx) error {
	userID, err := extractUserID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"error": "Unauthorized"})
	}

	limit := c.QueryInt("limit", 20)
	offset := c.QueryInt("offset", 0)

	if limit > 100 {
		limit = 100
	}

	notifications, err := dbpkg.GetNotificationsByUser(h.database, userID, limit, offset)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to fetch notifications"})
	}

	if notifications == nil {
		notifications = []model.Notification{}
	}

	return c.JSON(fiber.Map{
		"notifications": notifications,
		"limit":         limit,
		"offset":        offset,
	})
}

// UnreadCount returns the count of unread notifications
func (h *Handler) UnreadCount(c *fiber.Ctx) error {
	userID, err := extractUserID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"error": "Unauthorized"})
	}

	count, err := dbpkg.GetUnreadCount(h.database, userID)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to fetch count"})
	}

	return c.JSON(fiber.Map{"unread_count": count})
}

// MarkAsRead marks a single notification as read
func (h *Handler) MarkAsRead(c *fiber.Ctx) error {
	userID, err := extractUserID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"error": "Unauthorized"})
	}

	notifID := c.Params("id")
	if notifID == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Missing notification ID"})
	}

	if err := dbpkg.MarkAsRead(h.database, notifID, userID); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to mark as read"})
	}

	return c.JSON(fiber.Map{"status": "ok"})
}

// MarkAllAsRead marks all notifications as read for the user
func (h *Handler) MarkAllAsRead(c *fiber.Ctx) error {
	userID, err := extractUserID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"error": "Unauthorized"})
	}

	if err := dbpkg.MarkAllAsRead(h.database, userID); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to mark all as read"})
	}

	return c.JSON(fiber.Map{"status": "ok"})
}

// DeleteNotification deletes a notification
func (h *Handler) DeleteNotification(c *fiber.Ctx) error {
	userID, err := extractUserID(c)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"error": "Unauthorized"})
	}

	notifID := c.Params("id")
	if notifID == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "Missing notification ID"})
	}

	if err := dbpkg.DeleteNotification(h.database, notifID, userID); err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to delete"})
	}

	return c.JSON(fiber.Map{"status": "ok"})
}
