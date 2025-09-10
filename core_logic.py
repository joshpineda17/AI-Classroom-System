import base64
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
import json  # Para cargar configuraciones de asientos

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

# Indicador para el monitor de calibración.  Cuando es True, el generador de
# frames de calibración transmitirá la cámara con las cajas de asientos
# superpuestas. Este monitor se gestiona mediante las funciones
# start_calibration_monitor() y stop_calibration_monitor().
calibration_monitor_active = False

PERIODOS_REGISTRO = [("Clase 1", "06:00", "07:50"), ("Clase 2", "08:00", "09:40")]
KEYPOINT_DICT = {'nose': 0, 'left_eye': 1, 'right_eye': 2, 'left_ear': 3, 'right_ear': 4, 'left_shoulder': 5, 'right_shoulder': 6, 'left_elbow': 7, 'right_elbow': 8, 'left_wrist': 9, 'right_wrist': 10, 'left_hip': 11, 'right_hip': 12, 'left_knee': 13, 'right_knee': 14, 'left_ankle': 15, 'right_ankle': 16}
EDGES = [(0, 1), (0, 2), (1, 3), (2, 4), (0, 5), (0, 6), (5, 7), (7, 9), (6, 8), (8, 10), (5, 6), (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)]

# ------------------------------
# Configuración de asientos y participación
#
# El sistema puede cargar un archivo de asientos y otro de asignaciones
# para superponer cajas predefinidas en el streaming de pose.  También
# permite asignar estudiantes a asientos y registrar participaciones.

SEATS_FILE = os.path.join('data', 'seats.json')
SEAT_ASSIGNMENTS_FILE = os.path.join('data', 'seat_assignments.json')


def _rect_pixels(rect, normalized, frame_shape):
    """Convierte un rect [x,y,w,h] a pixeles si está normalizado."""
    x,y,w,h = rect
    if normalized:
        H, W = frame_shape[:2]
        return int(x*W), int(y*H), int(w*W), int(h*H)
    return int(x), int(y), int(w), int(h)

# Estructuras globales que se inicializarán mediante load_seat_config().
seat_boxes = []          # Lista de dicts con keys: seat_id, rect [x,y,w,h]
seat_assignments = {}    # seat_id -> student_id
participation_counts = {}  # seat_id -> int (participaciones acumuladas)
seat_last_participation_time = {}  # seat_id -> datetime

# Tiempo en segundos que debe pasar entre puntos consecutivos para un mismo asiento
PARTICIPATION_COOLDOWN = 3

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


# -----------------------------------------------------------------------------
# Gestión de asientos y participación
#
# Las siguientes funciones permiten cargar las cajas de asientos desde un archivo
# JSON, asignar estudiantes a asientos específicos y llevar un registro de
# participaciones.  Esta funcionalidad se utiliza opcionalmente en el
# streaming de pose para reconocer gestos y otorgar puntos a los estudiantes
# asignados a cada asiento.

def load_seat_config():
    """Carga la configuración de asientos y asignaciones desde disco.

    Lee los archivos definidos en SEATS_FILE y SEAT_ASSIGNMENTS_FILE.  Si
    data/seats.json no existe o está vacío, seat_boxes permanece vacío y la
    funcionalidad de asientos estará inactiva.
    """
    global seat_boxes, seat_assignments, participation_counts
    # Cargar cajas de asientos
    if os.path.exists(SEATS_FILE):
        try:
            with open(SEATS_FILE, 'r', encoding='utf-8') as f:
                seat_boxes = json.load(f)
        except Exception as e:
            cl_logger.warning(f"No se pudo cargar {SEATS_FILE}: {e}")
            seat_boxes = []
    else:
        seat_boxes = []
    # Cargar asignaciones si existen
    if os.path.exists(SEAT_ASSIGNMENTS_FILE):
        try:
            with open(SEAT_ASSIGNMENTS_FILE, 'r', encoding='utf-8') as f:
                seat_assignments.update(json.load(f))
        except Exception:
            seat_assignments.clear()
    else:
        seat_assignments.clear()
    # Inicializar contadores de participaciones
    participation_counts.clear()
    for seat in seat_boxes:
        participation_counts[seat.get('seat_id')] = 0

# --- Funciones auxiliares para asientos ---

def save_seat_boxes():
    """Guarda la lista global de seat_boxes en el archivo SEATS_FILE.

    También asegura que exista el directorio de datos.
    """
    try:
        os.makedirs(os.path.dirname(SEATS_FILE), exist_ok=True)
        with open(SEATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(seat_boxes, f, indent=4)
        cl_logger.info(f"Asientos guardados en {SEATS_FILE}.")
    except Exception as e:
        cl_logger.warning(f"No se pudo guardar los asientos: {e}")


def get_seat_boxes():
    """Devuelve la lista actual de asientos.

    Carga la configuración si aún no se ha inicializado.
    """
    if not seat_boxes:
        load_seat_config()
    return seat_boxes


def get_seat_assignments():
    """Devuelve las asignaciones de asientos actuales."""
    if not seat_assignments:
        load_seat_config()
    return seat_assignments


def add_seat_box(x, y, w, h, normalized: bool=False) -> str:
    """Agrega un nuevo asiento a la configuración.

    El identificador de asiento se genera automáticamente como "Pupitre N",
    donde N es el número siguiente basado en la longitud de seat_boxes.
    Se actualiza inmediatamente la configuración en disco y las asignaciones.

    Args:
        x, y, w, h (int): Coordenadas y tamaño del rectángulo en píxeles.

    Returns:
        str: El seat_id generado para el nuevo asiento.
    """
    # Asegurar que la configuración esté cargada
    if not seat_boxes:
        load_seat_config()
    seat_id = f"Pupitre {len(seat_boxes) + 1}"
    seat_boxes.append({"seat_id": seat_id, "rect": [float(x), float(y), float(w), float(h)], "normalized": bool(normalized)})
    # Inicializar contador y asignación
    participation_counts[seat_id] = 0
    seat_assignments[seat_id] = None
    # Guardar a disco
    save_seat_boxes()
    save_seat_assignments()
    return seat_id


def remove_last_seat_box() -> bool:
    """Elimina el último asiento de la lista y actualiza disco.

    Returns:
        bool: True si se eliminó un asiento, False si no había asientos.
    """
    if not seat_boxes:
        return False
    removed = seat_boxes.pop()
    sid = removed.get('seat_id')
    # Eliminar asignación y contador
    seat_assignments.pop(sid, None)
    participation_counts.pop(sid, None)
    # Guardar cambios
    save_seat_boxes()
    save_seat_assignments()
    cl_logger.info(f"Se eliminó la caja de asiento {sid}")
    return True


def start_calibration_monitor() -> dict:
    """Inicia el monitor de calibración de asientos.

    Retorna un diccionario de éxito similar a otros monitores para ser
    consumido por el frontend.  Si otro monitor (asistencia o pose)
    está activo, no se inicia.
    """
    global calibration_monitor_active
    if calibration_monitor_active or attendance_monitoring_active or pose_monitoring_active:
        return {"success": False, "message": "Otro monitoreo ya está activo."}
    calibration_monitor_active = True
    cl_logger.info("Monitoreo de calibración iniciado.")
    return {"success": True, "message": "Monitoreo de calibración iniciado."}


def stop_calibration_monitor() -> dict:
    """Detiene el monitor de calibración de asientos."""
    global calibration_monitor_active
    calibration_monitor_active = False
    cl_logger.info("Monitoreo de calibración detenido.")
    return {"success": True, "message": "Monitoreo de calibración detenido."}


def generate_calibrate_frames():
    """Genera frames con las cajas de asientos superpuestas para calibración.

    Este generador se utiliza para transmitir en streaming las imágenes de la
    cámara con las cajas de asientos dibujadas.  Requiere que el monitor de
    calibración esté activo.  Cada iteración verifica seat_boxes para
    reflejar cambios en tiempo real.
    """
    global calibration_monitor_active
    # Cargar asientos iniciales
    load_seat_config()
    cap = cv2.VideoCapture(0)
    cl_logger.info("Iniciando stream de CALIBRACIÓN.")
    while cap.isOpened() and calibration_monitor_active:
        ret, frame = cap.read()
        if not ret:
            break
        frame_display = cv2.flip(frame, 1)
        # Dibujar cajas de asientos
        for seat in seat_boxes:
            x, y, w_s, h_s = _rect_pixels(seat.get('rect'), seat.get('normalized', False), frame.shape if 'frame' in locals() else frame_display.shape)
            sid = seat.get('seat_id')
            cv2.rectangle(frame_display, (x, y), (x + w_s, y + h_s), (0, 255, 0), 2)
            cv2.putText(frame_display, sid, (x, max(0, y - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        # Codificar y enviar frame
        _, buffer = cv2.imencode('.jpg', frame_display)
        yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    cap.release()
    cl_logger.info("Stream de CALIBRACIÓN detenido.")


def save_seat_assignments():
    """Guarda las asignaciones de asientos en disco."""
    try:
        os.makedirs(os.path.dirname(SEAT_ASSIGNMENTS_FILE), exist_ok=True)
        with open(SEAT_ASSIGNMENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(seat_assignments, f, indent=4)
    except Exception as e:
        cl_logger.warning(f"No se pudo guardar asignaciones en {SEAT_ASSIGNMENTS_FILE}: {e}")


def assign_student_to_seat(student_id: str, seat_id: str) -> bool:
    """Asigna un estudiante a un asiento.

    Args:
        student_id: ID del estudiante registrado en la base de datos.
        seat_id: Identificador del asiento según data/seats.json.

    Returns:
        True si la asignación se realizó correctamente, False si el asiento no
        existe.
    """
    # Verificar que exista el asiento
    if not any(s.get('seat_id') == seat_id for s in seat_boxes):
        return False
    # Permitir desasignar si student_id es vacío o None
    if not student_id:
        seat_assignments.pop(seat_id, None)
    else:
        seat_assignments[seat_id] = student_id
    save_seat_assignments()
    return True


def rename_seat(old_id: str, new_id: str) -> bool:
    """Renombra un asiento existente.

    Este método modifica el identificador de un asiento en `seat_boxes` y actualiza
    las estructuras de asignaciones y contadores para reflejar el nuevo id.

    Args:
        old_id: Id actual del asiento que se desea renombrar.
        new_id: Nuevo identificador a asignar. Debe ser único.

    Returns:
        True si el renombrado se realizó con éxito, False en caso contrario (por
        ejemplo, si el id viejo no existe o el nuevo ya está en uso).
    """
    # Cargar configuración si aún no se ha hecho
    if not seat_boxes:
        load_seat_config()
    # Verificar que exista el asiento y que el nuevo id no esté en uso
    if not any(seat.get('seat_id') == old_id for seat in seat_boxes):
        return False
    if any(seat.get('seat_id') == new_id for seat in seat_boxes):
        return False
    # Renombrar en seat_boxes
    for seat in seat_boxes:
        if seat.get('seat_id') == old_id:
            seat['seat_id'] = new_id
            break
    # Actualizar asignaciones
    if old_id in seat_assignments:
        seat_assignments[new_id] = seat_assignments.pop(old_id)
    # Actualizar contadores y timestamps
    if old_id in participation_counts:
        participation_counts[new_id] = participation_counts.pop(old_id)
    if old_id in seat_last_participation_time:
        seat_last_participation_time[new_id] = seat_last_participation_time.pop(old_id)
    # Guardar cambios a disco
    save_seat_boxes()
    save_seat_assignments()
    return True

def quick_scan_and_identify():
    """
    Realiza un escaneo facial rápido utilizando la cámara web y devuelve
    la mejor coincidencia encontrada en aproximadamente 3 segundos.

    Retorna un diccionario con keys:
      - success: bool
      - student_id: id del estudiante reconocido o None
      - student_name: nombre completo del estudiante reconocido o None
      - confidence: porcentaje de confianza (0-100) de la coincidencia
      - message: mensaje de error en caso de fallo
    """
    # Obtener estudiantes registrados y sus embeddings
    students_data = database.get_all_students()
    if not students_data:
        return {"success": False, "message": "No hay estudiantes registrados para reconocer."}
    # Construir lista de encodings y metadatos
    known_face_encodings = []
    known_metadata = []
    for s in students_data:
        # Cada estudiante puede tener múltiples embeddings
        for emb in s.get('embeddings', []):
            known_face_encodings.append(np.array(emb))
            nombre_completo = f"{s.get('nombre')} {s.get('apellido', '')}".strip()
            known_metadata.append({'id': s.get('id'), 'nombre': nombre_completo})
    # Abrir cámara
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return {"success": False, "message": "Cámara no disponible."}
    # Escanear durante un tiempo limitado
    start_time = time.time()
    best_match = None
    best_confidence = 0.0
    try:
        while time.time() - start_time < 3.0:
            ret, frame = cap.read()
            if not ret:
                continue
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            if not face_locations:
                continue
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            for encoding in face_encodings:
                # Calcular distancias a los rostros conocidos
                face_distances = face_recognition.face_distance(known_face_encodings, encoding)
                if len(face_distances) == 0:
                    continue
                best_match_index = np.argmin(face_distances)
                distance = face_distances[best_match_index]
                # Solo consideramos coincidencias con distancia razonable
                if distance < 0.6:
                    confidence = (1.0 - distance) * 100.0
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = known_metadata[best_match_index]
    finally:
        cap.release()
    if best_match:
        return {"success": True, "student_id": best_match['id'], "student_name": best_match['nombre'], "confidence": best_confidence}
    # No se encontró coincidencia
    return {"success": True, "student_id": None, "student_name": None, "confidence": 0.0}

def confirm_attendance(student_id: str) -> dict:
    """
    Confirma la asistencia para el estudiante especificado.  Registra
    la asistencia en la base de datos si aún no se ha registrado y el
    periodo actual de clase es válido.

    Args:
        student_id: Id del estudiante a marcar asistencia.

    Returns:
        dict: Resultado de la operación con success y message.
    """
    # Verificar que el estudiante exista
    student = database.get_student_by_id(student_id)
    if not student:
        return {"success": False, "message": "Estudiante no encontrado."}
    periodo, msg = get_current_attendance_period()
    if not periodo:
        return {"success": False, "message": msg or "Fuera de horario de clase."}
    # Revisar si ya se registró asistencia hoy
    if database.has_attended_today_in_period(student_id, periodo):
        return {"success": False, "message": "La asistencia ya fue registrada para hoy en este período."}
    try:
        database.record_attendance(student_id, periodo)
        nombre_completo = f"{student.get('nombre')} {student.get('apellido', '')}".strip()
        return {"success": True, "message": f"Asistencia registrada para {nombre_completo}."}
    except Exception as e:
        return {"success": False, "message": f"Error al registrar asistencia: {e}"}


def award_participation_for_seat(seat_id: str) -> bool:
    """Otorga un punto de participación al estudiante asignado al asiento.

    Se respetará un tiempo de espera (PARTICIPATION_COOLDOWN) entre
    participaciones consecutivas para un mismo asiento.  El contador de
    participation_counts se incrementará, y se insertará un registro en la
    base de datos si existe un estudiante asignado y el periodo de clase es
    válido.

    Args:
        seat_id: Identificador del asiento.

    Returns:
        True si se otorgó la participación, False si no se cumple el cooldown
        o no hay estudiante asignado.
    """
    now = datetime.datetime.now()
    last = seat_last_participation_time.get(seat_id)
    if last and (now - last).total_seconds() < PARTICIPATION_COOLDOWN:
        return False  # Cooldown activo
    # Actualizar timestamp
    seat_last_participation_time[seat_id] = now
    # Incrementar contador local
    if seat_id not in participation_counts:
        participation_counts[seat_id] = 0
    participation_counts[seat_id] += 1
    # Registrar en base de datos si hay estudiante y período válido
    student_id = seat_assignments.get(seat_id)
    if student_id:
        periodo, _ = get_current_attendance_period()
        if periodo:
            database.record_participation(student_id, periodo)
    return True

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
            # cv2.imshow deshabilitado para entorno tablet
# cv2.imshow('Registro Facial', frame_display)
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
    if not MOVENET_MODEL:
        return
    # Cargar configuración de asientos al iniciar el streaming
    load_seat_config()
    cap = cv2.VideoCapture(0)
    cl_logger.info("Iniciando stream de POSE.")
    while cap.isOpened() and pose_monitoring_active:
        ret, frame = cap.read()
        if not ret:
            break
        frame_display = cv2.flip(frame, 1)
        h, w, _ = frame_display.shape

        # Ejecutar MoveNet para obtener keypoints de múltiples personas
        results = movenet(np.expand_dims(frame_display, axis=0))

        # Para determinar la mano más alta de cualquier persona en este frame
        highest_hand = None  # (x_px, y_px)

        for person in np.squeeze(results):
            # Filtrar por puntuación de confianza de la persona (último valor)
            if person[55] < 0.35:
                continue
            keypoints = person[:51].reshape((17, 3))

            # Dibujar el esqueleto de la persona
            for edge in EDGES:
                p1, p2 = edge
                y1, x1, c1 = keypoints[p1]
                y2, x2, c2 = keypoints[p2]
                if c1 > 0.3 and c2 > 0.3:
                    cv2.line(frame_display, (int(x1 * w), int(y1 * h)), (int(x2 * w), int(y2 * h)), (255, 255, 0), 2)

            # Calcular si la mano izquierda o derecha está levantada
            left_wrist_y, left_wrist_x, left_wrist_c = keypoints[KEYPOINT_DICT['left_wrist']]
            left_shoulder_y, _, left_shoulder_c = keypoints[KEYPOINT_DICT['left_shoulder']]
            right_wrist_y, right_wrist_x, right_wrist_c = keypoints[KEYPOINT_DICT['right_wrist']]
            right_shoulder_y, _, right_shoulder_c = keypoints[KEYPOINT_DICT['right_shoulder']]

            left_hand_up = left_wrist_c > 0.3 and left_shoulder_c > 0.3 and left_wrist_y < left_shoulder_y
            right_hand_up = right_wrist_c > 0.3 and right_shoulder_c > 0.3 and right_wrist_y < right_shoulder_y

            if left_hand_up or right_hand_up:
                # Tomar la mano más alta para determinar participación
                if left_hand_up:
                    lx_px, ly_px = int(left_wrist_x * w), int(left_wrist_y * h)
                    cv2.circle(frame_display, (lx_px, ly_px), 20, (0, 255, 255), 5)
                    if highest_hand is None or ly_px < highest_hand[1]:
                        highest_hand = (lx_px, ly_px)
                if right_hand_up:
                    rx_px, ry_px = int(right_wrist_x * w), int(right_wrist_y * h)
                    cv2.circle(frame_display, (rx_px, ry_px), 20, (0, 255, 255), 5)
                    if highest_hand is None or ry_px < highest_hand[1]:
                        highest_hand = (rx_px, ry_px)

        # Si se detectó una mano levantada en este frame, intentar asignar a un asiento
        if highest_hand is not None and seat_boxes:
            hx_px, hy_px = highest_hand
            # Determinar el asiento con el que colisiona la mano (x,y dentro de la caja verticalmente sobre el asiento)
            selected_seat_id = None
            for seat in seat_boxes:
                x, y, w_s, h_s = _rect_pixels(seat.get('rect'), seat.get('normalized', False), frame.shape if 'frame' in locals() else frame_display.shape)
                seat_id = seat.get('seat_id')
                # Considerar la mano como participación si está por encima del top del asiento y en rango horizontal
                if hx_px >= x and hx_px <= x + w_s and hy_px <= y + h_s:
                    selected_seat_id = seat_id
                    break
            if selected_seat_id:
                # Otorgar participación para el asiento seleccionado
                if award_participation_for_seat(selected_seat_id):
                    # Dibujar indicación de participación
                    cv2.putText(frame_display, f"{selected_seat_id} +1", (hx_px - 40, hy_px - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        # Dibujar boxes de asientos y etiquetas
        for seat in seat_boxes:
            sx, sy, sw, sh = _rect_pixels(seat.get('rect'), seat.get('normalized', False), frame.shape if 'frame' in locals() else frame_display.shape)
            sid = seat.get('seat_id')
            # Determinar color según si hay mano actual en este asiento
            color = (0, 255, 0)
            # Obtener nombre del estudiante
            student_id = seat_assignments.get(sid)
            student_name = ""
            if student_id:
                try:
                    student = database.get_student_by_id(student_id)
                    if student:
                        student_name = f"{student.get('nombre')} {student.get('apellido', '')}".strip()
                except Exception:
                    student_name = ""
            pts = participation_counts.get(sid, 0)
            # Dibujar el rectángulo del asiento
            cv2.rectangle(frame_display, (sx, sy), (sx + sw, sy + sh), color, 2)
            # Construir la etiqueta
            label_parts = [sid]
            if student_name:
                label_parts.append(student_name)
            label_parts.append(f"Pts:{pts}")
            label = " | ".join(label_parts)
            cv2.putText(frame_display, label, (sx, max(0, sy - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Generar frame MJPEG
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

def quick_identify_from_base64(image_b64: str) -> dict:
    """Identifica un estudiante a partir de una imagen base64 enviada desde el navegador.

    Espera datos en formato 'data:image/jpeg;base64,...' o el string base64 sin header.
    Devuelve un dict con keys: success, student_id, student_name, confidence, message.
    """
    try:
        # Limpiar header si viene con data URL
        if image_b64.startswith('data:'):
            header, b64data = image_b64.split(',', 1)
        else:
            b64data = image_b64
        img_bytes = base64.b64decode(b64data)
    except Exception as e:
        return {"success": False, "message": f"base64 inválido: {e}"}

    # Decodificar a imagen BGR para usar face_recognition
    np_arr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if frame is None:
        return {"success": False, "message": "No se pudo decodificar la imagen."}

    # Obtener embeddings registrados
    students_data = database.get_all_students()
    if not students_data:
        return {"success": False, "message": "No hay estudiantes registrados para reconocer."}

    known_face_encodings = []
    known_metadata = []
    for s in students_data:
        nombre = f"{s.get('nombre','')} {s.get('apellido','')}".strip()
        for emb in s.get('embeddings', []):
            enc = np.array(emb, dtype=np.float32)
            if enc.size == 128 or enc.size == 512:
                known_face_encodings.append(enc)
                known_metadata.append({'id': s.get('id'), 'nombre': nombre})

    if not known_face_encodings:
        return {"success": False, "message": "No hay embeddings disponibles."}

    # Detección y codificación del rostro en la imagen
    rgb = frame[:, :, ::-1]
    boxes = face_recognition.face_locations(rgb, model='hog')
    if not boxes:
        return {"success": False, "message": "No se detectaron rostros."}
    encodings = face_recognition.face_encodings(rgb, boxes)
    if not encodings:
        return {"success": False, "message": "No se pudieron calcular encodings."}

    # Comparar con base conocida: usar distancia mínima
    import numpy.linalg as LA
    best_idx = -1
    best_dist = 1e9
    target = encodings[0]
    for i, enc in enumerate(known_face_encodings):
        # Asegurar mismo tamaño (algunas bases pueden tener 512)
        if enc.shape != target.shape:
            continue
        d = LA.norm(enc - target)
        if d < best_dist:
            best_dist = d
            best_idx = i

    if best_idx == -1:
        return {"success": False, "message": "No se encontró coincidencia compatible."}

    # Convertir distancia a una pseudo-confianza (heurística)
    # Para encodings 128D (face_recognition), distancias < 0.6 suelen considerarse match
    # Mapeamos [0.3..0.6] -> [100..0]
    d = float(best_dist)
    conf = max(0.0, min(1.0, (0.6 - d) / 0.3)) * 100.0

    meta = known_metadata[best_idx]
    return {
        "success": True,
        "student_id": meta.get('id'),
        "student_name": meta.get('nombre'),
        "confidence": round(conf, 2)
    }
