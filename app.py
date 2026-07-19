import os
import csv
import io
from datetime import datetime
import calendar as pycalendar
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import cloudinary
import cloudinary.uploader

# ==============================================================
# ☁️ 1. Cloudinary 공식 영구 저장소 보안 세팅
# ==============================================================
cloudinary.config(
    cloud_name = "keflcpmi",
    api_key = "833587119529933",
    api_secret = "FSsEX_w_Mnf_Ri__wsZ6Wdi_sRw"
)

app = Flask(__name__)
app.secret_key = "chemi_secret_admin_key_1234"
ADMIN_PASSWORD = "chemi3542s!"

# ==============================================================
# 🗄️ 2. Supabase(PostgreSQL) 클라우드 연결 세팅
# ==============================================================
SUPABASE_DATABASE_URL = "postgresql+psycopg2://postgres.etdfporsnhyhqguuqkqd:ehqhr0843!!@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

app.config['SQLALCHEMY_DATABASE_URI'] = SUPABASE_DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==============================================================
# 📐 3. 데이터베이스 모델 (테이블) 정의
# ==============================================================
class Idea(db.Model):
    __tablename__ = 'ideas'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    writer = db.Column(db.String(100))
    content = db.Column(db.Text)
    category = db.Column(db.String(50), default="just")
    comments = db.relationship('Comment', backref='idea', cascade="all, delete-orphan", lazy=True)

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    idea_id = db.Column(db.Integer, db.ForeignKey('ideas.id'), nullable=False)
    writer = db.Column(db.String(100))
    content = db.Column(db.Text)
    emoticon = db.Column(db.String(50))

class Calendar(db.Model):
    __tablename__ = 'calendar'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(50))
    title = db.Column(db.String(200))

class Reagent(db.Model):
    __tablename__ = 'reagents'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    formula = db.Column(db.String(100))
    amount = db.Column(db.String(50), default="1개")  # 수량(amount) 칼럼
    location = db.Column(db.String(100))
    risk = db.Column(db.String(50))
    status = db.Column(db.String(50), default="보관중")
    category = db.Column(db.String(100), default="일반시약")

class Photo(db.Model):
    __tablename__ = 'photos'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.Text)
    title = db.Column(db.String(200))
    tag = db.Column(db.String(100))

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text, nullable=False)

class Notice(db.Model):
    __tablename__ = 'notices'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    reg_date = db.Column(db.String(50))

# 데이터베이스 안심 초기화 기능 (구조 불일치 해결 핵심 구역)
def init_supabase_db():
    try:
        # 1. 먼저 테이블 생성을 시도합니다.
        db.create_all()
        # 테스트 쿼리를 날려 amount 컬럼이 진짜 잘 작동하는지 검사합니다.
        db.session.execute(text("SELECT amount FROM reagents LIMIT 1;"))
    except Exception as e:
        # 2. 만약 에러가 난다면 옛날 구조와 충돌한 것이므로 롤백 후 reagents 테이블만 새로 고칩니다.
        print("테이블 구조 불일치 감지! 재재배포 및 자동 동기화를 진행합니다:", e)
        db.session.rollback()
        try:
            db.session.execute(text("DROP TABLE IF EXISTS reagents CASCADE;"))
            db.session.commit()
            db.create_all()  # 새 구조(amount 포함)로 완전 재 생성
        except Exception as ex:
            db.session.rollback()
            print("강제 테이블 리셋 실패, 에러 무시 후 진행합니다:", ex)
        
    # 기본 시약 데이터 세팅 (비어있을 때만 최초 1회 실행)
    try:
        if Reagent.query.count() == 0:
            reagents_list = [
                Reagent(name="염산 (Hydrochloric acid)", formula="HCl", amount="1개", location="산성장 A-01", risk="위험", status="보관중", category="위험성물질"),
                Reagent(name="황산 (Sulfuric acid)", formula="H2SO4", amount="1개", location="산성장 A-02", risk="위험", status="보관중", category="위험성물질"),
                Reagent(name="질산 (Nitric acid)", formula="HNO3", amount="1개", location="산성장 A-03", risk="위험", status="보관중", category="위험성물질"),
                Reagent(name="수산화나트륨 (Sodium hydroxide)", formula="NaOH", amount="1개", location="염기장 B-01", risk="경고", status="보관중", category="염기성물질"),
                Reagent(name="탄산나트륨 (Sodium carbonate)", formula="Na2CO3", amount="1개", location="무기장 C-02", risk="낮음", status="보관중", category="무기화합물"),
                Reagent(name="염화나트륨 (Sodium chloride)", formula="NaCl", amount="1개", location="무기장 C-03", risk="낮음", status="보관중", category="무기화합물"),
                Reagent(name="황산구리 (Copper(II) sulfate)", formula="CuSO4", amount="1개", location="무기장 C-04", risk="경고", status="보관중", category="무기화합물"),
                Reagent(name="산화칼슘 (Calcium oxide)", formula="CaO", amount="1개", location="무기장 C-05", risk="경고", status="보관중", category="무기화합물"),
                Reagent(name="에탄올 (Ethanol)", formula="C2H5OH", amount="1개", location="유기장 D-01", risk="경고", status="보관중", category="유기화합물"),
                Reagent(name="과산화수소 (Hydrogen peroxide)", formula="H2O2", amount="1개", location="유기장 D-02", risk="위험", status="보관중", category="유기화합물")
            ]
            db.session.bulk_save_objects(reagents_list)
            db.session.commit()
    except Exception:
        db.session.rollback()

# ==============================================================
# 🛣️ 4. 라우터 및 비즈니스 로직
# ==============================================================

@app.route('/')
def home():
    main_photo = "KakaoTalk_20260709_143736435.jpg"
    notice = Notice.query.order_by(Notice.id.desc()).first()
    return render_template("index.html", main_photo=main_photo, notice=notice)

@app.route("/addNotice", methods=["POST"])
def add_notice():
    if session.get("is_admin"):
        content = request.form.get("content", "").strip()
        if content:
            new_notice = Notice(content=content, reg_date=datetime.now().strftime("%Y-%m-%d %H:%M"))
            db.session.add(new_notice)
            db.session.commit()
    return redirect(url_for("home"))

@app.route("/deleteNotice/<int:nid>")
def delete_notice(nid):
    if session.get("is_admin"):
        notice = Notice.query.get(nid)
        if notice:
            db.session.delete(notice)
            db.session.commit()
    return redirect(url_for("home"))

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
    posts = Idea.query.order_by(Idea.id.desc()).all()
    ideas_with_comments = []
    for post in posts:
        ideas_with_comments.append({
            'id': post.id,
            'title': post.title,
            'writer': post.writer,
            'content': post.content,
            'category': post.category if post.category else "just",
            'comments': [(c.id, c.writer, c.content, c.emoticon) for c in post.comments],
            'comment_count': len(post.comments)
        })
    return render_template("ideas.html", posts=ideas_with_comments)

@app.route("/addIdea", methods=["POST"])
def addIdea():
    title = request.form.get("title", "")
    writer = request.form.get("writer", "익명")
    content = request.form.get("content", "")
    category = request.form.get("category", "just")
    
    new_idea = Idea(title=title, writer=writer, content=content, category=category)
    db.session.add(new_idea)
    db.session.commit()
    return redirect(url_for("ideas"))

@app.route("/addComment", methods=["POST"])
def addComment():
    idea_id = request.form.get("idea_id")
    writer = request.form.get("writer", "익명")
    content = request.form.get("content", "")
    emoticon = request.form.get("emoticon", "")
    
    new_comment = Comment(idea_id=idea_id, writer=writer, content=content, emoticon=emoticon)
    db.session.add(new_comment)
    db.session.commit()
    return redirect(url_for("ideas"))

@app.route("/deleteIdea/<int:idea_id>")
def delete_idea(idea_id):
    if session.get("is_admin"):
        post = Idea.query.get(idea_id)
        if post:
            db.session.delete(post)
            db.session.commit()
    return redirect(url_for("ideas"))

@app.route("/deleteComment/<int:comment_id>")
def delete_comment(comment_id):
    if session.get("is_admin"):
        comment = Comment.query.get(comment_id)
        if comment:
            db.session.delete(comment)
            db.session.commit()
    return redirect(url_for("ideas"))

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
    
    raw_schedules = Calendar.query.order_by(Calendar.date.asc()).all()
    schedules = [{'id': s.id, 'date': s.date, 'title': s.title} for s in raw_schedules]
    
    days = []
    for _ in range(empty_cells):
        days.append({"day": "", "schedules": [], "date": ""})
        
    for day in range(1, total_days + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        day_schedules = [s['title'] for s in schedules if s['date'] == date_str]
        days.append({"day": str(day), "schedules": day_schedules, "date": date_str})
        
    return render_template("calendar.html", year=year, month=month, days=days, schedules=schedules)

@app.route("/addSchedule", methods=["POST"])
def add_schedule():
    if session.get("is_admin"):
        date = request.form.get("date")
        title = request.form.get("title")
        new_schedule = Calendar(date=date, title=title)
        db.session.add(new_schedule)
        db.session.commit()
    return redirect(url_for("calendar"))

@app.route("/deleteSchedule/<int:sid>")
def delete_schedule(sid):
    if session.get("is_admin"):
        sch = Calendar.query.get(sid)
        if sch:
            db.session.delete(sch)
            db.session.commit()
    return redirect(url_for("calendar"))

# 🧪 5. 시약 관리 (SQLAlchemy 연동 통합 완료)
@app.route('/reagent')
def reagent_list():
    keyword = request.args.get('keyword', '')
    category_filter = request.args.get('category_filter', '')
    
    query = Reagent.query
    if keyword:
        query = query.filter((Reagent.name.like(f'%{keyword}%')) | (Reagent.formula.like(f'%{keyword}%')))
    if category_filter:
        query = query.filter(Reagent.category == category_filter)
        
    try:
        reagents = query.order_by(Reagent.name.asc()).all()
    except Exception:
        db.session.rollback()
        reagents = []
    return render_template('reagent.html', reagents=reagents, keyword=keyword, selected_category=category_filter)

@app.route('/addReagent', methods=['POST'])
def add_reagent():
    name = request.form.get('name')
    formula = request.form.get('formula')
    amount = request.form.get('amount', '1개')
    category = request.form.get('category', '일반시약')
    location = request.form.get('location')
    risk = request.form.get('danger', '낮음')  
    status = request.form.get('status', '보관중')
    
    if name:
        new_reagent = Reagent(name=name, formula=formula, amount=amount, location=location, risk=risk, status=status, category=category)
        db.session.add(new_reagent)
        db.session.commit()
    return redirect(url_for('reagent_list'))

@app.route('/editReagent', methods=['POST'])
def edit_reagent():
    if session.get("is_admin"):
        rid = request.form.get('id')
        reagent = Reagent.query.get(rid)
        if reagent:
            reagent.name = request.form.get('name')
            reagent.formula = request.form.get('formula')
            reagent.amount = request.form.get('amount', '1개')
            reagent.category = request.form.get('category')
            reagent.location = request.form.get('location')
            reagent.risk = request.form.get('danger')
            reagent.status = request.form.get('status')
            db.session.commit()
    return redirect(url_for('reagent_list'))

@app.route("/deleteReagent/<int:reagent_id>")
def delete_reagent(reagent_id):
    if session.get("is_admin"):
        reagent = Reagent.query.get(reagent_id)
        if reagent:
            db.session.delete(reagent)
            db.session.commit()
    return redirect(url_for("reagent_list"))

@app.route('/uploadReagentExcel', methods=['POST'])
def upload_reagent_excel():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "파일이 전송되지 않았습니다."})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "선택된 파일이 없습니다."})
        
    try:
        stream = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
        csv_input = csv.reader(stream)
        
        for i, row in enumerate(csv_input):
            if i == 0 or not row or len(row) < 2: 
                continue
                
            name = row[0].strip()
            formula = row[1].strip()
            amount = row[2].strip() if len(row) > 2 else "1개"
            category = row[3].strip() if len(row) > 3 else "일반시약"
            location = row[4].strip() if len(row) > 4 else "1층"
            risk = row[5].strip() if len(row) > 5 else "낮음"
            status = row[6].strip() if len(row) > 6 else "보관중"
            
            new_reagent = Reagent(name=name, formula=formula, amount=amount, category=category, location=location, risk=risk, status=status)
            db.session.add(new_reagent)
            
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

# ==============================================================
# 📷 6. 사진 및 프로젝트 관리
# ==============================================================
@app.route("/upload", methods=["GET", "POST"])
def upload():
    photos_list = Photo.query.order_by(Photo.id.desc()).all()
    photos = [(p.id, p.filename, p.title, p.tag) for p in photos_list]
    return render_template("upload.html", photos=photos)

@app.route("/uploadPhoto", methods=["POST"])
def upload_photo():
    title = request.form.get("title", "제목 없음")
    tag = request.form.get("tag", "")
    file = request.files.get("photo")
    
    if not file or file.filename == "":
        flash("업로드할 파일을 선택해 주세요.")
        return redirect(url_for("upload"))
        
    try:
        upload_result = cloudinary.uploader.upload(file, options={"quality": "auto", "fetch_format": "auto"})
        image_url = upload_result.get("secure_url")
        
        new_photo = Photo(filename=image_url, title=title, tag=tag)
        db.session.add(new_photo)
        db.session.commit()
        flash("성공적으로 클라우드에 사진이 저장되었습니다! 🚀")
        
    except Exception as e:
        print("Cloudinary 전송 에러:", e)
        flash("사진 업로드 중 오류가 발생했습니다.")
        
    return redirect(url_for("upload"))

@app.route("/deletePhoto/<int:photo_id>")
def delete_photo(photo_id):
    if session.get("is_admin"):
        pt = Photo.query.get(photo_id)
        if pt:
            db.session.delete(pt)
            db.session.commit()
    return redirect(url_for("upload"))

@app.route("/projects")
def projects_page():
    raw_projects = Project.query.order_by(Project.id.desc()).all()
    projects = [{'id': p.id, 'title': p.title, 'summary': p.summary} for p in raw_projects]
    return render_template("projects.html", projects=projects)

@app.route("/addProject", methods=["POST"])
def add_project():
    title = request.form.get("title")
    summary = request.form.get("summary")
    if title and summary:
        new_project = Project(title=title, summary=summary)
        db.session.add(new_project)
        db.session.commit()
    return redirect(url_for("projects_page"))

@app.route("/deleteProject/<int:project_id>")
def delete_project(project_id):
    if session.get('is_admin'):
        pj = Project.query.get(project_id)
        if pj:
            db.session.delete(pj)
            db.session.commit()
    return redirect(url_for("projects_page"))

if __name__ == "__main__":
    with app.app_context():
        init_supabase_db()
    app.run(debug=True)
