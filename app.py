from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ------------------------------
# MODELS
# ------------------------------
class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    store = db.relationship('Store', backref=db.backref('items', lazy=True))


# ------------------------------
# ROUTES
# ------------------------------

@app.route("/")
def home():
    stores = Store.query.all()
    return render_template("select_store.html", stores=stores)

@app.route("/store/<int:store_id>")
def dashboard(store_id):
    store = Store.query.get_or_404(store_id)
    items = Item.query.filter_by(store_id=store_id).all()

    total_value = sum([i.price * i.stock for i in items])

    return render_template("dashboard.html",
                           store=store,
                           items=items,
                           total_value=total_value)

@app.route("/add_item/<int:store_id>", methods=["GET", "POST"])
def add_item(store_id):
    store = Store.query.get_or_404(store_id)

    if request.method == "POST":
        name = request.form["name"]
        stock = int(request.form["stock"])
        price = float(request.form["price"])

        new_item = Item(name=name, stock=stock, price=price, store_id=store_id)
        db.session.add(new_item)
        db.session.commit()

        return redirect(url_for("dashboard", store_id=store_id))

    return render_template("add_item.html", store=store)

@app.route("/edit_item/<int:item_id>", methods=["GET", "POST"])
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)

    if request.method == "POST":
        item.name = request.form["name"]
        item.stock = int(request.form["stock"])
        item.price = float(request.form["price"])
        db.session.commit()

        return redirect(url_for("dashboard", store_id=item.store_id))

    return render_template("edit_item.html", item=item)

@app.route("/delete_item/<int:item_id>")
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    store_id = item.store_id

    db.session.delete(item)
    db.session.commit()

    return redirect(url_for("dashboard", store_id=store_id))

@app.route("/add_store", methods=["POST"])
def add_store():
    name = request.form["store_name"]
    new_store = Store(name=name)
    db.session.add(new_store)
    db.session.commit()

    return redirect(url_for("home"))


# ------------------------------
# AUTO CREATE TABLES
# ------------------------------
with app.app_context():
    db.create_all()


# ------------------------------
# RUN APP
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
