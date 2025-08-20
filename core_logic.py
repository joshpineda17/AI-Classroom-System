# core_logic.py
import cv2
import os
import time
import numpy as np
import face_recognition
import database
import threading
import datetime
import pyaudio
import wave
import whisper
import logging
import random
import llm_processor 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
cl_logger = logging.getLogger(__name__)

try:
    import tensorflow as tf
    import tensorflow_hub as hub
    MOVENET_MODEL = hub.load("https://tfhub.dev/google/movenet/multipose/lightning/1")
    INPUT_SIZE = 256
    cl_logger.info("✅ Modelo MoveNet MultiPose cargado exitosamente.")
except Exception as e:
    cl_logger.warning(f"🚨 ADVERTENCIA: TensorFlow o el modelo MoveNet no se pudo cargar ({e}). El monitoreo de pose no funcionará.")
    MOVENET_MODEL = None

REGISTRO_FACIAL_DIR = "rostros_registrados"
RECORDS_DIR = "records"
TEXTS_DIR = os.path.join(RECORDS_DIR, "texts")
os.makedirs(REGISTRO_FACIAL_DIR, exist_ok=True)
os.makedirs(RECORDS_DIR, exist_ok=True)
os.makedirs(TEXTS_DIR, exist_ok=True)

attendance_monitoring_active = False
pose_monitoring_active = False
is_recording_active = False
audio_recording_thread = None
audio_frames = []
p_audio_instance = None

PERIODOS_REGISTRO = [("Clase 1", "06:00", "07:50"), ("Clase 2", "08:00", "09:40")]
KEYPOINT_DICT = {'nose': 0, 'left_eye': 1, 'right_eye': 2, 'left_ear': 3, 'right_ear': 4, 'left_shoulder': 5, 'right_shoulder': 6, 'left_elbow': 7, 'right_elbow': 8, 'left_wrist': 9, 'right_wrist': 10, 'left_hip': 11, 'right_hip': 12, 'left_knee': 13, 'right_knee': 14, 'left_ankle': 15, 'right_ankle': 16}
EDGES = [(0, 1), (0, 2), (1, 3), (2, 4), (0, 5), (0, 6), (5, 7), (7, 9), (6, 8), (8, 10), (5, 6), (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)]

KOLB_QUESTIONS = {1: ("Prefiero trabajar en equipo para generar ideas y escuchar otras perspectivas.", "Activo/Divergente"),2: ("Me gusta seguir un plan lógico y estructurado para aprender.", "Asimilativo"),3: ("Disfruto aplicar la teoría directamente a problemas prácticos.", "Convergente"),4: ("Suelo basar mis decisiones en la intuición y en la experiencia de otros.", "Acomodador"),5: ("Me entusiasma probar actividades nuevas aunque no las domine.", "Activo/Divergente"),6: ("Me concentro en comprender a fondo los conceptos antes de actuar.", "Asimilativo"),7: ("Prefiero resolver problemas técnicos más que debatir temas sociales.", "Convergente"),8: ("Tomo decisiones rápidamente aunque no tenga toda la información.", "Acomodador"),9: ("Me gusta imaginar diferentes formas de resolver un mismo problema.", "Activo/Divergente"),10: ("Prefiero estudiar con lecturas, conferencias o clases magistrales.", "Asimilativo"),11: ("Aprendo mejor haciendo pruebas y experimentos prácticos.", "Convergente"),12: ("Me gusta coordinar ideas de otros para formar una propuesta única.", "Acomodador")}
KOLB_MAP = {"Activo/Divergente": [1, 5, 9], "Asimilativo": [2, 6, 10], "Convergente": [3, 7, 11], "Acomodador": [4, 8, 12]}
FELDER_QUESTIONS = {101: ("Prefiero aprender con ejemplos concretos antes que con teorías abstractas.", "Sensitivo"),102: ("Me gusta descubrir nuevas ideas aunque sean poco prácticas.", "Intuitivo"),103: ("Me resulta fácil recordar detalles específicos de lo que aprendo.", "Sensitivo"),104: ("Prefiero aprender conceptos generales antes de los detalles.", "Intuitivo"),201: ("Entiendo mejor cuando la información está en diagramas o gráficos.", "Visual"),202: ("Prefiero leer o escuchar explicaciones detalladas.", "Verbal"),203: ("Recuerdo más fácilmente imágenes que palabras.", "Visual"),204: ("Aprendo mejor leyendo textos o escuchando a alguien explicarlo.", "Verbal"),301: ("Aprendo más cuando participo en debates o actividades en grupo.", "Activo"),302: ("Prefiero pensar en silencio antes de compartir mis ideas.", "Reflexivo"),303: ("Comprendo mejor si aplico lo aprendido de inmediato.", "Activo"),304: ("Prefiero analizar la información antes de actuar.", "Reflexivo"),401: ("Aprendo paso a paso, siguiendo un orden lógico.", "Secuencial"),402: ("Puedo comprender un tema saltando de un aspecto a otro.", "Global"),403: ("Necesito completar un paso antes de pasar al siguiente.", "Secuencial"),404: ("Entiendo un tema aunque no siga un orden específico.", "Global")}
FELDER_DIMENSIONS = {"Sensitivo/Intuitivo": (["Sensitivo"], ["Intuitivo"], [101, 102, 103, 104]),"Visual/Verbal": (["Visual"], ["Verbal"], [201, 202, 203, 204]),"Activo/Reflexivo": (["Activo"], ["Reflexivo"], [301, 302, 303, 304]),"Secuencial/Global": (["Secuencial"], ["Global"], [401, 402, 403, 404])}
VAK_QUESTIONS = {901: ("Recuerdo mejor lo que veo que lo que escucho.", "Visual"),902: ("Me gusta usar colores, gráficos y diagramas al estudiar.", "Visual"),903: ("Prefiero instrucciones escritas antes que orales.", "Visual"),911: ("Entiendo mejor cuando escucho explicaciones.", "Auditivo"),912: ("Me gusta estudiar hablando o escuchando grabaciones.", "Auditivo"),913: ("Prefiero explicaciones orales a leer un texto.", "Auditivo"),921: ("Comprendo mejor si practico lo que aprendo.", "Kinestésico"),922: ("Me gusta manipular objetos o hacer experimentos.", "Kinestésico"),923: ("Aprendo más en actividades donde puedo moverme o interactuar físicamente.", "Kinestésico")}
VAK_MAP = {"Visual": [901, 902, 903], "Auditivo": [911, 912, 913], "Kinestésico": [921, 922, 923]}
ALL_QUESTIONS = {**KOLB_QUESTIONS, **FELDER_QUESTIONS, **VAK_QUESTIONS}

def calculate_learning_styles(responses):
    kolb_scores = {k: sum(responses.get(q, 0) for q in qs) for k, qs in KOLB_MAP.items()}
    kolb_dominant = max(kolb_scores, key=kolb_scores.get) if kolb_scores else "N/A"
    felder_dominant = {}
    for dim, (pA, pB, qids) in FELDER_DIMENSIONS.items():
        a = sum(responses.get(qid, 0) for qid in qids if FELDER_QUESTIONS[qid][1] == pA[0])
        b = sum(responses.get(qid, 0) for qid in qids if FELDER_QUESTIONS[qid][1] == pB[0])
        felder_dominant[dim] = pA[0] if a >= b else pB[0]
    vak_scores = {k: sum(responses.get(q, 0) for q in qs) for k, qs in VAK_MAP.items()}
    vak_dominant = max(vak_scores, key=vak_scores.get) if vak_scores else "N/A"
    return kolb_dominant, felder_dominant, vak_dominant

def form_smart_groups(num_groups):
    students = database.get_all_students_with_learning_styles()
    eligible = [s for s in students if s.get('kolb_style')]
    if not eligible or num_groups <= 0 or num_groups > len(eligible):
        return [], "No hay suficientes estudiantes evaluados para formar los grupos."
    random.shuffle(eligible)
    groups = [[] for _ in range(num_groups)]
    for student in eligible:
        groups.sort(key=len)
        groups[0].append(student)
    return groups, None

def get_current_attendance_period():
    now = datetime.datetime.now()
    for name, start_str, end_str in PERIODOS_REGISTRO:
        start_time = datetime.datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.datetime.strptime(end_str, "%H:%M").time()
        if start_time <= now.time() <= end_time: return name, None
    return None, "Fuera de horario de clase"

def register_student_from_camera(student_id, nombre, apellido):
    if database.get_student_by_id(student_id):
        return {"success": False, "message": f"Error: El ID '{student_id}' ya está registrado."}
    cap = cv2.VideoCapture(0)
    if not cap.isOpened(): return {"success": False, "message": "Error: Cámara no disponible."}
    
    captured_embeddings, required_embeddings, start_time = [], 5, time.time()
    try:
        while len(captured_embeddings) < required_embeddings and (time.time() - start_time) < 20:
            ret, frame = cap.read()
            if not ret: continue
            frame_display = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame_display, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            cv2.putText(frame_display, f"Mire a la camara... {len(captured_embeddings)}/{required_embeddings}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            if face_locations:
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                if face_encodings:
                    captured_embeddings.append(face_encodings[0].tolist())
                    time.sleep(0.5)
            cv2.imshow('Registro Facial', frame_display)
            if cv2.waitKey(1) & 0xFF == ord('q'): break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    if len(captured_embeddings) >= required_embeddings:
        filepath = os.path.join(REGISTRO_FACIAL_DIR, f"{student_id}_{nombre}.jpg")
        if database.add_student(student_id, nombre, apellido, filepath, captured_embeddings):
            return {"success": True, "action": "redirect_questionnaire", "student_id": student_id, "message": "Registro facial completado. Ahora serás dirigido al cuestionario."}
        return {"success": False, "message": "Error al guardar en la base de datos."}
    return {"success": False, "message": "No se capturaron suficientes rostros."}

def generate_attendance_frames():
    global attendance_monitoring_active
    students_data = database.get_all_students()
    if not students_data:
        cl_logger.warning("No hay estudiantes registrados para iniciar monitoreo de asistencia.")
        return

    known_face_encodings = [np.array(emb) for s in students_data for emb in s['embeddings']]
    known_face_metadata = [{'id': s['id'], 'nombre': s['nombre']} for s in students_data for _ in s['embeddings']]

    cap = cv2.VideoCapture(0)
    cl_logger.info("Iniciando stream de ASISTENCIA.")

    face_locations = []
    face_names = []
    frame_count = 0

    while cap.isOpened() and attendance_monitoring_active:
        ret, frame = cap.read()
        if not ret: break
        
        frame_display = cv2.flip(frame, 1)

        if frame_count % 5 == 0:
            small_frame = cv2.resize(frame_display, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            face_names = []

            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                name = "Desconocido"
                
                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                if len(face_distances) > 0:
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        metadata = known_face_metadata[best_match_index]
                        student_id = metadata['id']
                        confidence = (1.0 - face_distances[best_match_index]) * 100
                        name = f"{metadata['nombre']} ({confidence:.1f}%)"
                        
                        periodo, _ = get_current_attendance_period()
                        if periodo and not database.has_attended_today_in_period(student_id, periodo):
                            database.record_attendance(student_id, periodo)
                            cl_logger.info(f"Asistencia registrada para {metadata['nombre']} en {periodo}")
                
                face_names.append(name)

        frame_count += 1

        for (top, right, bottom, left), name in zip(face_locations, face_names):
            top *= 4; right *= 4; bottom *= 4; left *= 4
            color = (0, 255, 0) if name != "Desconocido" else (0, 0, 255)
            cv2.rectangle(frame_display, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame_display, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            cv2.putText(frame_display, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)

        _, buffer = cv2.imencode('.jpg', frame_display)
        yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    cap.release()
    cl_logger.info("Stream de ASISTENCIA detenido.")

def movenet(input_image):
    input_image = tf.cast(tf.image.resize_with_pad(input_image, INPUT_SIZE, INPUT_SIZE), dtype=tf.int32)
    outputs = MOVENET_MODEL.signatures['serving_default'](input_image)
    return outputs['output_0'].numpy()

def generate_pose_frames():
    global pose_monitoring_active
    if not MOVENET_MODEL: return
    cap = cv2.VideoCapture(0)
    cl_logger.info("Iniciando stream de POSE.")
    while cap.isOpened() and pose_monitoring_active:
        ret, frame = cap.read()
        if not ret: break
        frame_display = cv2.flip(frame, 1)
        h, w, _ = frame_display.shape
        
        results = movenet(np.expand_dims(frame_display, axis=0))
        
        for person in np.squeeze(results):
            if person[55] < 0.35: continue
            keypoints = person[:51].reshape((17, 3))
            
            for edge in EDGES:
                p1, p2 = edge; y1, x1, c1 = keypoints[p1]; y2, x2, c2 = keypoints[p2]
                if c1 > 0.3 and c2 > 0.3:
                    cv2.line(frame_display, (int(x1 * w), int(y1 * h)), (int(x2 * w), int(y2 * h)), (255, 255, 0), 2)

            left_wrist_y, left_wrist_x, left_wrist_c = keypoints[KEYPOINT_DICT['left_wrist']]
            left_shoulder_y, _, left_shoulder_c = keypoints[KEYPOINT_DICT['left_shoulder']]
            right_wrist_y, right_wrist_x, right_wrist_c = keypoints[KEYPOINT_DICT['right_wrist']]
            right_shoulder_y, _, right_shoulder_c = keypoints[KEYPOINT_DICT['right_shoulder']]

            left_hand_up = left_wrist_c > 0.3 and left_shoulder_c > 0.3 and left_wrist_y < left_shoulder_y
            right_hand_up = right_wrist_c > 0.3 and right_shoulder_c > 0.3 and right_wrist_y < right_shoulder_y

            if left_hand_up or right_hand_up:
                text_pos_y = float('inf'); text_pos_x = 0
                if left_hand_up:
                    lx_px, ly_px = int(left_wrist_x * w), int(left_wrist_y * h)
                    cv2.circle(frame_display, (lx_px, ly_px), 20, (0, 255, 255), 5)
                    if ly_px < text_pos_y: text_pos_y, text_pos_x = ly_px, lx_px
                if right_hand_up:
                    rx_px, ry_px = int(right_wrist_x * w), int(right_wrist_y * h)
                    cv2.circle(frame_display, (rx_px, ry_px), 20, (0, 255, 255), 5)
                    if ry_px < text_pos_y: text_pos_y, text_pos_x = ry_px, rx_px
                cv2.putText(frame_display, "Participando!", (text_pos_x - 50, text_pos_y - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        _, buffer = cv2.imencode('.jpg', frame_display)
        yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    cap.release()
    cl_logger.info("Stream de POSE detenido.")

def start_attendance_monitoring():
    global attendance_monitoring_active
    if attendance_monitoring_active or pose_monitoring_active: return {"success": False, "message": "Otro monitoreo ya está activo."}
    attendance_monitoring_active = True
    return {"success": True, "message": "Monitoreo de asistencia iniciado."}

def stop_attendance_monitoring():
    global attendance_monitoring_active
    attendance_monitoring_active = False
    return {"success": True, "message": "Monitoreo de asistencia detenido."}

def start_pose_gesture_monitoring():
    global pose_monitoring_active
    if pose_monitoring_active or attendance_monitoring_active: return {"success": False, "message": "Otro monitoreo ya está activo."}
    pose_monitoring_active = True
    return {"success": True, "message": "Monitoreo de clase iniciado."}

def stop_pose_monitoring():
    global pose_monitoring_active
    pose_monitoring_active = False
    return {"success": True, "message": "Monitoreo de clase detenido."}

def get_attendance_monitor_status(): return attendance_monitoring_active
def get_pose_monitor_status(): return pose_monitoring_active

def delete_student(student_id):
    try:
        image_path = database.delete_student_and_data(student_id)
        if image_path and os.path.exists(image_path): os.remove(image_path)
        return {"success": True, "message": f"Estudiante {student_id} eliminado."}
    except Exception as e:
        return {"success": False, "message": f"Error al eliminar: {e}"}

def _record_audio_loop():
    global audio_frames, is_recording_active, p_audio_instance
    CHUNK=1024; p_audio_instance = pyaudio.PyAudio()
    stream = p_audio_instance.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=CHUNK)
    audio_frames = []
    cl_logger.info("Grabación de audio iniciada.")
    while is_recording_active: audio_frames.append(stream.read(CHUNK))
    cl_logger.info("Grabación de audio detenida.")
    stream.stop_stream(); stream.close(); p_audio_instance.terminate()

def start_manual_audio_recording():
    global is_recording_active, audio_recording_thread
    if is_recording_active: return {"success": False, "message": "La grabación ya está en curso."}
    is_recording_active = True
    audio_recording_thread = threading.Thread(target=_record_audio_loop, daemon=True)
    audio_recording_thread.start()
    return {"success": True, "message": "Grabación de audio iniciada."}

def stop_manual_audio_recording_and_transcribe(model_size="base"):
    global is_recording_active, audio_frames
    if not is_recording_active: return {"success": False, "message": "No hay grabación activa."}
    is_recording_active = False
    if audio_recording_thread: audio_recording_thread.join(timeout=5)

    if not audio_frames: return {"success": False, "message": "No se capturó audio."}

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename_base = f"manual_rec_{timestamp}"
    wav_filepath = os.path.join(RECORDS_DIR, f"{filename_base}.wav")
    with wave.open(wav_filepath, 'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16)); wf.setframerate(44100); wf.writeframes(b''.join(audio_frames))

    try:
        model = whisper.load_model(model_size)
        result = model.transcribe(wav_filepath, language="es")
        transcribed_text = result["text"] or "No se detectó audio."
        
        txt_filepath = os.path.join(TEXTS_DIR, f"{filename_base}.txt")
        with open(txt_filepath, 'w', encoding='utf-8') as f: f.write(transcribed_text)
        
        duration = len(audio_frames) * 1024 / 44100
        start_time = datetime.datetime.now() - datetime.timedelta(seconds=duration)
        database.save_recording_metadata("Grabacion Manual", start_time.isoformat(), datetime.datetime.now().isoformat(), wav_filepath, txt_filepath, duration, transcribed_text)
        return {"success": True, "message": "Grabación finalizada y transcrita."}
    except Exception as e:
        return {"success": False, "message": f"Error en transcripción: {e}"}

def get_manual_recording_status(): return is_recording_active

def delete_transcription_files(transcription_id):
    try:
        wav_path, txt_path = database.delete_transcription(transcription_id)
        if wav_path and os.path.exists(wav_path): os.remove(wav_path)
        if txt_path and os.path.exists(txt_path): os.remove(txt_path)
        return {"success": True, "message": "Transcripción eliminada."}
    except Exception as e:
        return {"success": False, "message": f"Error al eliminar archivos: {e}"}
        
def enhance_transcript_with_llm(transcription_id):
    original_text = database.get_transcription_text(transcription_id)
    if not original_text:
        return {"success": False, "message": "Texto de transcripción no encontrado."}
    
    cl_logger.info(f"Iniciando mejora de IA para transcripción ID: {transcription_id}")
    try:
        enhanced_text = llm_processor.enrich_text(original_text)
        database.save_enhanced_text(transcription_id, enhanced_text)
        cl_logger.info(f"Mejora de IA completada para transcripción ID: {transcription_id}")
        return {"success": True, "enhanced_text": enhanced_text}
    except Exception as e:
        cl_logger.error(f"Error durante la mejora con LLM: {e}")
        return {"success": False, "message": f"Error del procesador IA: {e}"}