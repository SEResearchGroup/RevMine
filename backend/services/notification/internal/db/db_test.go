package db

import "testing"

func TestWithDefaultSSLModeAddsDisableForPostgresURL(t *testing.T) {
	got := withDefaultSSLMode("postgresql://postgres:postgres@notification-db:5432/notification_db")
	want := "postgresql://postgres:postgres@notification-db:5432/notification_db?sslmode=disable"

	if got != want {
		t.Fatalf("expected %q, got %q", want, got)
	}
}

func TestWithDefaultSSLModeKeepsExplicitSSLMode(t *testing.T) {
	dsn := "postgresql://postgres:postgres@db.example/notification_db?sslmode=require"

	if got := withDefaultSSLMode(dsn); got != dsn {
		t.Fatalf("expected explicit sslmode to be preserved, got %q", got)
	}
}
