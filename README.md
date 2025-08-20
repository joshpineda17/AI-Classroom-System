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

* **Backend:** **Python**, **Flask**
* **Computer Vision:** **OpenCV**, **`face_recognition`** (dlib), **TensorFlow** (MoveNet)
* **Procesamiento de Audio:** **PyAudio**, **OpenAI Whisper**
* **Modelo de Lenguaje (LLM):** **`llama-cpp-python`** con el modelo **Phi-3**
* **Base de Datos:** **SQLite**
* **Frontend:** **HTML**, **CSS**, **JavaScript**, **Bootstrap 5**

---

## 🚀 Guía de Instalación y Ejecución

Sigue estos pasos para poner en marcha el proyecto en un entorno local.

### ### 1. Prerrequisitos

Asegúrate de tener instalado:
* [Python 3.9+](https://www.python.org/downloads/)
* [Git](https://git-scm.com/downloads)

### ### 2. Clonar el Repositorio

Abre una terminal y clona este repositorio en tu máquina local.
```bash
git clone [https://github.com/joshpineda17/AI-Classroom-System.git](https://github.com/joshpineda17/AI-Classroom-System.git)
cd AI-Classroom-System
```

### ### 3. Crear y Activar el Entorno Virtual (`venv`)

Un entorno virtual es crucial para aislar las dependencias del proyecto.

**a. Crear el `venv`:**
```bash
python -m venv venv
```

**b. Activar el `venv`:**

* **En Windows (CMD o PowerShell):**
    ```bash
    venv\Scripts\activate
    ```
* **En macOS o Linux:**
    ```bash
    source venv/bin/activate
    ```
Una vez activo, verás `(venv)` al inicio de la línea de tu terminal.

### ### 4. Instalar las Dependencias

Con el entorno virtual activado, instala todas las librerías necesarias con un solo comando:
```bash
pip install -r requirements.txt
```

### ### 5. Descargar el Modelo de Lenguaje (LLM)

Este paso es **manual y obligatorio** para la función de "Mejorar con IA".

* **Crea la carpeta:** Dentro de tu proyecto, crea una carpeta llamada `modelos`.
* **Descarga el archivo:**
    * Ve al siguiente enlace: [Microsoft Phi-3-mini GGUF en Hugging Face](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf)
    * Busca y descarga el archivo `Phi-3-mini-4k-instruct-q4.gguf`.
* **Ubica el archivo:** Mueve el archivo `.gguf` descargado a la carpeta `modelos` que creaste.

### ### 6. Ejecutar el Programa

Una vez completada la instalación, inicia la aplicación Flask:
```bash
python app.py
```
El servidor se iniciará. Abre tu navegador web y navega a la siguiente dirección para usar la aplicación:
**http://127.0.0.1:5000**

---
## 📂 Estructura del Proyecto

```
/
├── app.py                  # Servidor Flask, maneja las rutas y la lógica principal.
├── /venv/                  # Adonde se almacena todo el etorno virtual  
├── core_logic.py           # Contiene toda la IA (reconocimiento facial, pose, audio).
├── database.py             # Gestiona la base de datos SQLite.
├── llm_processor.py        # Módulo para interactuar con el modelo de lenguaje.
├── requirements.txt        # Lista de dependencias de Python.
├── .gitignore              # Archivos y carpetas a ignorar por Git (como venv).
├── /modelos/               # Carpeta para los modelos de IA pesados (ej. LLM).
├── /static/                # Archivos CSS y JavaScript.
└── /templates/             # Archivos HTML de la aplicación.
```
