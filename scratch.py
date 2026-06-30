from app import create_app
from flask import request

app = create_app()

with app.test_client() as client:
    # First we need to login
    with client.session_transaction() as sess:
        sess['user_id'] = '123'
        sess['role'] = 'HeadCoach'
    
    # We need a valid race_result ID from the db
    with app.app_context():
        from app.extensions import supabase
        res = supabase.table('race_results').select('id, event_id').limit(1).execute()
        if res.data:
            race_id = res.data[0]['id']
            print(f"Testing with race_id: {race_id}")
            
            # Post to edit
            response = client.post(f'/swimmers/edit_race/{race_id}', data={
                'competition': '2023 DAVRAA MEET',
                'stroke': 'Butterfly',
                'distance': '50',
                'category': 'Boys 6-12',
                'time': '00:00:39.79'
            }, follow_redirects=True)
            
            print(f"Status Code: {response.status_code}")
            print("Response body preview:")
            body = response.get_data(as_text=True)
            if "Error updating race result" in body:
                print("Error flashed!")
                # let's grep for the exact message
                import re
                match = re.search(r'Error updating race result:.*?(<|")', body)
                if match:
                    print(match.group(0))
            else:
                print("No error flashed.")
        else:
            print("No race results found to test.")
