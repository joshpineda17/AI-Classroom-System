# 🤖 AI-Classroom System

Un sistema de gestión de aula inteligente desarrollado en Python que utiliza inteligencia artificial para automatizar la asistencia, analizar estilos de aprendizaje y mejorar el contenido de las clases. Este proyecto está diseñado para ser una herramienta de apoyo para el educador moderno, centralizando tareas clave en un dashboard web intuitivo.



---

## ✨ Características Principales

* **Registro Biométrico:** Registro de estudiantes mediante captura y almacenamiento de embeddings faciales.
* **Análisis de Personalidad:** Cuestionario automatizado para determinar los estilos de aprendizaje de los alumnos según los modelos de Kolb, VAK y Felder-Silverman.
* **Asistencia Automatizada:** Monitoreo en tiempo real a través de la cámara para registrar la asistencia facial con un porcentaje de confianza.
* **Detección de Gestos:** Análisis de pose en tiempo real para detectar la participación de los estudiantes (manos levantadas).
* **Transcripción de Clases:** Grabación de audio de la clase y transcripción automática usando el modelo Whisper de OpenAI.
* **Mejora con IA:** Un LLM (Large Language Model) procesa las transcripciones para añadir contexto, expandir conceptos y hacer el contenido más educativo.
* **Dashboard Intuitivo:** Interfaz web creada con Flask para que el profesor gestione todas las funciones de forma centralizada y amigable con pantallas táctiles.

---

## 🛠️ Tecnologías Utilizadas

* **Backend:** **Python 3.10.0**, **Flask**
* **Computer Vision:** **OpenCV**, **`face_recognition`** (dlib), **TensorFlow** (MoveNet)
* **Procesamiento de Audio:** **PyAudio**, **OpenAI Whisper**
* **Modelo de Lenguaje (LLM):** **`llama-cpp-python`** con el modelo **Phi-3**
* **Base de Datos:** **SQLite**
* **Frontend:** **HTML**, **CSS**, **JavaScript**, **Bootstrap 5**

---

## 🚀 Instalación y Ejecución

A continuación, se detallan los pasos para configurar y ejecutar este proyecto utilizando **Python 3.10.0**.

### ### Instalación

Sigue estos pasos para la configuración inicial del entorno virtual y las dependencias del proyecto.

1.  **Clonar el repositorio:**
    Abre una terminal (como Git Bash o CMD) y clona este repositorio en tu máquina local.
    ```bash
    git clone [https://github.com/joshpineda17/AI-Classroom-System.git](https://github.com/joshpineda17/AI-Classroom-System.git)
    ```

2.  **Navegar al directorio del proyecto:**
    ```bash
    cd AI-Classroom-System
    ```
    *(Reemplaza la ruta si es necesario para llegar a la carpeta del proyecto)*.

3.  **Crear el Entorno Virtual:**
    Se recomienda abrir el **Símbolo del sistema (CMD) como administrador** para este paso para evitar posibles problemas de permisos.
    ```bash
    python -m venv venv
    ```

4.  **Activar el Entorno Virtual:**
    ```bash
    .\venv\Scripts\activate
    ```
    Una vez activo, verás `(venv)` al inicio de la línea de tu terminal.

5.  **Actualizar `pip`:**
    Es una buena práctica asegurarse de tener la última versión del instalador de paquetes.
    ```bash
    pip install --upgrade pip
    ```

6.  **Instalar las Dependencias:**
    Este comando leerá el archivo `requirements.txt` e instalará todas las librerías necesarias.
    ```bash
    pip install -r requirements.txt
    ```

7.  **Descargar el Modelo de Lenguaje (LLM):**
    Este paso es **manual y obligatorio** para la función de "Mejorar con IA".
    * Crea una carpeta llamada `modelos` en la raíz del proyecto.
    * Descarga el archivo `Phi-3-mini-4k-instruct-q4.gguf` desde [Hugging Face](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf).
    * Coloca el archivo `.gguf` descargado dentro de la carpeta `modelos`.

### ### Ejecución

Una vez que el entorno está configurado, puedes ejecutar el proyecto.

1.  **Abre una nueva terminal (CMD normal)** y navega al directorio del proyecto.
    ```bash
    cd C:\ruta\a\tu\AI-Classroom-System
    ```

2.  **Activa el entorno virtual** (si no está activo):
    ```bash
    .\venv\Scripts\activate
    ```

3.  **Ejecuta la aplicación principal:**
    ```bash
    python app.py
    ```

4.  **Accede a la aplicación:**
    El servidor se iniciará. Abre tu navegador web y navega a la siguiente dirección:
    **http://127.0.0.1:5000**

### ### Detener la Aplicación

1.  **Para detener el servidor web**, ve a la terminal donde se está ejecutando y presiona las teclas `Ctrl + C`.
2.  **Para desactivar el entorno virtual** y volver a la terminal normal, ejecuta:
    ```bash
    deactivate
    ```

---
## 📂 Estructura del Proyecto

```
/
├── app.py                  # Servidor Flask, maneja las rutas y la lógica principal.
├── core_logic.py           # Contiene toda la IA (reconocimiento facial, pose, audio).
├── database.py             # Gestiona la base de datos SQLite.
├── llm_processor.py        # Módulo para interactuar con el modelo de lenguaje.
├── requirements.txt        # Lista de dependencias de Python.
├── .gitignore              # Archivos y carpetas a ignorar por Git (como venv).
├── /modelos/               # Carpeta para los modelos de IA pesados (ej. LLM).
├── /static/                # Archivos CSS y JavaScript.
├── /venv/                  # Carpeta con el entorno virtual y sus instalaciones
└── /templates/             # Archivos HTML de la aplicación.
```
