from flask import jsonify

from database.database import get_connection


def _database_is_ready():
    connection = None

    try:
        connection = get_connection()
        connection.execute("SELECT 1").fetchone()
        return True
    except Exception:
        return False
    finally:
        if connection is not None:
            connection.close()


def register_health_routes(app):
    @app.get("/health/live")
    def health_live():
        response = jsonify({"status": "ok"})
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health/ready")
    def health_ready():
        ready = _database_is_ready()
        response = jsonify({"status": "ready" if ready else "not_ready"})
        response.headers["Cache-Control"] = "no-store"
        return response, 200 if ready else 503
