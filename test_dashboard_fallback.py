from app import create_app

app = create_app()

with app.test_client() as client:
    # Need to fake session
    with client.session_transaction() as sess:
        sess['user_id'] = '123'
        sess['role'] = 'HeadCoach'
    
    response = client.get('/dashboard/')
    html = response.data.decode('utf-8')
    
    # Let's extract the JS part for the charts
    js_start = html.find('const chartData = ')
    if js_start != -1:
        js_end = html.find(';', js_start)
        print("chartData output:")
        print(html[js_start:js_end+1])
    
    if "No performance trend data available yet." in html:
        print("Fallback text IS in the HTML.")
    else:
        print("Fallback text is MISSING from the HTML.")
