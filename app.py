from datetime import datetime
import calendar as pycalendar
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
# 💡 실제 배포 시에는 무작위 문자열로 바꾸는 것이 좋습니다.
app.secret_key = "chemi_secret_admin_key_1234"

UPLOAD_FOLDER = os.path.join("static", "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_PASSWORD = "chemistry123!"

def get_db_connection():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "database.db")
    conn = sqlite3.connect(db_path)
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    # 아이디어 게시판 테이블
    c.execute("""
    CREATE TABLE IF NOT EXISTS ideas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        writer TEXT,
        content TEXT,
        category TEXT
    )
    """)

    # 댓글 및 이모티콘 테이블
    c.execute("""
    CREATE TABLE IF NOT EXISTS comments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        idea_id INTEGER,
        writer TEXT,
        content TEXT,
        emoticon TEXT,
        FOREIGN KEY(idea_id) REFERENCES ideas(id)
    )
    """)

    # 일정 테이블
    c.execute("""
    CREATE TABLE IF NOT EXISTS calendar(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        title TEXT
    )
    """)

    # 시약 테이블 (초기 생성 시 category 포함)
    c.execute("""
    CREATE TABLE IF NOT EXISTS reagents(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        formula TEXT,
        location TEXT,
        risk TEXT,
        status TEXT,
        category TEXT
    )
    """)
    
    # 사진 테이블
    c.execute("""
    CREATE TABLE IF NOT EXISTS photos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        title TEXT,
        tag TEXT
    )
    """)

    # 팀프로젝트 테이블
    c.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        summary TEXT NOT NULL
    )
    """)
    conn.commit()

    # 예시 시약 데이터 초기화 로직 수정
    reagents = [
        ("염산 (Hydrochloric acid)", "HCl", "산성장 A-01", "위험", "보관중", "산성물질"),
        ("황산 (Sulfuric acid)", "H2SO4", "산성장 A-02", "위험", "보관중", "산성물질"),
        ("질산 (Nitric acid)", "HNO3", "산성장 A-03", "위험", "보관중", "산성물질"),
        ("수산화나트륨 (Sodium hydroxide)", "NaOH", "염기장 B-01", "경고", "보관중", "염기성물질"),
        ("탄산나트륨 (Sodium carbonate)", "Na2CO3", "무기장 C-02", "낮음", "보관중", "무기화합물"),
        ("염화나트륨 (Sodium chloride)", "NaCl", "무기장 C-03", "낮음", "보관중", "무기화합물"),
        ("황산구리 (Copper(II) sulfate)", "CuSO4", "무기장 C-04", "경고", "보관중", "무기화합물"),
        ("산화칼슘 (Calcium oxide)", "CaO", "무기장 C-05", "경고", "보관중", "무기화합물"),
        ("에탄올 (Ethanol)", "C2H5OH", "유기장 D-01", "경고", "보관중", "유기화합물"),
        ("과산화수소 (Hydrogen peroxide)", "H2O2", "유기장 D-02", "위험", "보관중", "유기화합물")
    ]
    
    for r in reagents:
        c.execute("SELECT * FROM reagents WHERE name=?", (r[0],))
        if c.fetchone() is None:
            c.execute("INSERT INTO reagents(name, formula, location, risk, status, category) VALUES(?,?,?,?,?,?)", r)

    conn.commit()
    conn.close()

# 💡 중복되었던 루트 주소 하나로 통합!
@app.route('/')
def home():
    main_photo = "KakaoTalk_20260709_143736435.jpg"
    return render_template("index.html", main_photo=main_photo)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("home"))
        else:
            flash("비밀번호가 일치하지 않습니다!")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("is_admin", None)
    return redirect(url_for("home"))

@app.route("/ideas")
def ideas():
    # 프론트엔드 검색창 및 카테고리 버튼에서 넘겨준 값 받기
    keyword = request.args.get('keyword', '')
    category_filter = request.args.get('category', 'ALL') # 기본값 ALL
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # 동적 SQL 쿼리 작성
    query = "SELECT * FROM ideas WHERE 1=1"
    params = []
    
    # 카테고리 필터링 (ALL이 아닐 때만 조건 추가)
    if category_filter and category_filter != 'ALL':
        query += " AND category = ?"
        params.append(category_filter)
        
    # 키워드 검색 (제목 또는 내용 기준)
    if keyword:
        query += " AND (title LIKE ? OR content LIKE ?)"
        params.extend([f'%{keyword}%', f'%{keyword}%'])
        
    # 최신글 순 정렬
    query += " ORDER BY id DESC"
    
    c.execute(query, params)
    posts = c.fetchall()
    
    ideas_with_comments = []
    for post in posts:
        post_id = post[0]
        c.execute("SELECT id, writer, content, emoticon FROM comments WHERE idea_id = ? ORDER BY id ASC", (post_id,))
        comments = c.fetchall()
        ideas_with_comments.append({
            'id': post[0],
            'title': post[1],
            'writer': post[2],
            'content': post[3],
            'category': post[4] if len(post) > 4 else "IDEA",
            'comments': comments,
            'comment_count': len(comments)
        })
        
    conn.close()
    
    # HTML 화면으로 필터링된 데이터와 상태 정보 전달
    return render_template("ideas.html", 
                           posts=ideas_with_comments, 
                           current_category=category_filter, 
                           keyword=keyword)

@app.route("/calendar")
def calendar():
    now = datetime.now()
    year = request.args.get("year", default=now.year, type=int)
    month = request.args.get("month", default=now.month, type=int)
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1
    start_weekday, total_days = pycalendar.monthrange(year, month)
    empty_cells = (start_weekday + 1) % 7
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, date, title FROM calendar ORDER BY date ASC")
    raw_schedules = c.fetchall()
    
    schedules = []
    for s in raw_schedules:
        schedules.append({
            'id': s[0],
            'date': s[1],
            'title': s[2]
        })
    
    days = []
    for _ in range(empty_cells):
        days.append({"day": "", "schedules": [], "date": ""})
        
    for day in range(1, total_days + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        day_schedules = [s['title'] for s in schedules if s['date'] == date_str]
        days.append({"day": str(day), "schedules": day_schedules, "date": date_str})
        
    c.close()
    conn.close()
    return render_template("calendar.html", year=year, month=month, days=days, schedules=schedules)

@app.route("/addSchedule", methods=["POST"])
def add_schedule():
    if session.get("is_admin"):
        date = request.form.get("date")
        title = request.form.get("title")
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO calendar(date, title) VALUES(?,?)", (date, title))
        conn.commit()
        conn.close()
    return redirect(url_for("calendar"))

@app.route("/deleteSchedule/<int:sid>")
def delete_schedule(sid):
    if session.get("is_admin"):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("DELETE FROM calendar WHERE id=?", (sid,))
        conn.commit()
        conn.close()
    return redirect(url_for("calendar"))

@app.route('/reagent')
def reagent_list():
    keyword = request.args.get('keyword', '')
    category_filter = request.args.get('category_filter', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM reagents WHERE 1=1"
    params = []
    
    if keyword:
        query += " AND (name LIKE ? OR formula LIKE ?)"
        params.extend([f'%{keyword}%', f'%{keyword}%'])
        
    if category_filter:
        query += " AND category = ?"
        params.append(category_filter)
        
    cursor.execute(query, params)
    reagents = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('reagent.html', 
                           reagents=reagents, 
                           keyword=keyword, 
                           selected_category=category_filter)

@app.route("/upload")
def upload():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM photos ORDER BY id DESC")
    photos = c.fetchall()
    conn.close()
    return render_template("upload.html", photos=photos)

@app.route("/uploadPhoto", methods=["POST"])
def upload_photo():
    title = request.form.get("title", "제목 없음")
    tag = request.form.get("tag", "")
    file = request.files.get("photo")
    if file and file.filename != "":
        # 파일명 중복을 방지하기 위해 타임스탬프를 붙여줍니다.
        filename = secure_filename(file.filename)
        unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], unique_filename))
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO photos(filename, title, tag) VALUES(?,?,?)", (unique_filename, title, tag))
        conn.commit()
        conn.close()
    return redirect(url_for("upload"))

@app.route("/deletePhoto/<int:photo_id>")
def delete_photo(photo_id):
    if session.get("is_admin"):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT filename FROM photos WHERE id = ?", (photo_id,))
        row = c.fetchone()
        if row and not row[0].startswith("dummy"):
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], row[0])
            if os.path.exists(filepath):
                os.remove(filepath)
        c.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
        conn.commit()
        conn.close()
    return redirect(url_for("upload"))

@app.route("/projects")
def projects_page():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, summary FROM projects ORDER BY id DESC")
    raw_projects = cursor.fetchall()
    
    projects = []
    for p in raw_projects:
        projects.append({
            'id': p[0],
            'title': p[1],
            'summary': p[2]
        })
    cursor.close()
    conn.close()
    return render_template("projects.html", projects=projects)

@app.route("/addProject", methods=["POST"])
def add_project():
    title = request.form.get("title")
    summary = request.form.get("summary")
    if title and summary:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO projects (title, summary) VALUES (?, ?)", (title, summary))
        conn.commit()
        cursor.close()
        conn.close()
    return redirect(url_for("projects_page"))

@app.route("/deleteProject/<int:project_id>")
def delete_project(project_id):
    if session.get('is_admin'):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
        cursor.close()
        conn.close()
    return redirect(url_for("projects_page"))

# DB 초기화는 앱 실행 전에 한 번만 수행합니다.
init_db()

if __name__ == "__main__":
    app.run(debug=True)
