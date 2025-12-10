# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///storesenseai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---------------------
# Database Models
# ---------------------

class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    items = db.relationship('Item', backref='store', lazy=True)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    avg_daily_sales = db.Column(db.Float, default=1)
    threshold = db.Column(db.Integer, default=5)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)

# ---------------------
# Routes
# ---------------------

@app.route('/')
def home():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    search_item = request.args.get('search_item', '')
    search_store = request.args.get('search_store', '')

    stores = Store.query.filter(Store.name.ilike(f"%{search_store}%")).all()
    items_query = Item.query

    if search_item:
        items_query = items_query.filter(Item.name.ilike(f"%{search_item}%"))
    if search_store:
        items_query = items_query.join(Store).filter(Store.name.ilike(f"%{search_store}%"))

    items = items_query.all()

    total_value = sum([item.price * item.stock for item in items])

    # Prepare items with additional info
    item_data = []
    for item in items:
        days_to_sell_out = round(item.stock / item.avg_daily_sales, 2)
        low_stock_alert = item.stock < item.threshold
        item_data.append({
            'id': item.id,
            'name': item.name,
            'category': item.category,
            'price': item.price,
            'stock': item.stock,
            'days_to_sell_out': days_to_sell_out,
            'low_stock_alert': low_stock_alert,
            'store_name': item.store.name
        })

    return render_template('dashboard.html', items=item_data, stores=stores, total_value=total_value, search_item=search_item, search_store=search_store)

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    stores = Store.query.all()
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        avg_daily_sales = float(request.form['avg_daily_sales'])
        threshold = int(request.form['threshold'])
        store_id = int(request.form['store_id'])

        new_item = Item(
            name=name, category=category, price=price,
            stock=stock, avg_daily_sales=avg_daily_sales,
            threshold=threshold, store_id=store_id
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Item added successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_item.html', stores=stores)

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    stores = Store.query.all()
    if request.method == 'POST':
        item.name = request.form['name']
        item.category = request.form['category']
        item.price = float(request.form['price'])
        item.stock = int(request.form['stock'])
        item.avg_daily_sales = float(request.form['avg_daily_sales'])
        item.threshold = int(request.form['threshold'])
        item.store_id = int(request.form['store_id'])

        db.session.commit()
        flash('Item updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_item.html', item=item, stores=stores)

@app.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Item deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

# ---------------------
# Initialize Sample Data
# ---------------------
@app.before_first_request
def create_tables():
    db.create_all()

    # Add sample stores if none exist
    if Store.query.count() == 0:
        store1 = Store(name="Main Street Store")
        store2 = Store(name="Downtown Shop")
        store3 = Store(name="Online Outlet")
        db.session.add_all([store1, store2, store3])
        db.session.commit()

    # Add sample items if none exist
    if Item.query.count() == 0:
        sample_items = [
            Item(name="Laptop", category="Electronics", price=1000, stock=10, avg_daily_sales=2, threshold=3, store_id=1),
            Item(name="Notebook", category="Stationery", price=5, stock=50, avg_daily_sales=5, threshold=10, store_id=2),
            Item(name="Headphones", category="Electronics", price=150, stock=20, avg_daily_sales=4, threshold=5, store_id=3)
        ]
        db.session.add_all(sample_items)
        db.session.commit()

# ---------------------
# Run Server
# ---------------------
if __name__ == '__main__':
    app.run(debug=True)
