"""Calibrador de posiciones de asientos para el sistema AI-Classroom.

Este script permite al profesor o administrador definir manualmente las
regiones en las que se sientan los estudiantes. Cuando la calidad
de la cámara o la distancia impiden la detección facial fiable,
podemos delimitar cajas fijas por asiento usando el ratón y
almacenarlas en un archivo JSON.  Posteriormente, otras partes del
sistema (por ejemplo, un monitor de participación) pueden leer estas
coordenadas para asociar eventos como levantar la mano con el
estudiante correcto.

Uso:
    python calibrate_seats.py --output data/seats.json

Controles:
    - Haga clic y arrastre con el botón izquierdo para dibujar una caja.
    - Tras soltar el botón, se le pedirá el ID del asiento (por ejemplo
      "A1" o "B3") en la consola.
    - Presione 'u' para deshacer la última caja.
    - Presione 's' para guardar todas las cajas en el archivo de salida.
    - Presione 'q' para salir sin guardar.

El archivo JSON resultante tendrá la forma:
    [
        {"seat_id": "A1", "rect": [x, y, w, h]},
        {"seat_id": "A2", "rect": [x, y, w, h]},
        ...
    ]
Cada valor (x, y, w, h) está en píxeles respecto al frame capturado.
"""

import argparse
import cv2
import json
import os

# Archivo donde se guardarán las asignaciones de estudiantes a asientos
ASSIGNMENTS_FILE = os.path.join('data', 'seat_assignments.json')


def draw_boxes(frame, boxes, current_box):
    """Dibuja las cajas ya definidas y la caja actual en la ventana.

    Args:
        frame (ndarray): Fotograma BGR de la cámara.
        boxes (list): Lista de dicts con seat_id y rect.
        current_box (tuple or None): Coordenadas (x0,y0,x1,y1) de la caja
            en curso mientras el usuario arrastra el ratón.
    """
    overlay = frame.copy()
    for b in boxes:
        x, y, w, h = b["rect"]
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(overlay, b["seat_id"], (x, max(0, y - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    if current_box is not None:
        x0, y0, x1, y1 = current_box
        cv2.rectangle(overlay, (x0, y0), (x1, y1), (0, 255, 255), 1)
    return overlay


def calibrate(output_path: str, camera_index: int = 0) -> None:
    """Ejecuta la interfaz de calibración de asientos.

    Este modo de calibración utiliza el ratón para delimitar cajas sobre el
    vídeo en vivo. Cada vez que se dibuja una nueva caja se genera
    automáticamente un identificador de asiento del tipo "Pupitre N", donde
    N es el número consecutivo de la caja (empezando en 1). Además, tras
    agregar la caja se guarda inmediatamente la lista completa de asientos
    en el archivo JSON de salida y un archivo de asignaciones vacío.

    Args:
        output_path (str): Ruta al archivo JSON donde se guardarán las
            coordenadas de las cajas. El directorio se creará si no existe.
        camera_index (int, opcional): Índice de la cámara a usar.
            Por defecto es 0.
    """
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"[ERROR] No se pudo abrir la cámara en el índice {camera_index}.")
        return

    boxes = []  # lista de dicts con seat_id y rect
    # Al inicio, intentar cargar asientos existentes para continuar numeración
    if os.path.exists(output_path):
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)
            if isinstance(existing, list):
                boxes.extend(existing)
        except Exception:
            pass
    drawing = False
    ix = iy = 0
    current_box = None

    def save_boxes_and_assignments():
        """Guarda inmediatamente las cajas y un archivo de asignaciones vacío."""
        # Crear carpeta si no existe
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        # Guardar cajas
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(boxes, f, indent=4)
        # Crear archivo de asignaciones con valores nulos
        assignments = {b["seat_id"]: None for b in boxes}
        os.makedirs(os.path.dirname(ASSIGNMENTS_FILE), exist_ok=True)
        with open(ASSIGNMENTS_FILE, 'w', encoding='utf-8') as af:
            json.dump(assignments, af, indent=4)
        print(f"[SUCCESS] Asientos guardados automáticamente en {output_path}.")

    def mouse_callback(event, x, y, flags, param):
        nonlocal drawing, ix, iy, current_box
        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            ix, iy = x, y
            current_box = None
        elif event == cv2.EVENT_MOUSEMOVE and drawing:
            current_box = (ix, iy, x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            drawing = False
            current_box = (ix, iy, x, y)
            # Normalizar la caja (obtener x,y,w,h con x,y como esquina superior izquierda)
            x0, y0, x1, y1 = current_box
            x_n, y_n = min(x0, x1), min(y0, y1)
            w_n, h_n = abs(x1 - x0), abs(y1 - y0)
            # Generar seat_id automáticamente
            seat_number = len(boxes) + 1
            seat_id = f"Pupitre {seat_number}"
            boxes.append({"seat_id": seat_id, "rect": [x_n, y_n, w_n, h_n]})
            print(f"[INFO] Añadido asiento automático {seat_id}.")
            # Guardar inmediatamente
            save_boxes_and_assignments()
            current_box = None

    window_name = "Calibración de Asientos"
    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, mouse_callback)

    print("\nControles:\n  - Dibuje una caja haciendo clic y arrastrando.\n  - 'u' deshace la última caja.\n  - 'q' sale.\n")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] No se pudo capturar el frame de la cámara.")
            break

        frame_display = draw_boxes(frame, boxes, current_box)
        cv2.imshow(window_name, frame_display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            print("Saliendo de la calibración.")
            break
        elif key == ord('u'):
            # deshacer última caja
            if boxes:
                removed = boxes.pop()
                print(f"[INFO] Caja eliminada: {removed['seat_id']}")
                save_boxes_and_assignments()
            current_box = None
        # Nota: ya no es necesario presionar 's' para guardar

    cap.release()
    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="Calibrador de posiciones de asientos para AI-Classroom.")
    parser.add_argument('--output', type=str, default='data/seats.json', help='Ruta del archivo JSON de salida.')
    parser.add_argument('--camera', type=int, default=0, help='Índice de la cámara a utilizar.')
    args = parser.parse_args()
    calibrate(args.output, args.camera)


if __name__ == '__main__':
    main()