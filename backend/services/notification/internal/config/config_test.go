package config

import "testing"

func TestLoadReadsConfigurationFromEnvironment(t *testing.T) {
	t.Setenv("PORT", "9000")
	t.Setenv("DATABASE_URL", "postgres://db.example.invalid/notification")
	t.Setenv("KAFKA_BOOTSTRAP_SERVERS", "kafka-a:9092")
	t.Setenv("KAFKA_GROUP_ID", "notifications-test")

	cfg := Load()

	if cfg.Port != "9000" {
		t.Fatalf("expected custom port, got %s", cfg.Port)
	}
	if cfg.DatabaseURL != "postgres://db.example.invalid/notification" {
		t.Fatalf("expected DATABASE_URL from environment, got %s", cfg.DatabaseURL)
	}
	if cfg.KafkaBrokers[0] != "kafka-a:9092" {
		t.Fatalf("expected custom Kafka broker, got %s", cfg.KafkaBrokers[0])
	}
	if cfg.KafkaGroupID != "notifications-test" {
		t.Fatalf("expected custom Kafka group, got %s", cfg.KafkaGroupID)
	}
}

func TestLoadRequiresDatabaseURL(t *testing.T) {
	t.Setenv("DATABASE_URL", "")

	defer func() {
		if recover() == nil {
			t.Fatal("expected Load to panic when DATABASE_URL is missing")
		}
	}()

	Load()
}
