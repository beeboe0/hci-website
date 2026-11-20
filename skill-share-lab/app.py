import sqlite3
import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, g, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "dev_secret_skillshare_lab_2026"
DATABASE = "skillshare.db"

# ========== 数据库连接管理 ==========
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with open("schema.sql", mode="r", encoding="utf-8") as f:
            sql = f.read()
        db.cursor().executescript(sql)
        db.commit()

def db_tables_exist():
    if not os.path.exists(DATABASE):
        return False
    try:
        temp_db = sqlite3.connect(DATABASE)
        cur = temp_db.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user';")
        res = cur.fetchone()
        temp_db.close()
        return res is not None
    except sqlite3.Error:
        return False

if not db_tables_exist():
    print("=== 正在读取schema.sql初始化数据库 ===")
    init_db()

# ========== 登录校验装饰器 ==========
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrap

# ========== 基础路由 ==========
@app.route('/')
def index():
    return redirect(url_for('rent'))

# ========== 注册 / 登录 ==========
@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        db = get_db()
        try:
            hash_pw = generate_password_hash(password)
            db.execute("INSERT INTO user (username, email, password) VALUES (?,?,?)",
                       (username, email, hash_pw))
            db.commit()
            flash("注册成功，请登录")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("用户名或邮箱已存在")
    return render_template("register.html")

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        db = get_db()
        user = db.execute("SELECT * FROM user WHERE username=?", (username,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("rent"))
        flash("用户名或密码错误")
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))

# ========== 书籍浏览 ==========
@app.route('/rent')
@login_required
def rent():
    db = get_db()
    listings = db.execute("SELECT l.*, u.display_name, u.username FROM listing l JOIN user u ON l.user_id=u.id WHERE l.status='available'").fetchall()
    return render_template("rent.html", listings=listings)

@app.route('/detail/<int:lid>')
@login_required
def detail(lid):
    db = get_db()
    listing = db.execute("SELECT l.*, u.display_name, u.username, u.bio FROM listing l JOIN user u ON l.user_id=u.id WHERE l.id=?", (lid,)).fetchone()
    return render_template("detail.html", listing=listing)

# ========== 当前租借 / 我的发布 / 收藏 ==========
@app.route('/current')
@login_required
def current():
    uid = session["user_id"]
    db = get_db()
    renting = db.execute('''
        SELECT t.*, l.title, l.author, l.return_window 
        FROM "transaction" t JOIN listing l ON t.listing_id=l.id 
        WHERE t.borrower_id=? AND t.type="expense"
    ''', (uid,)).fetchall()
    my_listings = db.execute("SELECT * FROM listing WHERE user_id=?", (uid,)).fetchall()
    bookmarks = db.execute('''
        SELECT b.id as bid, l.* FROM bookmark b JOIN listing l ON b.listing_id=l.id 
        WHERE b.user_id=?
    ''', (uid,)).fetchall()
    return render_template("current.html", renting=renting, my_listings=my_listings, bookmarks=bookmarks)

@app.route('/publish', methods=["GET", "POST"])
@login_required
def publish():
    uid = session["user_id"]
    if request.method == "POST":
        title = request.form["title"].strip()
        author = request.form.get("author", "").strip()
        price = float(request.form["price"])
        return_window = request.form.get("return_window", "").strip()
        subject = request.form.get("subject", "").strip()
        db = get_db()
        db.execute("INSERT INTO listing (user_id, title, author, price, return_window, subject) VALUES (?,?,?,?,?,?)",
                   (uid, title, author, price, return_window, subject))
        db.commit()
        flash("书籍发布成功")
        return redirect(url_for("current"))
    return render_template("publish.html")

@app.route('/rent_now/<int:lid>')
@login_required
def rent_now(lid):
    uid = session["user_id"]
    db = get_db()
    listing = db.execute("SELECT * FROM listing WHERE id=?", (lid,)).fetchone()
    if listing is None or listing["status"] != "available":
        flash("该书籍不可租借")
        return redirect(url_for("rent"))
    lender_id = listing["user_id"]
    price = listing["price"]
    db.execute('INSERT INTO "transaction"(lender_id, borrower_id, listing_id, amount, type) VALUES (?,?,?,?,"income")',
               (lender_id, uid, lid, price))
    db.execute('INSERT INTO "transaction"(lender_id, borrower_id, listing_id, amount, type) VALUES (?,?,?,?,"expense")',
               (lender_id, uid, lid, price))
    db.execute("UPDATE listing SET status='rented' WHERE id=?", (lid,))
    db.commit()
    flash("租借成功")
    return redirect(url_for("current"))

# ========== 历史记录 ==========
@app.route('/history')
@login_required
def history():
    uid = session["user_id"]
    db = get_db()
    lent = db.execute('''
        SELECT t.*, l.title, l.author FROM "transaction" t JOIN listing l ON t.listing_id=l.id 
        WHERE t.lender_id=? AND t.type="income"
    ''', (uid,)).fetchall()
    borrowed = db.execute('''
        SELECT t.*, l.title, l.author FROM "transaction" t JOIN listing l ON t.listing_id=l.id 
        WHERE t.borrower_id=? AND t.type="expense"
    ''', (uid,)).fetchall()
    return render_template("history.html", lent=lent, borrowed=borrowed)

# ========== 财务 ==========
@app.route('/finance')
@login_required
def finance():
    uid = session["user_id"]
    db = get_db()
    income = db.execute('SELECT * FROM "transaction" WHERE lender_id=? AND type="income"', (uid,)).fetchall()
    expense = db.execute('SELECT * FROM "transaction" WHERE borrower_id=? AND type="expense"', (uid,)).fetchall()
    total_income = sum(row["amount"] for row in income)
    total_expense = sum(row["amount"] for row in expense)
    balance = total_income - total_expense
    return render_template("finance.html", income=income, expense=expense, balance=balance)

# ========== 聊天 ==========
@app.route('/chat')
@login_required
def chat():
    return render_template("chat.html")

# ========== 个人资料 ==========
@app.route('/edit_profile', methods=["GET", "POST"])
@login_required
def edit_profile():
    uid = session["user_id"]
    db = get_db()
    user = db.execute("SELECT * FROM user WHERE id=?", (uid,)).fetchone()
    if request.method == "POST":
        display_name = request.form.get("display_name", "")
        bio = request.form.get("bio", "")
        university = request.form.get("university", "")
        birthday = request.form.get("birthday", "")
        year_study = request.form.get("year_study", "")
        db.execute("UPDATE user SET display_name=?, bio=?, university=?, birthday=?, year_study=? WHERE id=?",
                   (display_name, bio, university, birthday, year_study, uid))
        db.commit()
        flash("资料更新成功")
        return redirect(url_for("edit_profile"))
    return render_template("edit_profile.html", user=user)

@app.route('/settings')
@login_required
def settings():
    return render_template("settings.html")

if __name__ == "__main__":
    # use_reloader=False 关闭双进程，防止Windows下SQLite文件损坏
    app.run(debug=True, use_reloader=False)
