# app.py
from flask import Flask, render_template, request, jsonify, Response, send_from_directory, redirect, url_for
from flask_socketio import SocketIO
import core_logic
import database
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
app_logger = logging.getLogger(__name__)

app = Flask(__name__)
socketio = SocketIO(app)

app.config['RECORDS_FOLDER'] = 'records'

with app.app_context():
    database.init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/groups')
def group_formation_page():
    return render_template('groups.html')

@app.route('/questionnaire/<student_id>')
def show_questionnaire(student_id):
    student = database.get_student_by_id(student_id)
    if not student: return "Estudiante no encontrado.", 404
    return render_template('questionnaire.html', student=student, questions=core_logic.ALL_QUESTIONS)

@app.route('/student/<student_id>')
def student_details(student_id):
    student_info = database.get_student_details_with_styles(student_id)
    if not student_info:
        return "Estudiante no encontrado o sin datos de personalidad.", 404
    return render_template('student_detail.html', student=student_info)

@app.route('/register', methods=['POST'])
def register():
    student_id = request.form['student_id']
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    result = core_logic.register_student_from_camera(student_id, nombre, apellido)
    return jsonify(result)

@app.route('/submit_questionnaire/<student_id>', methods=['POST'])
def submit_questionnaire(student_id):
    responses = {int(k): int(v) for k, v in request.form.items()}
    kolb, felder, vak = core_logic.calculate_learning_styles(responses)
    database.add_learning_styles(student_id, kolb, felder, vak)
    return redirect(url_for('dashboard'))

# --- Rutas de Video Streaming ---
@app.route('/video_feed/attendance')
def video_feed_attendance():
    return Response(core_logic.generate_attendance_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed/pose')
def video_feed_pose():
    return Response(core_logic.generate_pose_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# --- Rutas de Control de Monitoreo ---
@app.route('/start_attendance_monitor', methods=['POST'])
def start_attendance_monitor(): return jsonify(core_logic.start_attendance_monitoring())

@app.route('/stop_attendance_monitor', methods=['POST'])
def stop_attendance_monitor(): return jsonify(core_logic.stop_attendance_monitoring())

@app.route('/start_pose_monitor', methods=['POST'])
def start_pose_monitor(): return jsonify(core_logic.start_pose_gesture_monitoring())

@app.route('/stop_pose_monitor', methods=['POST'])
def stop_pose_monitor(): return jsonify(core_logic.stop_pose_monitoring())

@app.route('/status')
def status():
    periodo, msg = core_logic.get_current_attendance_period()
    return jsonify(
        attendance_active=core_logic.get_attendance_monitor_status(),
        pose_active=core_logic.get_pose_monitor_status(),
        recording_active=core_logic.get_manual_recording_status(),
        periodo=periodo if periodo else msg
    )

# --- Rutas de Grabación y Transcripción ---
@app.route('/start_manual_recording', methods=['POST'])
def start_manual_recording(): return jsonify(core_logic.start_manual_audio_recording())

@app.route('/stop_manual_recording', methods=['POST'])
def stop_manual_recording():
    model_size = request.form.get('model_size', 'base')
    return jsonify(core_logic.stop_manual_audio_recording_and_transcribe(model_size))

@app.route('/api/enhance_transcription/<int:transcription_id>', methods=['POST'])
def enhance_transcription_route(transcription_id):
    result = core_logic.enhance_transcript_with_llm(transcription_id)
    return jsonify(result)

# --- Rutas de API para Datos ---
@app.route('/api/students_list')
def api_students_list(): return jsonify(database.get_all_students_basic_info())

@app.route('/api/delete_student/<student_id>', methods=['DELETE'])
def delete_student_route(student_id): return jsonify(core_logic.delete_student(student_id))

@app.route('/api/attendance_summary_today')
def api_attendance_summary_today(): return jsonify(database.get_attendance_summary_by_period())

@app.route('/api/participation_summary_today')
def api_participation_summary_today(): return jsonify(database.get_participation_summary_by_period())

@app.route('/api/transcriptions')
def api_transcriptions():
    transcriptions = database.get_all_transcriptions()
    for record in transcriptions:
        record['file_path'] = f"/records/{os.path.basename(record['file_path'])}" if record.get('file_path') else None
        record['text_file_path'] = f"/records/texts/{os.path.basename(record['text_file_path'])}" if record.get('text_file_path') else None
    return jsonify(transcriptions)

@app.route('/api/delete_transcription/<int:transcription_id>', methods=['DELETE'])
def delete_transcription_route(transcription_id):
    return jsonify(core_logic.delete_transcription_files(transcription_id))

@app.route('/records/<path:filename>')
def serve_record(filename): return send_from_directory(app.config['RECORDS_FOLDER'], filename, as_attachment=True)

@app.route('/records/texts/<path:filename>')
def serve_text_record(filename): return send_from_directory(os.path.join(app.config['RECORDS_FOLDER'], 'texts'), filename)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)