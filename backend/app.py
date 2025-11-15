from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    CORS(app)

    # register blueprints
    from api.predict import predict_bp
    from api.health import health_bp

    app.register_blueprint(predict_bp, url_prefix="/api")
    app.register_blueprint(health_bp, url_prefix="/api")

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, send_from_directory, render_template
from flask_cors import CORS
import os

def create_app():
    # serve templates from the template/ folder and static from static/
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "template"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
        static_url_path="/static"
    )
    CORS(app)

    # Register blueprints
    # temporary dev-only health check (bypass any before_request auth)
from flask import jsonify, request

@app.route("/internal_ping", methods=["GET"])
def internal_ping():
    # only allow local dev callers
    if request.remote_addr not in ("127.0.0.1", "localhost"):
        return jsonify({"error":"not allowed"}), 403
    return jsonify({"status":"ok","note":"dev-only internal_ping"}), 200

    from api.predict import predict_bp
    from api.health import health_bp

    app.register_blueprint(predict_bp, url_prefix="/api")
    app.register_blueprint(health_bp, url_prefix="/api")

    # Root route -> serve your index.html from template/index.html
    @app.route("/", methods=["GET"])
    def index():
        # uses the template folder configured above
        try:
            return render_template("index.html")
        except Exception:
            # fallback to send file if render_template can't find it
            return send_from_directory(app.template_folder, "index.html")

    return app

# make the app object available for 'flask run'
app = create_app()
