CREATE TABLE public.demo_workspaces (id text PRIMARY KEY CHECK (id = 'plougastel-demo'), state jsonb NOT NULL, revision integer NOT NULL DEFAULT 0, updated_at timestamptz NOT NULL DEFAULT now());
GRANT SELECT, UPDATE ON public.demo_workspaces TO anon, authenticated;
GRANT ALL ON public.demo_workspaces TO service_role;
ALTER TABLE public.demo_workspaces ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public fictional demo read" ON public.demo_workspaces FOR SELECT TO anon, authenticated USING (id = 'plougastel-demo');
CREATE POLICY "Public fictional demo edit" ON public.demo_workspaces FOR UPDATE TO anon, authenticated USING (id = 'plougastel-demo') WITH CHECK (id = 'plougastel-demo');