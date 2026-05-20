package db

import (
	"database/sql"
	"log"
	"net/url"
	"strings"

	_ "github.com/lib/pq"
)

func Connect(databaseURL string) (*sql.DB, error) {
	db, err := sql.Open("postgres", withDefaultSSLMode(databaseURL))
	if err != nil {
		return nil, err
	}

	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(5)

	if err := db.Ping(); err != nil {
		return nil, err
	}

	log.Println("Connected to database")
	return db, nil
}

func withDefaultSSLMode(databaseURL string) string {
	if strings.Contains(databaseURL, "sslmode=") {
		return databaseURL
	}

	parsed, err := url.Parse(databaseURL)
	if err != nil || (parsed.Scheme != "postgres" && parsed.Scheme != "postgresql") {
		return databaseURL
	}

	query := parsed.Query()
	query.Set("sslmode", "disable")
	parsed.RawQuery = query.Encode()
	return parsed.String()
}

func Migrate(db *sql.DB) error {
	query := `
	CREATE TABLE IF NOT EXISTS notifications (
		id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
		user_id INTEGER NOT NULL,
		type VARCHAR(100) NOT NULL,
		title VARCHAR(255) NOT NULL,
		message TEXT NOT NULL,
		data JSONB DEFAULT '{}',
		read BOOLEAN DEFAULT FALSE,
		created_at TIMESTAMPTZ DEFAULT NOW()
	);

	CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
	CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications(user_id, read);
	CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at DESC);
	`

	_, err := db.Exec(query)
	if err != nil {
		return err
	}

	// Add link_url column if it doesn't exist (safe migration for existing databases)
	_, err = db.Exec(`ALTER TABLE notifications ADD COLUMN IF NOT EXISTS link_url TEXT NOT NULL DEFAULT ''`)
	if err != nil {
		return err
	}

	log.Println("Database migration completed")
	return nil
}
