from flask import jsonify


def json_error(message: str, status: int = 500):
    return jsonify({"error": message}), status
