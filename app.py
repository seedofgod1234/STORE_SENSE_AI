# app.py
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///storesense.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

@app.route('/')
def home():
    stores = Store.query.all()
    return render_template('select_store.html', stores=stores)

@app.route('/dashboard/<int:store_id>')
def dashboard(store_id):
    store = Store.query.get_or_404(store_id)
    items = Item.query.filter_by(store_id=store.id).all()
    return render_template('dashboard.html', store=store, items=items)

@app.route('/add_item/<int:store_id>', methods=['GET', 'POST'])
def add_item(store_id):
    store = Store.query.get_or_404(store_id)
    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']
        new_item = Item(store_id=store.id, name=name, quantity=quantity)
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('dashboard', store_id=store.id))
    return render_template('add_item.html', store=store)

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    if request.method == 'POST':
        item.name = request.form['name']
        item.quantity = request.form['quantity']
        db.session.commit()
        return redirect(url_for('dashboard', store_id=item.store_id))
    return render_template('edit_item.html', item=item)

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

# Required for Render
if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))  # FIX FOR RENDER
    app.run(host='0.0.0.0', port=port)
