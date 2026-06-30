from flask import Blueprint

swimmers_bp = Blueprint('swimmers', __name__, url_prefix='/swimmers')

from . import routes
