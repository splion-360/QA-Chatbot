
CREATE TABLE conversation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE conversation_history IS 'Stores conversation history for context-aware chat';
COMMENT ON COLUMN conversation_history.id IS 'Unique identifier for each conversation entry';
COMMENT ON COLUMN conversation_history.user_id IS 'User ID from auth service';
COMMENT ON COLUMN conversation_history.message IS 'User message/question';
COMMENT ON COLUMN conversation_history.response IS 'AI assistant response';


CREATE INDEX idx_conversation_history_user_id ON conversation_history(user_id);
CREATE INDEX idx_conversation_history_created_at ON conversation_history(created_at);


ALTER TABLE conversation_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own conversation history" ON conversation_history
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can add to their own conversation history" ON conversation_history
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own conversation history" ON conversation_history
    FOR DELETE USING (auth.uid() = user_id);