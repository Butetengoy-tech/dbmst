import app.extensions
from app import create_app

flask_app = create_app()
with flask_app.test_client() as client:
    with client.session_transaction() as sess:
        sess['user_id'] = '123'
        sess['role'] = 'HeadCoach'
    res = client.get('/')
    print(res.status_code)
    # Check if empty state is in the page
    text = res.get_data(as_text=True)
    if "No improvement data available yet." in text and len(app.extensions.supabase.table('race_results').select('id').execute().data) > 0:
        print("Data is not rendering properly!")
    else:
        print("Dashboard generated successfully.")
