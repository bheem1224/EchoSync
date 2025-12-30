from flask import Blueprint, jsonify
from web.services.library_service import LibraryAdapter

bp = Blueprint("library", __name__, url_prefix="/api/library")

@bp.get("/")
def library_overview():
    adapter = LibraryAdapter()
    data = adapter.overview()
    return jsonify(data), 200
