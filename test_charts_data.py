from app import create_app
import json

app = create_app()

with app.app_context():
    # Let's see what routes.py does
    from app.extensions import supabase
    from collections import defaultdict
    import datetime

    # Let's mock what the dashboard route does
    results_res = supabase.table('race_results').select('*, events(*, competitions(*))').execute()
    results = results_res.data
    
    # We want to see if there's any data
    print(f"Total race results: {len(results)}")
    
    # Check if there is data for trend_labels
    month_avg_times = defaultdict(list)
    stroke_counts = defaultdict(int)
    event_counts = defaultdict(int)
    swimmer_event_history = defaultdict(lambda: defaultdict(list))
    
    def time_to_seconds(time_str):
        if not time_str: return 0
        parts = str(time_str).split(':')
        if len(parts) == 3: return float(parts[0])*3600 + float(parts[1])*60 + float(parts[2])
        elif len(parts) == 2: return float(parts[0])*60 + float(parts[1])
        try: return float(time_str)
        except: return 0

    for r in results:
        sw_id = r.get('swimmer_id')
        ev = r.get('events')
        comp = ev.get('competitions') if ev else None
        if not sw_id or not ev or not comp: continue
        
        cdate = comp.get('date', '')
        stroke = ev.get('stroke', 'Unknown')
        distance = ev.get('distance', 0)
        ename = f"{distance}m {stroke}"
        sec = time_to_seconds(r.get('time'))
        
        if sec > 0:
            swimmer_event_history[sw_id][ename].append({'date': cdate, 'seconds': sec})
            month = cdate[:7] if cdate else 'Unknown'
            if month != 'Unknown':
                month_avg_times[month].append(sec)
            
        stroke_counts[stroke] += 1
        event_counts[ename] += 1
        
    print(f"month_avg_times: {month_avg_times}")
    
    charts = {
        "trend_labels": [],
        "trend_data": [],
        "stroke_labels": [],
        "stroke_data": [],
        "event_labels": [],
        "event_data": []
    }
    
    sorted_months = sorted([m for m in month_avg_times.keys()])[-6:]
    charts["trend_labels"] = sorted_months
    for m in sorted_months:
        avg = sum(month_avg_times[m]) / len(month_avg_times[m])
        charts["trend_data"].append(round(avg, 2))
        
    for k, v in stroke_counts.items():
        charts["stroke_labels"].append(k)
        charts["stroke_data"].append(v)
        
    for k, v in event_counts.items():
        charts["event_labels"].append(k)
        charts["event_data"].append(v)
        
    print(f"Charts Output: {json.dumps(charts)}")
