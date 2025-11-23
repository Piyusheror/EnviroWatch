from flask import Blueprint, jsonify


health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@health_bp.route("/ping", methods=["GET"])
def ping():
    return jsonify({"ping": "pong"})