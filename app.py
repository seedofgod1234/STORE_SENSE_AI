from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# -----------------------------
# App Configuration
# -----------------------------
app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    "sqlite:///storesense.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

# -----------------------------
# Models
# -----------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("Item", backref="owner", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    daily_sales = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    @property
    def days_to_sell_out(self):
        if self.daily_sales <= 0:
            return None
        return self.stock // self.daily_sales

    @property
    def low_stock(self):
        return self.stock <= self.daily_sales * 3


# -----------------------------
# Login Manager
# -----------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        store_name = request.form["store_name"]
        email = request.form["email"]
        password = request.form["password"]

        if User.query.filter_by(email=email).first():
            flash("Email already registered", "danger")
            return redirect(url_for("register"))

        user = User(store_name=store_name, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password", "danger")
            return redirect(url_for("login"))

        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    search = request.args.get("q", "")

    if search:
        items = Item.query.filter(
            Item.user_id == current_user.id,
            Item.name.ilike(f"%{search}%")
        ).all()
    else:
        items = Item.query.filter_by(user_id=current_user.id).all()

    return render_template("dashboard.html", items=items, search=search)


@app.route("/add-item", methods=["GET", "POST"])
@login_required
def add_item():
    if request.method == "POST":
        name = request.form["name"]
        stock = int(request.form["stock"])
        daily_sales = int(request.form["daily_sales"])

        item = Item(
            name=name,
            stock=stock,
            daily_sales=daily_sales,
            owner=current_user
        )

        db.session.add(item)
        db.session.commit()

        return redirect(url_for("dashboard"))

    return render_template("add_item.html")


@app.route("/delete-item/<int:item_id>")
@login_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)

    if item.user_id != current_user.id:
        return redirect(url_for("dashboard"))

    db.session.delete(item)
    db.session.commit()
    return redirect(url_for("dashboard"))


# -----------------------------
# Database Init (SAFE FOR FLASK 3)
# -----------------------------
with app.app_context():
    db.create_all()


# -----------------------------
# Local Run
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
