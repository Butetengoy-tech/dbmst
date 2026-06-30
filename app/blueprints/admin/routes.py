from flask import render_template, request, redirect, url_for, flash, session
from . import admin_bp
from app.extensions import supabase
from app.blueprints.swimmers.routes import login_required, role_required

@admin_bp.route('/staff', methods=['GET', 'POST'])
@login_required
@role_required('System Administrator')
def staff():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        if role not in ['HeadCoach', 'AsstCoach']:
            flash("Invalid role selected.", "error")
            return redirect(url_for('admin.staff'))
            
        try:
            if supabase:
                # 1. Sign up the user (Database trigger will auto-create user_profiles as Swimmer)
                response = supabase.auth.sign_up({"email": email, "password": password})
                
                if response.user:
                    # 2. Call the RPC to securely promote them to Staff
                    # Using the hardcoded secret token we put in the SQL
                    supabase.rpc('promote_to_staff', {
                        'target_user_id': response.user.id,
                        'target_role': role,
                        'secret_token': 'WeagonsAdmin123!@#',
                        'target_full_name': full_name,
                        'target_email': email
                    }).execute()
                    
                    flash(f"Successfully created {role} account for {email}", "success")
                else:
                    flash("Failed to create account.", "error")
            else:
                flash("Supabase is not configured.", "error")
        except Exception as e:
            error_msg = str(e)
            if '23503' in error_msg and 'users' in error_msg:
                flash(f"Error: The email '{email}' is already registered. Please use a different email or delete the existing user from your Supabase Dashboard first.", "error")
            else:
                flash(f"Error creating staff: {error_msg}", "error")
            
        return redirect(url_for('admin.staff'))
        
    return render_template('admin/staff.html')
