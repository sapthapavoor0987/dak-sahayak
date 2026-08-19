-- Enable pgvector extension (run once in Supabase SQL Editor)
CREATE EXTENSION IF NOT EXISTS vector;

-- Table 1: documents (Vector Store for RAG)
CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(768),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING hnsw (embedding vector_cosine_ops);

-- Table 2: conversations (Chat Sessions)
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT DEFAULT 'New Chat',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, updated_at DESC);

-- Table 3: messages (Individual Chat Messages)
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at ASC);

-- Table 4: pincodes (PIN Code Directory)
CREATE TABLE IF NOT EXISTS pincodes (
    id BIGSERIAL PRIMARY KEY,
    pincode VARCHAR(6) NOT NULL,
    office_name TEXT,
    office_type TEXT,
    delivery_status TEXT,
    taluk TEXT,
    division TEXT,
    district TEXT,
    region TEXT,
    state TEXT,
    circle TEXT
);

CREATE INDEX IF NOT EXISTS idx_pincodes_pincode ON pincodes(pincode);
CREATE INDEX IF NOT EXISTS idx_pincodes_office ON pincodes(LOWER(office_name));


-- RPC Function: match_documents (Vector Similarity Search)
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(768),
    match_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 3
)
RETURNS TABLE (
    id BIGINT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.content,
        d.metadata,
        1 - (d.embedding <=> query_embedding) AS similarity
    FROM documents d
    WHERE 1 - (d.embedding <=> query_embedding) > match_threshold
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;


-- Row Level Security (RLS) Policies

-- Conversations: Users can only see their own
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can CRUD own conversations" ON conversations;
CREATE POLICY "Users can CRUD own conversations"
    ON conversations FOR ALL
    USING (auth.uid() = user_id);

-- Messages: Users can only see messages in their own conversations
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can CRUD own messages" ON messages;
CREATE POLICY "Users can CRUD own messages"
    ON messages FOR ALL
    USING (conversation_id IN (
        SELECT id FROM conversations WHERE user_id = auth.uid()
    ));

-- Documents: Readable by all authenticated users (knowledge base)
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can read documents" ON documents;
CREATE POLICY "Authenticated users can read documents"
    ON documents FOR SELECT
    USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

-- Pincodes: Readable by all (public data)
ALTER TABLE pincodes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Anyone can read pincodes" ON pincodes;
CREATE POLICY "Anyone can read pincodes"
    ON pincodes FOR SELECT
    USING (true);
