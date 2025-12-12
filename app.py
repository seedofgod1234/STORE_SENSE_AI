# app.py - Final StoreSenseAI (per-store starter items + predictions)
from math import ceil
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'replace_with_a_real_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///storesense_final.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# -----------------------
# MODELS
# -----------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    # user can own multiple stores
    stores = db.relationship('Store', backref='owner', lazy=True)
    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)

class StoreType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    default_products = db.relationship('DefaultProduct', backref='store_type', lazy=True)

class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    region = db.Column(db.String(100), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    store_type_id = db.Column(db.Integer, db.ForeignKey('store_type.id'), nullable=True)
    items = db.relationship('Item', backref='store', lazy=True)
    store_type = db.relationship('StoreType', viewonly=True, primaryjoin='Store.store_type_id==StoreType.id')

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    price = db.Column(db.Float, nullable=False, default=0.0)
    avg_daily_sales = db.Column(db.Float, nullable=False, default=1.0)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)

class DefaultProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    store_type_id = db.Column(db.Integer, db.ForeignKey('store_type.id'), nullable=False)
    price = db.Column(db.Float, nullable=False, default=0.0)
    avg_daily_sales = db.Column(db.Float, nullable=False, default=1.0)
    starter_stock = db.Column(db.Integer, nullable=False, default=0)

# -----------------------
# LOGIN
# -----------------------
@login_manager.user_loader
def load_user(uid):
    return User.query.get(int(uid))

# -----------------------
# HELPERS
# -----------------------
def seed_defaults():
    # create store types once
    types = [
        "Supermarket","Pharmacy","Electronics Store","Clothing Boutique",
        "Shoe Store","Restaurant","Cosmetics Shop","Bookstore","Hardware Store","Mobile Accessories"
    ]
    if StoreType.query.count() == 0:
        for t in types:
            db.session.add(StoreType(name=t))
        db.session.commit()

    # create default products per store type if missing
    if DefaultProduct.query.count() == 0:
        mapping = {
            "Supermarket": [
                ("Rice 5kg", 4500.0, 4, 20),
                ("Bread Loaf", 200.0, 8, 25),
                ("Milk 1L", 500.0, 6, 15),
                ("Sugar 2kg", 900.0, 3, 10),
                ("Indomie (pack)", 150.0, 10, 30)
            ],
            "Pharmacy": [
                ("Paracetamol", 200.0, 5, 30),
                ("Cough Syrup", 1200.0, 1, 10),
                ("Bandages", 300.0, 0.5, 20)
            ],
            "Electronics Store": [
                ("Phone Charger", 1500.0, 2, 10),
                ("Earbuds", 4000.0, 1, 5)
            ],
            "Clothing Boutique": [
                ("T-Shirt", 2500.0, 0.5, 10),
                ("Jeans", 5000.0, 0.2, 5)
            ],
            "Shoe Store": [
                ("Sneakers", 8000.0, 0.1, 3),
                ("Slippers", 1200.0, 0.3, 8)
            ],
            "Restaurant": [
                ("Burger", 500.0, 5, 20),
                ("Fries (portion)", 200.0, 6, 30)
            ],
            "Cosmetics Shop": [
                ("Body Lotion", 1200.0, 1, 8),
                ("Face Cream", 1800.0, 0.5, 5)
            ],
            "Bookstore": [
                ("Notebook", 300.0, 1, 12),
                ("Pen Pack", 200.0, 2, 20)
            ],
            "Hardware Store": [
                ("Screwdriver", 1500.0, 0.2, 5),
                ("Nails (box)", 800.0, 1, 20)
            ],
            "Mobile Accessories": [
                ("Screen Protector", 500.0, 3, 25),
                ("Power Bank", 7000.0, 0.3, 5)
            ]
        }
        for st_name, products in mapping.items():
            st = StoreType.query.filter_by(name=st_name).first()
            if not st:
                continue
            for name, price, ads, stock in products:
                dp = DefaultProduct(name=name, store_type_id=st.id, price=price, avg_daily_sales=ads, starter_stock=stock)
                db.session.add(dp)
        db.session.commit()

def import_defaults_into_store(store):
    # create Item rows for the store by copying DefaultProducts
    if not store or not store.store_type_id:
        return
    defaults = DefaultProduct.query.filter_by(store_type_id=store.store_type_id).all()
    for dp in defaults:
        it = Item(name=dp.name, stock=dp.starter_stock, price=dp.price, avg_daily_sales=dp.avg_daily_sales, store_id=store.id)
        db.session.add(it)
    db.session.commit()

def compute_predictions_for_items(items):
    # add days_to_sell_out, reorder_amount, low_stock flags
    for i in items:
        if i.avg_daily_sales and i.avg_daily_sales > 0:
            i.days_to_sell_out = round(i.stock / i.avg_daily_sales, 1)
        else:
            i.days_to_sell_out = "∞"
        # recommended reorder to cover 7 days lead time
        needed = max(0, ceil(i.avg_daily_sales * 7 - i.stock))
        i.reorder_amount = needed
        # low stock if stock below 3x avg_daily_sales or reorder_amount>0
        i.low_stock = (i.stock < max(5, i.avg_daily_sales * 3)) or (i.reorder_amount > 0)

# -----------------------
# ROUTES
# -----------------------
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('stores'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('stores'))
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = (request.form.get('password') or '').strip()
        store_name = (request.form.get('store_name') or '').strip()
        region = (request.form.get('region') or '').strip()
        store_type_id = request.form.get('store_type_id') or None
        if not username or not password or not store_name:
            flash('Username, password and store name are required.', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'warning')
            return redirect(url_for('register'))

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        stype = int(store_type_id) if store_type_id else None
        new_store = Store(name=store_name, region=region, user_id=user.id, store_type_id=stype)
        db.session.add(new_store)
        db.session.commit()

        # import defaults into that store (starter items)
        if stype:
            import_defaults_into_store(new_store)

        login_user(user)
        flash('Account created and store initialized.', 'success')
        return redirect(url_for('stores'))

    store_types = StoreType.query.order_by(StoreType.name).all()
    return render_template('register.html', store_types=store_types)

@app.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('stores'))
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = (request.form.get('password') or '').strip()
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash('Invalid credentials.', 'danger')
            return redirect(url_for('login'))
        login_user(user)
        return redirect(url_for('stores'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/stores', methods=['GET','POST'])
@login_required
def stores():
    # show user's stores and allow searching store list (B)
    q = (request.args.get('q') or '').strip()
    user_stores = Store.query.filter_by(user_id=current_user.id).all()
    # also provide all available store types for creating new store
    store_types = StoreType.query.order_by(StoreType.name).all()
    # optional global store search (not required but useful)
    if q:
        # filter user's stores by name
        user_stores = [s for s in user_stores if q.lower() in s.name.lower()]
    return render_template('select_store.html', stores=user_stores, store_types=store_types, q=q)

@app.route('/create_store', methods=['POST'])
@login_required
def create_store():
    name = (request.form.get('store_name') or '').strip()
    region = (request.form.get('region') or '').strip()
    store_type_id = request.form.get('store_type_id') or None
    if not name:
        flash('Store name required', 'danger')
        return redirect(url_for('stores'))
    stype = int(store_type_id) if store_type_id else None
    s = Store(name=name, region=region, user_id=current_user.id, store_type_id=stype)
    db.session.add(s)
    db.session.commit()
    if stype:
        import_defaults_into_store(s)
    flash('Store created.', 'success')
    return redirect(url_for('stores'))

@app.route('/dashboard/<int:store_id>')
@login_required
def dashboard(store_id):
    store = Store.query.get_or_404(store_id)
    if store.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('stores'))

    search = (request.args.get('search') or '').strip()
    # fetch user's actual items
    items = Item.query.filter_by(store_id=store.id).all()

    # If user has no items or search yields none, use suggestions from DefaultProduct
    suggestions = []
    if search:
        matched_items = [it for it in items if search.lower() in it.name.lower()]
        if matched_items:
            items = matched_items
        else:
            if store.store_type_id:
                suggestions = DefaultProduct.query.filter(DefaultProduct.store_type_id==store.store_type_id,
                                                          DefaultProduct.name.ilike(f'%{search}%')).all()
            else:
                suggestions = DefaultProduct.query.filter(DefaultProduct.name.ilike(f'%{search}%')).all()
    # compute predictions for items list
    compute_predictions_for_items(items)
    total_value = sum([it.price * it.stock for it in items])
    return render_template('dashboard.html', store=store, items=items, suggestions=suggestions, total_value=total_value, search=search)

@app.route('/add_item/<int:store_id>', methods=['GET','POST'])
@login_required
def add_item(store_id):
    store = Store.query.get_or_404(store_id)
    if store.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('stores'))
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        stock = int(request.form.get('stock') or 0)
        price = float(request.form.get('price') or 0.0)
        avg = float(request.form.get('avg_daily_sales') or 1.0)
        it = Item(name=name, stock=stock, price=price, avg_daily_sales=avg, store_id=store.id)
        db.session.add(it)
        db.session.commit()
        flash('Item added.', 'success')
        return redirect(url_for('dashboard', store_id=store.id))
    return render_template('add_item.html', store=store)

@app.route('/edit_item/<int:item_id>', methods=['GET','POST'])
@login_required
def edit_item(item_id):
    it = Item.query.get_or_404(item_id)
    store = it.store
    if store.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('stores'))
    if request.method == 'POST':
        it.name = (request.form.get('name') or '').strip()
        it.stock = int(request.form.get('stock') or 0)
        it.price = float(request.form.get('price') or 0.0)
        it.avg_daily_sales = float(request.form.get('avg_daily_sales') or 1.0)
        db.session.commit()
        flash('Saved.', 'success')
        return redirect(url_for('dashboard', store_id=store.id))
    return render_template('edit_item.html', item=it)

@app.route('/import_default/<int:store_id>/<int:default_id>', methods=['POST'])
@login_required
def import_default(store_id, default_id):
    store = Store.query.get_or_404(store_id)
    if store.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('stores'))
    dp = DefaultProduct.query.get_or_404(default_id)
    it = Item(name=dp.name, stock=dp.starter_stock, price=dp.price, avg_daily_sales=dp.avg_daily_sales, store_id=store.id)
    db.session.add(it)
    db.session.commit()
    flash(f'Imported {dp.name}', 'success')
    return redirect(url_for('dashboard', store_id=store.id))

@app.route('/delete_item/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    it = Item.query.get_or_404(item_id)
    store = it.store
    if store.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('stores'))
    db.session.delete(it)
    db.session.commit()
    flash('Item deleted', 'info')
    return redirect(url_for('dashboard', store_id=store.id))

# -----------------------
# BOOTSTRAP DB & DEFAULTS
# -----------------------
with app.app_context():
    db.create_all()
    seed_defaults()

# -----------------------
# RUN
# -----------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
