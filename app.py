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
# ☁️ 1. Cloudinary 공식 영구 저장소 세팅
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
# 📋 3. DB 모델 클래스 정의
# ==============================================================
class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Idea(db.Model):
    __tablename__ = 'ideas'
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    comments = db.relationship('IdeaComment', backref='idea', cascade='all, delete-orphan', lazy=True)

class IdeaComment(db.Model):
    __tablename__ = 'idea_comments'
    id = db.Column(db.Integer, primary_key=True)
    idea_id = db.Column(db.Integer, db.ForeignKey('ideas.id', ondelete='CASCADE'), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    emoticon = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Calendar(db.Model):
    __tablename__ = 'calendar'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(255), nullable=False)

class Reagent(db.Model):
    __tablename__ = 'reagents'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    formula = db.Column(db.String(255), nullable=True)
    amount = db.Column(db.String(100), nullable=True, default='1개')
    category = db.Column(db.String(100), nullable=True, default='일반시약')
    location = db.Column(db.String(255), nullable=False)
    risk = db.Column(db.String(50), nullable=True, default='낮음')
    status = db.Column(db.String(100), nullable=True, default='보관중')

class Photo(db.Model):
    __tablename__ = 'photos'
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.Text, nullable=False)
    caption = db.Column(db.Text, nullable=True)
    tags = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

with app.app_context():
    db.create_all()

# ==============================================================
# 🌐 4. 라우트 및 비즈니스 로직
# ==============================================================
@app.route("/")
def index():
    announcements = Announcement.query.order_by(Announcement.id.desc()).all()
    return render_template("index.html", announcements=announcements)

@app.route("/addNotice", methods=["POST"])
def add_notice():
    if session.get("is_admin"):
        title = request.form.get("title")
        content = request.form.get("content")
        if title and content:
            ann = Announcement(title=title, content=content)
            db.session.add(ann)
            db.session.commit()
    return redirect(url_for("index"))

@app.route("/deleteNotice/<int:notice_id>")
def delete_notice(notice_id):
    if session.get("is_admin"):
        ann = Announcement.query.get(notice_id)
        if ann:
            db.session.delete(ann)
            db.session.commit()
    return redirect(url_for("index"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("index"))
        else:
            flash("비밀번호가 올바르지 않습니다.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("is_admin", None)
    return redirect(url_for("index"))

@app.route("/ideas")
def ideas():
    all_ideas = Idea.query.order_by(Idea.id.desc()).all()
    return render_template("ideas.html", ideas=all_ideas)

@app.route("/addIdea", methods=["POST"])
def add_idea():
    author = request.form.get("author")
    content = request.form.get("content")
    if author and content:
        new_idea = Idea(author=author, content=content)
        db.session.add(new_idea)
        db.session.commit()
    return redirect(url_for("ideas"))

@app.route("/deleteIdea/<int:idea_id>")
def delete_idea(idea_id):
    if session.get("is_admin"):
        idea = Idea.query.get(idea_id)
        if idea:
            db.session.delete(idea)
            db.session.commit()
    return redirect(url_for("ideas"))

@app.route("/addComment/<int:idea_id>", methods=["POST"])
def add_comment(idea_id):
    author = request.form.get("author")
    content = request.form.get("content")
    emoticon = request.form.get("emoticon")
    if author and content:
        comment = IdeaComment(idea_id=idea_id, author=author, content=content, emoticon=emoticon)
        db.session.add(comment)
        db.session.commit()
    return redirect(url_for("ideas"))

@app.route("/deleteComment/<int:comment_id>")
def delete_comment(comment_id):
    if session.get("is_admin"):
        comment = IdeaComment.query.get(comment_id)
        if comment:
            db.session.delete(comment)
            db.session.commit()
    return redirect(url_for("ideas"))

@app.route("/calendar")
def calendar():
    year = request.args.get("year", datetime.now().year, type=int)
    month = request.args.get("month", datetime.now().month, type=int)
    
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1

    cal = pycalendar.monthcalendar(year, month)
    schedules = Calendar.query.all()
    
    schedule_dict = {}
    for s in schedules:
        schedule_dict.setdefault(s.date, []).append(s.title)

    days = []
    for week in cal:
        for day in week:
            if day == 0:
                days.append({"day": None, "schedules": []})
            else:
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                days.append({"day": day, "schedules": schedule_dict.get(date_str, [])})

    return render_template("calendar.html", year=year, month=month, days=days, schedules=schedules)

@app.route("/addSchedule", methods=["POST"])
def add_schedule():
    if session.get("is_admin"):
        date = request.form.get("date")
        title = request.form.get("title")
        if date and title:
            sch = Calendar(date=date, title=title)
            db.session.add(sch)
            db.session.commit()
    return redirect(url_for("calendar"))

@app.route("/deleteSchedule/<int:schedule_id>")
def delete_schedule(schedule_id):
    if session.get("is_admin"):
        sch = Calendar.query.get(schedule_id)
        if sch:
            db.session.delete(sch)
            db.session.commit()
    return redirect(url_for("calendar"))

@app.route("/reagent")
def reagent():
    query = request.args.get("q", "").strip()
    if query:
        reagents = Reagent.query.filter(
            (Reagent.name.ilike(f"%{query}%")) | (Reagent.location.ilike(f"%{query}%"))
        ).all()
    else:
        reagents = Reagent.query.all()
    return render_template("reagent.html", reagents=reagents, query=query)

@app.route("/addReagent", methods=["POST"])
def add_reagent():
    if session.get("is_admin"):
        name = request.form.get("name")
        formula = request.form.get("formula")
        amount = request.form.get("amount")
        category = request.form.get("category")
        location = request.form.get("location")
        risk = request.form.get("risk")
        status = request.form.get("status")
        if name and location:
            rg = Reagent(
                name=name, formula=formula, amount=amount,
                category=category, location=location, risk=risk, status=status
            )
            db.session.add(rg)
            db.session.commit()
    return redirect(url_for("reagent"))

@app.route("/editReagent", methods=["POST"])
def edit_reagent():
    if session.get("is_admin"):
        rg_id = request.form.get("id")
        rg = Reagent.query.get(rg_id)
        if rg:
            rg.name = request.form.get("name")
            rg.formula = request.form.get("formula")
            rg.amount = request.form.get("amount")
            rg.category = request.form.get("category")
            rg.location = request.form.get("location")
            rg.risk = request.form.get("risk")
            rg.status = request.form.get("status")
            db.session.commit()
    return redirect(url_for("reagent"))

@app.route("/deleteReagent/<int:reagent_id>")
def delete_reagent(reagent_id):
    if session.get("is_admin"):
        rg = Reagent.query.get(reagent_id)
        if rg:
            db.session.delete(rg)
            db.session.commit()
    return redirect(url_for("reagent"))

@app.route("/uploadReagentExcel", methods=["POST"])
def upload_reagent_excel():
    if not session.get("is_admin"):
        return jsonify({"success": False, "message": "관리자 권한이 필요합니다."})
    
    file = request.files.get("file")
    if not file:
        return jsonify({"success": False, "message": "파일이 선택되지 않았습니다."})
    
    try:
        stream = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
        csv_input = csv.reader(stream)
        
        count = 0
        for row in csv_input:
            if not row or len(row) < 2:
                continue
            name = row[0].strip()
            formula = row[1].strip() if len(row) > 1 else ""
            amount = row[2].strip() if len(row) > 2 else "1개"
            category = row[3].strip() if len(row) > 3 else "일반시약"
            location = row[4].strip() if len(row) > 4 else "1층"
            risk = row[5].strip() if len(row) > 5 else "낮음"
            status = row[6].strip() if len(row) > 6 else "보관중"
            
            if name and location:
                rg = Reagent(
                    name=name, formula=formula, amount=amount,
                    category=category, location=location, risk=risk, status=status
                )
                db.session.add(rg)
                count += 1
                
        db.session.commit()
        return jsonify({"success": True, "message": f"{count}개의 시약이 등록되었습니다."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"파일 처리 중 오류: {str(e)}"})

@app.route("/upload")
def upload():
    photos = Photo.query.order_by(Photo.id.desc()).all()
    # upload.html의 {{ post[0] }}, {{ post[1] }} 인덱스 순서에 맞게 튜플로 매핑
    photo_list = [(p.id, p.url, p.caption, p.tags) for p in photos]
    return render_template("upload.html", photos=photo_list)

@app.route("/uploadPhoto", methods=["POST"])
def upload_photo():
    if not session.get("is_admin"):
        flash("관리자만 사진을 업로드할 수 있습니다.")
        return redirect(url_for("upload"))

    file = request.files.get("file")
    caption = request.form.get("caption")
    tags = request.form.get("tags")

    if file:
        try:
            upload_result = cloudinary.uploader.upload(file)
            image_url = upload_result.get("secure_url")
            
            new_photo = Photo(url=image_url, caption=caption, tags=tags)
            db.session.add(new_photo)
            db.session.commit()
        except Exception as e:
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
    app.run(debug=True)
