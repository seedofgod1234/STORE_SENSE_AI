import os
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'devkey')

# In-memory data
users = {}
stores = [
    "Clothes", "Shoes", "Jewelry", "Bags", "Perfumes", "Creams",
    "Fruits", "Wines", "Kitchen Accessories", "Electronics", "Books"
]
inventory = {}  # {username: [{item}]}

# Routes
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            flash("Username already exists!")
            return redirect(url_for('register'))
        users[username] = password
        session['username'] = username
        return redirect(url_for('select_store'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if users.get(username) == password:
            session['username'] = username
            return redirect(url_for('select_store'))
        flash("Invalid username or password!")
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('store', None)
    return redirect(url_for('login'))

@app.route('/select_store', methods=['GET', 'POST'])
def select_store():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        store = request.form['store'].strip()
        if store not in stores:
            stores.append(store)
        session['store'] = store
        if session['username'] not in inventory:
            inventory[session['username']] = []
        return redirect(url_for('dashboard'))
    return render_template('select_store.html', stores=stores)

@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    user_inventory = inventory.get(session['username'], [])
    query = request.args.get('search', '').lower()
    filtered_inventory = [item for item in user_inventory if query in item['name'].lower()]
    total_value = sum(item['stock'] * item.get('price', 0) for item in user_inventory)
    return render_template('dashboard.html', inventory=filtered_inventory,
                           store=session.get('store', ''), total_value=total_value)

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        stock = int(request.form['stock'])
        price = float(request.form['price'])
        user_inventory = inventory.setdefault(session['username'], [])
        user_inventory.append({
            'name': name,
            'stock': stock,
            'price': price
        })
        return redirect(url_for('dashboard'))
    return render_template('add_item.html')

@app.route('/edit_item/<int:item_index>', methods=['GET', 'POST'])
def edit_item(item_index):
    if 'username' not in session:
        return redirect(url_for('login'))
    user_inventory = inventory.get(session['username'], [])
    if item_index >= len(user_inventory):
        flash("Item not found!")
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        user_inventory[item_index]['name'] = request.form['name']
        user_inventory[item_index]['stock'] = int(request.form['stock'])
        user_inventory[item_index]['price'] = float(request.form['price'])
        return redirect(url_for('dashboard'))
    item = user_inventory[item_index]
    return render_template('edit_item.html', item=item, index=item_index)

@app.route('/delete_item/<int:item_index>', methods=['GET'])
def delete_item(item_index):
    if 'username' not in session:
        return redirect(url_for('login'))
    user_inventory = inventory.get(session['username'], [])
    if item_index < len(user_inventory):
        user_inventory.pop(item_index)
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
