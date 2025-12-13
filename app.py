from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = "storesense-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///storesense.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


# =========================
# MODELS
# =========================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    store_name = db.Column(db.String(150), nullable=False)


# =========================
# LOGIN MANAGER
# =========================
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# =========================
# ROUTES
# =========================
@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        store_name = request.form.get("store_name")

        if not username or not store_name:
            flash("All fields are required", "danger")
            return redirect(url_for("login"))

        user = User.query.filter_by(username=username).first()

        if not user:
            user = User(username=username, store_name=store_name)
            db.session.add(user)
            db.session.commit()

        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    return f"""
    <h2>Welcome {current_user.username}</h2>
    <p>Store: {current_user.store_name}</p>
    <a href="{url_for('logout')}">Logout</a>
    """


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# =========================
# DB INIT (SAFE)
# =========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
