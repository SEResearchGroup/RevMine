package db

import (
	"database/sql"
	"log"

	_ "github.com/lib/pq"
)

func Connect(databaseURL string) (*sql.DB, error) {
	db, err := sql.Open("postgres", databaseURL)
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

	log.Println("Database migration completed")
	return nil
}
