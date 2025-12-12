from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///store.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    total_sold = db.Column(db.Integer, default=0)
    created_at = db.Column(db.Date, default=date.today)

    def daily_sales(self):
        days = max((date.today() - self.created_at).days, 1)
        return self.total_sold / days

    def days_to_sell_out(self):
        rate = self.daily_sales()
        if rate == 0:
            return "∞"
        return round(self.stock / rate, 1)

    def reorder_amount(self, target_days=7):
        rate = self.daily_sales()
        needed = (target_days * rate) - self.stock
        return max(round(needed), 0)

    def status(self):
        days_left = self.days_to_sell_out()
        if days_left == "∞":
            return "🟢 Stable"
        if days_left <= 3:
            return "🔴 Urgent"
        if days_left <= 7:
            return "⚠️ Low"
        return "🟢 OK"


@app.before_first_request
def create_tables():
    db.create_all()


@app.route("/", methods=["GET"])
def dashboard():
    query = request.args.get("q", "")
    if query:
        items = Item.query.filter(Item.name.ilike(f"%{query}%")).all()
    else:
        items = Item.query.all()
    return render_template("dashboard.html", items=items, query=query)


@app.route("/add", methods=["GET", "POST"])
def add_item():
    if request.method == "POST":
        name = request.form["name"]
        stock = int(request.form["stock"])
        sold = int(request.form["sold"])
        item = Item(name=name, stock=stock, total_sold=sold)
        db.session.add(item)
        db.session.commit()
        return redirect(url_for("dashboard"))
    return render_template("add_item.html")


@app.route("/sell/<int:item_id>")
def sell_item(item_id):
    item = Item.query.get_or_404(item_id)
    if item.stock > 0:
        item.stock -= 1
        item.total_sold += 1
        db.session.commit()
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
