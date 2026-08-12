-- SQL to create the students table in Supabase.
-- Run this in the Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS public.students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT,
    email TEXT,
    grade TEXT,
    status TEXT DEFAULT 'not_started',
    scores JSONB,
    letter TEXT,
    answers JSONB,
    is_admin BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    CONSTRAINT unique_auth_user_id UNIQUE (auth_user_id)
);

-- Enable Row Level Security (optional but recommended)
ALTER TABLE public.students ENABLE ROW LEVEL SECURITY;

-- If RLS is enabled, you would want policies like:
CREATE POLICY "Allow users to read their own record" ON public.students FOR SELECT USING (auth.uid() = auth_user_id);
CREATE POLICY "Allow users to update their own record" ON public.students FOR UPDATE USING (auth.uid() = auth_user_id);
CREATE POLICY "Allow admins to read all records" ON public.students FOR SELECT USING (EXISTS (SELECT 1 FROM public.students WHERE auth_user_id = auth.uid() AND is_admin = true));
CREATE POLICY "Allow admins to update all records" ON public.students FOR UPDATE USING (EXISTS (SELECT 1 FROM public.students WHERE auth_user_id = auth.uid() AND is_admin = true));
