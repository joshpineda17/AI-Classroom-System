# database.py
import sqlite3
import datetime
import json
import logging
import threading

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
db_logger = logging.getLogger(__name__)

DATABASE_NAME = 'asistencia_ia.db'
db_lock = threading.Lock()

def _get_db_conn():
    conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def _create_tables(conn):
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS students (id TEXT PRIMARY KEY, nombre TEXT NOT NULL, apellido TEXT NOT NULL, registro_fecha TEXT, imagen_path TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS face_embeddings (student_id TEXT NOT NULL, embedding BLOB NOT NULL, FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE)")
    cursor.execute("CREATE TABLE IF NOT EXISTS attendance (student_id TEXT NOT NULL, periodo TEXT NOT NULL, fecha TEXT NOT NULL, timestamp TEXT NOT NULL, FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE)")
    cursor.execute("CREATE TABLE IF NOT EXISTS participation (student_id TEXT NOT NULL, periodo TEXT NOT NULL, timestamp TEXT NOT NULL, FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE)")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS learning_styles (
            student_id TEXT PRIMARY KEY,
            kolb_style TEXT,
            felder_styles TEXT,
            vak_style TEXT,
            completed_date TEXT,
            FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transcriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT NOT NULL,
            start_timestamp TEXT NOT NULL,
            end_timestamp TEXT NOT NULL,
            file_path TEXT NOT NULL,
            text_file_path TEXT,
            duration_seconds REAL NOT NULL,
            transcribed_text TEXT,
            enhanced_text TEXT
        )
    """)
    conn.commit()

def init_db():
    with db_lock, _get_db_conn() as conn:
        _create_tables(conn)

def add_student(id, nombre, apellido, imagen_path, embeddings):
    try:
        with db_lock, _get_db_conn() as conn:
            registro_fecha = datetime.date.today().isoformat()
            conn.execute("INSERT INTO students (id, nombre, apellido, registro_fecha, imagen_path) VALUES (?, ?, ?, ?, ?)", (id, nombre, apellido, registro_fecha, imagen_path))
            for emb in embeddings:
                conn.execute("INSERT INTO face_embeddings (student_id, embedding) VALUES (?, ?)", (id, json.dumps(emb)))
            return True
    except: return False

def delete_student_and_data(student_id):
    try:
        with db_lock, _get_db_conn() as conn:
            cursor = conn.execute("SELECT imagen_path FROM students WHERE id = ?", (student_id,))
            result = cursor.fetchone()
            imagen_path = result['imagen_path'] if result else None
            conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
            return imagen_path
    except: return None

def get_all_students():
    try:
        with _get_db_conn() as conn:
            students = {s['id']: dict(s, embeddings=[]) for s in conn.execute("SELECT id, nombre, apellido FROM students")}
            for emb in conn.execute("SELECT student_id, embedding FROM face_embeddings"):
                if emb['student_id'] in students:
                    students[emb['student_id']]['embeddings'].append(json.loads(emb['embedding']))
            return list(students.values())
    except: return []

def get_student_by_id(id):
    try:
        with _get_db_conn() as conn:
            row = conn.execute("SELECT * FROM students WHERE id = ?", (id,)).fetchone()
            return dict(row) if row else None
    except: return None

def add_learning_styles(student_id, kolb_style, felder_styles_dict, vak_style):
    try:
        with db_lock, _get_db_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO learning_styles (student_id, kolb_style, felder_styles, vak_style, completed_date) VALUES (?, ?, ?, ?, ?)",
                         (student_id, kolb_style, json.dumps(felder_styles_dict), vak_style, datetime.date.today().isoformat()))
            return True
    except: return False

def get_all_students_basic_info():
    try:
        with _get_db_conn() as conn:
            return [dict(row) for row in conn.execute("SELECT id, nombre, apellido, registro_fecha FROM students")]
    except: return []

def get_attendance_summary_by_period():
    try:
        with _get_db_conn() as conn:
            return [dict(row) for row in conn.execute("SELECT periodo, COUNT(DISTINCT student_id) as total FROM attendance WHERE fecha = ? GROUP BY periodo", (datetime.date.today().isoformat(),))]
    except: return []

def has_attended_today_in_period(student_id, periodo):
    try:
        with _get_db_conn() as conn:
            return conn.execute("SELECT 1 FROM attendance WHERE student_id = ? AND periodo = ? AND fecha = ? LIMIT 1", (student_id, periodo, datetime.date.today().isoformat())).fetchone() is not None
    except: return False

def record_attendance(student_id, periodo):
    try:
        with db_lock, _get_db_conn() as conn:
            conn.execute("INSERT INTO attendance (student_id, periodo, fecha, timestamp) VALUES (?, ?, ?, ?)", (student_id, periodo, datetime.date.today().isoformat(), datetime.datetime.now().isoformat()))
    except Exception as e:
        db_logger.error(f"Error al registrar asistencia para {student_id}: {e}")

def get_participation_summary_by_period():
    try:
        with _get_db_conn() as conn:
            return [dict(row) for row in conn.execute("SELECT periodo, COUNT(DISTINCT student_id) as total_participantes, COUNT(student_id) as total_participaciones FROM participation WHERE date(timestamp) = ? GROUP BY periodo", (datetime.date.today().isoformat(),))]
    except: return []

def get_all_students_with_learning_styles():
    try:
        with _get_db_conn() as conn:
            students = [dict(row) for row in conn.execute("SELECT s.id, s.nombre, s.apellido, ls.kolb_style, ls.felder_styles, ls.vak_style FROM students s LEFT JOIN learning_styles ls ON s.id = ls.student_id ORDER BY s.apellido, s.nombre")]
            for s in students:
                s['felder_styles'] = json.loads(s['felder_styles']) if s.get('felder_styles') else {}
            return students
    except: return []
    
def save_recording_metadata(class_name, start_timestamp, end_timestamp, file_path, text_file_path, duration_seconds, transcribed_text):
    try:
        with db_lock, _get_db_conn() as conn:
            conn.execute("INSERT INTO transcriptions (class_name, start_timestamp, end_timestamp, file_path, text_file_path, duration_seconds, transcribed_text) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (class_name, start_timestamp, end_timestamp, file_path, text_file_path, duration_seconds, transcribed_text))
            return True
    except: return False

def get_all_transcriptions():
    try:
        with _get_db_conn() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM transcriptions ORDER BY start_timestamp DESC")]
    except: return []

def delete_transcription(transcription_id):
    try:
        with db_lock, _get_db_conn() as conn:
            cursor = conn.execute("SELECT file_path, text_file_path FROM transcriptions WHERE id = ?", (transcription_id,))
            result = cursor.fetchone()
            file_path, text_file_path = (result['file_path'], result['text_file_path']) if result else (None, None)
            conn.execute("DELETE FROM transcriptions WHERE id = ?", (transcription_id,))
            return file_path, text_file_path
    except: return None, None

def get_student_details_with_styles(student_id):
    try:
        with _get_db_conn() as conn:
            row = conn.execute("SELECT s.*, ls.* FROM students s LEFT JOIN learning_styles ls ON s.id = ls.student_id WHERE s.id = ?", (student_id,)).fetchone()
            if not row: return None
            student_dict = dict(row)
            student_dict['felder_styles'] = json.loads(student_dict['felder_styles']) if student_dict.get('felder_styles') else {}
            return student_dict
    except: return None

def get_transcription_text(transcription_id):
    try:
        with _get_db_conn() as conn:
            result = conn.execute("SELECT transcribed_text FROM transcriptions WHERE id = ?", (transcription_id,)).fetchone()
            return result['transcribed_text'] if result else None
    except: return None

def save_enhanced_text(transcription_id, enhanced_text):
    try:
        with db_lock, _get_db_conn() as conn:
            conn.execute("UPDATE transcriptions SET enhanced_text = ? WHERE id = ?", (enhanced_text, transcription_id))
            return True
    except: return False