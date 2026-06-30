from flask import render_template, request, redirect, url_for, flash
from . import competitions_bp
from app.extensions import supabase
from app.blueprints.swimmers.routes import login_required, role_required

@competitions_bp.route('/')
@login_required
def index():
    if supabase:
        try:
            response = supabase.table('competitions').select('*').execute()
            competitions = response.data if hasattr(response, 'data') else response.get('data', [])
            return render_template('competitions/index.html', competitions=competitions)
        except Exception as e:
            flash(str(e), "error")
    else:
        # Demo fallback data
        competitions = [
            {"name": "National Championships", "venue": "Aquatic Center", "date": "2024-08-15", "pool_type": "50m"},
            {"name": "Winter Regionals", "venue": "City Pool", "date": "2024-12-05", "pool_type": "25m"}
        ]
        return render_template('competitions/index.html', competitions=competitions)
    return render_template('competitions/index.html', competitions=[])

@competitions_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required('HeadCoach', 'AsstCoach')
def add():
    if request.method == 'POST':
        name = request.form.get('name')
        organizer = request.form.get('organizer')
        venue = request.form.get('venue')
        date = request.form.get('date')
        pool_type = request.form.get('pool_type')
        
        try:
            if supabase:
                supabase.table('competitions').insert({
                    "name": name,
                    "organizer": organizer,
                    "venue": venue,
                    "date": date,
                    "pool_type": pool_type
                }).execute()
                flash("Competition added successfully.", "success")
                return redirect(url_for('competitions.index'))
        except Exception as e:
            flash(str(e), "error")
            
    return render_template('competitions/form.html', comp=None)

from flask import send_file
import pandas as pd
import io
from datetime import datetime

@competitions_bp.route('/template')
@login_required
@role_required('HeadCoach', 'AsstCoach')
def download_template():
    df = pd.DataFrame(columns=[
        'Competition', 'Name', 'Middle Name', 'Last Name', 'Event', 'Category', 'Stroke', 'Time', 'Date'
    ])
    # Add a sample row
    df.loc[0] = ['National Championships', 'Xhierywn Helian', 'F', 'Cuizon', 'Event 3', 'Boys 6-12', '400 LC Meter Freestyle', '06:54.7', '2024-08-15']
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Template')
    output.seek(0)
    
    return send_file(output, download_name='race_results_template.xlsx', as_attachment=True)


@competitions_bp.route('/upload', methods=['POST'])
@login_required
@role_required('HeadCoach', 'AsstCoach')
def upload_excel():
    if 'file' not in request.files:
        flash("No file uploaded", "error")
        return redirect(url_for('competitions.index'))
        
    file = request.files['file']
    if not file.filename.endswith(('.xls', '.xlsx')):
        flash("Invalid file format", "error")
        return redirect(url_for('competitions.index'))
        
    try:
        df = pd.read_excel(file)
        success_count = 0
        
        if not supabase:
            flash("Supabase not connected. Upload simulated.", "success")
            return redirect(url_for('competitions.index'))
            
        import re
        import difflib
        
        # Pre-fetch all swimmers for efficient fuzzy matching to handle typos in Excel
        all_swimmers = []
        try:
            swimmer_data_res = supabase.table('swimmers').select('id, full_name').execute()
            all_swimmers = swimmer_data_res.data if swimmer_data_res.data else []
        except:
            pass

        for index, row in df.iterrows():
            comp_name = str(row.get('Competition', '')).strip()
            first_name = str(row.get('Name', '')).strip()
            middle_name = str(row.get('Middle Name', '')).strip()
            last_name = str(row.get('Last Name', '')).strip()
            
            if first_name.lower() == 'nan': first_name = ''
            if middle_name.lower() == 'nan': middle_name = ''
            if last_name.lower() == 'nan': last_name = ''
            
            name_parts = [first_name, middle_name, last_name]
            swimmer_name = " ".join([p for p in name_parts if p])
            
            category_val = str(row.get('Category', '')).strip()
            stroke_val = str(row.get('Stroke', '')).strip()
            time_str = str(row.get('Time', '')).strip()
            date_val = row.get('Date')
            
            if not (comp_name and swimmer_name and time_str and time_str != 'nan'):
                continue
                
            # 1. Parse Distance and Stroke from 'Stroke' column
            distance = 50
            dist_match = re.search(r'\d+', stroke_val)
            if dist_match:
                distance = int(dist_match.group(0))
                
            stroke_clean = stroke_val
            if dist_match:
                stroke_clean = stroke_clean.replace(dist_match.group(0), '', 1)
            # Remove common pool types like "LC Meter" using word boundaries to preserve strokes like "IM"
            stroke_clean = re.sub(r'\b(LC Meter|SC Meter|Meter|LC|SC|m)\b', '', stroke_clean, flags=re.IGNORECASE).strip()
            stroke = stroke_clean if stroke_clean and stroke_clean.lower() != 'nan' else 'Freestyle'

            # 2. Extract Category
            # The Excel template uses 'Category' for Age Groups (e.g., 'Boys 6-12').
            # The database expects 'Individual' or 'Relay'. Map it accordingly.
            category = 'Relay' if 'relay' in stroke.lower() else 'Individual'
                
            # 3. Format Date
            comp_date = '2024-01-01'
            if pd.notna(date_val):
                try:
                    comp_date = pd.to_datetime(date_val).strftime('%Y-%m-%d')
                except:
                    pass

            # 4. Create/Get Competition
            comp_res = supabase.table('competitions').select('id, date').eq('name', comp_name).execute()
            if comp_res.data:
                comp_id = comp_res.data[0]['id']
                if pd.isna(date_val) or not str(date_val).strip() or str(date_val).lower() == 'nan':
                    comp_date = comp_res.data[0].get('date', comp_date)
            else:
                new_comp = supabase.table('competitions').insert({
                    'name': comp_name,
                    'date': comp_date,
                    'pool_type': '50m'
                }).execute()
                comp_id = new_comp.data[0]['id']

            # 5. Create/Get Event
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

            # 6. Get or Create Swimmer
            swimmer_id = None
            best_match_ratio = 0
            
            # Fuzzy match against all swimmers to catch slight typos (e.g., 'Xhierywn' vs 'Xheirwyn')
            if all_swimmers and swimmer_name:
                for s in all_swimmers:
                    ratio = difflib.SequenceMatcher(None, swimmer_name.lower(), s['full_name'].lower()).ratio()
                    if ratio > best_match_ratio:
                        best_match_ratio = ratio
                        swimmer_id = s['id']
            
            # If no match > 0.85 (85% similar), create a new swimmer
            if best_match_ratio < 0.85:
                new_swimmer = supabase.table('swimmers').insert({
                    'full_name': swimmer_name,
                    'birthday': '2000-01-01',
                    'gender': 'Unknown'
                }).execute()
                swimmer_id = new_swimmer.data[0]['id']
                all_swimmers.append({'id': swimmer_id, 'full_name': swimmer_name})
            
            # 7. Insert or Update Race Result
            try:
                formatted_time = time_str.replace(',', '.')
                colons = formatted_time.count(':')
                if colons == 0:
                    formatted_time = f"00:00:{formatted_time}"
                elif colons == 1:
                    formatted_time = f"00:{formatted_time}"
                    
                # Check if this exact event/swimmer combination already exists to prevent duplicates
                existing_res = supabase.table('race_results').select('id').eq('event_id', event_id).eq('swimmer_id', swimmer_id).execute()
                
                if existing_res.data:
                    # Update to avoid duplicating entries if user uploads the same file twice
                    supabase.table('race_results').update({
                        'time': formatted_time
                    }).eq('id', existing_res.data[0]['id']).execute()
                else:
                    supabase.table('race_results').insert({
                        'event_id': event_id,
                        'swimmer_id': swimmer_id,
                        'time': formatted_time
                    }).execute()
                
                success_count += 1
            except Exception as row_error:
                print(f"Skipping row for {swimmer_name} due to error: {str(row_error)}")
                continue
            
        flash(f"Successfully imported {success_count} race results.", "success")
    except Exception as e:
        flash(f"Error processing file: {str(e)}", "error")
        
    return redirect(url_for('competitions.index'))

@competitions_bp.route('/manual', methods=['POST'])
@login_required
@role_required('HeadCoach', 'AsstCoach')
def manual_entry():
    if not supabase:
        flash("Supabase not connected. Manual entry simulated.", "success")
        return redirect(url_for('competitions.index'))
        
    swimmer_name = request.form.get('swimmer_name')
    comp_name = request.form.get('comp_name')
    distance = request.form.get('distance', type=int)
    stroke = request.form.get('stroke')
    time_val = request.form.get('time')
    
    try:
        # Find Swimmer
        swimmer_res = supabase.table('swimmers').select('id').ilike('full_name', f"%{swimmer_name}%").execute()
        if not swimmer_res.data:
            flash("Swimmer not found", "error")
            return redirect(url_for('competitions.index'))
        swimmer_id = swimmer_res.data[0]['id']
        
        # Find Competition
        comp_res = supabase.table('competitions').select('id').eq('name', comp_name).execute()
        if not comp_res.data:
            new_comp = supabase.table('competitions').insert({
                'name': comp_name,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'pool_type': '50m'
            }).execute()
            comp_id = new_comp.data[0]['id']
        else:
            comp_id = comp_res.data[0]['id']
            
        # Find Event
        event_res = supabase.table('events').select('id').eq('competition_id', comp_id).eq('stroke', stroke).eq('distance', distance).eq('category', 'Individual').execute()
        if not event_res.data:
            new_event = supabase.table('events').insert({
                'competition_id': comp_id,
                'stroke': stroke,
                'distance': distance,
                'category': 'Individual'
            }).execute()
            event_id = new_event.data[0]['id']
        else:
            event_id = event_res.data[0]['id']
            
        # Format Time
        formatted_time = str(time_val).replace(',', '.')
        colons = formatted_time.count(':')
        if colons == 0:
            formatted_time = f"00:00:{formatted_time}"
        elif colons == 1:
            formatted_time = f"00:{formatted_time}"
            
        supabase.table('race_results').insert({
            'event_id': event_id,
            'swimmer_id': swimmer_id,
            'time': formatted_time
        }).execute()
        
        flash("Race result added manually.", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
        
    return redirect(url_for('competitions.index'))
