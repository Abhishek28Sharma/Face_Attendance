# import os
# import io
# import threading
# import sqlite3
# import datetime
# import json
# from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for

# # Import from model.py (Ensure your model.py has these functions defined)
# from model import train_model_background, extract_embedding_for_image, MODEL_PATH

# APP_DIR = os.path.dirname(os.path.abspath(__file__))
# DB_PATH = os.path.join(APP_DIR, "attendance.db")
# DATASET_DIR = os.path.join(APP_DIR, "dataset")
# os.makedirs(DATASET_DIR, exist_ok=True)

# TRAIN_STATUS_FILE = os.path.join(APP_DIR, "train_status.json")
# CONFIG_FILE = os.path.join(APP_DIR, "config.json")

# app = Flask(__name__, static_folder="static", template_folder="templates")

# # --- Configuration & Fine Logic ---
# def get_config():
#     if not os.path.exists(CONFIG_FILE):
#         return {"fine_per_lecture": 50}
#     with open(CONFIG_FILE, "r") as f:
#         return json.load(f)

# # --- Database Initialization ---
# def init_db():
#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()
#     # Updated Students Table with is_paid column
#     c.execute("""CREATE TABLE IF NOT EXISTS students (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     name TEXT NOT NULL, roll TEXT, class TEXT, 
#                     section TEXT, reg_no TEXT, created_at TEXT,
#                     is_paid INTEGER DEFAULT 0)""")
    
#     # Attendance Table
#     c.execute("""CREATE TABLE IF NOT EXISTS attendance (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT, 
#                     student_id INTEGER,
#                     name TEXT, day TEXT, time TEXT, 
#                     month TEXT, year TEXT, period TEXT)""")
    
#     # Timetable Table
#     c.execute("""CREATE TABLE IF NOT EXISTS timetable (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     day_of_week TEXT NOT NULL,
#                     period_name TEXT NOT NULL,
#                     start_time TEXT NOT NULL,
#                     end_time TEXT NOT NULL)""")
#     conn.commit()
#     conn.close()

# init_db()

# # --- Helpers ---
# def get_current_period():
#     current_day = datetime.datetime.now().strftime("%A")
#     now_time = datetime.datetime.now().strftime("%H:%M")
#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()
#     c.execute("""SELECT period_name FROM timetable 
#                  WHERE day_of_week = ? AND start_time <= ? AND end_time >= ?""", 
#               (current_day, now_time, now_time))
#     res = c.fetchone()
#     conn.close()
#     return res[0] if res else "Free Period"

# def write_train_status(status_dict):
#     with open(TRAIN_STATUS_FILE, "w") as f:
#         json.dump(status_dict, f)

# def read_train_status():
#     if not os.path.exists(TRAIN_STATUS_FILE):
#         return {"running": False, "progress": 0, "message": "Not trained"}
#     with open(TRAIN_STATUS_FILE, "r") as f:
#         return json.load(f)

# # --- Routine Management ---
# @app.route("/set_routine", methods=["GET", "POST"])
# def set_routine():
#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()
#     if request.method == "POST":
#         day_of_week = request.form.get("day_of_week")
#         p_name = request.form.get("period_name")
#         s_time = request.form.get("start_time")
#         e_time = request.form.get("end_time")
#         c.execute("INSERT INTO timetable (day_of_week, period_name, start_time, end_time) VALUES (?,?,?,?)", 
#                   (day_of_week, p_name, s_time, e_time))
#         conn.commit()
#     c.execute("SELECT * FROM timetable ORDER BY start_time ASC")
#     routine = c.fetchall()
#     conn.close()
#     return render_template("set_routine.html", routine=routine)

# @app.route("/delete_period/<int:pid>")
# def delete_period(pid):
#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()
#     c.execute("DELETE FROM timetable WHERE id=?", (pid,))
#     conn.commit()
#     conn.close()
#     return jsonify({"success": True})

# @app.route("/get_active_period_name")
# def get_active_period_name():
#     return jsonify({"period": get_current_period()})

# # --- Fine Policy Update ---
# @app.route("/update_fine", methods=["POST"])
# def update_fine():
#     fine_amt = request.form.get("fine_amount", 50)
#     with open(CONFIG_FILE, "w") as f:
#         json.dump({"fine_per_lecture": int(fine_amt)}, f)
#     # Redirect back to recalculate and show changes
#     return redirect(url_for('view_history'))

# @app.route("/toggle_fine_status/<int:sid>", methods=["POST"])
# def toggle_fine_status(sid):
#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()
#     # Toggle logic: updates 1 to 0 or 0 to 1
#     c.execute("UPDATE students SET is_paid = NOT is_paid WHERE id = ?", (sid,))
#     conn.commit()
#     conn.close()
#     return jsonify({"success": True})

# # --- Attendance & Student Routes ---
# @app.route("/")
# def index():
#     return render_template("index.html")

# @app.route("/add_student", methods=["GET", "POST"])
# def add_student():
#     if request.method == "GET":
#         return render_template("add_student.html")
#     data = request.form
#     name, roll, cls, sec, reg_no = data.get("name",""), data.get("roll",""), data.get("class",""), data.get("sec",""), data.get("reg_no","")
#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()
#     c.execute("INSERT INTO students (name, roll, class, section, reg_no, created_at) VALUES (?,?,?,?,?,?)",
#               (name, roll, cls, sec, reg_no, datetime.datetime.utcnow().isoformat()))
#     sid = c.lastrowid
#     conn.commit()
#     conn.close()
#     os.makedirs(os.path.join(DATASET_DIR, str(sid)), exist_ok=True)
#     return jsonify({"student_id": sid})

# @app.route("/upload_face", methods=["POST"])
# def upload_face():
#     sid = request.form.get("student_id")
#     folder = os.path.join(DATASET_DIR, str(sid))
#     os.makedirs(folder, exist_ok=True)
#     files = request.files.getlist("images[]")
#     for i, f in enumerate(files):
#         fname = f"{datetime.datetime.utcnow().timestamp():.6f}_{i}.jpg"
#         f.save(os.path.join(folder, fname))
#     return jsonify({"saved": True})

# @app.route("/mark_attendance")
# def mark_attendance_page():
#     return render_template("mark_attendance.html")

# @app.route("/recognize_face", methods=["POST"])
# def recognize_face():
#     if "image" not in request.files: return jsonify({"recognized": False})
#     emb = extract_embedding_for_image(request.files["image"].stream)
#     if emb is None: return jsonify({"recognized": False})
    
#     from model import load_model_if_exists, predict_with_model
#     clf = load_model_if_exists()
#     if not clf: return jsonify({"recognized": False, "error": "Model not trained"})

#     pred_label, conf = predict_with_model(clf, emb)
#     if conf < 0.6: return jsonify({"recognized": False})

#     now = datetime.datetime.now()
#     sid = int(pred_label)
#     active_period = get_current_period()
    
#     if active_period == "Free Period":
#         conn = sqlite3.connect(DB_PATH)
#         c = conn.cursor()
#         c.execute("SELECT name FROM students WHERE id=?", (sid,))
#         res = c.fetchone()
#         name = res[0] if res else "Unknown"
#         conn.close()
#         return jsonify({"recognized": True, "name": name, "period": "Free Period", "already_logged": True})

#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()
#     c.execute("""SELECT id FROM attendance 
#                  WHERE student_id=? AND period=? AND day=? AND month=? AND year=?""", 
#               (sid, active_period, now.strftime("%d"), now.strftime("%B"), now.strftime("%Y")))
#     already_marked = c.fetchone()

#     c.execute("SELECT name FROM students WHERE id=?", (sid,))
#     res = c.fetchone()
#     name = res[0] if res else "Unknown"
    
#     if not already_marked:
#         c.execute("""INSERT INTO attendance (student_id, name, day, time, month, year, period) 
#                      VALUES (?,?,?,?,?,?,?)""",
#                   (sid, name, now.strftime("%d"), now.strftime("%H:%M:%S"), 
#                    now.strftime("%B"), now.strftime("%Y"), active_period))
#         conn.commit()
#     conn.close()
#     return jsonify({"recognized": True, "name": name, "period": active_period, "already_logged": bool(already_marked), "confidence": float(conf)})

# # --- Subject-wise History View (Pivot Table) ---
# @app.route("/view_pivot_history")
# def view_pivot_history():
#     target_date = request.args.get('date', datetime.datetime.now().strftime("%d"))
#     target_month = request.args.get('month', datetime.datetime.now().strftime("%B"))
#     target_year = request.args.get('year', datetime.datetime.now().strftime("%Y"))

#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()
#     try:
#         date_obj = datetime.datetime.strptime(f"{target_date} {target_month} {target_year}", "%d %B %Y")
#         day_name = date_obj.strftime("%A")
#     except:
#         day_name = datetime.datetime.now().strftime("%A")

#     c.execute("SELECT period_name FROM timetable WHERE day_of_week = ? ORDER BY start_time ASC", (day_name,))
#     subjects = [row[0] for row in c.fetchall()]
#     c.execute("SELECT id, name, roll FROM students ORDER BY name ASC")
#     students = c.fetchall()

#     report_data = []
#     for sid, sname, sroll in students:
#         student_row = {'name': sname, 'roll': sroll, 'attendance': {}, 'present_count': 0, 'percentage': 0}
#         for sub in subjects:
#             c.execute("SELECT id FROM attendance WHERE student_id=? AND period=? AND day=? AND month=? AND year=?",
#                       (sid, sub, target_date, target_month, target_year))
#             is_present = c.fetchone()
#             if is_present:
#                 student_row['attendance'][sub] = 'p'
#                 student_row['present_count'] += 1
#             else:
#                 student_row['attendance'][sub] = 'a'
#         if len(subjects) > 0:
#             student_row['percentage'] = round((student_row['present_count'] / len(subjects)) * 100, 2)
#         report_data.append(student_row)
#     conn.close()
#     return render_template("pivot_history.html", subjects=subjects, report_data=report_data, current_date=f"{target_date} {target_month} ({day_name})")

# # --- Monthly Analytics & Fine Calculation ---
# @app.route("/view_history")
# def view_history():
#     target_month = request.args.get('month', datetime.datetime.now().strftime("%B"))
#     target_year = request.args.get('year', datetime.datetime.now().strftime("%Y"))
    
#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()
    
#     # Total Lectures: Number of unique subject sessions recorded in the month
#     c.execute("""SELECT COUNT(DISTINCT period || day) FROM attendance 
#                  WHERE month=? AND year=?""", (target_month, target_year))
#     total_lectures_held = c.fetchone()[0] or 1
    
#     # Fetch ID for checkbox toggle and is_paid for status
#     c.execute("SELECT id, name, roll, is_paid FROM students ORDER BY roll ASC")
#     students = c.fetchall()
    
#     fine_rate = get_config()["fine_per_lecture"]
#     analytics_data = []

#     for sid, sname, sroll, is_paid in students:
#         c.execute("SELECT COUNT(id) FROM attendance WHERE student_id=? AND month=? AND year=?", (sid, target_month, target_year))
#         attended = c.fetchone()[0]
#         missed = max(0, total_lectures_held - attended)
#         percentage = round((attended / total_lectures_held) * 100, 2)
#         fine = missed * fine_rate
        
#         analytics_data.append({
#             "id": sid,
#             "roll": sroll, 
#             "name": sname, 
#             "attended": attended, 
#             "total_scheduled": total_lectures_held, 
#             "percentage": percentage, 
#             "fine": fine,
#             "is_paid": is_paid
#         })
#     conn.close()
#     return render_template("view_history.html", analytics_data=analytics_data, config=get_config(), 
#                            current_month=target_month, current_year=target_year)

# # --- CSV Export ---
# @app.route("/export_report")
# def export_report():
#     target_month = request.args.get('month', datetime.datetime.now().strftime("%B"))
#     target_year = request.args.get('year', datetime.datetime.now().strftime("%Y"))
    
#     conn = sqlite3.connect(DB_PATH)
#     c = conn.cursor()
#     c.execute("SELECT COUNT(DISTINCT period || day) FROM attendance WHERE month=? AND year=?", (target_month, target_year))
#     total_lectures_held = c.fetchone()[0] or 1
#     c.execute("SELECT id, name, roll, is_paid FROM students ORDER BY roll ASC")
#     students = c.fetchall()
    
#     fine_rate = get_config()["fine_per_lecture"]
    
#     output = io.StringIO()
#     output.write(f"Attendance Report for {target_month} {target_year}\n")
#     output.write("Roll No,Name,Attended,Total Lectures,Percentage,Fine (INR),Status\n")
    
#     for sid, sname, sroll, is_paid in students:
#         c.execute("SELECT COUNT(id) FROM attendance WHERE student_id=? AND month=? AND year=?", (sid, target_month, target_year))
#         attended = c.fetchone()[0]
#         missed = max(0, total_lectures_held - attended)
#         percentage = round((attended / total_lectures_held) * 100, 2)
#         fine = missed * fine_rate
#         status = "Paid" if is_paid else "Unpaid"
#         output.write(f"{sroll},{sname},{attended},{total_lectures_held},{percentage}%,{fine},{status}\n")
    
#     conn.close()
#     mem = io.BytesIO()
#     mem.write(output.getvalue().encode())
#     mem.seek(0)
#     return send_file(mem, as_attachment=True, download_name=f"Attendance_Report_{target_month}.csv", mimetype="text/csv")

# # --- System Routes ---
# @app.route("/train_model")
# def train_model_route():
#     status = read_train_status()
#     if status.get("running"): return jsonify({"status": "already_running"}), 202
#     write_train_status({"running": True, "progress": 0, "message": "Starting training"})
#     t = threading.Thread(target=train_model_background, 
#                          args=(DATASET_DIR, lambda p, m: write_train_status({"running": True, "progress": p, "message": m})))
#     t.daemon = True
#     t.start()
#     return jsonify({"status": "started"})

# @app.route("/train_status")
# def train_status():
#     return jsonify(read_train_status())

# if __name__ == "__main__":
#     app.run(debug=True)


import os
import io
import math 
import shutil 
import threading
import sqlite3
import datetime
import json
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for

# Import from model.py
from model import train_model_background, extract_embedding_for_image, MODEL_PATH

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "attendance.db")
DATASET_DIR = os.path.join(APP_DIR, "dataset")
os.makedirs(DATASET_DIR, exist_ok=True)

TRAIN_STATUS_FILE = os.path.join(APP_DIR, "train_status.json")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")

app = Flask(__name__, static_folder="static", template_folder="templates")

# --- Configuration & Fine Logic ---
def get_config():
    if not os.path.exists(CONFIG_FILE):
        return {"fine_per_lecture": 50}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

# --- Database Initialization ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL, roll TEXT, class TEXT, 
                    section TEXT, reg_no TEXT, created_at TEXT,
                    is_paid INTEGER DEFAULT 0)""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    student_id INTEGER,
                    name TEXT, day TEXT, time TEXT, 
                    month TEXT, year TEXT, period TEXT)""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS timetable (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    day_of_week TEXT NOT NULL,
                    period_name TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL)""")

    # NEW: Table for Branches/Departments
    c.execute("""CREATE TABLE IF NOT EXISTS departments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    branch_name TEXT UNIQUE NOT NULL,
                    total_semesters INTEGER NOT NULL)""")

    # NEW: Table for Dynamic Camera Assignment
    c.execute("""CREATE TABLE IF NOT EXISTS camera_configs (
                    camera_id TEXT PRIMARY KEY,
                    branch TEXT,
                    semester_range TEXT)""") # Format: "1st,2nd,3rd"

    conn.commit()
    conn.close()

init_db()

# --- Control Panel & Branch Management ---
@app.route("/control_panel", methods=["GET", "POST"])
def control_panel():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == "POST":
        action = request.form.get("action")
        if action == "add_branch":
            branch = request.form.get("branch_name").upper()
            sems = request.form.get("total_sems")
            try:
                c.execute("INSERT INTO departments (branch_name, total_semesters) VALUES (?,?)", (branch, sems))
            except: pass 
        elif action == "assign_camera":
            cam_id = request.form.get("camera_id")
            branch = request.form.get("branch")
            sem_range = request.form.get("sem_range") # e.g. "1st,2nd"
            c.execute("INSERT OR REPLACE INTO camera_configs (camera_id, branch, semester_range) VALUES (?,?,?)", 
                      (cam_id, branch, sem_range))
        conn.commit()

    c.execute("SELECT * FROM departments")
    branches = c.fetchall()
    c.execute("SELECT * FROM camera_configs")
    configs = c.fetchall()
    conn.close()
    return render_template("control_panel.html", branches=branches, configs=configs)

# --- Helpers ---
def get_current_period():
    current_day = datetime.datetime.now().strftime("%A")
    now_time = datetime.datetime.now().strftime("%H:%M")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT period_name FROM timetable 
                 WHERE day_of_week = ? AND start_time <= ? AND end_time >= ?""", 
              (current_day, now_time, now_time))
    res = c.fetchone()
    conn.close()
    return res[0] if res else "Free Period"

def write_train_status(status_dict):
    with open(TRAIN_STATUS_FILE, "w") as f:
        json.dump(status_dict, f)

def read_train_status():
    if not os.path.exists(TRAIN_STATUS_FILE):
        return {"running": False, "progress": 0, "message": "Not trained"}
    with open(TRAIN_STATUS_FILE, "r") as f:
        return json.load(f)

# --- Routing ---
@app.route("/set_routine", methods=["GET", "POST"])
def set_routine():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == "POST":
        day_of_week = request.form.get("day_of_week")
        p_name = request.form.get("period_name")
        s_time = request.form.get("start_time")
        e_time = request.form.get("end_time")
        c.execute("INSERT INTO timetable (day_of_week, period_name, start_time, end_time) VALUES (?,?,?,?)", 
                  (day_of_week, p_name, s_time, e_time))
        conn.commit()
    c.execute("SELECT * FROM timetable ORDER BY start_time ASC")
    routine = c.fetchall()
    conn.close()
    return render_template("set_routine.html", routine=routine)

@app.route("/delete_period/<int:pid>")
def delete_period(pid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM timetable WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/get_active_period_name")
def get_active_period_name():
    return jsonify({"period": get_current_period()})

@app.route("/update_fine", methods=["POST"])
def update_fine():
    fine_amt = request.form.get("fine_amount", 50)
    with open(CONFIG_FILE, "w") as f:
        json.dump({"fine_per_lecture": int(fine_amt)}, f)
    return redirect(url_for('view_history'))

@app.route("/toggle_fine_status/<int:sid>", methods=["POST"])
def toggle_fine_status(sid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE students SET is_paid = NOT is_paid WHERE id = ?", (sid,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/manage_students")
def manage_students():
    branch = request.args.get('branch', 'CSE')
    semester = request.args.get('semester', '1st')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM students WHERE section=? AND class=? ORDER BY roll ASC", (branch, semester))
    student_list = c.fetchall()
    conn.close()
    return render_template("manage_students.html", students=student_list, branch=branch, semester=semester)

@app.route("/delete_student/<int:sid>", methods=["POST"])
def delete_student(sid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM students WHERE id=?", (sid,))
    shutil.rmtree(os.path.join(DATASET_DIR, str(sid)), ignore_errors=True)
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/add_student", methods=["GET", "POST"])
def add_student():
    if request.method == "GET":
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT branch_name FROM departments")
        branches = [b[0] for b in c.fetchall()]
        conn.close()
        return render_template("add_student.html", branches=branches)
    data = request.form
    name, roll, cls, sec, reg_no = data.get("name",""), data.get("roll",""), data.get("class",""), data.get("sec",""), data.get("reg_no","")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO students (name, roll, class, section, reg_no, created_at) VALUES (?,?,?,?,?,?)",
              (name, roll, cls, sec, reg_no, datetime.datetime.utcnow().isoformat()))
    sid = c.lastrowid
    conn.commit()
    conn.close()
    os.makedirs(os.path.join(DATASET_DIR, str(sid)), exist_ok=True)
    return jsonify({"student_id": sid})

@app.route("/upload_face", methods=["POST"])
def upload_face():
    sid = request.form.get("student_id")
    folder = os.path.join(DATASET_DIR, str(sid))
    os.makedirs(folder, exist_ok=True)
    files = request.files.getlist("images[]")
    for i, f in enumerate(files):
        fname = f"{datetime.datetime.utcnow().timestamp():.6f}_{i}.jpg"
        f.save(os.path.join(folder, fname))
    return jsonify({"saved": True})

@app.route("/mark_attendance")
def mark_attendance_page():
    return render_template("mark_attendance.html")

@app.route("/recognize_face", methods=["POST"])
def recognize_face():
    if "image" not in request.files: return jsonify({"recognized": False})
    
    camera_id = request.form.get("camera_id", "1")
    emb = extract_embedding_for_image(request.files["image"].stream)
    if emb is None: return jsonify({"recognized": False})
    
    from model import load_model_if_exists, predict_with_model
    clf = load_model_if_exists()
    if not clf: return jsonify({"recognized": False, "error": "Model not trained"})

    pred_label, conf = predict_with_model(clf, emb)
    if conf < 0.6: return jsonify({"recognized": False})

    sid = int(pred_label)
    active_period = get_current_period()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Dynamic Camera Validation from DB
    c.execute("SELECT branch, semester_range FROM camera_configs WHERE camera_id=?", (camera_id,))
    rule = c.fetchone()
    
    if not rule:
        conn.close()
        return jsonify({"recognized": True, "error": f"Camera {camera_id} not configured in Panel"})

    target_branch, target_sems = rule
    allowed_sems = target_sems.split(',')

    c.execute("SELECT name, class, section FROM students WHERE id=?", (sid,))
    student_data = c.fetchone()
    
    if not student_data:
        conn.close()
        return jsonify({"recognized": False})
        
    s_name, s_sem, s_branch = student_data
    
    # Verify Branch and Semester against dynamic rules
    if s_branch != target_branch or s_sem not in allowed_sems:
        conn.close()
        return jsonify({
            "recognized": True, 
            "name": s_name, 
            "error": f"Access Denied: Unit assigned to {target_branch} {target_sems}"
        })

    if active_period == "Free Period":
        conn.close()
        return jsonify({"recognized": True, "name": s_name, "period": "Free Period", "already_logged": True})

    now = datetime.datetime.now()
    c.execute("""SELECT id FROM attendance 
                 WHERE student_id=? AND period=? AND day=? AND month=? AND year=?""", 
              (sid, active_period, now.strftime("%d"), now.strftime("%B"), now.strftime("%Y")))
    already_marked = c.fetchone()

    if not already_marked:
        c.execute("""INSERT INTO attendance (student_id, name, day, time, month, year, period) 
                     VALUES (?,?,?,?,?,?,?)""",
                  (sid, s_name, now.strftime("%d"), now.strftime("%H:%M:%S"), 
                   now.strftime("%B"), now.strftime("%Y"), active_period))
        conn.commit()
    conn.close()
    return jsonify({"recognized": True, "name": s_name, "period": active_period, "already_logged": bool(already_marked), "confidence": float(conf)})

@app.route("/view_pivot_history")
def view_pivot_history():
    target_date = request.args.get('date', datetime.datetime.now().strftime("%d"))
    target_month = request.args.get('month', datetime.datetime.now().strftime("%B"))
    target_year = request.args.get('year', datetime.datetime.now().strftime("%Y"))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        date_obj = datetime.datetime.strptime(f"{target_date} {target_month} {target_year}", "%d %B %Y")
        day_name = date_obj.strftime("%A")
    except:
        day_name = datetime.datetime.now().strftime("%A")
    c.execute("SELECT period_name FROM timetable WHERE day_of_week = ? ORDER BY start_time ASC", (day_name,))
    subjects = [row[0] for row in c.fetchall()]
    c.execute("SELECT id, name, roll FROM students ORDER BY name ASC")
    students = c.fetchall()
    report_data = []
    for sid, sname, sroll in students:
        student_row = {'name': sname, 'roll': sroll, 'attendance': {}, 'present_count': 0, 'percentage': 0}
        for sub in subjects:
            c.execute("SELECT id FROM attendance WHERE student_id=? AND period=? AND day=? AND month=? AND year=?",
                      (sid, sub, target_date, target_month, target_year))
            is_present = c.fetchone()
            if is_present:
                student_row['attendance'][sub] = 'p'
                student_row['present_count'] += 1
            else:
                student_row['attendance'][sub] = 'a'
        if len(subjects) > 0:
            student_row['percentage'] = round((student_row['present_count'] / len(subjects)) * 100, 2)
        report_data.append(student_row)
    conn.close()
    return render_template("pivot_history.html", subjects=subjects, report_data=report_data, current_date=f"{target_date} {target_month} ({day_name})")

@app.route("/view_history")
def view_history():
    target_month = request.args.get('month', datetime.datetime.now().strftime("%B"))
    target_year = request.args.get('year', datetime.datetime.now().strftime("%Y"))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(DISTINCT period || day) FROM attendance WHERE month=? AND year=?", (target_month, target_year))
    total_lectures_held = c.fetchone()[0] or 1
    required_for_75 = math.ceil(total_lectures_held * 0.75)
    c.execute("SELECT id, name, roll, is_paid FROM students ORDER BY roll ASC")
    students = c.fetchall()
    fine_rate = get_config()["fine_per_lecture"]
    analytics_data = []
    for sid, sname, sroll, is_paid in students:
        c.execute("SELECT COUNT(id) FROM attendance WHERE student_id=? AND month=? AND year=?", (sid, target_month, target_year))
        attended = c.fetchone()[0]
        shortfall = max(0, required_for_75 - attended)
        percentage = round((attended / total_lectures_held) * 100, 2)
        fine = shortfall * fine_rate
        analytics_data.append({
            "id": sid, "roll": sroll, "name": sname, "attended": attended, 
            "total_scheduled": total_lectures_held, "required_for_75": required_for_75,
            "percentage": percentage, "fine": fine, "is_paid": is_paid
        })
    conn.close()
    return render_template("view_history.html", analytics_data=analytics_data, config=get_config(), 
                           current_month=target_month, current_year=target_year)

@app.route("/export_report")
def export_report():
    target_month = request.args.get('month', datetime.datetime.now().strftime("%B"))
    target_year = request.args.get('year', datetime.datetime.now().strftime("%Y"))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(DISTINCT period || day) FROM attendance WHERE month=? AND year=?", (target_month, target_year))
    total_lectures_held = c.fetchone()[0] or 1
    required_for_75 = math.ceil(total_lectures_held * 0.75)
    c.execute("SELECT id, name, roll, is_paid FROM students ORDER BY roll ASC")
    students = c.fetchall()
    fine_rate = get_config()["fine_per_lecture"]
    output = io.StringIO()
    output.write(f"Attendance Report for {target_month} {target_year}\n")
    output.write("Roll No,Name,Attended,Total Lectures,Percentage,Shortfall Fine (to 75%),Status\n")
    for sid, sname, sroll, is_paid in students:
        c.execute("SELECT COUNT(id) FROM attendance WHERE student_id=? AND month=? AND year=?", (sid, target_month, target_year))
        attended = c.fetchone()[0]
        shortfall = max(0, required_for_75 - attended)
        percentage = round((attended / total_lectures_held) * 100, 2)
        fine = shortfall * fine_rate
        status = "Paid" if is_paid else "Unpaid"
        output.write(f"{sroll},{sname},{attended},{total_lectures_held},{percentage}%,{fine},{status}\n")
    conn.close()
    mem = io.BytesIO()
    mem.write(output.getvalue().encode())
    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name=f"Attendance_Report_{target_month}.csv", mimetype="text/csv")

@app.route("/train_model")
def train_model_route():
    status = read_train_status()
    if status.get("running"): return jsonify({"status": "already_running"}), 202
    write_train_status({"running": True, "progress": 0, "message": "Starting training"})
    t = threading.Thread(target=train_model_background, 
                         args=(DATASET_DIR, lambda p, m: write_train_status({"running": True, "progress": p, "message": m})))
    t.daemon = True
    t.start()
    return jsonify({"status": "started"})

@app.route("/train_status")
def train_status():
    return jsonify(read_train_status())

if __name__ == "__main__":
    app.run(debug=True)