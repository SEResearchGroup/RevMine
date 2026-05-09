package main

import (
	"log"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
	"time"

	"notification-service/internal/config"
	"notification-service/internal/db"
	"notification-service/internal/handler"
	"notification-service/internal/kafka"
	"notification-service/internal/ws"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
)

func main() {
	// Structured JSON logging via slog
	jsonLogger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: slog.LevelInfo,
		ReplaceAttr: func(groups []string, a slog.Attr) slog.Attr {
			// Rename "time" → "timestamp" for consistency with other services
			if a.Key == slog.TimeKey {
				a.Key = "timestamp"
			}
			// Rename "msg" → "message" for Loki JSON parsing
			if a.Key == slog.MessageKey {
				a.Key = "message"
			}
			return a
		},
	}))
	slog.SetDefault(jsonLogger)

	cfg := config.Load()

	slog.Info("Notification service starting",
		"service", "notification",
		"port", cfg.Port,
		"event", "service_startup",
	)

	// Initialize database
	database, err := db.Connect(cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer database.Close()
	slog.Info("Database connected", "service", "notification", "event", "db_connected")

	if err := db.Migrate(database); err != nil {
		log.Fatalf("Failed to run migrations: %v", err)
	}
	slog.Info("Database migrations applied", "service", "notification", "event", "db_migrated")

	// Initialize WebSocket hub
	hub := ws.NewHub()
	go hub.Run()
	slog.Info("WebSocket hub started", "service", "notification", "event", "ws_hub_started")

	// Initialize Kafka consumer
	consumer, err := kafka.NewConsumer(cfg.KafkaBrokers, cfg.KafkaGroupID, database, hub)
	if err != nil {
		log.Fatalf("Failed to create Kafka consumer: %v", err)
	}
	go consumer.Start()
	slog.Info("Kafka consumer started",
		"service", "notification",
		"brokers", cfg.KafkaBrokers,
		"group_id", cfg.KafkaGroupID,
		"event", "kafka_consumer_started",
	)

	// Initialize Fiber app (no built-in logger — replaced by slog middleware)
	app := fiber.New(fiber.Config{
		DisableStartupMessage: false,
	})

	// Request logging middleware
	app.Use(func(c *fiber.Ctx) error {
		start := time.Now()
		err := c.Next()
		duration := time.Since(start).Seconds()
		slog.Info("HTTP request",
			"service", "notification",
			"method", c.Method(),
			"path", c.Path(),
			"status_code", c.Response().StatusCode(),
			"duration", duration,
			"event", "http_request",
		)
		return err
	})

	app.Use(cors.New(cors.Config{
		AllowOrigins: "*",
		AllowHeaders: "Origin, Content-Type, Accept, Authorization, X-User-ID",
	}))

	// Routes
	h := handler.New(database, hub)
	api := app.Group("/api/notifications")

	api.Get("/ws", h.WebSocketUpgrade(), h.WebSocket())
	api.Get("/", h.ListNotifications)
	api.Get("/unread-count", h.UnreadCount)
	api.Patch("/:id/read", h.MarkAsRead)
	api.Patch("/read-all", h.MarkAllAsRead)
	api.Delete("/:id", h.DeleteNotification)

	api.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "ok"})
	})

	// Graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-quit
		slog.Info("Shutdown signal received, stopping service",
			"service", "notification",
			"event", "service_shutdown",
		)
		consumer.Stop()
		app.Shutdown()
	}()

	port := cfg.Port
	if port == "" {
		port = "8005"
	}
	slog.Info("Notification service listening",
		"service", "notification",
		"port", port,
		"event", "service_ready",
	)
	if err := app.Listen(":" + port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
