package db

import (
	"database/sql"
	"encoding/json"

	"notification-service/internal/model"
)

func InsertNotification(db *sql.DB, n *model.Notification) error {
	query := `
		INSERT INTO notifications (user_id, type, title, message, data, link_url, read)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		RETURNING id, created_at
	`
	return db.QueryRow(query, n.UserID, n.Type, n.Title, n.Message, n.Data, n.LinkURL, n.Read).
		Scan(&n.ID, &n.CreatedAt)
}

func GetNotificationsByUser(db *sql.DB, userID int, limit, offset int) ([]model.Notification, error) {
	query := `
		SELECT id, user_id, type, title, message, data, link_url, read, created_at
		FROM notifications
		WHERE user_id = $1
		ORDER BY created_at DESC
		LIMIT $2 OFFSET $3
	`
	rows, err := db.Query(query, userID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var notifications []model.Notification
	for rows.Next() {
		var n model.Notification
		var data sql.NullString
		var linkURL sql.NullString
		if err := rows.Scan(&n.ID, &n.UserID, &n.Type, &n.Title, &n.Message, &data, &linkURL, &n.Read, &n.CreatedAt); err != nil {
			return nil, err
		}
		if data.Valid {
			n.Data = data.String
		}
		if linkURL.Valid {
			n.LinkURL = linkURL.String
		}
		notifications = append(notifications, n)
	}
	return notifications, nil
}

func GetUnreadCount(db *sql.DB, userID int) (int, error) {
	var count int
	err := db.QueryRow("SELECT COUNT(*) FROM notifications WHERE user_id = $1 AND read = FALSE", userID).Scan(&count)
	return count, err
}

func MarkAsRead(db *sql.DB, notificationID string, userID int) error {
	_, err := db.Exec(
		"UPDATE notifications SET read = TRUE WHERE id = $1 AND user_id = $2",
		notificationID, userID,
	)
	return err
}

func MarkAllAsRead(db *sql.DB, userID int) error {
	_, err := db.Exec("UPDATE notifications SET read = TRUE WHERE user_id = $1 AND read = FALSE", userID)
	return err
}

func DeleteNotification(db *sql.DB, notificationID string, userID int) error {
	_, err := db.Exec("DELETE FROM notifications WHERE id = $1 AND user_id = $2", notificationID, userID)
	return err
}

// NotificationToJSON serializes a notification for WebSocket push
func NotificationToJSON(n *model.Notification) ([]byte, error) {
	return json.Marshal(n)
}
