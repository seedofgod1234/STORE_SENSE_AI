from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store_sense_ai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    stores = db.relationship('Store', backref='owner', lazy=True)

class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    store_type = db.Column(db.String(100), nullable=False)
    region = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.relationship('Item', backref='store', lazy=True)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    avg_daily_sales = db.Column(db.Float, nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)

# --- User loader ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('select_store'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'], method='sha256')
        store_name = request.form['store_name']
        region = request.form['region']
        store_type = request.form['store_type']

        if User.query.filter_by(username=username).first():
            return "Username already exists."

        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()

        # Create store
        new_store = Store(name=store_name, store_type=store_type, region=region, owner=new_user)
        db.session.add(new_store)
        db.session.commit()

        # Add default items
        default_items = get_default_items(store_type)
        for item in default_items:
            db.session.add(Item(
                name=item['name'],
                stock=item['stock'],
                price=item['price'],
                avg_daily_sales=item['avg_daily_sales'],
                store=new_store
            ))
        db.session.commit()

        login_user(new_user)
        return redirect(url_for('select_store'))

    return render_template('register.html')

def get_default_items(store_type):
    items = []
    types = {
        'supermarket':[{'name':'Rice','stock':50,'price':2.0,'avg_daily_sales':5},
                       {'name':'Beans','stock':40,'price':1.5,'avg_daily_sales':4},
                       {'name':'Sugar','stock':30,'price':1.2,'avg_daily_sales':3}],
        'pharmacy':[{'name':'Paracetamol','stock':100,'price':0.5,'avg_daily_sales':10},
                    {'name':'Vitamin C','stock':80,'price':0.8,'avg_daily_sales':8}],
        'electronics':[{'name':'Charger','stock':20,'price':10,'avg_daily_sales':2},
                       {'name':'Earphones','stock':15,'price':15,'avg_daily_sales':1}],
        'fashion':[{'name':'T-Shirt','stock':25,'price':12,'avg_daily_sales':3},
                   {'name':'Jeans','stock':15,'price':25,'avg_daily_sales':2}],
        'beverages':[{'name':'Coke','stock':50,'price':1.5,'avg_daily_sales':6},
                     {'name':'Fanta','stock':40,'price':1.5,'avg_daily_sales':5}],
        'hair':[{'name':'Shampoo','stock':30,'price':3,'avg_daily_sales':3},
                {'name':'Hair Gel','stock':20,'price':4,'avg_daily_sales':2}],
        'provision':[{'name':'Flour','stock':40,'price':2,'avg_daily_sales':4},
                     {'name':'Cooking Oil','stock':30,'price':3,'avg_daily_sales':3}],
        'fruits':[{'name':'Apple','stock':50,'price':1,'avg_daily_sales':5},
                  {'name':'Banana','stock':60,'price':0.8,'avg_daily_sales':6}],
        'restaurant':[{'name':'Burger','stock':20,'price':5,'avg_daily_sales':2},
                      {'name':'Pizza','stock':15,'price':8,'avg_daily_sales':1}],
        'wholesale':[{'name':'Soap','stock':100,'price':1,'avg_daily_sales':10},
                     {'name':'Detergent','stock':80,'price':2,'avg_daily_sales':8}],
    }
    return types.get(store_type.lower(), [])

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password,password):
            return "Invalid credentials"
        login_user(user)
        return redirect(url_for('select_store'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/stores')
@login_required
def select_store():
    stores = Store.query.filter_by(user_id=current_user.id).all()
    return render_template('select_store.html', stores=stores)

@app.route('/dashboard/<int:store_id>', methods=['GET','POST'])
@login_required
def dashboard(store_id):
    store = Store.query.get_or_404(store_id)
    if store.owner != current_user:
        return "Unauthorized access"

    search_query = request.args.get('search', '').lower()
    items = Item.query.filter_by(store_id=store.id).all()
    suggestions = []

    if search_query:
        items = [item for item in items if search_query in item.name.lower()]
        if not items:
            suggestions = get_default_items(store.store_type)
            suggestions = [s for s in suggestions if search_query in s['name'].lower()]

    for item in items:
        item.days_left = round(item.stock / max(item.avg_daily_sales,1),2)

    return render_template('dashboard.html', store=store, items=items, suggestions=suggestions)

@app.route('/add_item/<int:store_id>', methods=['GET','POST'])
@login_required
def add_item(store_id):
    store = Store.query.get_or_404(store_id)
    if store.owner != current_user:
        return "Unauthorized access"

    if request.method=='POST':
        name = request.form['name']
        stock = int(request.form['stock'])
        price = float(request.form['price'])
        avg_daily_sales = float(request.form['avg_daily_sales'])
        new_item = Item(name=name, stock=stock, price=price, avg_daily_sales=avg_daily_sales, store=store)
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('dashboard', store_id=store.id))
    return render_template('add_item.html')

@app.route('/edit_item/<int:item_id>', methods=['GET','POST'])
@login_required
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    if item.store.owner != current_user:
        return "Unauthorized access"

    if request.method=='POST':
        item.name = request.form['name']
        item.stock = int(request.form['stock'])
        item.price = float(request.form['price'])
        item.avg_daily_sales = float(request.form['avg_daily_sales'])
        db.session.commit()
        return redirect(url_for('dashboard', store_id=item.store.id))

    return render_template('edit_item.html', item=item)

@app.route('/import_suggestion/<int:store_id>/<item_name>')
@login_required
def import_suggestion(store_id, item_name):
    store = Store.query.get_or_404(store_id)
    if store.owner != current_user:
        return "Unauthorized access"

    suggestions = get_default_items(store.store_type)
    for s in suggestions:
        if s['name'] == item_name:
            new_item = Item(
                name=s['name'],
                stock=s['stock'],
                price=s['price'],
                avg_daily_sales=s['avg_daily_sales'],
                store=store
            )
            db.session.add(new_item)
            db.session.commit()
            break
    return redirect(url_for('dashboard', store_id=store.id))

# --- Run app ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    db.create_all()
    app.run(host="0.0.0.0", port=port)
