-- Add summary range tracking to the summary table
ALTER TABLE summary 
ADD COLUMN IF NOT EXISTS start_date TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS end_date TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS document_count INTEGER DEFAULT 0;

-- Add index for the date range queries
CREATE INDEX IF NOT EXISTS idx_summary_date_range ON summary(user_id, start_date, end_date);

-- Add comments
COMMENT ON COLUMN summary.start_date IS 'Start date of the summarization range';
COMMENT ON COLUMN summary.end_date IS 'End date of the summarization range';
COMMENT ON COLUMN summary.document_count IS 'Number of unique documents included in this summary';