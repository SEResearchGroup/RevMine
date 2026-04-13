package model

import "time"

type Notification struct {
	ID        string    `json:"id"`
	UserID    int       `json:"user_id"`
	Type      string    `json:"type"`
	Title     string    `json:"title"`
	Message   string    `json:"message"`
	Data      string    `json:"data,omitempty"` // JSON string for extra context
	LinkURL   string    `json:"link_url,omitempty"` // Optional frontend navigation path
	Read      bool      `json:"read"`
	CreatedAt time.Time `json:"created_at"`
}
