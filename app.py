from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
import pandas as pd

app = Flask(__name__)
app.secret_key = '3263'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Firm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    ein = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(250), nullable=False)
    mol = db.Column(db.String(150), nullable=False)

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firm.id'), nullable=False)
    filename = db.Column(db.String(250), nullable=False)
    month = db.Column(db.String(50), nullable=False)
    year = db.Column(db.String(50), nullable=False)

# Database setup
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", password="123")
        db.session.add(admin)
        db.session.commit()

# Login loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            session['last_company_id'] = None
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    search_query = request.args.get('search', '')
    firms = Firm.query.filter(Firm.name.contains(search_query)).all()

    last_company_id = session.get('last_company_id')
    company_to_display = Firm.query.get(last_company_id) if last_company_id else (firms[0] if firms else None)

    return render_template('dashboard.html', firms=firms, company=company_to_display, search_query=search_query)

@app.route('/search_companies')
@login_required
def search_companies():
    query = request.args.get('query', '').lower()  # Get the search query from the URL
    firms = Firm.query.filter(Firm.name.like(f"{query}%")).all()  # Filter firms starting with the query
    return jsonify([{'id': firm.id, 'name': firm.name} for firm in firms])  # Return matching firms as JSON

@app.route('/add_firm', methods=['GET', 'POST'])
@login_required
def add_firm():
    if request.method == 'POST':
        name = request.form['name']
        ein = request.form['ein']
        address = request.form['address']
        mol = request.form['mol']
        firm = Firm(name=name, ein=ein, address=address, mol=mol)
        db.session.add(firm)
        db.session.commit()
        flash('Firm added successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_firm.html')

@app.route('/firm/<int:firm_id>', methods=['GET', 'POST'])
@login_required
def firm_profile(firm_id):
    session['last_company_id'] = firm_id
    firm = Firm.query.get_or_404(firm_id)
    files = File.query.filter_by(firm_id=firm_id).all()
    if request.method == 'POST':
        file = request.files['file']
        month = request.form['month']
        year = request.form['year']
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Save metadata to the database
        new_file = File(firm_id=firm_id, filename=filename, month=month, year=year)
        db.session.add(new_file)
        db.session.commit()

        flash('File uploaded successfully!', 'success')
        return redirect(url_for('firm_profile', firm_id=firm_id))
    return render_template('firm_profile.html', firm=firm, files=files)

@app.route('/delete_file/<int:file_id>', methods=['POST'])
@login_required
def delete_file(file_id):
    file = File.query.get_or_404(file_id)
    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
    db.session.delete(file)
    db.session.commit()
    flash('File deleted successfully!', 'success')
    return redirect(url_for('firm_profile', firm_id=file.firm_id))

@app.route('/create_account', methods=['GET', 'POST'])
@login_required
def create_account():
    if current_user.username != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
        else:
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully!', 'success')
            return redirect(url_for('dashboard'))

    return render_template('create_account.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))



# Run the server
if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)