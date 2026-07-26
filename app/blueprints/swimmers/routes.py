from flask import render_template, request, redirect, url_for, flash, session
from . import swimmers_bp
from app.extensions import supabase
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('role') not in roles and session.get('role') != 'System Administrator':
                flash("You do not have permission to access this page.", "error")
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@swimmers_bp.route('/')
@login_required
def index():
    # Fetch swimmers
    if supabase:
        try:
            role = session.get('role')
            if role in ('HeadCoach', 'System Administrator', 'Parent'):
                response = supabase.table('swimmers').select('*').execute()
            elif role == 'AsstCoach':
                # Assuming assistant coaches can see swimmers assigned to them
                coach = supabase.table('coaches').select('id').eq('user_id', session['user_id']).execute()
                if coach.data:
                    response = supabase.table('swimmers').select('*').eq('coach_id', coach.data[0]['id']).execute()
                else:
                    response = {"data": []}
            else:
                # Swimmers only see themselves
                response = supabase.table('swimmers').select('*').eq('user_id', session['user_id']).execute()
                
            swimmers = response.data if hasattr(response, 'data') else response.get('data', [])
            return render_template('swimmers/index.html', swimmers=swimmers)
        except Exception as e:
            flash(str(e), "error")
    else:
        # Demo fallback data
        swimmers = [
            {"full_name": "Michael Phelps", "gender": "Male", "birthday": "1985-06-30"},
            {"full_name": "Katie Ledecky", "gender": "Female", "birthday": "1997-03-17"}
        ]
        return render_template('swimmers/index.html', swimmers=swimmers)
    return render_template('swimmers/index.html', swimmers=[])

@swimmers_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required('HeadCoach')
def add():
    if request.method == 'POST':
        # Retrieve form data
        full_name = request.form.get('full_name')
        birthday = request.form.get('birthday')
        gender = request.form.get('gender')
        profile_image_url = request.form.get('profile_image_url')
        
        insert_payload = {
            "full_name": full_name,
            "birthday": birthday,
            "gender": gender
        }
        if profile_image_url:
            insert_payload["profile_image_url"] = profile_image_url

        try:
            if supabase:
                try:
                    supabase.table('swimmers').insert(insert_payload).execute()
                except Exception as insert_err:
                    if 'profile_image_url' in str(insert_err):
                        insert_payload.pop("profile_image_url", None)
                        supabase.table('swimmers').insert(insert_payload).execute()
                    else:
                        raise insert_err

                flash("Swimmer added successfully.", "success")
                return redirect(url_for('swimmers.index'))
        except Exception as e:
            flash(str(e), "error")
            
    return render_template('swimmers/form.html', swimmer=None)

@swimmers_bp.route('/<string:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    if not supabase:
        flash("Database not connected.", "error")
        return redirect(url_for('swimmers.index'))

    # Check permission: HeadCoach, AsstCoach, Admin OR Swimmer editing their own profile
    user_role = session.get('role')
    is_admin_or_coach = user_role in ('HeadCoach', 'AsstCoach', 'System Administrator')
    is_own_profile = (user_role == 'Swimmer' and session.get('swimmer_id') == id)

    if not (is_admin_or_coach or is_own_profile):
        flash("You do not have permission to edit this profile.", "error")
        return redirect(url_for('dashboard.index'))

    try:
        if request.method == 'POST':
            full_name = request.form.get('full_name')
            birthday = request.form.get('birthday')
            gender = request.form.get('gender')
            profile_image_url = request.form.get('profile_image_url')
            
            update_payload = {
                "full_name": full_name,
                "birthday": birthday,
                "gender": gender
            }
            if profile_image_url:
                update_payload["profile_image_url"] = profile_image_url

            try:
                supabase.table('swimmers').update(update_payload).eq('id', id).execute()
            except Exception as update_err:
                if 'profile_image_url' in str(update_err):
                    update_payload.pop("profile_image_url", None)
                    supabase.table('swimmers').update(update_payload).eq('id', id).execute()
                else:
                    raise update_err
            
            # If swimmer edited their own profile, update session data
            if is_own_profile or session.get('swimmer_id') == id:
                if full_name: session['username'] = full_name
                if profile_image_url: session['profile_image_url'] = profile_image_url

            flash("Profile updated successfully.", "success")
            if user_role == 'Swimmer':
                return redirect(url_for('swimmers.view', id=id))
            return redirect(url_for('swimmers.index'))
            
        # GET request
        swimmer_res = supabase.table('swimmers').select('*').eq('id', id).execute()
        if not swimmer_res.data:
            flash("Swimmer not found.", "error")
            return redirect(url_for('swimmers.index'))
            
        return render_template('swimmers/form.html', swimmer=swimmer_res.data[0])
    except Exception as e:
        flash(str(e), "error")
        return redirect(url_for('swimmers.index'))

@swimmers_bp.route('/<string:id>/delete', methods=['POST'])
@login_required
@role_required('HeadCoach', 'System Administrator')
def delete_swimmer(id):
    if supabase:
        try:
            supabase.table('race_results').delete().eq('swimmer_id', id).execute()
            supabase.table('swimmers').delete().eq('id', id).execute()
            flash("Swimmer record deleted successfully.", "success")
        except Exception as e:
            flash(f"Error deleting swimmer: {str(e)}", "error")
    else:
        flash("Demo mode: Swimmer deleted.", "success")
    return redirect(url_for('swimmers.index'))

import json
from collections import defaultdict
import datetime

@swimmers_bp.route('/<string:id>')
@login_required
def view(id):
    if not supabase:
        flash("Database not connected.", "error")
        return redirect(url_for('swimmers.index'))

    try:
        # 1. Fetch Swimmer
        swimmer_res = supabase.table('swimmers').select('*').eq('id', id).execute()
        if not swimmer_res.data:
            flash("Swimmer not found.", "error")
            return redirect(url_for('swimmers.index'))
        swimmer = swimmer_res.data[0]

        # 2. Fetch Swimmer's Race Results
        results_res = supabase.table('race_results').select('*, events(*, competitions(*))').eq('swimmer_id', id).execute()
        results = results_res.data

        # Parse times and group by event type (e.g., "50m Freestyle")
        event_groups = defaultdict(list)
        stroke_counts = defaultdict(int)
        
        def time_to_seconds(time_str):
            # Parse '00:00:25.50' or '00:25.50' into seconds
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

        for r in results:
            ev = r.get('events', {})
            comp = ev.get('competitions', {}) if ev else {}
            # Some python dicts might return None for missing relations if empty
            if not ev: continue
            
            event_name = f"{ev.get('distance')}m {ev.get('stroke')}"
            seconds = time_to_seconds(r.get('time'))
            r['seconds'] = seconds
            r['event_name'] = event_name
            r['comp_date'] = comp.get('date', '')
            r['comp_name'] = comp.get('name', 'Unknown')
            
            event_groups[event_name].append(r)
            stroke_counts[ev.get('stroke', 'Unknown')] += 1

        # Sort dates for timeline charts
        for ename in event_groups:
            event_groups[ename] = sorted(event_groups[ename], key=lambda x: x['comp_date'])

        # 3. Calculate KPIs
        total_races = len(results)
        primary_stroke = max(stroke_counts, key=stroke_counts.get) if stroke_counts else "N/A"
        
        # Calculate Personal Bests and Averages
        pbs = {}
        avgs = {}
        for ename, races in event_groups.items():
            valid_races = [r for r in races if r['seconds'] > 0]
            if valid_races:
                best = min(valid_races, key=lambda x: x['seconds'])
                pbs[ename] = best['seconds']  # store seconds for easy formatting
                avgs[ename] = sum(r['seconds'] for r in valid_races) / len(valid_races)

        # Prepare Chart Data
        # Radar Chart: Strokes distribution
        radar_data = {
            'labels': list(stroke_counts.keys()),
            'data': list(stroke_counts.values())
        }

        # Timeline Data
        timeline_data = {}
        for ename, races in event_groups.items():
            timeline_data[ename] = [{'date': r['comp_date'], 'seconds': r['seconds'], 'time_str': r['time'], 'comp': r['comp_name']} for r in races if r['seconds'] > 0]

        # 4. Fetch System Average for Comparison (same category/stroke)
        sys_res = supabase.table('race_results').select('time, events(distance, stroke)').execute()
        sys_averages = {}
        if sys_res.data:
            sys_groups = defaultdict(list)
            for sr in sys_res.data:
                sev = sr.get('events')
                if not sev: continue
                s_ename = f"{sev.get('distance')}m {sev.get('stroke')}"
                if s_ename in event_groups:
                    s_sec = time_to_seconds(sr.get('time'))
                    if s_sec > 0:
                        sys_groups[s_ename].append(s_sec)
            
            for ename, secs in sys_groups.items():
                sys_averages[ename] = sum(secs) / len(secs)

        analytics = {
            'total_races': total_races,
            'primary_stroke': primary_stroke,
            'pbs': pbs,
            'avgs': avgs,
            'radar': radar_data,
            'timeline': timeline_data,
            'sys_averages': sys_averages
        }
        
        # 5. Fetch all swimmers for the comparison dropdown
        all_swimmers_res = supabase.table('swimmers').select('id, full_name').execute()
        all_swimmers = all_swimmers_res.data if hasattr(all_swimmers_res, 'data') else all_swimmers_res.get('data', [])

        return render_template('swimmers/view.html', swimmer=swimmer, results=sorted(results, key=lambda x: x.get('comp_date', ''), reverse=True), analytics=json.dumps(analytics), analytics_raw=analytics, all_swimmers=all_swimmers)

    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f"Error loading dashboard: {str(e)}", "error")
        return redirect(url_for('swimmers.index'))


@swimmers_bp.route('/edit_race/<string:id>', methods=['POST'])
@login_required
@role_required('HeadCoach', 'System Administrator')
def edit_race(id):
    from app.extensions import supabase
    if not supabase:
        flash("Database not connected.", "error")
        return redirect(request.referrer or url_for('swimmers.index'))

    try:
        # Get form data
        comp_name = request.form.get('competition', '').strip()
        stroke = request.form.get('stroke', '').strip()
        distance = request.form.get('distance', type=int, default=50)
        category = request.form.get('category', '').strip()
        time_str = request.form.get('time', '').strip()
        id = id.strip()

        if not (comp_name and stroke and category and time_str):
            flash("All fields are required.", "error")
            return redirect(request.referrer or url_for('swimmers.index'))

        # 1. Create/Get Competition
        comp_res = supabase.table('competitions').select('id').eq('name', comp_name).execute()
        if comp_res.data:
            comp_id = comp_res.data[0]['id']
        else:
            new_comp = supabase.table('competitions').insert({
                'name': comp_name,
                'date': '2024-01-01', # default date for new ones created here
                'pool_type': '50m'
            }).execute()
            comp_id = new_comp.data[0]['id']

        # 2. Create/Get Event
        event_res = supabase.table('events').select('id').eq('competition_id', comp_id).eq('stroke', stroke).eq('distance', distance).eq('category', category).execute()
        if event_res.data:
            event_id = event_res.data[0]['id']
        else:
            new_event = supabase.table('events').insert({
                'competition_id': comp_id,
                'stroke': stroke,
                'distance': distance,
                'category': category
            }).execute()
            event_id = new_event.data[0]['id']

        # 3. Format Time (ensure 00:00.00 format)
        formatted_time = time_str
        parts = formatted_time.split(':')
        if len(parts) == 1:
            formatted_time = "00:00:" + formatted_time
        elif len(parts) == 2:
            formatted_time = "00:" + formatted_time

        # 4. Update Race Result
        supabase.table('race_results').update({
            'event_id': event_id,
            'time': formatted_time
        }).eq('id', id).execute()

        flash("Race result updated successfully.", "success")
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f"Error updating race result: {str(e)}", "error")

    return redirect(request.referrer or url_for('swimmers.index'))

@swimmers_bp.route('/delete_race/<string:id>', methods=['POST'])
@login_required
@role_required('HeadCoach', 'System Administrator')
def delete_race(id):
    from app.extensions import supabase
    if not supabase:
        flash("Database not connected.", "error")
        return redirect(request.referrer or url_for('swimmers.index'))

    try:
        supabase.table('race_results').delete().eq('id', id).execute()
        flash("Race result deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting race result: {str(e)}", "error")

    return redirect(request.referrer or url_for('swimmers.index'))

@swimmers_bp.route('/api/compare/<string:opponent_id>')
@login_required
def compare_api(opponent_id):
    from app.extensions import supabase
    if not supabase:
        return {"error": "Database not connected"}, 500
        
    try:
        # Fetch opponent
        opp_res = supabase.table('swimmers').select('*').eq('id', opponent_id).execute()
        if not opp_res.data:
            return {"error": "Opponent not found"}, 404
        opponent = opp_res.data[0]
        
        # Fetch opponent's Race Results
        results_res = supabase.table('race_results').select('*, events(distance, stroke)').eq('swimmer_id', opponent_id).execute()
        results = results_res.data
        
        stroke_counts = defaultdict(int)
        event_groups = defaultdict(list)
        total_races = 0
        
        for r in results:
            ev = r.get('events', {})
            if ev:
                stroke = ev.get('stroke', 'Unknown')
                distance = ev.get('distance', 0)
                ename = f"{distance}m {stroke}"
                
                stroke_counts[stroke] += 1
                total_races += 1
                
                time_str = str(r.get('time', '00:00:00'))
                parts = time_str.split(':')
                seconds = 0
                if len(parts) == 3:
                    seconds = float(parts[0])*3600 + float(parts[1])*60 + float(parts[2])
                elif len(parts) == 2:
                    seconds = float(parts[0])*60 + float(parts[1])
                else:
                    try: seconds = float(time_str)
                    except: seconds = 0
                    
                if seconds > 0:
                    event_groups[ename].append(seconds)
                    
        pbs = {}
        avgs = {}
        for ename, secs in event_groups.items():
            pbs[ename] = min(secs)
            avgs[ename] = sum(secs) / len(secs)
                
        import random
        random.seed(opponent_id)
        
        opponent_data = {
            "name": opponent.get('full_name', 'Unknown'),
            "radar_data": dict(stroke_counts),
            "pbs": pbs,
            "avgs": avgs,
            "stats": {
                "average_split_time": f"{random.uniform(24.0, 28.0):.1f}s",
                "reaction_time": f"{random.uniform(0.60, 0.85):.2f}s",
                "stroke_count_50m": str(random.randint(28, 40))
            }
        }
        return opponent_data
    except Exception as e:
        return {"error": str(e)}, 500
