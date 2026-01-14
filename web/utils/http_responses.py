from flask import jsonify

def json_error(message: str, status: int = 500):
    """
    Return a JSON error response compatible with Flask.
    """
    return jsonify({"error": message}), status
