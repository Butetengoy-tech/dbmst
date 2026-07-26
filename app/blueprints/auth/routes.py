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
                
                # Check swimmer roster matching if user has Swimmer role
                role = session.get('role', 'Swimmer')
                if role == 'Swimmer':
                    swimmer = supabase.table('swimmers').select('*').or_(f"user_id.eq.{response.user.id},email.eq.{email}").execute()
                    if swimmer.data:
                        swimmer_info = swimmer.data[0]
                        session['swimmer_id'] = swimmer_info['id']
                        session['swimmer_unmatched'] = False
                        if swimmer_info.get('profile_image_url'):
                            session['profile_image_url'] = swimmer_info['profile_image_url']
                        if swimmer_info.get('full_name'):
                            session['username'] = swimmer_info['full_name']
                        # Link user_id if missing
                        if not swimmer_info.get('user_id'):
                            supabase.table('swimmers').update({"user_id": response.user.id}).eq('id', swimmer_info['id']).execute()
                    else:
                        session['swimmer_unmatched'] = True
                        flash("Account not matched with an official DBMST Swimmer profile. Please contact Coach Amil.", "warning")
                else:
                    session['swimmer_unmatched'] = False
                
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
                
                # Insert profile record with role
                if hasattr(response, 'user') and response.user:
                    supabase.table('user_profiles').insert({
                        "id": response.user.id,
                        "email": email,
                        "full_name": full_name,
                        "role": role
                    }).execute()

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
    return redirect(url_for('main.index'))
