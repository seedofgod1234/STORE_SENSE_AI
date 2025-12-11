# app.py — final StoreSenseAI backend (SQLite, deploy-ready)
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import os

# --- App & DB setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'replace_with_a_strong_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# -------------------------
# Models
# -------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    stores = db.relationship('Store', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class StoreType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    default_products = db.relationship('DefaultProduct', backref='store_type', lazy=True)

class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    region = db.Column(db.String(100), nullable=True)  # country/region field
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    store_type_id = db.Column(db.Integer, db.ForeignKey('store_type.id'), nullable=True)
    items = db.relationship('Item', backref='store', lazy=True)
    store_type = db.relationship('StoreType', primaryjoin='Store.store_type_id==StoreType.id', viewonly=True)

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

# -------------------------
# Login loader
# -------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------------
# Auth routes
# -------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
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
            flash('Username already taken. Pick another.', 'warning')
            return redirect(url_for('register'))

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # create store for user immediately
        stype_id = int(store_type_id) if store_type_id else None
        new_store = Store(name=store_name, region=region, user_id=user.id, store_type_id=stype_id)
        db.session.add(new_store)
        db.session.commit()

        # import starter products for this store type if any
        if stype_id:
            default_products = DefaultProduct.query.filter_by(store_type_id=stype_id).all()
            for dp in default_products:
                it = Item(
                    name=dp.name,
                    stock=dp.starter_stock,
                    price=dp.price,
                    avg_daily_sales=dp.avg_daily_sales,
                    store_id=new_store.id
                )
                db.session.add(it)
            db.session.commit()

        flash('Account and store created — please log in.', 'success')
        return redirect(url_for('login'))
    # GET
    store_types = StoreType.query.order_by(StoreType.name).all()
    return render_template('register.html', store_types=store_types)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = (request.form.get('password') or '').strip()
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('home'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

# -------------------------
# App routes
# -------------------------
@app.route('/')
@login_required
def home():
    # Show user's stores and available store types
    user_stores = Store.query.filter_by(user_id=current_user.id).all()
    store_types = StoreType.query.order_by(StoreType.name).all()
    return render_template('select_store.html', stores=user_stores, store_types=store_types)

@app.route('/create_store', methods=['POST'])
@login_required
def create_store():
    name = (request.form.get('store_name') or '').strip()
    region = (request.form.get('region') or '').strip()
    store_type_id = request.form.get('store_type_id') or None
    if not name:
        flash('Store name is required.', 'danger')
        return redirect(url_for('home'))
    stype_id = int(store_type_id) if store_type_id else None
    s = Store(name=name, region=region, user_id=current_user.id, store_type_id=stype_id)
    db.session.add(s)
    db.session.commit()

    # import starter items for chosen type if present
    if stype_id:
        defaults = DefaultProduct.query.filter_by(store_type_id=stype_id).all()
        for dp in defaults:
            it = Item(
                name=dp.name,
                stock=dp.starter_stock,
                price=dp.price,
                avg_daily_sales=dp.avg_daily_sales,
                store_id=s.id
            )
            db.session.add(it)
        db.session.commit()

    flash('Store created.', 'success')
    return redirect(url_for('dashboard', store_id=s.id))

@app.route('/store/<int:store_id>')
@login_required
def dashboard(store_id):
    store = Store.query.get_or_404(store_id)
    if store.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    search_query = (request.args.get('search') or '').strip()
    if search_query:
        items = Item.query.filter(Item.store_id == store.id, Item.name.ilike(f'%{search_query}%')).all()
    else:
        items = Item.query.filter_by(store_id=store.id).all()

    # suggestions when search exists and user has no matching items
    suggestions = []
    if search_query:
        if store.store_type_id:
            suggestions = DefaultProduct.query.filter(
                DefaultProduct.store_type_id == store.store_type_id,
                DefaultProduct.name.ilike(f'%{search_query}%')
            ).all()
        else:
            suggestions = DefaultProduct.query.filter(DefaultProduct.name.ilike(f'%{search_query}%')).all()

    # compute totals/predictions
    total_value = sum([i.price * i.stock for i in items])
    for i in items:
        if i.avg_daily_sales and i.avg_daily_sales > 0:
            i.days_to_sell_out = round(i.stock / i.avg_daily_sales, 1)
        else:
            i.days_to_sell_out = '∞'
        i.low_stock = i.stock < 5

    return render_template('dashboard.html', store=store, items=items, total_value=total_value, suggestions=suggestions, search_query=search_query)

@app.route('/add_item/<int:store_id>', methods=['GET', 'POST'])
@login_required
def add_item(store_id):
    store = Store.query.get_or_404(store_id)
    if store.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        stock = int(request.form.get('stock') or 0)
        price = float(request.form.get('price') or 0.0)
        avg_daily_sales = float(request.form.get('avg_daily_sales') or 1.0)
        it = Item(name=name, stock=stock, price=price, avg_daily_sales=avg_daily_sales, store_id=store.id)
        db.session.add(it)
        db.session.commit()
        flash('Item added.', 'success')
        return redirect(url_for('dashboard', store_id=store.id))
    return render_template('add_item.html', store=store)

@app.route('/import_suggestion/<int:store_id>/<int:default_id>', methods=['POST'])
@login_required
def import_suggestion(store_id, default_id):
    store = Store.query.get_or_404(store_id)
    if store.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    dp = DefaultProduct.query.get_or_404(default_id)
    new_item = Item(
        name=dp.name,
        stock=dp.starter_stock,
        price=dp.price,
        avg_daily_sales=dp.avg_daily_sales,
        store_id=store.id
    )
    db.session.add(new_item)
    db.session.commit()
    flash(f'Imported "{dp.name}" to your store. Edit stock and price as needed.', 'success')
    return redirect(url_for('dashboard', store_id=store.id))

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    store = item.store
    if store.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    if request.method == 'POST':
        item.name = (request.form.get('name') or '').strip()
        item.stock = int(request.form.get('stock') or 0)
        item.price = float(request.form.get('price') or 0.0)
        item.avg_daily_sales = float(request.form.get('avg_daily_sales') or 1.0)
        db.session.commit()
        flash('Item updated.', 'success')
        return redirect(url_for('dashboard', store_id=store.id))
    return render_template('edit_item.html', item=item)

@app.route('/delete_item/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    store = item.store
    if store.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    db.session.delete(item)
    db.session.commit()
    flash('Item removed.', 'info')
    return redirect(url_for('dashboard', store_id=store.id))

# -------------------------
# Seed default store types & default products (runs once)
# -------------------------
def seed_defaults():
    if StoreType.query.count() == 0:
        types = [
            "Supermarket","Pharmacy","Electronics Store","Clothing & Fashion Store",
            "Bakery","Provision Store","Cosmetics & Beauty Store"
        ]
        for t in types:
            db.session.add(StoreType(name=t))
        db.session.commit()

    if DefaultProduct.query.count() == 0:
        # mapping: (product name, store_type_name, price, avg_daily_sales, starter_stock)
        suggestions = [
            ("Bread","Supermarket",100.0,8,20),
            ("Eggs (6)","Supermarket",120.0,6,30),
            ("Rice 5kg","Supermarket",4500.0,4,20),
            ("Sugar 2kg","Supermarket",900.0,3,10),
            ("Paracetamol","Pharmacy",200.0,2,15),
            ("Vitamin C","Pharmacy",800.0,1,10),
            ("Phone Charger","Electronics Store",1500.0,3,10),
            ("Earbuds","Electronics Store",4000.0,1,5),
            ("T-Shirt","Clothing & Fashion Store",2500.0,0.5,10),
            ("Jeans","Clothing & Fashion Store",5000.0,0.2,5),
            ("Loaf Bread","Bakery",200.0,10,25),
            ("Cake Slice","Bakery",600.0,2,10),
            ("Cooking Oil 2L","Provision Store",2000.0,2,12),
            ("Milk 1L","Provision Store",500.0,6,15),
            ("Body Lotion","Cosmetics & Beauty Store",1200.0,1,8),
            ("Face Cream","Cosmetics & Beauty Store",1800.0,0.5,5),
        ]
        for name, st_name, price, ads, stock in suggestions:
            st = StoreType.query.filter_by(name=st_name).first()
            if st:
                dp = DefaultProduct(name=name, store_type_id=st.id, price=price, avg_daily_sales=ads, starter_stock=stock)
                db.session.add(dp)
        db.session.commit()

with app.app_context():
    db.create_all()
    seed_defaults()

# -------------------------
# Run (Render port compatibility)
# -------------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
