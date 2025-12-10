from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = "vealsarafel!storesenseAI$2025#fullpowerkey1234567890"

# --------------------
# In-memory stores
# --------------------
# users: email -> {id, name, password_hash, store_type}
users = {}

# master_store_types: list of store type strings (editable by users adding custom)
master_store_types = [
    "Supermarket","Grocery Store","Bakery","Butchery","Fruit & Vegetable","Drinks & Wine",
    "Clothing Store","Boutique","Shoe Store","Jewelry Store","Perfume Store","Cosmetics Store",
    "Electronics","Mobile Shop","Laptop Store","Appliances Store","Camera Store",
    "Furniture Store","Kitchen Accessories","Home Decor","Lighting Store",
    "Pharmacy","Health & Wellness","Supplements Store",
    "Baby & Kids","Toy Store","School Supplies",
    "Books & Stationery","Gift Shop","Pet Store","Hardware","Agriculture Store",
    "Automotive","Wines & Spirits","Sports Equipment","Toys & Games","Other"
]

# inventory: list of items
# each item: {id, owner_id, store_type, name, stock, used, unit_price, expiry_date (YYYY-MM-DD), avg_per_day, threshold (optional)}
inventory = []

# helper
def get_user_by_email(email):
    return users.get(email)

def get_current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    for u in users.values():
        if u["id"] == uid:
            return u
    return None

def days_left(expiry_date_str):
    try:
        exp = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
        return (exp - datetime.now().date()).days
    except Exception:
        return None

# --------------------
# Routes
# --------------------

@app.route("/")
def index():
    # if logged in and has store_type -> go to dashboard, else go to login
    user = get_current_user()
    if user:
        if user.get("store_type"):
            return redirect(url_for("dashboard"))
        return redirect(url_for("select_store"))
    return redirect(url_for("login"))

# Register
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        if not email or not password:
            flash("Please fill email and password","error")
            return redirect(url_for("register"))
        if email in users:
            flash("Email already registered","error")
            return redirect(url_for("register"))
        users[email] = {
            "id": str(uuid.uuid4()),
            "name": name or email.split("@")[0],
            "email": email,
            "password_hash": generate_password_hash(password),
            "store_type": None
        }
        session["user_id"] = users[email]["id"]
        return redirect(url_for("select_store"))
    return render_template("register.html", store_types=master_store_types)

# Login
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        user = get_user_by_email(email)
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            if user.get("store_type"):
                return redirect(url_for("dashboard"))
            return redirect(url_for("select_store"))
        flash("Invalid credentials","error")
        return redirect(url_for("login"))
    return render_template("login.html")

# Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out","success")
    return redirect(url_for("login"))

# Select store (required before dashboard)
@app.route("/select_store", methods=["GET","POST"])
def select_store():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    if request.method == "POST":
        chosen = request.form.get("store_type","").strip()
        custom = request.form.get("custom_store","").strip()
        # if custom provided, add to master list (avoid duplicates)
        if custom:
            if custom not in master_store_types:
                master_store_types.append(custom)
            chosen = custom
        if not chosen:
            flash("Please choose or add a store type","error")
            return redirect(url_for("select_store"))
        # set user's store_type
        user["store_type"] = chosen
        flash(f"Store set to {chosen}","success")
        return redirect(url_for("dashboard"))

    return render_template("select_store.html", store_types=master_store_types, current_store=user.get("store_type"))

# Change store (from dashboard)
@app.route("/change_store")
def change_store():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    # clear store_type and send to selection page
    user["store_type"] = None
    flash("Choose a new store type","info")
    return redirect(url_for("select_store"))

# Dashboard
@app.route("/dashboard")
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    store = user.get("store_type")
    if not store:
        return redirect(url_for("select_store"))

    search_q = request.args.get("search","").strip().lower()
    # user-specific items in that store
    user_items = [it for it in inventory if it["owner_id"] == user["id"] and it["store_type"] == store]
    if search_q:
        user_items = [it for it in user_items if search_q in it["name"].lower()]

    # compute days_left, avg/day, threshold flag, inventory value
    total_value = 0.0
    for it in user_items:
        it["days_left"] = days_left(it.get("expiry_date","")) if it.get("expiry_date") else None
        # avg per day fallback
        it["avg_per_day"] = round(it.get("avg_per_day", 0) , 2)
        it["threshold_flag"] = (it["stock"] <= it.get("threshold", 0)) if it.get("threshold") is not None else False
        total_value += it.get("stock",0) * float(it.get("unit_price",0) or 0)
    total_value = round(total_value,2)

    return render_template("dashboard.html", items=user_items, total_value=total_value, store=store)

# List items/manage (same as dashboard but editable list)
@app.route("/list_items", methods=["GET","POST"])
def list_items():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    store = user.get("store_type")
    if not store:
        return redirect(url_for("select_store"))

    if request.method == "POST":
        # Bulk update quantities/avg/threshold if present
        # We'll iterate items belonging to user & store and update by index
        for i, it in enumerate([it for it in inventory if it["owner_id"]==user["id"] and it["store_type"]==store]):
            stock = request.form.get(f"stock_{i}")
            avg = request.form.get(f"avg_{i}")
            threshold = request.form.get(f"threshold_{i}")
            if stock is not None:
                try:
                    it["stock"] = int(stock)
                except:
                    pass
            if avg is not None:
                try:
                    it["avg_per_day"] = float(avg)
                except:
                    pass
            if threshold is not None:
                try:
                    it["threshold"] = int(threshold)
                except:
                    pass
        flash("Items updated","success")
        return redirect(url_for("dashboard"))

    search_q = request.args.get("search","").strip().lower()
    user_items = [it for it in inventory if it["owner_id"]==user["id"] and it["store_type"]==store]
    if search_q:
        user_items = [it for it in user_items if search_q in it["name"].lower()]
    # compute some extra fields
    for it in user_items:
        it["days_left"] = days_left(it.get("expiry_date","")) if it.get("expiry_date") else None
        it["avg_per_day"] = round(it.get("avg_per_day",0),2)
    return render_template("list_items.html", items=user_items, store=store, search_query=request.args.get("search",""))

# Add item
@app.route("/add_item", methods=["GET","POST"])
def add_item():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    store = user.get("store_type")
    if not store:
        return redirect(url_for("select_store"))

    if request.method == "POST":
        name = request.form.get("name","").strip()
        stock = int(request.form.get("stock","0") or 0)
        avg = float(request.form.get("avg_per_day","0") or 0)
        unit_price = float(request.form.get("unit_price","0") or 0)
        expiry = request.form.get("expiry_date","").strip()
        threshold = request.form.get("threshold")
        threshold = int(threshold) if threshold else None

        item = {
            "id": str(uuid.uuid4()),
            "owner_id": user["id"],
            "store_type": store,
            "name": name,
            "stock": stock,
            "used": 0,
            "unit_price": unit_price,
            "expiry_date": expiry,
            "avg_per_day": avg,
            "threshold": threshold
        }
        inventory.append(item)
        flash("Item added","success")
        return redirect(url_for("dashboard"))
    return render_template("add_item.html", store=store)

# Edit item
@app.route("/edit_item/<item_id>", methods=["GET","POST"])
def edit_item(item_id):
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    item = next((it for it in inventory if it["id"]==item_id and it["owner_id"]==user["id"]), None)
    if not item:
        flash("Item not found","error")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        item["name"] = request.form.get("name", item["name"])
        item["stock"] = int(request.form.get("stock", item["stock"]) or item["stock"])
        item["avg_per_day"] = float(request.form.get("avg_per_day", item.get("avg_per_day", 0)) or item.get("avg_per_day",0))
        item["unit_price"] = float(request.form.get("unit_price", item.get("unit_price",0)) or item.get("unit_price",0))
        item["expiry_date"] = request.form.get("expiry_date", item.get("expiry_date",""))
        threshold = request.form.get("threshold")
        item["threshold"] = int(threshold) if threshold else None
        flash("Item updated","success")
        return redirect(url_for("dashboard"))

    return render_template("edit_item.html", item=item)

# Delete item
@app.route("/delete_item/<item_id>", methods=["GET"])
def delete_item(item_id):
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    global inventory
    inventory = [it for it in inventory if not (it["id"]==item_id and it["owner_id"]==user["id"])]
    flash("Item deleted","success")
    return redirect(url_for("dashboard"))

# --------------------
# Run
# --------------------
if __name__ == "__main__":
    app.run(debug=True)
