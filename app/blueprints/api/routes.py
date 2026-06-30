from flask import jsonify, request
from . import api_bp
from app.extensions import supabase
from app.blueprints.swimmers.routes import login_required

@api_bp.route('/analytics/swimmer/<uuid:swimmer_id>/progression')
@login_required
def swimmer_progression(swimmer_id):
    # Fetch from Supabase
    if supabase:
        try:
            # Example query fetching race results joined with events and competitions
            response = supabase.table('race_results')\
                .select('time, events(stroke, distance, competitions(date))')\
                .eq('swimmer_id', str(swimmer_id))\
                .execute()
            
            # Format data for Chart.js
            data = response.data if hasattr(response, 'data') else response.get('data', [])
            return jsonify({"status": "success", "data": data})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    
    # Mock data fallback
    return jsonify({
        "status": "success", 
        "data": [
            {"date": "2023-01-01", "time": "25.50", "event": "50m Free"},
            {"date": "2023-03-15", "time": "25.10", "event": "50m Free"},
            {"date": "2023-06-20", "time": "24.80", "event": "50m Free"}
        ]
    })

@api_bp.route('/analytics/team-performance')
@login_required
def team_performance():
    return jsonify({
        "status": "success",
        "data": {
            "total_medals": 124,
            "average_improvement": "3.5%",
            "top_strokes": ["Freestyle", "Butterfly"]
        }
    })
