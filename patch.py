import textwrap

code = textwrap.dedent('''
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
''')

with open(r'c:\DBMST\swimming-performance-system\app\blueprints\swimmers\routes.py', 'a') as f:
    f.write(code)
