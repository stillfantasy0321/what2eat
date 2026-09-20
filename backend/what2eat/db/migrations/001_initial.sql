CREATE TABLE users(id uuid PRIMARY KEY, created_at timestamptz NOT NULL DEFAULT now());
INSERT INTO users(id) VALUES ('00000000-0000-0000-0000-000000000001');
CREATE TABLE sessions(
 id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id), title text NOT NULL,
 status text NOT NULL DEFAULT 'active', next_seq bigint NOT NULL DEFAULT 1,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX sessions_user_order ON sessions(user_id,updated_at DESC,id DESC);
CREATE TABLE chat_runs(
 request_id uuid PRIMARY KEY, session_id uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
 assistant_message_id uuid NOT NULL, input_hash text NOT NULL, status text NOT NULL,
 error_code text, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX one_running_chat_per_session ON chat_runs(session_id) WHERE status='running';
CREATE TABLE messages(
 id uuid PRIMARY KEY, session_id uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
 request_id uuid NOT NULL, seq bigint NOT NULL, role text NOT NULL,
 message jsonb NOT NULL, sources jsonb NOT NULL DEFAULT '[]', status text NOT NULL,
 visible boolean NOT NULL DEFAULT true,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(session_id,seq)
);
CREATE TABLE documents(
 id uuid PRIMARY KEY, content_hash text NOT NULL, source_path text NOT NULL,
 source_url text, title text NOT NULL, category text NOT NULL DEFAULT '用户资料',
 index_version text NOT NULL, state text NOT NULL CHECK(state IN ('pending','indexing','ready','failed','deleting')),
 error text, metadata jsonb NOT NULL DEFAULT '{}',
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(content_hash,index_version)
);
