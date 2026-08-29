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
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "keflcpmi"),
    api_key = os.environ.get("CLOUDINARY_API_KEY", "833587119529933"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET", "FSsEX_w_Mnf_Ri__wsZ6Wdi_sRw")
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chemi_secret_admin_key_1234")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "chemi3542s!")

# ==============================================================
# 🗄️ 2. Supabase(PostgreSQL) 클라우드 연결 세팅
# ==============================================================
SUPABASE_DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql+psycopg2://postgres.etdfporsnhyhqguuqkqd:ehqhr0843!!@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"
)

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
    date = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    applicant = db.Column(db.String(100), default="익명")  
    purpose = db.Column(db.Text, default="")            
    status = db.Column(db.String(50), default="승인 대기 중")

class Reagent(db.Model):
    __tablename__ = 'reagents'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    formula = db.Column(db.String(100))
    location = db.Column(db.String(100))
    amount = db.Column(db.String(50), default="1개")  
    risk = db.Column(db.String(50), default="낮음")
    status = db.Column(db.String(50), default="보관중")
    note = db.Column(db.String(200), default="")

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

# 데이터베이스 및 테이블 자동 보정 함수 (안전 모드)
def init_supabase_db():
    with app.app_context():
        try:
            db.create_all()
            
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS notices (
                    id SERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    reg_date VARCHAR(50)
                );
            """))
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS calendar (
                    id SERIAL PRIMARY KEY,
                    date VARCHAR(50),
                    title VARCHAR(200),
                    applicant VARCHAR(100),
                    purpose TEXT,
                    status VARCHAR(50) DEFAULT '승인 대기 중'
                );
            """))
            db.session.execute(text("ALTER TABLE calendar ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT '승인 대기 중';"))
            db.session.execute(text("ALTER TABLE calendar ADD COLUMN IF NOT EXISTS applicant VARCHAR(100) DEFAULT '익명';"))
            db.session.execute(text("ALTER TABLE calendar ADD COLUMN IF NOT EXISTS purpose TEXT DEFAULT '';"))
            db.session.commit()
        except Exception as e:
            print("DB 자동 보정 중 예외 발생:", e)
            db.session.rollback()

        try:
            if Reagent.query.count() == 0:
                reagents_list = [
                    Reagent(name="염산 (Hydrochloric acid)", formula="HCl", location="산성장 A-01", amount="1개", risk="위험", status="보관중", note=""),
                    Reagent(name="황산 (Sulfuric acid)", formula="H2SO4", location="산성장 A-02", amount="1개", risk="위험", status="보관중", note=""),
                    Reagent(name="질산 (Nitric acid)", formula="HNO3", location="산성장 A-03", amount="1개", risk="위험", status="보관중", note=""),
                    Reagent(name="수산화나트륨 (Sodium hydroxide)", formula="NaOH", location="염기장 B-01", amount="1개", risk="경고", status="보관중", note=""),
                    Reagent(name="탄산나트륨 (Sodium carbonate)", formula="Na2CO3", location="무기장 C-02", amount="1개", risk="낮음", status="보관중", note=""),
                    Reagent(name="염화나트륨 (Sodium chloride)", formula="NaCl", location="무기장 C-03", amount="1개", risk="낮음", status="보관중", note=""),
                    Reagent(name="황산구리 (Copper(II) sulfate)", formula="CuSO4", location="무기장 C-04", amount="1개", risk="경고", status="보관중", note=""),
                    Reagent(name="산화칼슘 (Calcium oxide)", formula="CaO", location="무기장 C-05", amount="1개", risk="경고", status="보관중", note=""),
                    Reagent(name="에탄올 (Ethanol)", formula="C2H5OH", location="유기장 D-01", amount="1개", risk="경고", status="보관중", note=""),
                    Reagent(name="과산화수소 (Hydrogen peroxide)", formula="H2O2", location="유기장 D-02", amount="1개", risk="위험", status="보관중", note="")
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
    try:
        notices = Notice.query.order_by(Notice.id.desc()).all()
    except Exception:
        db.session.rollback()
        notices = []
    return render_template("index.html", main_photo=main_photo, notices=notices)

@app.route("/addNotice", methods=["POST"])
def add_notice():
    if session.get("is_admin"):
        content = request.form.get("content", "").strip()
        if content:
            try:
                new_notice = Notice(content=content, reg_date=datetime.now().strftime("%Y-%m-%d %H:%M"))
                db.session.add(new_notice)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print("공지사항 추가 오류:", e)
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
    
    try:
        raw_schedules = Calendar.query.order_by(Calendar.date.asc()).all()
    except Exception as e:
        print("캘린더 조회 오류:", e)
        db.session.rollback()
        raw_schedules = []

    schedules = [{
        'id': s.id, 
        'date': s.date, 
        'title': s.title, 
        'applicant': s.applicant if s.applicant else "익명", 
        'purpose': s.purpose if s.purpose else "",
        'status': s.status if s.status else "승인 대기 중"
    } for s in raw_schedules]
    
    days = []
    for _ in range(empty_cells):
        days.append({"day": "", "schedules": [], "date": ""})
        
    for day in range(1, total_days + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        day_schedules = [s for s in schedules if s['date'] == date_str]
        days.append({"day": str(day), "schedules": day_schedules, "date": date_str})
        
    # 동아리 공식 일정은 해당 월에만 뜨고, 실험실 예약 등은 월과 상관없이 전체 다 뜨도록 설정
    display_schedules = []
    for s in schedules:
        if s['status'] == "동아리 공식 일정":
            try:
                s_year, s_month, _ = map(int, s['date'].split('-'))
                if s_year == year and s_month == month:
                    display_schedules.append(s)
            except:
                pass
        else:
            display_schedules.append(s)
        
    return render_template("calendar.html", year=year, month=month, days=days, schedules=display_schedules)

@app.route("/addSchedule", methods=["POST"])
def add_schedule():
    date = request.form.get("date")
    title = request.form.get("title")
    applicant = request.form.get("applicant", "익명")
    purpose = request.form.get("purpose", "")
    
    is_admin_action = session.get("is_admin", False)
    
    if date and title:
        try:
            status_val = "동아리 공식 일정" if is_admin_action else "승인 대기 중"
            if is_admin_action and (not applicant or applicant == "익명"):
                applicant = "동아리 관리자"
                
            new_schedule = Calendar(date=date, title=title, applicant=applicant, purpose=purpose, status=status_val)
            db.session.add(new_schedule)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print("일정 추가 중 데이터베이스 오류 발생:", e)
    return redirect(url_for("calendar"))

@app.route("/approveSchedule/<int:sid>")
def approve_schedule(sid):
    if session.get("is_admin"):
        try:
            sch = Calendar.query.get(sid)
            if sch:
                sch.status = "승인 완료"
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print("일정 승인 오류:", e)
    return redirect(url_for("calendar"))

@app.route("/deleteSchedule/<int:sid>")
def delete_schedule(sid):
    if session.get("is_admin"):
        try:
            sch = Calendar.query.get(sid)
            if sch:
                db.session.delete(sch)
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print("일정 삭제 오류:", e)
    return redirect(url_for("calendar"))

# ==============================================================
# 🧪 5. 시약 관리
# ==============================================================
@app.route('/reagent')
def reagent_list():
    keyword = request.args.get('keyword', '')
    
    query = Reagent.query
    if keyword:
        query = query.filter((Reagent.name.like(f'%{keyword}%')) | (Reagent.formula.like(f'%{keyword}%')))
        
    try:
        reagents = query.order_by(Reagent.name.asc()).all()
    except Exception:
        db.session.rollback()
        reagents = []
    return render_template('reagent.html', reagents=reagents, keyword=keyword)

@app.route('/addReagent', methods=['POST'])
def add_reagent():
    name = request.form.get('name')
    formula = request.form.get('formula', '')
    location = request.form.get('location')
    amount = request.form.get('amount', '1개')
    risk = request.form.get('risk') or request.form.get('danger') or '낮음'  
    status = request.form.get('status', '보관중')
    note = request.form.get('note', '')
    
    if name and location:
        new_reagent = Reagent(
            name=name, formula=formula, location=location, 
            amount=amount, risk=risk, status=status, note=note
        )
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
            reagent.formula = request.form.get('formula', '')
            reagent.location = request.form.get('location')
            reagent.amount = request.form.get('amount', '1개')
            reagent.risk = request.form.get('risk') or request.form.get('danger') or '낮음'
            reagent.status = request.form.get('status', '보관중')
            reagent.note = request.form.get('note', '')
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

@app.route("/deleteAllReagents")
def delete_all_reagents():
    if session.get("is_admin"):
        try:
            db.session.query(Reagent).delete()
            db.session.commit()
        except Exception:
            db.session.rollback()
    return redirect(url_for("reagent_list"))

@app.route('/uploadReagentExcel', methods=['POST'])
def upload_reagent_excel():
    if not session.get("is_admin"):
        return jsonify({"success": False, "message": "관리자 권한이 필요합니다."})

    if 'file' not in request.files:
        return jsonify({"success": False, "message": "파일이 전송되지 않았습니다."})
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "선택된 파일이 없습니다."})
        
    try:
        raw_bytes = file.stream.read()
        try:
            decoded_text = raw_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            decoded_text = raw_bytes.decode("cp949")

        stream = io.StringIO(decoded_text, newline=None)
        csv_input = csv.reader(stream)
        
        count = 0
        for i, row in enumerate(csv_input):
            if i == 0 or not row or len(row) < 1: 
                continue
                
            name = row[0].strip() if len(row) > 0 else ""
            if not name:
                continue
                
            formula = row[1].strip() if len(row) > 1 else ""
            location = row[2].strip() if len(row) > 2 else ""
            amount = row[3].strip() if len(row) > 3 else "1개"
            risk = row[4].strip() if len(row) > 4 else "낮음"
            status = row[5].strip() if len(row) > 5 else "보관중"
            note = row[6].strip() if len(row) > 6 else ""
            
            new_reagent = Reagent(
                name=name, formula=formula, location=location, 
                amount=amount, risk=risk, status=status, note=note
            )
            db.session.add(new_reagent)
            count += 1
            
        db.session.commit()
        return jsonify({"success": True, "message": f"{count}개의 시약 항목이 성공적으로 등록되었습니다!"})
    except Exception as e:
        db.session.rollback()
        err_msg = str(e) if str(e) else "파일 데이터 처리 중 오류가 발생했습니다."
        return jsonify({"success": False, "message": err_msg})

# ==============================================================
# 📷 6. 사진 및 프로젝트 관리
# ==============================================================
@app.route("/upload", methods=["GET", "POST"])
def upload():
    try:
        photos_list = Photo.query.order_by(Photo.id.desc()).all()
    except Exception:
        db.session.rollback()
        photos_list = []
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
    try:
        raw_projects = Project.query.order_by(Project.id.desc()).all()
    except Exception:
        db.session.rollback()
        raw_projects = []
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
    init_supabase_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
    
