from database.database import get_connection
from flask import render_template, request, redirect, session
import socket

from database.user_manager import UserManager
from database.user_session_manager import UserSessionManager

from helper.datetime_helper import (
    utc_to_ist
)

def register_auth_routes(app):


    @app.route("/login", methods=["GET", "POST"])
    def login():

        if request.method == "POST":

            username = request.form.get("username")
            password = request.form.get("password")

            if UserManager.verify_user(username, password):

                UserManager.update_last_login(
                    username
                )

                user = UserManager.get_user(username)
                last_login_ist = utc_to_ist(user["last_login"])

                client_ip = request.remote_addr
                workstation_name = socket.gethostname()

                session_id = UserSessionManager.login(
                    username=username,
                    client_ip=client_ip,
                    workstation_name=workstation_name
                )

                session["logged_in"] = True
                session["username"] = username
                session["role"] = user["role"]
                session["session_id"] = session_id
                session["last_login_ist"] = last_login_ist

                print("LAST LOGIN IST =", session["last_login_ist"])

                return redirect("/")

            return render_template(
                "auth/login.html",
                error="Invalid Username Or Password"
            )

        return render_template("auth/login.html")

    @app.route("/logout")
    def logout():

        if session.get("session_id"):
            UserSessionManager.logout(session["session_id"])

        session.clear()

        return redirect("/login")
    
    @staticmethod
    def update_last_login(
        username
    ):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users

            SET last_login = CURRENT_TIMESTAMP

            WHERE username = ?
            """,
            (username,)
        )

        conn.commit()

        conn.close()
