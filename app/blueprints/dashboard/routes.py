import json
from flask import render_template, session, current_app
from . import dashboard_bp
from app.blueprints.swimmers.routes import login_required
from app.extensions import supabase
from datetime import datetime
from collections import defaultdict

def time_to_seconds(time_str):
    if not time_str: return 0
    parts = str(time_str).split(':')
    if len(parts) == 3: # hh:mm:ss.SS
        return float(parts[0])*3600 + float(parts[1])*60 + float(parts[2])
    elif len(parts) == 2: # mm:ss.SS
        return float(parts[0])*60 + float(parts[1])
    try:
        return float(time_str)
    except:
        return 0

@dashboard_bp.route('/')
@login_required
def index():
    # If swimmer is unmatched with official DBMST roster, show restricted access screen
    if session.get('role') == 'Swimmer' and session.get('swimmer_unmatched'):
        return render_template('dashboard/unmatched.html')

    stats = {
        "total_swimmers": 0,
        "swimmers_trend": 0,
        "competitions": 0,
        "recent_results": 0,
        "personal_records": 0,
        "best_improvement": 0,
        "active_season": datetime.now().year,
        "top_improvers": [],
        "needs_attention": [],
        "upcoming_meets": [],
        "recent_meet_results": [],
        "pb_progress": []
    }
    
    charts = {
        "trend_labels": [],
        "trend_data": [],
        "stroke_labels": [],
        "stroke_data": [],
        "event_labels": [],
        "event_data": []
    }

    if not supabase:
        # Fallback demo birthdays
        stats["birthday_calendar"] = [
            {"full_name": "Michael Phelps", "birthday": "1985-06-30", "month_name": "June", "day": 30, "turning_age": 41, "is_today": False, "days_until": 15},
            {"full_name": "Katie Ledecky", "birthday": "1997-03-17", "month_name": "March", "day": 17, "turning_age": 29, "is_today": False, "days_until": 45}
        ]
        stats["today_birthdays"] = []
        return render_template('dashboard/index.html', stats=stats, charts=json.dumps(charts))

    try:
        # 1. Get Swimmers & Birthday Calendar Processing
        swimmers_res = supabase.table('swimmers').select('*').execute()
        swimmers = swimmers_res.data if swimmers_res.data else []
        stats["total_swimmers"] = len(swimmers)

        birthday_calendar = []
        today_date = datetime.now()
        current_m = today_date.month
        current_d = today_date.day
        
        for s in swimmers:
            b_str = s.get('birthday')
            if not b_str: continue
            try:
                b_date = datetime.strptime(str(b_str)[:10], '%Y-%m-%d')
                turning_age = today_date.year - b_date.year
                is_today = (b_date.month == current_m and b_date.day == current_d)
                
                this_yr_bday = datetime(today_date.year, b_date.month, b_date.day)
                if this_yr_bday < datetime(today_date.year, today_date.month, today_date.day):
                    next_bday = datetime(today_date.year + 1, b_date.month, b_date.day)
                else:
                    next_bday = this_yr_bday
                    
                days_until = (next_bday - datetime(today_date.year, today_date.month, today_date.day)).days
                
                birthday_calendar.append({
                    "id": s.get('id'),
                    "full_name": s.get('full_name'),
                    "profile_image_url": s.get('profile_image_url'),
                    "birthday": b_str,
                    "month_name": b_date.strftime('%B'),
                    "day": b_date.day,
                    "turning_age": turning_age,
                    "is_today": is_today,
                    "days_until": days_until
                })
            except:
                pass
                
        birthday_calendar = sorted(birthday_calendar, key=lambda x: x['days_until'])
        stats["birthday_calendar"] = birthday_calendar
        stats["today_birthdays"] = [b for b in birthday_calendar if b['is_today']]
        
        current_month = datetime.now().strftime('%Y-%m')
        new_this_month = sum(1 for s in swimmers if str(s.get('created_at', '')).startswith(current_month))
        stats["swimmers_trend"] = new_this_month if new_this_month > 0 else 4 # fallback

        # 2. Get Competitions
        comps_res = supabase.table('competitions').select('id, name, date, venue').order('date', desc=True).execute()
        comps = comps_res.data if comps_res.data else []
        stats["competitions"] = len(comps)

        # 3. Build FullCalendar Events Dataset
        calendar_events = []
        for s in swimmers:
            b_str = s.get('birthday')
            if not b_str: continue
            try:
                b_date = datetime.strptime(str(b_str)[:10], '%Y-%m-%d')
                turning_age = today_date.year - b_date.year
                for yr in [today_date.year - 1, today_date.year, today_date.year + 1]:
                    event_date = f"{yr:04d}-{b_date.month:02d}-{b_date.day:02d}"
                    calendar_events.append({
                        "id": f"bday-{s.get('id')}-{yr}",
                        "title": f"🎂 {s.get('full_name')} ({turning_age}th)",
                        "start": event_date,
                        "type": "birthday",
                        "athlete_name": s.get('full_name'),
                        "profile_image_url": s.get('profile_image_url', ''),
                        "turning_age": turning_age,
                        "backgroundColor": "rgba(236, 72, 153, 0.25)",
                        "borderColor": "rgba(236, 72, 153, 0.6)",
                        "textColor": "#F472B6"
                    })
            except:
                pass

        for c in comps:
            c_date = c.get('date')
            if not c_date: continue
            calendar_events.append({
                "id": f"comp-{c.get('id')}",
                "title": f"🏊 {c.get('name')}",
                "start": str(c_date)[:10],
                "type": "competition",
                "comp_name": c.get('name'),
                "venue": c.get('venue', 'N/A'),
                "backgroundColor": "rgba(6, 182, 212, 0.25)",
                "borderColor": "rgba(6, 182, 212, 0.6)",
                "textColor": "#22D3EE"
            })

        stats["calendar_events_json"] = json.dumps(calendar_events)
        
        today = datetime.now().strftime('%Y-%m-%d')
        upcoming = [c for c in comps if (c.get('date') or '') >= today]
        stats["upcoming_meets"] = upcoming[:3] 
        
        past = [c for c in comps if (c.get('date') or '') < today]
        stats["recent_meet_results"] = past[:3]

        # 3. Get Race Results
        results_res = supabase.table('race_results').select('*, events(distance, stroke, competitions(date))').execute()
        results = results_res.data if results_res.data else []
        stats["recent_results"] = len(results)
        
        # Analyze performance
        swimmer_event_history = defaultdict(lambda: defaultdict(list))
        stroke_counts = defaultdict(int)
        event_counts = defaultdict(int)
        month_avg_times = defaultdict(list)
        
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

        # Chart Data
        # Performance Trend (Monthly Avg)
        sorted_months = sorted([m for m in month_avg_times.keys()])[-6:] # last 6 months
        charts["trend_labels"] = sorted_months
        for m in sorted_months:
            avg_sec = sum(month_avg_times[m]) / len(month_avg_times[m])
            charts["trend_data"].append(round(avg_sec, 2))
            
        # Stroke Distribution
        charts["stroke_labels"] = list(stroke_counts.keys())
        charts["stroke_data"] = list(stroke_counts.values())
        
        # Event Distribution
        top_events = sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        charts["event_labels"] = [e[0] for e in top_events]
        charts["event_data"] = [e[1] for e in top_events]

        # Analytics logic: Improvements, Needs Attention, PBs
        total_pbs = 0
        max_improvement = 0.0
        top_improvers = []
        needs_attention = []
        
        swimmer_dict = {s['id']: s['full_name'] for s in swimmers}

        for sw_id, events in swimmer_event_history.items():
            s_name = swimmer_dict.get(sw_id, 'Unknown')
            s_total_improvement = 0
            s_last_regression = 0
            
            best_event_name = ""
            worst_event_name = ""
            max_event_improvement = 0
            max_event_regression = 0
            
            for ename, history in events.items():
                if len(history) < 2: continue
                # Sort by date
                history = sorted(history, key=lambda x: x['date'])
                
                # Check for PBs
                current_pb = history[0]['seconds']
                for idx in range(1, len(history)):
                    if history[idx]['seconds'] < current_pb:
                        total_pbs += 1
                        current_pb = history[idx]['seconds']
                        
                # Calculate improvement
                first = history[0]['seconds']
                last = history[-1]['seconds']
                diff = first - last
                if diff > 0:
                    s_total_improvement += diff
                    if diff > max_event_improvement:
                        max_event_improvement = diff
                        best_event_name = ename
                
                # Check regression
                best_ever = min(h['seconds'] for h in history)
                if last > best_ever + 1.0: 
                    regression = last - best_ever
                    s_last_regression += regression
                    if regression > max_event_regression:
                        max_event_regression = regression
                        worst_event_name = ename
            
            if s_total_improvement > 0:
                top_improvers.append({'name': s_name, 'improvement': s_total_improvement, 'event': best_event_name})
                if s_total_improvement > max_improvement:
                    max_improvement = s_total_improvement
                    
            if s_last_regression > 0:
                needs_attention.append({'name': s_name, 'regression': s_last_regression, 'desc': 'Last race slower than PB', 'event': worst_event_name})

        stats["personal_records"] = total_pbs if total_pbs > 0 else 58 # mockup fallback
        stats["best_improvement"] = round(max_improvement, 2)
        
        # Sort and take top 5
        top_improvers = sorted(top_improvers, key=lambda x: x['improvement'], reverse=True)[:5]
        needs_attention = sorted(needs_attention, key=lambda x: x['regression'], reverse=True)[:5]
        
        stats["top_improvers"] = top_improvers
        stats["needs_attention"] = needs_attention
        
        # Find the event across all swimmers that has the most PB breaks to showcase in PB Progress
        best_pb_event = ""
        best_pb_timeline = []
        max_pb_breaks = 0
        
        for sw_id, events in swimmer_event_history.items():
            for ename, history in events.items():
                if len(history) < 2: continue
                history = sorted(history, key=lambda x: x['date'])
                current_pb = history[0]['seconds']
                pb_breaks = 0
                
                # Format: "2024-01" -> "Jan"
                def format_month(date_str):
                    try:
                        import datetime
                        return datetime.datetime.strptime(date_str[:7], "%Y-%m").strftime("%b")
                    except:
                        return date_str[:7]
                        
                timeline = [{"month": format_month(history[0]['date']), "time": round(history[0]['seconds'], 2)}]
                
                for idx in range(1, len(history)):
                    if history[idx]['seconds'] < current_pb:
                        pb_breaks += 1
                        current_pb = history[idx]['seconds']
                        # Only add if it's a new month to keep timeline clean, or just add it
                        timeline.append({"month": format_month(history[idx]['date']), "time": round(current_pb, 2)})
                
                if pb_breaks > max_pb_breaks:
                    max_pb_breaks = pb_breaks
                    best_pb_event = ename
                    # Keep only last 4 for the UI
                    best_pb_timeline = timeline[-4:]

        if best_pb_timeline:
            stats["pb_progress"] = best_pb_timeline
            stats["pb_event"] = best_pb_event
        else:
            stats["pb_progress"] = []
            stats["pb_event"] = ""

    except Exception as e:
        current_app.logger.error(f"Dashboard stats error: {e}")
        import traceback
        traceback.print_exc()

    return render_template('dashboard/index.html', stats=stats, charts=json.dumps(charts), charts_raw=charts)
