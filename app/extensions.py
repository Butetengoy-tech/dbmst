from supabase import create_client, Client

# Initialize Supabase client
supabase: Client = None

def init_supabase(app):
    global supabase
    url = app.config.get('SUPABASE_URL')
    key = app.config.get('SUPABASE_KEY')
    if url and key:
        supabase = create_client(url, key)
