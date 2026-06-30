from flask import render_template, request, redirect, url_for, flash, session, make_response
from . import auth_bp
from app.extensions import supabase

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            from flask import current_app
            
            # SUPER ADMINISTRATOR BYPASS
            admin_user = current_app.config.get('SUPER_ADMIN_USERNAME')
            admin_pass = current_app.config.get('SUPER_ADMIN_PASSWORD')
            
            if admin_user and admin_pass and email == admin_user and password == admin_pass:
                session['user_id'] = 'super-admin-uuid'
                session['role'] = 'System Administrator'
                flash("Logged in as System Administrator!", "success")
                return redirect(url_for('dashboard.index'))

            # Authenticate with Supabase
            if supabase:
                response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                
                # Setup session
                session['user_id'] = response.user.id
                session['access_token'] = response.session.access_token
                
                # Fetch role
                profile = supabase.table('user_profiles').select('role').eq('id', response.user.id).execute()
                if profile.data:
                    session['role'] = profile.data[0]['role']
                
                return redirect(url_for('dashboard.index'))
            else:
                flash("Supabase is not configured.", "error")
        except Exception as e:
            flash(str(e), "error")
            
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'Swimmer')
        full_name = request.form.get('full_name')
        
        try:
            if supabase:
                response = supabase.auth.sign_up({"email": email, "password": password})
                
                flash("Registration successful. Please login.", "success")
                return redirect(url_for('auth.login'))
            else:
                flash("Supabase is not configured.", "error")
        except Exception as e:
            flash(str(e), "error")
            
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    if supabase:
        supabase.auth.sign_out()
    return redirect(url_for('auth.login'))
