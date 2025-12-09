from flask import Flask, render_template, request, redirect, url_for, flash, session
import math

app = Flask(__name__)
app.secret_key = "supersecretkey123"

# ----------------------------
# In-memory storage for demo
# ----------------------------
users = {}  # email: password
store_items = {}  # user_email: list of items


# ----------------------------
# Routes
# ----------------------------
@app.route('/')
def home():
    if 'user' in session:
        user_email = session['user']
        # Ensure store_items list exists for old accounts
        if user_email not in store_items:
            store_items[user_email] = []

        items = store_items.get(user_email, [])

        # Generate low stock notifications
        low_stock_notifications = []
        for item in items:
            if item['quantity'] <= item['low_threshold']:
                low_stock_notifications.append(f"Low stock: {item['name']} (Qty: {item['quantity']})")

        return render_template('dashboard.html', user=user_email, items=items,
                               notifications=low_stock_notifications)
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if email in users:
            flash("Email already registered.", "danger")
            return redirect(url_for('register'))

        users[email] = password
        session['user'] = email
        store_items[email] = []  # Initialize empty store items list
        flash("Account created successfully!", "success")
        return redirect(url_for('home'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if email in users and users[email] == password:
            session['user'] = email
            return redirect(url_for('home'))
        else:
            flash("Invalid credentials.", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))


# ----------------------------
# Add new store item
# ----------------------------
@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_email = session['user']
    # Ensure store_items list exists for old accounts
    if user_email not in store_items:
        store_items[user_email] = []

    if request.method == 'POST':
        try:
            name = request.form['name']
            quantity = int(request.form['quantity'])
            price = float(request.form['price'])
            avg_daily_sales = float(request.form['avg_daily_sales'])
            low_threshold = int(request.form['low_threshold'])

            # Calculate days left safely
            days_left = math.ceil(quantity / avg_daily_sales) if avg_daily_sales > 0 else None
            reorder_amount = max(low_threshold * 2 - quantity, 0)

            item = {
                'name': name,
                'quantity': quantity,
                'price': price,
                'avg_daily_sales': avg_daily_sales,
                'low_threshold': low_threshold,
                'days_left': days_left,
                'reorder_amount': reorder_amount
            }

            store_items[user_email].append(item)
            flash(f"Item '{name}' added successfully!", "success")
        except ValueError:
            flash("Please enter valid numbers for quantity, price, average daily sales, and low threshold.", "danger")
        except Exception as e:
            flash(f"Error adding item: {e}", "danger")

        return redirect(url_for('home'))

    return render_template('add_item.html')


# ----------------------------
# Run app
# ----------------------------
if __name__ == '__main__':
    app.run(debug=True)
