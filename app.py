from flask import Flask, render_template,request,session,redirect,url_for
import sqlite3

app = Flask(__name__)
app.secret_key= 'freelance_secret_key' #session(oturum) yönetimi için gerekli

def get_db_connection():
    #ham sql kullanmak için veritabanına bağlanır.
    conn=sqlite3.connect('freelance.db')
    conn.row_factory= sqlite3.Row #verilere isimleri ile erişmeyi sağlar
    return conn

@app.route('/register',methods=['GET', 'POST'])
def register():
    if request.method=="POST":
        username = request.form['username']
        password = request.form['password']

        db = get_db_connection()
        try:
            db.execute("INSERT INTO users (username, password) VALUES (?,?)",(username,password))
            db.commit()
            db.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            db.close()
            return "Username already exists!"

    return render_template('register.html')

@app.route('/login' , methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db_connection()
        user = db.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
        db.close()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials!"

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    db = get_db_connection()
    
    # Sadece kullanıcının projelerini çekiyoruz
    projects = db.execute("SELECT * FROM projects WHERE user_id = ?", (user_id,)).fetchall()
    db.close()
    
    # İş Mantığı (Business Logic): Değerleri Python ile dinamik hesaplıyoruz
    total_revenue = 0
    pending_payments = 0
    
    for project in projects:
        if project['status'] == 'Paid':
            total_revenue += project['budget']
        elif project['status'] == 'Pending':
            pending_payments += project['budget']
    
    # Verileri şablona gönderiyoruz
    return render_template('dashboard.html', projects=projects, total_revenue=total_revenue, pending_payments=pending_payments)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/add_project', methods=['GET', 'POST'])
def app_project():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        client_name = request.form['client_name']
        project_title = request.form['project_title']
        budget_raw = request.form['budget']
        deadline = request.form.get('deadline')
        user_id = session['user_id'] # Projeyi giriş yapan kişiye bağlıyoruz

        # Kabul Kriteri Güvencesi: Eksik veri kontrolü
        if not client_name or not project_title or not budget_raw or not deadline:
            flash("Warning: All fields are mandatory!")
            return redirect(url_for('add_project'))

        try:
            budget = float(budget_raw)
            if budget <=0:
                return "Error: Budget must be a positive numerical value!",400
        
        except ValueError:
            return "Error: Budget must be a valid number!",400

        db = get_db_connection()
        db.execute("INSERT INTO projects (user_id, client_name, project_title, budget, deadline) VALUES (?,?,?,?,?)", (user_id,client_name,project_title,budget, deadline))
        db.commit()
        db.close()

        return redirect(url_for('dashboard'))

    return render_template('add_project.html')

@app.route('/delete_project/<int:project_id>')
def delete_project(project_id):
    #güvenlik kontrolü, eğer giriş yapılmadıysa login sayfasına yönlendirir.
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    db = get_db_connection()

    # Güvenlik önlemi: Sadece giriş yapan kullanıcıya ait olan projeyi sil (SQL injection ve yetki aşımı koruması)
    db.execute("DELETE FROM projects WHERE id = ? AND user_id = ?", (project_id, user_id))
    db.commit()
    db.close()
    
    # Silme işleminden sonra güncel listeyi görmesi için dashboard'a geri yönlendiriyoruz
    return redirect(url_for('dashboard'))

@app.route('/edit_project/<int:project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    db = get_db_connection()

    # Önce düzenlenmek istenen projeyi çekiyoruz (ve kullanıcının kendi projesi mi diye bakıyoruz)
    project = db.execute("SELECT * FROM projects WHERE id = ? AND user_id = ?", (project_id, user_id)).fetchone()

    if not project:
        db.close()
        return "Project not found or unauthorized!",404

    if request.method == 'POST':
        client_name = request.form.get('client_name')
        project_title = request.form.get('project_title')
        budget_raw = request.form.get('budget')
        deadline = request.form.get('deadline')

        # İş Mantığı Kriteri: Eksik alan kontrolü
        if not client_name or not project_title or not budget_raw or not deadline:
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

        # Ham SQL ile veritabanını güncelliyoruz (CRUD - Update)
        db.execute("""
            UPDATE projects 
            SET client_name = ?, project_title = ?, budget = ?, deadline = ? 
            WHERE id = ? AND user_id = ?
        """, (client_name, project_title, budget, deadline, project_id, user_id))
        
        db.commit()
        db.close()
        return redirect(url_for('dashboard'))

    db.close()
    return render_template('edit_project.html', project=project)


@app.route('/toggle_status/<int:project_id>')
def toggle_status(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    db = get_db_connection()
    
    # Güvenlik Kontrolü: Projenin gerçekten bu kullanıcıya ait olduğundan emin oluyoruz
    project = db.execute("SELECT status FROM projects WHERE id = ? AND user_id = ?", (project_id, user_id)).fetchone()
    
    if project:
        # Durum Pending ise Paid, Paid ise Pending yapıyoruz
        new_status = 'Paid' if project['status'] == 'Pending' else 'Pending'
        
        # Ham SQL ile durumu güncelliyoruz
        db.execute("UPDATE projects SET status = ? WHERE id = ? AND user_id = ?", (new_status, project_id, user_id))
        
        # Değişiklikleri veritabanına mühürlüyoruz
        db.commit()
        
    db.close()
    
    # Güncel durumu görmesi için dashboard'a geri yönlendiriyoruz
    return redirect(url_for('dashboard'))

if __name__=="__main__":
    app.run(debug=True)
