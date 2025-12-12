# app.py (minimal stable StoreSenseAI)
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = "replace_this_with_a_real_secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///storesense_minimal.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    # simple profile fields
    store_name = db.Column(db.String(200), nullable=True)
    region = db.Column(db.String(100), nullable=True)
    # relationship
    items = db.relationship("Item", backref="user", lazy=True)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)
    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    price = db.Column(db.Float, nullable=False, default=0.0)
    avg_daily_sales = db.Column(db.Float, nullable=False, default=1.0)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        store_name = (request.form.get("store_name") or "").strip()
        region = (request.form.get("region") or "").strip()
        if not username or not password:
            flash("Username and password required.", "danger")
            return redirect(url_for("register"))
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "warning")
            return redirect(url_for("register"))
        user = User(username=username, store_name=store_name, region=region)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        # add a couple starter items so dashboard isn't empty
        starter = [
            Item(name="Sample Item 1", stock=10, price=100.0, avg_daily_sales=1.0, user_id=user.id),
            Item(name="Sample Item 2", stock=5, price=50.0, avg_daily_sales=0.5, user_id=user.id)
        ]
        db.session.add_all(starter)
        db.session.commit()
        flash("Account created — please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash("Invalid username or password.", "danger")
            return redirect(url_for("login"))
        login_user(user)
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    q = (request.args.get("search") or "").strip()
    if q:
        items = Item.query.filter(Item.user_id==current_user.id, Item.name.ilike(f"%{q}%")).all()
    else:
        items = Item.query.filter_by(user_id=current_user.id).all()
    # compute days_to_sell_out safe
    for it in items:
        it.days_to_sell_out = round(it.stock / it.avg_daily_sales, 2) if it.avg_daily_sales and it.avg_daily_sales>0 else "∞"
        it.low_stock = it.stock < 5
    total_value = sum(it.price * it.stock for it in items)
    return render_template("dashboard.html", items=items, store_name=current_user.store_name, total_value=total_value, q=q)

@app.route("/add_item", methods=["GET","POST"])
@login_required
def add_item():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        stock = int(request.form.get("stock") or 0)
        price = float(request.form.get("price") or 0.0)
        avg = float(request.form.get("avg_daily_sales") or 1.0)
        item = Item(name=name, stock=stock, price=price, avg_daily_sales=avg, user_id=current_user.id)
        db.session.add(item)
        db.session.commit()
        flash("Item added.", "success")
        return redirect(url_for("dashboard"))
    return render_template("add_item.html")

@app.route("/edit_item/<int:item_id>", methods=["GET","POST"])
@login_required
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        item.name = (request.form.get("name") or "").strip()
        item.stock = int(request.form.get("stock") or 0)
        item.price = float(request.form.get("price") or 0.0)
        item.avg_daily_sales = float(request.form.get("avg_daily_sales") or 1.0)
        db.session.commit()
        flash("Saved.", "success")
        return redirect(url_for("dashboard"))
    return render_template("edit_item.html", item=item)

@app.route("/delete_item/<int:item_id>", methods=["POST"])
@login_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for("dashboard"))
    db.session.delete(item)
    db.session.commit()
    flash("Deleted.", "info")
    return redirect(url_for("dashboard"))

# create DB inside app context and run
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
