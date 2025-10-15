-- Add provider_tokens column to users table
ALTER TABLE public.users 
ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();

-- Add name column to the users table 
ALTER TABLE public.users 
ADD COLUMN name TEXT NOT NULL; 
