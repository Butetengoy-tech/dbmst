import os
import sys
# Add current dir to path
sys.path.insert(0, os.path.abspath('.'))

import app.extensions
from app import create_app

flask_app = create_app()
supabase = app.extensions.supabase

with flask_app.app_context():
    print("Swimmers:")
    res = supabase.table('swimmers').select('*').execute()
    print(len(res.data) if res.data else 0)

    print("Competitions:")
    res = supabase.table('competitions').select('*').execute()
    print(len(res.data) if res.data else 0)

    print("Race Results:")
    res = supabase.table('race_results').select('*, events(distance, stroke, competitions(date))').execute()
    print(len(res.data) if res.data else 0)
    if res.data:
        print(res.data[:2])
