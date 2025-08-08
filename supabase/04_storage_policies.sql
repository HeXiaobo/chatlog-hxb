-- Storage bucket policies for file upload functionality

-- Create the storage bucket (if not exists)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'wechat-files',
    'wechat-files', 
    true,
    52428800, -- 50MB limit
    ARRAY['application/json', 'text/plain']::text[]
)
ON CONFLICT (id) DO NOTHING;

-- Enable RLS on storage objects
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Policy: Allow anyone to upload files
CREATE POLICY "Allow public file uploads" ON storage.objects
FOR INSERT 
WITH CHECK (bucket_id = 'wechat-files');

-- Policy: Allow anyone to read files 
CREATE POLICY "Allow public file access" ON storage.objects
FOR SELECT 
USING (bucket_id = 'wechat-files');

-- Policy: Allow file updates (for processing status)
CREATE POLICY "Allow file updates" ON storage.objects
FOR UPDATE 
USING (bucket_id = 'wechat-files')
WITH CHECK (bucket_id = 'wechat-files');

-- Policy: Allow file deletion
CREATE POLICY "Allow file deletion" ON storage.objects
FOR DELETE 
USING (bucket_id = 'wechat-files');