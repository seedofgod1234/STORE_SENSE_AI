from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = "vealsarafel!storesenseAI$2025#fullpowerkey1234567890"

# -------------------------
# In-memory storage for demo
# Replace with a database for production
# -------------------------
users = {}
items = []

# Predefined store types
store_types = [
    "Food & Grocery", "Clothes & Apparel", "Shoes & Bags",
    "Jewellery", "Perfumes & Creams", "Kitchen Accessories",
    "Electronics", "Wines & Spirits", "Books & Stationery",
    "Sports Equipment", "Toys & Games", "Health & Beauty"
]

# -------------------------
# Index route redirects to login
# -------------------------
@app.route('/')
def index():
    return redirect(url_for('login'))

# -------------------------
# User Authentication
# -------------------------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        store_type = request.form.get('store_type')
        
        if email in users:
            flash("Email already registered", "error")
            return redirect(url_for('register'))

        users[email] = {
            "id": str(uuid.uuid4()),
            "name": name,
            "email": email,
            "password": password,
            "store_type": store_type
        }
        session['user_id'] = users[email]['id']
        return redirect(url_for('dashboard'))
    return render_template('register.html', store_types=store_types)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users.get(email)
        if user and user['password'] == password:
            session['user_id'] = user['id']
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "error")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Logged out successfully", "success")
    return redirect(url_for('login'))

# -------------------------
# Dashboard & Items
# -------------------------
def get_current_user():
    uid = session.get('user_id')
    for u in users.values():
        if u['id'] == uid:
            return u
    return None

@app.route('/dashboard')
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    search_query = request.args.get('search', '').lower()
    filtered_items = [
        item for item in items
        if item['user_id'] == user['id'] and search_query in item['name'].lower()
    ]

    total_value = sum(item['stock'] * item['unit_price'] for item in filtered_items)
    return render_template('dashboard.html', items=filtered_items, total_value=total_value, user=user)

@app.route('/add_item', methods=['GET','POST'])
def add_item():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        stock = int(request.form['stock'])
        used = int(request.form.get('used', 0))
        expiry = request.form.get('expiry')
        unit_price = float(request.form.get('unit_price', 0))
        avg_day = float(request.form.get('avg_day', 0))
        item_id = str(uuid.uuid4())
        
        items.append({
            "id": item_id,
            "user_id": user['id'],
            "name": name,
            "stock": stock,
            "used": used,
            "expiry": expiry,
            "avg_day": avg_day,
            "unit_price": unit_price
        })
        flash("Item added successfully", "success")
        return redirect(url_for('dashboard'))

    return render_template('add_item.html')

@app.route('/edit_item/<item_id>', methods=['GET','POST'])
def edit_item(item_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    item = next((i for i in items if i['id'] == item_id and i['user_id'] == user['id']), None)
    if not item:
        flash("Item not found", "error")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        item['name'] = request.form['name']
        item['stock'] = int(request.form['stock'])
        item['used'] = int(request.form.get('used', 0))
        item['expiry'] = request.form.get('expiry')
        item['avg_day'] = float(request.form.get('avg_day', 0))
        item['unit_price'] = float(request.form.get('unit_price', 0))
        flash("Item updated successfully", "success")
        return redirect(url_for('dashboard'))

    return render_template('edit_item.html', item=item)

@app.route('/delete_item/<item_id>', methods=['POST'])
def delete_item(item_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    global items
    items = [i for i in items if not (i['id'] == item_id and i['user_id'] == user['id'])]
    flash("Item deleted successfully", "success")
    return redirect(url_for('dashboard'))

# -------------------------
# Run App
# -------------------------
if __name__ == '__main__':
    app.run(debug=True)
