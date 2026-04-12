package ws

import (
	"log"
	"sync"

	"github.com/gofiber/contrib/websocket"
)

// Hub manages all active WebSocket connections per user
type Hub struct {
	mu      sync.RWMutex
	clients map[int]map[*websocket.Conn]bool // userID -> set of connections
}

func NewHub() *Hub {
	return &Hub{
		clients: make(map[int]map[*websocket.Conn]bool),
	}
}

func (h *Hub) Run() {
	// Hub is passive — no background loop needed.
	// Register/Unregister/Send are called directly.
	select {}
}

func (h *Hub) Register(userID int, conn *websocket.Conn) {
	h.mu.Lock()
	defer h.mu.Unlock()

	if h.clients[userID] == nil {
		h.clients[userID] = make(map[*websocket.Conn]bool)
	}
	h.clients[userID][conn] = true
	log.Printf("[WS] User %d connected (total connections: %d)", userID, len(h.clients[userID]))
}

func (h *Hub) Unregister(userID int, conn *websocket.Conn) {
	h.mu.Lock()
	defer h.mu.Unlock()

	if conns, ok := h.clients[userID]; ok {
		delete(conns, conn)
		if len(conns) == 0 {
			delete(h.clients, userID)
		}
	}
	log.Printf("[WS] User %d disconnected", userID)
}

// SendToUser sends a message bytes to all connections of a user
func (h *Hub) SendToUser(userID int, message []byte) {
	h.mu.RLock()
	defer h.mu.RUnlock()

	conns, ok := h.clients[userID]
	if !ok {
		return
	}

	for conn := range conns {
		if err := conn.WriteMessage(websocket.TextMessage, message); err != nil {
			log.Printf("[WS] Error sending to user %d: %v", userID, err)
			conn.Close()
			// Cleanup will happen via Unregister when the read loop detects close
		}
	}
}
