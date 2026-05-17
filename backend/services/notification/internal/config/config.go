package config

import "os"

type Config struct {
	Port           string
	DatabaseURL    string
	KafkaBrokers   []string
	KafkaGroupID   string
}

func Load() *Config {
	return &Config{
		Port:         getEnv("PORT", "8005"),
		DatabaseURL:  requireEnv("DATABASE_URL"),
		KafkaBrokers: []string{getEnv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")},
		KafkaGroupID: getEnv("KAFKA_GROUP_ID", "notification-service"),
	}
}

func getEnv(key, fallback string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return fallback
}

func requireEnv(key string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	panic("missing required environment variable: " + key)
}
