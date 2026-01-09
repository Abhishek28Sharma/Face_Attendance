# import os
# import io
# import threading
# import sqlite3
# import datetime
# import json
# from flask import Flask, render_template, request, jsonify, send_file

# from model import train_model_background, extract_embedding_for_image, MODEL_PATH

# APP_DIR = os.path.dirname(os.path.abspath(__file__))
# DB_PATH = os.path.join(APP_DIR, "attendance.db")
# DATASET_DIR = os.path.join(APP_DIR, "dataset")
# os.makedirs(DATASET_DIR, exist_ok=True)

# TRAIN_STATUS_FILE = os.path.join(APP_DIR, "train_status.json")

# app = Flask(__name__, static_folder="static", template_folder="templates")

# # ---------- DB helpers ----------
# def init_db():
#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()

#     c.execute("""CREATE TABLE IF NOT EXISTS students (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     name TEXT NOT NULL,
#                     roll TEXT,
#                     class TEXT,
#                     section TEXT,
#                     reg_no TEXT,
#                     created_at TEXT
#                 )""")

#     c.execute("""CREATE TABLE IF NOT EXISTS attendance (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     student_id INTEGER,
#                     name TEXT,
#                     day TEXT,
#                     time TEXT,
#                     month TEXT,
#                     year TEXT
#                 )""")

#     conn.commit()
#     conn.close()

# init_db()

# # ---------- Train status helpers ----------
# def write_train_status(status_dict):
#     with open(TRAIN_STATUS_FILE, "w") as f:
#         json.dump(status_dict, f)

# def read_train_status():
#     if not os.path.exists(TRAIN_STATUS_FILE):
#         return {"running": False, "progress": 0, "message": "Not trained"}
#     with open(TRAIN_STATUS_FILE, "r") as f:
#         return json.load(f)

# write_train_status({"running": False, "progress": 0, "message": "No training yet."})

# # ---------- Routes ----------
# @app.route("/")
# def index():
#     return render_template("index.html")

# # -------- Add student --------
# @app.route("/add_student", methods=["GET", "POST"])
# def add_student():
#     if request.method == "GET":
#         return render_template("add_student.html")

#     data = request.form
#     name = data.get("name","").strip()
#     roll = data.get("roll","").strip()
#     cls = data.get("class","").strip()
#     sec = data.get("sec","").strip()
#     reg_no = data.get("reg_no","").strip()

#     if not name:
#         return jsonify({"error":"name required"}), 400

#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()
#     now = datetime.datetime.utcnow().isoformat()
#     c.execute("""INSERT INTO students
#                  (name, roll, class, section, reg_no, created_at)
#                  VALUES (?, ?, ?, ?, ?, ?)""",
#               (name, roll, cls, sec, reg_no, now))
#     sid = c.lastrowid
#     conn.commit()
#     conn.close()

#     os.makedirs(os.path.join(DATASET_DIR, str(sid)), exist_ok=True)
#     return jsonify({"student_id": sid})

# # -------- Upload faces --------
# @app.route("/upload_face", methods=["POST"])
# def upload_face():
#     student_id = request.form.get("student_id")
#     if not student_id:
#         return jsonify({"error":"student_id required"}), 400

#     files = request.files.getlist("images[]")
#     folder = os.path.join(DATASET_DIR, student_id)
#     os.makedirs(folder, exist_ok=True)

#     saved = 0
#     for f in files:
#         fname = f"{datetime.datetime.utcnow().timestamp():.6f}_{saved}.jpg"
#         f.save(os.path.join(folder, fname))
#         saved += 1

#     return jsonify({"saved": saved})

# # -------- Train model --------
# @app.route("/train_model")
# def train_model_route():
#     status = read_train_status()
#     if status.get("running"):
#         return jsonify({"status":"already_running"}), 202

#     write_train_status({"running": True, "progress": 0, "message": "Starting training"})
#     t = threading.Thread(
#         target=train_model_background,
#         args=(DATASET_DIR, lambda p,m: write_train_status({"running": True, "progress": p, "message": m}))
#     )
#     t.daemon = True
#     t.start()
#     return jsonify({"status":"started"}), 202

# @app.route("/train_status")
# def train_status():
#     return jsonify(read_train_status())

# # -------- Mark attendance page --------
# @app.route("/mark_attendance")
# def mark_attendance_page():
#     return render_template("mark_attendance.html")

# # -------- Face recognition --------
# @app.route("/recognize_face", methods=["POST"])
# def recognize_face():
#     if "image" not in request.files:
#         return jsonify({"recognized": False, "error":"no image"}), 400

#     emb = extract_embedding_for_image(request.files["image"].stream)
#     if emb is None:
#         return jsonify({"recognized": False, "error":"no face"}), 200

#     from model import load_model_if_exists, predict_with_model
#     clf = load_model_if_exists()
#     if clf is None:
#         return jsonify({"recognized": False, "error":"model not trained"}), 200

#     pred_label, conf = predict_with_model(clf, emb)
#     if conf < 0.5:
#         return jsonify({"recognized": False, "confidence": float(conf)}), 200

#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()
#     c.execute("SELECT name FROM students WHERE id=?", (int(pred_label),))
#     row = c.fetchone()
#     name = row[0] if row else "Unknown"

#     now = datetime.datetime.now()
#     day = now.strftime("%d")
#     time = now.strftime("%H:%M:%S")
#     month = now.strftime("%B")
#     year = now.strftime("%Y")

#     c.execute("""INSERT INTO attendance
#                  (student_id, name, day, time, month, year)
#                  VALUES (?, ?, ?, ?, ?, ?)""",
#               (int(pred_label), name, day, time, month, year))
#     conn.commit()
#     conn.close()

#     return jsonify({
#         "recognized": True,
#         "student_id": int(pred_label),
#         "name": name,
#         "confidence": float(conf)
#     })

# # -------- Attendance records --------
# @app.route("/attendance_record")
# def attendance_record():
#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()
#     c.execute("""SELECT id, student_id, name, day, time, month, year
#                  FROM attendance ORDER BY id DESC LIMIT 5000""")
#     rows = c.fetchall()
#     print(rows)
#     conn.close()
#     return render_template("attendance_record.html", records=rows)

# # -------- CSV download --------
# @app.route("/download_csv")
# def download_csv():
#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()
#     c.execute("""SELECT id, student_id, name, day, time, month, year
#                  FROM attendance ORDER BY id DESC""")
#     rows = c.fetchall()
#     conn.close()

#     output = io.StringIO()
#     output.write("id,student_id,name,day,time,month,year\n")
#     for r in rows:
#         output.write(f"{r[0]},{r[1]},{r[2]},{r[3]},{r[4]},{r[5]},{r[6]}\n")

#     mem = io.BytesIO()
#     mem.write(output.getvalue().encode())
#     mem.seek(0)
#     return send_file(mem, as_attachment=True,
#                      download_name="attendance.csv",
#                      mimetype="text/csv")

# if __name__ == "__main__":
#     app.run(debug=True)
import os
import io
import threading
import sqlite3
import datetime
import json
from flask import Flask, render_template, request, jsonify, send_file

# Assuming these exist in your model.py
from model import train_model_background, extract_embedding_for_image, MODEL_PATH

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "attendance.db")
DATASET_DIR = os.path.join(APP_DIR, "dataset")
os.makedirs(DATASET_DIR, exist_ok=True)

TRAIN_STATUS_FILE = os.path.join(APP_DIR, "train_status.json")

app = Flask(__name__, static_folder="static", template_folder="templates")

# ---------- DB helpers ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    roll TEXT,
                    class TEXT,
                    section TEXT,
                    reg_no TEXT,
                    created_at TEXT
                )""")

    c.execute("""CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    name TEXT,
                    day TEXT,
                    time TEXT,
                    month TEXT,
                    year TEXT
                )""")

    conn.commit()
    conn.close()

init_db()

# ---------- Train status helpers ----------
def write_train_status(status_dict):
    with open(TRAIN_STATUS_FILE, "w") as f:
        json.dump(status_dict, f)

def read_train_status():
    if not os.path.exists(TRAIN_STATUS_FILE):
        return {"running": False, "progress": 0, "message": "Not trained"}
    with open(TRAIN_STATUS_FILE, "r") as f:
        return json.load(f)

write_train_status({"running": False, "progress": 0, "message": "No training yet."})

# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html")

# -------- Add student --------
@app.route("/add_student", methods=["GET", "POST"])
def add_student():
    if request.method == "GET":
        return render_template("add_student.html")

    data = request.form
    name = data.get("name","").strip()
    roll = data.get("roll","").strip()
    cls = data.get("class","").strip()
    sec = data.get("sec","").strip()
    reg_no = data.get("reg_no","").strip()

    if not name:
        return jsonify({"error":"name required"}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    c.execute("""INSERT INTO students
                 (name, roll, class, section, reg_no, created_at)
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (name, roll, cls, sec, reg_no, now))
    sid = c.lastrowid
    conn.commit()
    conn.close()

    os.makedirs(os.path.join(DATASET_DIR, str(sid)), exist_ok=True)
    return jsonify({"student_id": sid})

# -------- Upload faces --------
@app.route("/upload_face", methods=["POST"])
def upload_face():
    student_id = request.form.get("student_id")
    if not student_id:
        return jsonify({"error":"student_id required"}), 400

    files = request.files.getlist("images[]")
    folder = os.path.join(DATASET_DIR, student_id)
    os.makedirs(folder, exist_ok=True)

    saved = 0
    for f in files:
        fname = f"{datetime.datetime.utcnow().timestamp():.6f}_{saved}.jpg"
        f.save(os.path.join(folder, fname))
        saved += 1

    return jsonify({"saved": saved})

# -------- Train model --------
@app.route("/train_model")
def train_model_route():
    status = read_train_status()
    if status.get("running"):
        return jsonify({"status":"already_running"}), 202

    write_train_status({"running": True, "progress": 0, "message": "Starting training"})
    t = threading.Thread(
        target=train_model_background,
        args=(DATASET_DIR, lambda p,m: write_train_status({"running": True, "progress": p, "message": m}))
    )
    t.daemon = True
    t.start()
    return jsonify({"status":"started"}), 202

@app.route("/train_status")
def train_status():
    return jsonify(read_train_status())

# -------- Mark attendance page --------
@app.route("/mark_attendance")
def mark_attendance_page():
    return render_template("mark_attendance.html")

# -------- Face recognition with Duplicate Check --------
@app.route("/recognize_face", methods=["POST"])
def recognize_face():
    if "image" not in request.files:
        return jsonify({"recognized": False, "error":"no image"}), 400

    emb = extract_embedding_for_image(request.files["image"].stream)
    if emb is None:
        return jsonify({"recognized": False, "error":"no face"}), 200

    from model import load_model_if_exists, predict_with_model
    clf = load_model_if_exists()
    if clf is None:
        return jsonify({"recognized": False, "error":"model not trained"}), 200

    pred_label, conf = predict_with_model(clf, emb)
    if conf < 0.5:
        return jsonify({"recognized": False, "confidence": float(conf)}), 200

    # Get current date and time
    now = datetime.datetime.now()
    day = now.strftime("%d")
    time_str = now.strftime("%H:%M:%S")
    month = now.strftime("%B")
    year = now.strftime("%Y")
    student_id = int(pred_label)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # --- DUPLICATE CHECK LOGIC ---
    # Check if this student already has an entry for TODAY
    c.execute("""SELECT id FROM attendance 
                 WHERE student_id=? AND day=? AND month=? AND year=? """, 
              (student_id, day, month, year))
    already_marked = c.fetchone()

    # Get student name for the response
    c.execute("SELECT name FROM students WHERE id=?", (student_id,))
    row = c.fetchone()
    name = row[0] if row else "Unknown"

    if already_marked:
        conn.close()
        return jsonify({
            "recognized": True,
            "already_logged": True, # Flag for frontend
            "student_id": student_id,
            "name": name,
            "confidence": float(conf)
        })

    # If NOT marked today, save to database
    c.execute("""INSERT INTO attendance
                 (student_id, name, day, time, month, year)
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (student_id, name, day, time_str, month, year))
    conn.commit()
    conn.close()

    return jsonify({
        "recognized": True,
        "already_logged": False,
        "student_id": student_id,
        "name": name,
        "confidence": float(conf)
    })

# -------- Attendance records --------
@app.route("/attendance_record")
def attendance_record():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Updated query to match your new table headers (Roll No is pulled from students table if needed)
    c.execute("""SELECT id, student_id, name, day, time, month, year
                 FROM attendance ORDER BY id DESC LIMIT 5000""")
    rows = c.fetchall()
    conn.close()
    return render_template("attendance_record.html", records=rows)

# -------- CSV download --------
@app.route("/download_csv")
def download_csv():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT id, student_id, name, day, time, month, year
                 FROM attendance ORDER BY id DESC""")
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    output.write("id,student_id,name,day,time,month,year\n")
    for r in rows:
        output.write(f"{r[0]},{r[1]},{r[2]},{r[3]},{r[4]},{r[5]},{r[6]}\n")

    mem = io.BytesIO()
    mem.write(output.getvalue().encode())
    mem.seek(0)
    return send_file(mem, as_attachment=True,
                     download_name="attendance.csv",
                     mimetype="text/csv")

if __name__ == "__main__":
    app.run(debug=True)