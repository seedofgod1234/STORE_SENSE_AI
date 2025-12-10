from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "vealsarafel!storesenseAI$2025#fullpowerkey1234567890"

# In-memory storage (replace with database later)
users = {}
inventory = {}
store_types = [
    "Food & Grocery", "Clothing", "Jewelry", "Shoes", "Bags",
    "Cosmetics", "Perfumes", "Fruits & Vegetables", "Kitchen Accessories", "Wines & Beverages"
]

# =========================
# HOME ROUTE
# =========================
@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# =========================
# REGISTER ROUTE
# =========================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users:
            return "Username already exists!"
        
        users[username] = {
            'password': password,
            'store': None
        }
        session['username'] = username
        return redirect(url_for('select_store'))

    return render_template('register.html')

# =========================
# LOGIN ROUTE
# =========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users and users[username]['password'] == password:
            session['username'] = username
            if users[username]['store']:
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('select_store'))
        else:
            return "Invalid credentials!"
    return render_template('login.html')

# =========================
# LOGOUT
# =========================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# =========================
# SELECT STORE ROUTE
# =========================
@app.route('/select_store', methods=['GET', 'POST'])
def select_store():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        selected_store = request.form['store_name'].strip()
        if selected_store not in store_types:
            store_types.append(selected_store)  # allow custom store

        users[session['username']]['store'] = selected_store
        session['store'] = selected_store
        return redirect(url_for('dashboard'))

    return render_template('select_store.html', store_types=store_types)

# =========================
# DASHBOARD
# =========================
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    store = session.get('store')
    store_inventory = inventory.get(store, [])
    search_query = request.args.get('search', '').lower()
    
    if search_query:
        filtered_items = [item for item in store_inventory if search_query in item['name'].lower()]
    else:
        filtered_items = store_inventory

    # Calculate inventory value (simple example: stock * avg_per_day)
    inventory_value = sum(item['stock'] * item['avg_per_day'] for item in store_inventory)

    return render_template('dashboard.html',
                           items=filtered_items,
                           store=store,
                           inventory_value=inventory_value)

# =========================
# ADD ITEM
# =========================
@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if 'username' not in session:
        return redirect(url_for('login'))

    store = session.get('store')
    if store not in inventory:
        inventory[store] = []

    if request.method == 'POST':
        try:
            name = request.form['name']
            stock = int(request.form['stock'])
            used = int(request.form['used'])
            expiry_date = request.form['expiry_date']
            threshold = int(request.form['threshold'])
            avg_per_day = float(request.form['avg_per_day'])
            
            days_left = stock // (avg_per_day if avg_per_day > 0 else 1)

            inventory[store].append({
                'name': name,
                'stock': stock,
                'used': used,
                'expiry_date': expiry_date,
                'threshold': threshold,
                'avg_per_day': avg_per_day,
                'days_left': days_left
            })

            return redirect(url_for('dashboard'))
        except Exception as e:
            return f"Error adding item: {e}", 400

    return render_template('add_item.html', store=store)

# =========================
# EDIT ITEM
# =========================
@app.route('/edit_item/<int:item_index>', methods=['GET', 'POST'])
def edit_item(item_index):
    if 'username' not in session:
        return redirect(url_for('login'))

    store = session.get('store')
    store_inventory = inventory.get(store, [])

    if item_index < 0 or item_index >= len(store_inventory):
        return "Item not found", 404

    item = store_inventory[item_index]

    if request.method == 'POST':
        try:
            item['name'] = request.form['name']
            item['stock'] = int(request.form['stock'])
            item['used'] = int(request.form['used'])
            item['expiry_date'] = request.form['expiry_date']
            item['threshold'] = int(request.form['threshold'])
            item['avg_per_day'] = float(request.form['avg_per_day'])
            item['days_left'] = item['stock'] // (item['avg_per_day'] if item['avg_per_day'] > 0 else 1)
            return redirect(url_for('dashboard'))
        except Exception as e:
            return f"Error editing item: {e}", 400

    return render_template('edit_item.html', item=item, item_index=item_index, store=store)

# =========================
# DELETE ITEM
# =========================
@app.route('/delete_item/<int:item_index>', methods=['POST'])
def delete_item(item_index):
    if 'username' not in session:
        return redirect(url_for('login'))

    store = session.get('store')
    store_inventory = inventory.get(store, [])

    if 0 <= item_index < len(store_inventory):
        store_inventory.pop(item_index)
        inventory[store] = store_inventory

    return redirect(url_for('dashboard'))

# =========================
# RUN APP
# =========================
if __name__ == '__main__':
    app.run(debug=True)
