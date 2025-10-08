-- Add provider_tokens column to users table
ALTER TABLE public.users 
ADD COLUMN provider_tokens JSONB DEFAULT '{}';
