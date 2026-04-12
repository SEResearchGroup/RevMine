package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"

	"notification-service/internal/config"
	"notification-service/internal/db"
	"notification-service/internal/handler"
	"notification-service/internal/kafka"
	"notification-service/internal/ws"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/logger"
)

func main() {
	cfg := config.Load()

	// Initialize database
	database, err := db.Connect(cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer database.Close()

	if err := db.Migrate(database); err != nil {
		log.Fatalf("Failed to run migrations: %v", err)
	}

	// Initialize WebSocket hub
	hub := ws.NewHub()
	go hub.Run()

	// Initialize Kafka consumer
	consumer, err := kafka.NewConsumer(cfg.KafkaBrokers, cfg.KafkaGroupID, database, hub)
	if err != nil {
		log.Fatalf("Failed to create Kafka consumer: %v", err)
	}
	go consumer.Start()

	// Initialize Fiber app
	app := fiber.New(fiber.Config{
		DisableStartupMessage: false,
	})

	app.Use(logger.New())
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
		log.Println("Shutting down...")
		consumer.Stop()
		app.Shutdown()
	}()

	port := cfg.Port
	if port == "" {
		port = "8005"
	}
	log.Printf("Notification service starting on :%s", port)
	if err := app.Listen(":" + port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
