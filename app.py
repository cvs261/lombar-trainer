import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-key-change-me"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True


db = SQLAlchemy(app)

# ---------- Models ----------
class Week(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)  # 1..4
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    workouts = db.relationship("Workout", backref="week", lazy=True, cascade="all, delete-orphan")

class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    week_id = db.Column(db.Integer, db.ForeignKey("week.id"), nullable=False)
    day = db.Column(db.String(20), nullable=False)  # Luni..Vineri
    exercise = db.Column(db.String(120), nullable=False)
    sets = db.Column(db.String(20), default="")
    reps_time = db.Column(db.String(20), default="")
    equipment = db.Column(db.String(60), default="")
    done = db.Column(db.Boolean, default=False)
    image_path = db.Column(db.String(255), default="")
    notes = db.Column(db.String(255), default="")

class Estimation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    body_weight = db.Column(db.Float, nullable=False)
    plank_best = db.Column(db.Float, nullable=False)            # sec
    side_plank_avg = db.Column(db.Float, nullable=False)        # sec
    bird_control = db.Column(db.Integer, nullable=False)        # 1-5
    pain = db.Column(db.Integer, nullable=False)                # 0-10
    sciatic = db.Column(db.Integer, nullable=False)             # 0/1
    week_number = db.Column(db.Integer, nullable=False)         # 1-4
    core_score = db.Column(db.Float, nullable=False)
    hinge_kg = db.Column(db.Float, nullable=False)
    squat_kg = db.Column(db.Float, nullable=False)
    do_not_exceed = db.Column(db.Float, nullable=False)

# ---------- Estimator logic ----------
def estimate_loads(body_weight, plank, side_plank, bird_control, pain, sciatic, week_number):
    plank_norm = min(plank / 60.0, 1.0)
    side_norm = min(side_plank / 45.0, 1.0)
    bird_norm = min(bird_control / 5.0, 1.0)
    core_score = 0.45*plank_norm + 0.35*side_norm + 0.20*bird_norm

    pain_factor = max(0.4, 1 - pain * 0.07)
    sciatic_factor = 0.8 if sciatic == 1 else 1.0
    week_map = {1:0.6, 2:0.75, 3:0.9, 4:1.0}
    week_factor = week_map.get(int(week_number), 0.6)

    hinge_pct = 0.20 + 0.60 * core_score   # 20% .. 80%
    squat_pct = 0.15 + 0.45 * core_score   # 15% .. 60%

    hinge = body_weight * hinge_pct * pain_factor * sciatic_factor * week_factor
    squat = body_weight * squat_pct * pain_factor * sciatic_factor * week_factor

    if pain >= 4:
        do_not_exceed = 0.0
    else:
        do_not_exceed = max(hinge, squat) * 1.10  # +10% marjă dacă e „safe”

    return core_score, round(hinge,1), round(squat,1), round(do_not_exceed,1)

# ---------- Routes ----------
@app.route("/")
def index():
    db.create_all()
    if Week.query.count() == 0:
        # nu există date? mergem direct la init ca să populăm
        return redirect(url_for("init_db"))
    weeks = Week.query.order_by(Week.number.asc()).all()
    return render_template("index.html", weeks=weeks)


@app.route("/health")
def health():
    return "OK", 200


@app.route("/init")
def init_db():
    db.create_all()
    if Week.query.count() == 0:
        for i in range(1,5):
            week = Week(number=i)
            db.session.add(week)
            db.session.flush()
            # seed default plan per day
            plan = {
                    1: [
                        ("Luni", "Bird-dog – 2x8/parte"),
                        ("Luni", "Glute bridge – 2x10"),
                        ("Luni", "Plank pe genunchi – 2x20 sec"),
                        ("Luni", "Clamshell – 2x10/parte"),
                        ("Luni", "Dead bug – 2x8/parte"),
                        ("Luni", "Stretch: child’s pose, hip flexor, piriformis (30 sec fiecare)"),

                        ("Marți", "Bird-dog – 2x8/parte"),
                        ("Marți", "Glute bridge – 2x10"),
                        ("Marți", "Plank pe genunchi – 2x20 sec"),
                        ("Marți", "Clamshell – 2x10/parte"),
                        ("Marți", "Dead bug – 2x8/parte"),
                        ("Marți", "Stretch: child’s pose, hip flexor, piriformis (30 sec fiecare)"),

                        ("Miercuri", "Bird-dog – 2x8/parte"),
                        ("Miercuri", "Glute bridge – 2x10"),
                        ("Miercuri", "Plank pe genunchi – 2x20 sec"),
                        ("Miercuri", "Clamshell – 2x10/parte"),
                        ("Miercuri", "Dead bug – 2x8/parte"),
                        ("Miercuri", "Stretch: child’s pose, hip flexor, piriformis (30 sec fiecare)"),

                        ("Joi", "Bird-dog – 2x8/parte"),
                        ("Joi", "Glute bridge – 2x10"),
                        ("Joi", "Plank pe genunchi – 2x20 sec"),
                        ("Joi", "Clamshell – 2x10/parte"),
                        ("Joi", "Dead bug – 2x8/parte"),
                        ("Joi", "Stretch: child’s pose, hip flexor, piriformis (30 sec fiecare)"),

                        ("Vineri", "Bird-dog – 2x8/parte"),
                        ("Vineri", "Glute bridge – 2x10"),
                        ("Vineri", "Plank pe genunchi – 2x20 sec"),
                        ("Vineri", "Clamshell – 2x10/parte"),
                        ("Vineri", "Dead bug – 2x8/parte"),
                        ("Vineri", "Stretch: child’s pose, hip flexor, piriformis (30 sec fiecare)"),
                    ],
                    2: [
                        ("Luni", "Bird-dog – 3x8/parte"),
                        ("Luni", "Glute bridge – 3x12"),
                        ("Luni", "Plank clasic – 3x25–30 sec"),
                        ("Luni", "Side leg raise – 3x10/parte"),
                        ("Luni", "Dead bug – 3x10/parte"),
                        ("Luni", "Superman (brațe+coapse) – 2x8"),
                        ("Luni", "Stretch ca în săpt. 1"),

                        ("Marti", "Bird-dog – 3x8/parte"),
                        ("Marti", "Glute bridge – 3x12"),
                        ("Marti", "Plank clasic – 3x25–30 sec"),
                        ("Marti", "Side leg raise – 3x10/parte"),
                        ("Marti", "Dead bug – 3x10/parte"),
                        ("Marti", "Superman (brațe+coapse) – 2x8"),
                        ("Marti", "Stretch ca în săpt. 1"),

                        ("Miercuri", "Bird-dog – 3x8/parte"),
                        ("Miercuri", "Glute bridge – 3x12"),
                        ("Miercuri", "Plank clasic – 3x25–30 sec"),
                        ("Miercuri", "Side leg raise – 3x10/parte"),
                        ("Miercuri", "Dead bug – 3x10/parte"),
                        ("Miercuri", "Superman (brațe+coapse) – 2x8"),
                        ("Miercuri", "Stretch ca în săpt. 1"),

                        ("Joi", "Bird-dog – 3x8/parte"),
                        ("Joi", "Glute bridge – 3x12"),
                        ("Joi", "Plank clasic – 3x25–30 sec"),
                        ("Joi", "Side leg raise – 3x10/parte"),
                        ("Joi", "Dead bug – 3x10/parte"),
                        ("Joi", "Superman (brațe+coapse) – 2x8"),
                        ("Joi", "Stretch ca în săpt. 1"),

                        ("Vineri", "Bird-dog – 3x8/parte"),
                        ("Vineri", "Glute bridge – 3x12"),
                        ("Vineri", "Plank clasic – 3x25–30 sec"),
                        ("Vineri", "Side leg raise – 3x10/parte"),
                        ("Vineri", "Dead bug – 3x10/parte"),
                        ("Vineri", "Superman (brațe+coapse) – 2x8"),
                        ("Vineri", "Stretch ca în săpt. 1"),
                    ],
                    3: [
                        ("Luni", "Bird-dog cu menținere 5 sec – 3x8/parte"),
                        ("Luni", "Hip thrust – 3x12"),
                        ("Luni", "Plank lateral – 3x20 sec/parte"),
                        ("Luni", "Monster walk cu bandă – 3x10 pași/parte"),
                        ("Luni", "Dead bug – 3x12/parte"),
                        ("Luni", "Hollow body hold – 2x15–20 sec"),
                        ("Luni", "Stretch (inclusiv hamstring stretch)"),

                        ("Marti", "Bird-dog cu menținere 5 sec – 3x8/parte"),
                        ("Marti", "Hip thrust – 3x12"),
                        ("Marti", "Plank lateral – 3x20 sec/parte"),
                        ("Marti", "Monster walk cu bandă – 3x10 pași/parte"),
                        ("Marti", "Dead bug – 3x12/parte"),
                        ("Marti", "Hollow body hold – 2x15–20 sec"),
                        ("Marti", "Stretch (inclusiv hamstring stretch)"),

                        ("Miercuri", "Bird-dog cu menținere 5 sec – 3x8/parte"),
                        ("Miercuri", "Hip thrust – 3x12"),
                        ("Miercuri", "Plank lateral – 3x20 sec/parte"),
                        ("Miercuri", "Monster walk cu bandă – 3x10 pași/parte"),
                        ("Miercuri", "Dead bug – 3x12/parte"),
                        ("Miercuri", "Hollow body hold – 2x15–20 sec"),
                        ("Miercuri", "Stretch (inclusiv hamstring stretch)"),

                        ("Joi", "Bird-dog cu menținere 5 sec – 3x8/parte"),
                        ("Joi", "Hip thrust – 3x12"),
                        ("Joi", "Plank lateral – 3x20 sec/parte"),
                        ("Joi", "Monster walk cu bandă – 3x10 pași/parte"),
                        ("Joi", "Dead bug – 3x12/parte"),
                        ("Joi", "Hollow body hold – 2x15–20 sec"),
                        ("Joi", "Stretch (inclusiv hamstring stretch)"),

                        ("Vineri", "Bird-dog cu menținere 5 sec – 3x8/parte"),
                        ("Vineri", "Hip thrust – 3x12"),
                        ("Vineri", "Plank lateral – 3x20 sec/parte"),
                        ("Vineri", "Monster walk cu bandă – 3x10 pași/parte"),
                        ("Vineri", "Dead bug – 3x12/parte"),
                        ("Vineri", "Hollow body hold – 2x15–20 sec"),
                        ("Vineri", "Stretch (inclusiv hamstring stretch)"),
                    ],
                    4: [
                        ("Luni", "Bird-dog + atingere cot-genunchi – 3x10/parte"),
                        ("Luni", "Hip thrust – 3x15"),
                        ("Luni", "Plank clasic – 3x40–45 sec"),
                        ("Luni", "Plank lateral cu ridicare picior – 2x8/parte"),
                        ("Luni", "Good morning (fără greutate / cu baston) – 3x12"),
                        ("Luni", "Dead bug – 3x12/parte"),
                        ("Luni", "Russian twist (fără greutate) – 2x12/parte"),
                        ("Luni", "Stretch complet (5–7 min)"),

                        ("Marti", "Bird-dog + atingere cot-genunchi – 3x10/parte"),
                        ("Marti", "Hip thrust – 3x15"),
                        ("Marti", "Plank clasic – 3x40–45 sec"),
                        ("Marti", "Plank lateral cu ridicare picior – 2x8/parte"),
                        ("Marti", "Good morning (fără greutate / cu baston) – 3x12"),
                        ("Marti", "Dead bug – 3x12/parte"),
                        ("Marti", "Russian twist (fără greutate) – 2x12/parte"),
                        ("Marti", "Stretch complet (5–7 min)"),

                        ("Miercuri", "Bird-dog + atingere cot-genunchi – 3x10/parte"),
                        ("Miercuri", "Hip thrust – 3x15"),
                        ("Miercuri", "Plank clasic – 3x40–45 sec"),
                        ("Miercuri", "Plank lateral cu ridicare picior – 2x8/parte"),
                        ("Miercuri", "Good morning (fără greutate / cu baston) – 3x12"),
                        ("Miercuri", "Dead bug – 3x12/parte"),
                        ("Miercuri", "Russian twist (fără greutate) – 2x12/parte"),
                        ("Miercuri", "Stretch complet (5–7 min)"),

                        ("Joi", "Bird-dog + atingere cot-genunchi – 3x10/parte"),
                        ("Joi", "Hip thrust – 3x15"),
                        ("Joi", "Plank clasic – 3x40–45 sec"),
                        ("Joi", "Plank lateral cu ridicare picior – 2x8/parte"),
                        ("Joi", "Good morning (fără greutate / cu baston) – 3x12"),
                        ("Joi", "Dead bug – 3x12/parte"),
                        ("Joi", "Russian twist (fără greutate) – 2x12/parte"),
                        ("Joi", "Stretch complet (5–7 min)"),

                        ("Vineri", "Bird-dog + atingere cot-genunchi – 3x10/parte"),
                        ("Vineri", "Hip thrust – 3x15"),
                        ("Vineri", "Plank clasic – 3x40–45 sec"),
                        ("Vineri", "Plank lateral cu ridicare picior – 2x8/parte"),
                        ("Vineri", "Good morning (fără greutate / cu baston) – 3x12"),
                        ("Vineri", "Dead bug – 3x12/parte"),
                        ("Vineri", "Russian twist (fără greutate) – 2x12/parte"),
                        ("Vineri", "Stretch complet (5–7 min)"),
                    ]
                }
            for day, ex in plan.get(i, []):
                db.session.add(Workout(week_id=week.id, day=day, exercise=ex, equipment="Saltea"))
        db.session.commit()
    return redirect(url_for("index"))

@app.route("/week/<int:number>")
def view_week(number):
    week = Week.query.filter_by(number=number).first_or_404()
    order = {"Luni":1,"Marți":2,"Miercuri":3,"Joi":4,"Vineri":5}
    workouts = sorted(week.workouts, key=lambda w: (order.get(w.day, 99), w.id))
    return render_template("week.html", week=week, workouts=workouts)

@app.route("/workout/<int:w_id>/update", methods=["POST"])
def update_workout(w_id):
    w = Workout.query.get_or_404(w_id)
    w.sets = request.form.get("sets","")
    w.reps_time = request.form.get("reps_time","")
    w.equipment = request.form.get("equipment","")
    w.done = True if request.form.get("done") == "on" else False
    w.notes = request.form.get("notes","")

    file = request.files.get("image")
    if file and file.filename:
        filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{w.id}_{file.filename}"
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(path)
        w.image_path = filename
    db.session.commit()
    flash("Workout salvat.", "success")
    return redirect(url_for("view_week", number=w.week.number))

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/estimator", methods=["GET","POST"])
def estimator():
    result = None
    if request.method == "POST":
        try:
            bw = float(request.form["body_weight"])
            plank = float(request.form["plank_best"])
            side = float(request.form["side_plank_avg"])
            bird = int(request.form["bird_control"])
            pain = int(request.form["pain"])
            sci = int(request.form.get("sciatic", 0))
            week = int(request.form["week_number"])

            core, hinge, squat, dne = estimate_loads(bw, plank, side, bird, pain, sci, week)
            est = Estimation(body_weight=bw, plank_best=plank, side_plank_avg=side, bird_control=bird,
                             pain=pain, sciatic=sci, week_number=week, core_score=core,
                             hinge_kg=hinge, squat_kg=squat, do_not_exceed=dne)
            db.session.add(est)
            db.session.commit()
            result = est
        except Exception as e:
            flash(f"Eroare în calcule: {e}", "danger")
    recent = Estimation.query.order_by(Estimation.created_at.desc()).limit(10).all()
    return render_template("estimator.html", result=result, recent=recent)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

