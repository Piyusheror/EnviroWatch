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
from flask import Flask, send_from_directory, render_template, jsonify, request
from flask_cors import CORS




def create_app():
	# create Flask app with custom template/static folders
	base = os.path.dirname(__file__)
	app = Flask(
		__name__,
		template_folder=os.path.join(base, "template"),
		static_folder=os.path.join(base, "static"),
		static_url_path="/static",
	)
	CORS(app)


	# internal dev ping route
	@app.route("/internal_ping", methods=["GET"])
	def internal_ping():
		# allow only local dev callers
		if request.remote_addr not in ("127.0.0.1", "::1", "localhost"):
			return jsonify({"error": "not allowed"}), 403
		return jsonify({"status": "ok", "note": "dev-only internal_ping"}), 200


	# register blueprints
	from api.predict import predict_bp
	from api.health import health_bp


	app.register_blueprint(predict_bp, url_prefix="/api")
	app.register_blueprint(health_bp, url_prefix="/api")


	@app.route("/", methods=["GET"])
	def index():
		try:
			return render_template("index.html")
		except Exception:
			# fallback to serving the raw file if rendering fails
			return send_from_directory(app.template_folder, "index.html")


	return app




# expose app for `flask run`
app = create_app()


if __name__ == "__main__":
	app.run(debug=True)