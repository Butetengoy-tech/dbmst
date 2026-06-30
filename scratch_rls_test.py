from app import create_app
from flask import current_app
import app.extensions as ext

app = create_app()

with app.app_context():
    print("Testing signup to see if RLS blocks insert...")
    try:
        response = ext.supabase.auth.sign_up({
            "email": "testrls1@example.com", 
            "password": "Password123!"
        })
        if response.user:
            print("User created in Auth.")
            # Try to insert into user_profiles
            ext.supabase.table('user_profiles').insert({
                "id": response.user.id,
                "email": "testrls1@example.com",
                "role": "Swimmer"
            }).execute()
            print("Successfully inserted into user_profiles! No RLS block.")
        else:
            print("Failed to sign up.")
    except Exception as e:
        print(f"Exception: {e}")
