-- Initialize PostgreSQL with vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add this to the top of init-postgres.sql
DO $$
BEGIN
   IF NOT EXISTS (SELECT 1 FROM pg_user WHERE usename = 'ollama_proxy') THEN
      CREATE USER ollama_proxy WITH PASSWORD 'pass';
   END IF;
END $$;

-- Then your existing code follows...
GRANT ALL ON FUNCTION public.first(anyelement, "any") TO ollama_proxy;