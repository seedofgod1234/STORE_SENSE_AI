from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime

app = Flask(__name__)
app.secret_key = "vealsarafel!storesenseAI$2025#fullpowerkey1234567890"

# In-memory data stores
users = {}
store_types = {
    "Clothes": [{"name": "Shirt", "stock": 10, "used": 2, "price": 20, "expiry_date": "2025-12-31"}],
    "Shoes": [{"name": "Sneakers", "stock": 5, "used": 1, "price": 50, "expiry_date": "2025-12-31"}],
    "Bags": [{"name": "Handbag", "stock": 3, "used": 0, "price": 70, "expiry_date": "2025-12-31"}],
    "Perfumes": [{"name": "Eau de Parfum", "stock": 8, "used": 2, "price": 100, "expiry_date": "2025-12-31"}],
    "Kitchen": [{"name": "Knife Set", "stock": 4, "used": 1, "price": 40, "expiry_date": "2025-12-31"}],
    "Wines": [{"name": "Red Wine", "stock": 6, "used": 1, "price": 30, "expiry_date": "2025-12-31"}],
}

def calculate_days_left(expiry_date):
    today = datetime.now().date()
    expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
    return (expiry - today).days

@app.route("/", methods=["GET"])
def home():
    if "username" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in users:
            return "User exists! Go back and choose a different username."
        users[username] = {"password": password, "store": None, "inventory": []}
        session["username"] = username
        return redirect(url_for("select_store"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in users and users[username]["password"] == password:
            session["username"] = username
            if users[username]["store"]:
                return redirect(url_for("dashboard"))
            else:
                return redirect(url_for("select_store"))
        return "Invalid credentials!"
    return render_template("login.html")

@app.route("/select_store", methods=["GET", "POST"])
def select_store():
    if "username" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        store_type = request.form["store_type"]
        username = session["username"]
        users[username]["store"] = store_type
        # Pre-fill inventory based on store type
        users[username]["inventory"] = store_types.get(store_type, []).copy()
        return redirect(url_for("dashboard"))
    return render_template("select_store.html", store_types=store_types.keys())

@app.route("/dashboard", methods=["GET"])
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]
    search_query = request.args.get("search", "").lower()
    items = []
    inventory_value = 0

    for item in users[username]["inventory"]:
        item["days_left"] = calculate_days_left(item["expiry_date"])
        item["average_per_day"] = round(item["used"] / max(item["days_left"], 1), 2)
        item["threshold"] = "LOW" if item["days_left"] < 5 else "OK"
        if search_query in item["name"].lower():
            items.append(item)
        inventory_value += item["stock"] * item["price"]

    return render_template("dashboard.html", items=items, inventory_value=inventory_value)

@app.route("/add_item", methods=["GET", "POST"])
def add_item():
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]
    if request.method == "POST":
        name = request.form["name"]
        stock = int(request.form["stock"])
        used = int(request.form["used"])
        price = float(request.form["price"])
        expiry_date = request.form["expiry_date"]
        item = {"name": name, "stock": stock, "used": used, "price": price, "expiry_date": expiry_date}
        users[username]["inventory"].append(item)
        return redirect(url_for("dashboard"))
    return render_template("add_item.html")

@app.route("/edit/<string:name>", methods=["GET", "POST"])
def edit_item(name):
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]
    item = next((i for i in users[username]["inventory"] if i["name"] == name), None)
    if not item:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        item["stock"] = int(request.form["stock"])
        item["used"] = int(request.form["used"])
        item["price"] = float(request.form["price"])
        item["expiry_date"] = request.form["expiry_date"]
        return redirect(url_for("dashboard"))
    return render_template("edit_item.html", item=item)

@app.route("/delete/<string:name>")
def delete_item(name):
    if "username" not in session:
        return redirect(url_for("login"))
    username = session["username"]
    users[username]["inventory"] = [i for i in users[username]["inventory"] if i["name"] != name]
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
