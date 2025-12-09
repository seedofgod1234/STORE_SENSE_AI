from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = "supersecretkey123"  # Change if you want, keeps sessions safe

# ----------------------------
# Email Configuration (Gmail)
# ----------------------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'veal-sarafel@gmail.com'   # Your Gmail
app.config['MAIL_PASSWORD'] = 'qdrmxezrxvpatjiu'         # Your app password

mail = Mail(app)

# ----------------------------
# In-memory storage for demo
# ----------------------------
users = {}  # email: password
notifications = []

# ----------------------------
# Routes
# ----------------------------
@app.route('/')
def home():
    if 'user' in session:
        return render_template('dashboard.html', user=session['user'], notifications=notifications)
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

        # Send welcome notification email
        try:
            msg = Message("Welcome to StoreSense AI", sender=app.config['MAIL_USERNAME'], recipients=[email])
            msg.body = f"Hello {email}, your StoreSense AI account is ready!"
            mail.send(msg)
        except Exception as e:
            print("Email failed:", e)

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
# Run app
# ----------------------------
if __name__ == '__main__':
    app.run(debug=True)
