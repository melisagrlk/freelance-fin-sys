import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_freelance_os'

def get_db_connection():
    conn = sqlite3.connect('freelance.db')
    conn.row_factory = sqlite3.Row
    return conn

def calculate_financials(projects):
    """
    Business Logic: Calculates gross revenue, total earnings, and outstanding receivables.
    Designed to be fully compatible with both sqlite3.Row and unit test dicts.
    """
    total_revenue = 0
    pending_payments = 0
    gross_revenue = 0
    
    for project in projects:
        budget = project['budget']
        status = project['status']
        
        gross_revenue += budget
        if status == 'Paid':
            total_revenue += budget
        elif status == 'Pending':
            pending_payments += budget
            
    return gross_revenue, total_revenue, pending_payments

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # 🔐 MÜHENDİSLİK MANTIĞI: Küçük harf (islower) kontrolünü de zincire ekledik
        if (len(password) < 8 or 
            not any(char.isupper() for char in password) or 
            not any(char.islower() for char in password) or 
            not any(char.isdigit() for char in password)):
            
            flash("Warning: Password does not meet the secure requirements listed below!")
            return redirect(url_for('register'))
        
        db = get_db_connection()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        
        if user:
            flash("Username already exists!")
            db.close()
            return redirect(url_for('register'))
            
        # Güvenli hash'leme
        hashed_password = generate_password_hash(password)
        
        db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        db.commit()
        db.close()
        return redirect(url_for('login'))
        
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db_connection()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        db.close()
        
        # 🔐 MÜHENDİSLİK KRİTERİ: Gelen düz şifreyi, db'deki hash'li şifreyle güvenli şekilde kıyaslıyoruz
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials!")
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category_filter', '').strip()
    
    db = get_db_connection()
    query = "SELECT * FROM projects WHERE user_id = ?"
    params = [user_id]
    
    if search_query:
        query += " AND (client_name LIKE ? OR project_title LIKE ?)"
        formatted_search = f"%{search_query}%"
        params.extend([formatted_search, formatted_search])
        
    if category_filter:
        query += " AND category = ?"
        params.append(category_filter)
        
    projects = db.execute(query, tuple(params)).fetchall()
    db.close()
    
    # Financial calculation using business logic function
    gross_revenue, total_revenue, pending_payments = calculate_financials(projects)
    
    # [US6] Deadline and urgency analysis
    analyzed_projects = []
    current_date = datetime.now()
    
    for row in projects:
        project_dict = dict(row)
        try:
            project_deadline = datetime.strptime(project_dict['deadline'], '%Y-%m-%d')
            # Calculate remaining days (using .days treats it purely on date level)
            days_remaining = (project_deadline.date() - current_date.date()).days
            
            if 0 <= days_remaining <= 3 and project_dict['status'] == 'Pending':
                project_dict['is_urgent'] = True
            else:
                project_dict['is_urgent'] = False
        except:
            project_dict['is_urgent'] = False
            
        analyzed_projects.append(project_dict)
        
    return render_template('dashboard.html', projects=analyzed_projects, total_revenue=total_revenue, pending_payments=pending_payments, gross_revenue=gross_revenue)

@app.route('/add_project', methods=['GET', 'POST'])
def add_project():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        client_name = request.form['client_name']
        project_title = request.form['project_title']
        budget = float(request.form['budget'])
        deadline = request.form['deadline']
        category = request.form['category']
        user_id = session['user_id']
        
        db = get_db_connection()
        db.execute(
            "INSERT INTO projects (client_name, project_title, budget, deadline, category, status, user_id) VALUES (?, ?, ?, ?, ?, 'Pending', ?)",
            (client_name, project_title, budget, deadline, category, user_id)
        )
        db.commit()
        db.close()
        return redirect(url_for('dashboard'))
        
    return render_template('add_project.html')

@app.route('/edit_project/<int:project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    db = get_db_connection()
    project = db.execute("SELECT * FROM projects WHERE id = ? AND user_id = ?", (project_id, user_id)).fetchone()

    if not project:
        db.close()
        return "Project not found or unauthorized!", 404

    if request.method == 'POST':
        client_name = request.form.get('client_name')
        project_title = request.form.get('project_title')
        budget_raw = request.form.get('budget')
        deadline = request.form.get('deadline')
        category = request.form.get('category')

        if not client_name or not project_title or not budget_raw or not deadline or not category:
            flash("Warning: All fields are mandatory!")
            return redirect(url_for('edit_project', project_id=project_id))

        try:
            budget = float(budget_raw)
            if budget <= 0:
                flash("Warning: Budget must be a positive number!")
                return redirect(url_for('edit_project', project_id=project_id))
        except ValueError:
            flash("Warning: Invalid budget format!")
            return redirect(url_for('edit_project', project_id=project_id))

        db.execute("""
            UPDATE projects 
            SET client_name = ?, project_title = ?, budget = ?, deadline = ?, category = ? 
            WHERE id = ? AND user_id = ?
        """, (client_name, project_title, budget, deadline, category, project_id, user_id))
        
        db.commit()
        db.close()
        return redirect(url_for('dashboard'))

    db.close()
    return render_template('edit_project.html', project=project)

@app.route('/toggle_status/<int:project_id>')
def toggle_status(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db_connection()
    project = db.execute("SELECT * FROM projects WHERE id = ? AND user_id = ?", (project_id, session['user_id'])).fetchone()
    
    if project:
        new_status = 'Paid' if project['status'] == 'Pending' else 'Pending'
        db.execute("UPDATE projects SET status = ? WHERE id = ?", (new_status, project_id))
        db.commit()
        
    db.close()
    return redirect(url_for('dashboard'))

@app.route('/delete_project/<int:project_id>')
def delete_project(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db_connection()
    db.execute("DELETE FROM projects WHERE id = ? AND user_id = ?", (project_id, session['user_id']))
    db.commit()
    db.close()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)