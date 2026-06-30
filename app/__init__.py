from flask import Flask
from app.config import Config
from app.extensions import init_supabase

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    init_supabase(app)

    # Register blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.swimmers import swimmers_bp
    from app.blueprints.main import main_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(swimmers_bp)
    app.register_blueprint(main_bp)
    from app.blueprints.competitions import competitions_bp
    from app.blueprints.admin import admin_bp
    
    app.register_blueprint(competitions_bp)
    app.register_blueprint(admin_bp)

    @app.route('/health')
    def health_check():
        return {'status': 'ok'}

    return app
