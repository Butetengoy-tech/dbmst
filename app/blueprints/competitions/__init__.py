from flask import Blueprint

competitions_bp = Blueprint('competitions', __name__, url_prefix='/competitions')

from . import routes
