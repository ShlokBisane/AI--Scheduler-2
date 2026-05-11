-- ═══════════════════════════════════════════════════════════
-- Master Scheduler AI — Supabase PostgreSQL Migration
-- Run this in Supabase SQL Editor to create all tables
-- ═══════════════════════════════════════════════════════════

-- Settings table (single-row config)
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    openrouter_api_key TEXT DEFAULT '',
    user_name TEXT DEFAULT '',
    user_type TEXT DEFAULT 'student',
    profile_json TEXT DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chats table
CREATE TABLE IF NOT EXISTS chats (
    id BIGSERIAL PRIMARY KEY,
    title TEXT DEFAULT 'New Chat',
    mode TEXT DEFAULT 'student',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
    content TEXT NOT NULL,
    schedule_json TEXT,
    confirmed INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Schedule batches table (versioned schedules)
CREATE TABLE IF NOT EXISTS schedule_batches (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT REFERENCES chats(id) ON DELETE SET NULL,
    message_id BIGINT REFERENCES messages(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Schedules table
CREATE TABLE IF NOT EXISTS schedules (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT REFERENCES chats(id) ON DELETE SET NULL,
    batch_id BIGINT REFERENCES schedule_batches(id) ON DELETE SET NULL,
    subject TEXT NOT NULL,
    color TEXT DEFAULT '#4A90D9',
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    session_type TEXT DEFAULT 'study',
    topic TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 3,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Subject colors table
CREATE TABLE IF NOT EXISTS subject_colors (
    id BIGSERIAL PRIMARY KEY,
    subject TEXT UNIQUE NOT NULL,
    color TEXT NOT NULL DEFAULT '#4A90D9',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Schedule history table
CREATE TABLE IF NOT EXISTS schedule_history (
    id BIGSERIAL PRIMARY KEY,
    original_schedule_id BIGINT,
    chat_id BIGINT,
    subject TEXT NOT NULL,
    color TEXT DEFAULT '#4A90D9',
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    session_type TEXT DEFAULT 'study',
    topic TEXT DEFAULT '',
    status TEXT DEFAULT 'completed',
    priority INTEGER DEFAULT 3,
    reason TEXT DEFAULT 'completed',
    moved_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_schedules_date ON schedules(date);
CREATE INDEX IF NOT EXISTS idx_schedules_chat_id ON schedules(chat_id);
CREATE INDEX IF NOT EXISTS idx_schedules_status ON schedules(status);
CREATE INDEX IF NOT EXISTS idx_history_moved_at ON schedule_history(moved_at);
CREATE INDEX IF NOT EXISTS idx_schedules_batch_id ON schedules(batch_id);
CREATE INDEX IF NOT EXISTS idx_schedule_batches_active ON schedule_batches(is_active);
CREATE INDEX IF NOT EXISTS idx_schedule_batches_created_at ON schedule_batches(created_at);

-- Backfill support for existing installs
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS batch_id BIGINT;

-- Seed the settings row
INSERT INTO settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- Enable Row Level Security (disabled for simplicity — single-user app)
-- ALTER TABLE settings ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE chats ENABLE ROW LEVEL SECURITY;
-- etc.
ALTER TABLE chats DISABLE ROW LEVEL SECURITY;
ALTER TABLE messages DISABLE ROW LEVEL SECURITY;
ALTER TABLE schedules DISABLE ROW LEVEL SECURITY;
ALTER TABLE settings DISABLE ROW LEVEL SECURITY;
ALTER TABLE subject_colors DISABLE ROW LEVEL SECURITY;
ALTER TABLE schedule_history DISABLE ROW LEVEL SECURITY;
ALTER TABLE schedule_batches DISABLE ROW LEVEL SECURITY;