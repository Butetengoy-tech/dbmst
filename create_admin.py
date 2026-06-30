from app import create_app
import app.extensions as ext

app = create_app()

with app.app_context():
    email = "headcoach@example.com"
    password = "LivePassword123!"
    
    print("Attempting to create a live Head Coach account in Supabase...")
    try:
        # Sign up the user
        response = ext.supabase.auth.sign_up({"email": email, "password": password})
        
        if response.user:
            # Create user_profile record
            ext.supabase.table('user_profiles').insert({
                "id": response.user.id,
                "email": email,
                "role": "HeadCoach"
            }).execute()
            print(f"Success! Created account with email: {email} and password: {password}")
        else:
            print("Failed to create user. It might already exist.")
    except Exception as e:
        print(f"Error: {e}")
