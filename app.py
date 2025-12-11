from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    items = db.relationship('Item', backref='store', lazy=True)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    avg_daily_sales = db.Column(db.Float, default=1.0)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)

@app.route("/")
def home():
    stores = Store.query.all()
    return render_template("select_store.html", stores=stores)

@app.route("/select_store", methods=["POST"])
def select_store():
    store_id = request.form["store_id"]
    return redirect(url_for("dashboard", store_id=store_id))

@app.route("/store/<int:store_id>")
def dashboard(store_id):
    store = Store.query.get_or_404(store_id)
    search_query = request.args.get("search", "")
    if search_query:
        items = Item.query.filter(Item.store_id==store_id, Item.name.ilike(f"%{search_query}%")).all()
    else:
        items = Item.query.filter_by(store_id=store_id).all()
    
    total_value = sum([i.price * i.stock for i in items])
    
    for i in items:
        if i.avg_daily_sales > 0:
            i.days_to_sell_out = round(i.stock / i.avg_daily_sales, 1)
        else:
            i.days_to_sell_out = "∞"
        i.low_stock = i.stock < 5

    return render_template("dashboard.html", store=store, items=items, total_value=total_value)

@app.route("/add_item/<int:store_id>", methods=["GET","POST"])
def add_item(store_id):
    store = Store.query.get_or_404(store_id)
    if request.method=="POST":
        name = request.form["name"]
        stock = int(request.form["stock"])
        price = float(request.form["price"])
        avg_daily_sales = float(request.form.get("avg_daily_sales",1.0))
        new_item = Item(name=name, stock=stock, price=price, avg_daily_sales=avg_daily_sales, store_id=store_id)
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for("dashboard", store_id=store_id))
    return render_template("add_item.html", store=store)

@app.route("/edit_item/<int:item_id>", methods=["GET","POST"])
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    if request.method=="POST":
        item.name = request.form["name"]
        item.stock = int(request.form["stock"])
        item.price = float(request.form["price"])
        item.avg_daily_sales = float(request.form.get("avg_daily_sales",1.0))
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

with app.app_context():
    db.create_all()

if __name__=="__main__":
    port=int(os.getenv("PORT",5000))
    app.run(host="0.0.0.0", port=port)
