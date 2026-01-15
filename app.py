import os
import io
import threading
import sqlite3
import datetime
import json
from flask import Flask, render_template, request, jsonify, send_file

# Ensure these functions in model.py use os.walk for nested folders
from model import train_model_background, extract_embedding_for_image, MODEL_PATH

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "attendance.db")
DATASET_DIR = os.path.join(APP_DIR, "dataset")
os.makedirs(DATASET_DIR, exist_ok=True)

TRAIN_STATUS_FILE = os.path.join(APP_DIR, "train_status.json")

app = Flask(__name__, static_folder="static", template_folder="templates")

# ---------- Helpers ----------

def get_student_folder_path(semester, branch, roll):
    """Constructs a nested path: dataset/YEAR/MONTH/SEMESTER/BRANCH/ROLL_NO"""
    now = datetime.datetime.now()
    year, month = now.strftime("%Y"), now.strftime("%B")
    semester = str(semester).replace(" ", "_")
    branch = str(branch).replace(" ", "_")
    roll = str(roll).replace(" ", "_")
    return os.path.join(DATASET_DIR, year, month, semester, branch, roll)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL, roll TEXT, class TEXT, 
                    section TEXT, reg_no TEXT, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER,
                    name TEXT, day TEXT, time TEXT, month TEXT, year TEXT)""")
    conn.commit()
    conn.close()

def read_train_status():
    if not os.path.exists(TRAIN_STATUS_FILE):
        return {"running": False, "progress": 0, "message": "Not trained"}
    with open(TRAIN_STATUS_FILE, "r") as f:
        return json.load(f)

def write_train_status(status_dict):
    with open(TRAIN_STATUS_FILE, "w") as f:
        json.dump(status_dict, f)

init_db()

# ---------- Page Routes ----------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/add_student", methods=["GET", "POST"])
def add_student():
    if request.method == "GET":
        return render_template("add_student.html")
    
    data = request.form
    name = data.get("name", "").strip()
    roll = data.get("roll", "").strip()
    cls = data.get("class", "").strip()  # Semester
    sec = data.get("sec", "").strip()    # Branch
    reg_no = data.get("reg_no", "").strip()
    
    if not name or not roll:
        return jsonify({"error": "Name and Roll Number required"}), 400
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO students (name, roll, class, section, reg_no, created_at) VALUES (?,?,?,?,?,?)",
              (name, roll, cls, sec, reg_no, datetime.datetime.utcnow().isoformat()))
    sid = c.lastrowid
    conn.commit()
    conn.close()
    
    os.makedirs(get_student_folder_path(cls, sec, roll), exist_ok=True)
    return jsonify({"student_id": sid, "roll": roll, "semester": cls, "branch": sec})

@app.route("/mark_attendance")
def mark_attendance_page():
    return render_template("mark_attendance.html")

@app.route("/attendance_record")
def attendance_record():
    semester = request.args.get("semester", "").strip()
    branch = request.args.get("branch", "").strip()
    month = request.args.get("month", "").strip()
    day = request.args.get("day", "").strip()
    should_download = request.args.get("download", "false") == "true"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    query = """
        SELECT a.id, s.roll, s.reg_no, a.name, a.day, a.time, a.month, a.year, s.class, s.section
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE 1=1
    """
    params = []
    if semester: query += " AND s.class LIKE ?"; params.append(f"%{semester}%")
    if branch: query += " AND s.section LIKE ?"; params.append(f"%{branch}%")
    if month: query += " AND a.month = ?"; params.append(month)
    if day: query += " AND a.day = ?"; params.append(day.zfill(2))
    
    query += " ORDER BY a.id DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()

    if should_download:
        output = io.StringIO()
        output.write("Roll,RegNo,Name,Date,Time,Semester,Branch\n")
        for r in rows:
            output.write(f"{r[1]},{r[2]},{r[3]},{r[4]}-{r[6]}-{r[7]},{r[5]},{r[8]},{r[9]}\n")
        mem = io.BytesIO()
        mem.write(output.getvalue().encode())
        mem.seek(0)
        return send_file(mem, as_attachment=True, download_name="filtered_attendance.csv", mimetype="text/csv")

    return render_template("attendance_record.html", records=rows)

# ---------- Face Logic & API Routes ----------

@app.route("/train_model")
def train_model_route():
    status = read_train_status()
    if status.get("running"):
        return jsonify({"status": "already_running"}), 202

    write_train_status({"running": True, "progress": 0, "message": "Starting training"})
    t = threading.Thread(
        target=train_model_background,
        args=(DATASET_DIR, lambda p, m: write_train_status({"running": True, "progress": p, "message": m}))
    )
    t.daemon = True
    t.start()
    return jsonify({"status": "started"}), 202

@app.route("/train_status")
def train_status():
    return jsonify(read_train_status())

@app.route("/recognize_face", methods=["POST"])
def recognize_face():
    if "image" not in request.files:
        return jsonify({"recognized": False, "error": "no image"}), 400

    emb = extract_embedding_for_image(request.files["image"].stream)
    if emb is None: return jsonify({"recognized": False, "error": "no face"})
    
    from model import load_model_if_exists, predict_with_model
    clf = load_model_if_exists()
    if clf is None: return jsonify({"recognized": False, "error": "model not trained"})

    pred_label, conf = predict_with_model(clf, emb)
    if conf < 0.5: return jsonify({"recognized": False, "confidence": float(conf)})

    now = datetime.datetime.now()
    sid = int(pred_label)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Duplicate Check (Daily)
    c.execute("SELECT id FROM attendance WHERE student_id=? AND day=? AND month=? AND year=?", 
              (sid, now.strftime("%d"), now.strftime("%B"), now.strftime("%Y")))
    if c.fetchone():
        c.execute("SELECT name FROM students WHERE id=?", (sid,))
        name = c.fetchone()[0]
        conn.close()
        return jsonify({"recognized": True, "already_logged": True, "name": name})

    c.execute("SELECT name FROM students WHERE id=?", (sid,))
    res = c.fetchone()
    name = res[0] if res else "Unknown"
    
    c.execute("INSERT INTO attendance (student_id, name, day, time, month, year) VALUES (?,?,?,?,?,?)",
              (sid, name, now.strftime("%d"), now.strftime("%H:%M:%S"), now.strftime("%B"), now.strftime("%Y")))
    conn.commit()
    conn.close()
    return jsonify({"recognized": True, "already_logged": False, "name": name})

@app.route("/upload_face", methods=["POST"])
def upload_face():
    semester = request.form.get("semester")
    branch = request.form.get("branch")
    roll = request.form.get("roll")
    
    if not all([semester, branch, roll]):
        return jsonify({"error": "Missing metadata"}), 400

    folder = get_student_folder_path(semester, branch, roll)
    os.makedirs(folder, exist_ok=True)
    
    files = request.files.getlist("images[]")
    for i, f in enumerate(files):
        fname = f"{datetime.datetime.utcnow().timestamp()}_{i}.jpg"
        f.save(os.path.join(folder, fname))
    
    return jsonify({"saved": True, "count": len(files)})

@app.route("/download_csv")
def download_csv_legacy():
    # This maintains compatibility with any hardcoded /download_csv links
    return attendance_record()

if __name__ == "__main__":
    app.run(debug=True)