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
def api_students_list():
    """Devuelve lista normalizada y deshabilita caché."""
    raw = database.get_all_students_basic_info()  # puede ser lista de dicts o tuplas

    normed = []
    for s in (raw or []):
        # si viene como tupla (id,nombre,apellido,fecha) ajústalo aquí
        if isinstance(s, (list, tuple)) and len(s) >= 3:
            _id, _nom, _ape = s[0], s[1], s[2]
            _reg = s[3] if len(s) > 3 else None
            normed.append({
                "id": _id,
                "nombre": _nom or "",
                "apellido": _ape or "",
                "registro_fecha": _reg
            })
            continue
        # si viene como dict, normaliza claves
        _id = s.get("id") or s.get("student_id") or s.get("uid") or s.get("_id")
        _nom = s.get("nombre") or s.get("first_name") or s.get("name") or s.get("nombres") or ""
        _ape = s.get("apellido") or s.get("last_name") or s.get("surname") or s.get("apellidos") or ""
        _reg = (
            s.get("registro_fecha") or s.get("fecha_registro")
            or s.get("created_at") or s.get("createdAt") or s.get("registro")
        )
        normed.append({
            "id": _id, "nombre": _nom, "apellido": _ape, "registro_fecha": _reg
        })

    resp = jsonify({"students": normed})
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp

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

# --- Páginas y APIs para calibración y asignación de asientos ---

# Página para calibrar asientos dibujando cajas sobre el vídeo
@app.route('/calibrate_seats')
def calibrate_seats_page():
    return render_template('calibrate_seats.html')

# Página para asignar estudiantes a asientos existentes
@app.route('/assign_seats')
def assign_seats_page():
    return render_template('assign_seats.html')

# Iniciar monitor de calibración
@app.route('/start_calibration_monitor', methods=['POST'])
def start_calibration_monitor_route():
    return jsonify(core_logic.start_calibration_monitor())

# Detener monitor de calibración
@app.route('/stop_calibration_monitor', methods=['POST'])
def stop_calibration_monitor_route():
    return jsonify(core_logic.stop_calibration_monitor())

# Stream de vídeo para calibración
@app.route('/video_feed/calibrate')
def video_feed_calibrate():
    return Response(core_logic.generate_calibrate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Devuelve las cajas de asientos actuales
@app.route('/api/seat_boxes')
def api_seat_boxes():
    return jsonify(core_logic.get_seat_boxes())

# Devuelve las asignaciones de asientos actuales
@app.route('/api/seat_assignments')
def api_seat_assignments():
    return jsonify(core_logic.get_seat_assignments())

# Añade una nueva caja de asiento (x,y,w,h) y devuelve el ID generado
@app.route('/api/add_seat', methods=['POST'])
def api_add_seat():
    data = request.get_json(force=True)
    x = data.get('x'); y = data.get('y'); w = data.get('w'); h = data.get('h'); normalized = data.get('normalized', False)
    if None in (x, y, w, h):
        return jsonify({"success": False, "message": "Datos incompletos"}), 400
    try:
        seat_id = core_logic.add_seat_box(x, y, w, h, normalized=normalized)
        return jsonify({"success": True, "seat_id": seat_id})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# Elimina la última caja de asiento
@app.route('/api/remove_last_seat', methods=['POST'])
def api_remove_last_seat():
    success = core_logic.remove_last_seat_box()
    return jsonify({"success": success})

# Asigna un estudiante a un asiento
@app.route('/api/assign_seat', methods=['POST'])
def api_assign_seat():
    data = request.get_json(force=True)
    seat_id = data.get('seat_id')
    student_id = data.get('student_id')
    if not seat_id:
        return jsonify({"success": False, "message": "seat_id faltante"}), 400
    success = core_logic.assign_student_to_seat(student_id, seat_id)
    return jsonify({"success": success})

# Renombra un asiento existente
@app.route('/api/rename_seat', methods=['POST'])
def api_rename_seat():
    data = request.get_json(force=True)
    old_id = data.get('old_id')
    new_id = data.get('new_id')
    if not old_id or not new_id:
        return jsonify({"success": False, "message": "old_id y new_id son requeridos"}), 400
    success = core_logic.rename_seat(old_id, new_id)
    return jsonify({"success": success})

# --- Página y APIs para escaneo rápido de asistencia ---

@app.route('/quick_scan')
def quick_scan_page():
    """Página para escaneo rápido y confirmación de asistencia."""
    return render_template('quick_scan.html')

@app.route('/api/quick_scan', methods=['POST'])
def api_quick_scan():
    """Realiza un escaneo facial rápido de ~3 segundos y devuelve la mejor coincidencia."""
    try:
        result = core_logic.quick_scan_and_identify()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/quick_scan_image', methods=['POST'])
def api_quick_scan_image():
    """Recibe una imagen (base64) desde el navegador y devuelve el mejor match."""
    try:
        data = request.get_json(force=True)
        b64 = data.get('image_base64')
        if not b64:
            return jsonify({"success": False, "message": "image_base64 faltante"}), 400
        result = core_logic.quick_identify_from_base64(b64)
        return jsonify(result)
    except Exception as e:
        app_logger.exception("Error en /api/quick_scan_image")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/confirm_attendance', methods=['POST'])
def api_confirm_attendance():
    """Confirma la asistencia del estudiante indicado."""
    data = request.get_json(force=True)
    student_id = data.get('student_id')
    if not student_id:
        return jsonify({"success": False, "message": "student_id faltante"}), 400
    result = core_logic.confirm_attendance(student_id)
    return jsonify(result)

if __name__ == '__main__':
    # Ejecutar la aplicación sin recargador automático para evitar que el servidor
    # reinicie al detectar cambios en librerías de terceros (por ejemplo, durante
    # la transcripción de audio con Whisper).  El modo debug está desactivado
    # porque el reloader causa problemas en la grabación/transcripción.
    socketio.run(app, debug=False, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)