# 🤖 AI-Classroom System

Un sistema de gestión de aula inteligente desarrollado en **Python** que utiliza **inteligencia artificial** para automatizar la asistencia, analizar estilos de aprendizaje y mejorar el contenido de las clases. Este proyecto está diseñado para ser una herramienta de apoyo para el educador moderno, centralizando tareas clave en un **dashboard web intuitivo**.

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

## 📋 Requisitos Previos (¡Lectura Obligatoria!)

Antes de la instalación, es crucial entender los requisitos de hardware y software para que los componentes de IA funcionen correctamente. Este proyecto fue desarrollado y probado en un equipo con **8GB de RAM**, una **GPU NVIDIA GeForce 1660 Ti** y un procesador **Intel Core i7 de 9ª Generación**.

### Requisito Fundamental: El Hardware 🖥️

El requisito más importante es el hardware: necesitas una **GPU (tarjeta de video) de NVIDIA que sea compatible con CUDA**.

* **Tecnología Exclusiva**: CUDA es una tecnología propietaria de NVIDIA, por lo que no funcionará en tarjetas de AMD (Radeon) o Intel.
* **Modelos Compatibles**: La gran mayoría de las tarjetas NVIDIA modernas de las series **GeForce**, **Quadro** y **Tesla** son compatibles. Puedes verificar tu GPU en la [lista oficial de NVIDIA](https://developer.nvidia.com/cuda-gpus).

### Ecosistema de Software: CUDA 📚

Una vez que tienes el hardware, necesitas instalar un ecosistema de software donde las versiones de cada componente sean compatibles entre sí.

1.  **Driver Gráfico de NVIDIA**: Es el software base que permite que tu sistema operativo se comunique con la GPU. Debes tener una versión actualizada que soporte el CUDA Toolkit que vas a instalar.

2.  **NVIDIA CUDA Toolkit**: Es el paquete de desarrollo que incluye el compilador y las bibliotecas para programar la GPU. **La versión del Toolkit es crucial**, ya que librerías como TensorFlow dependen de versiones específicas. No asumas que la última versión es la correcta.

3.  **NVIDIA cuDNN (para IA)**: Es una biblioteca que acelera las operaciones de redes neuronales. Es **prácticamente obligatoria** para usar TensorFlow o PyTorch con la GPU. La versión de cuDNN debe ser compatible con la versión del CUDA Toolkit que instalaste.

### La Clave: La Matriz de Compatibilidad 🧩

Imagina que el driver, el CUDA Toolkit, cuDNN y la librería de IA (TensorFlow) son piezas de un rompecabezas. **Todas deben encajar perfectamente**. El error más común es instalar la última versión de todo y descubrir que no son compatibles.

> **Ejemplo**: La versión de TensorFlow usada en este proyecto podría requerir específicamente **CUDA 11.8** y **cuDNN 8.6**. Antes de instalar, revisa la documentación de las librerías en `requirements.txt` para encontrar la combinación de versiones correcta.

---

## 🚀 Guía de Instalación y Ejecución

A continuación, se detallan los pasos para configurar y ejecutar este proyecto utilizando **Python 3.10.0**.

### Instalación

Sigue estos pasos para la configuración inicial del entorno virtual y las dependencias del proyecto.

1.  **Clonar el repositorio:**
    Abre una terminal y clona este repositorio en tu máquina local.
    ```bash
    git clone [https://github.com/joshpineda17/AI-Classroom-System.git](https://github.com/joshpineda17/AI-Classroom-System.git)
    cd AI-Classroom-System
    ```

2.  **Crear y Activar el Entorno Virtual (`venv`):**
    Se recomienda abrir el **Símbolo del sistema (CMD) como administrador** para la instalación inicial.
    ```bash
    # Crear el entorno virtual
    python -m venv venv

    # Activar el entorno virtual (en Windows)
    .\venv\Scripts\activate
    ```
    Una vez activo, verás `(venv)` al inicio de la línea de tu terminal.

3.  **Actualizar `pip`:**
    Es una buena práctica asegurarse de tener la última versión del instalador de paquetes.
    ```bash
    pip install --upgrade pip
    ```

4.  **Instalar las Dependencias:**
    Este comando leerá el archivo `requirements.txt` e instalará todas las librerías necesarias.
    ```bash
    pip install -r requirements.txt
    ```

5.  **Configurar el Modelo de IA (Paso Manual Obligatorio):**
    El modelo de lenguaje (LLM) es demasiado grande para incluirlo en GitHub, por lo que debe configurarse manualmente.

    **a. Crear la carpeta `modelos`:**
    Dentro de la carpeta raíz del proyecto (`AI-Classroom-System`), ejecuta el siguiente comando:
    ```bash
    mkdir modelos
    ```

    **b. Descargar el modelo de lenguaje:**
    * **Archivo necesario:** `Phi-3-mini-4k-instruct-q4.gguf`
    * **Enlace de descarga:** [Microsoft Phi-3-mini GGUF en Hugging Face](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf)

    **c. Ubicar el modelo:**
    Mueve el archivo `.gguf` descargado a la carpeta `modelos`. La estructura final debe ser:
    ```
    AI-Classroom-System/
    └─── modelos/
         └─── Phi-3-mini-4k-instruct-q4.gguf
    ```

### Ejecución

Una vez que el entorno está configurado, puedes ejecutar el proyecto.

1.  **Abre una terminal** y navega al directorio del proyecto.

2.  **Activa el entorno virtual** (si no está activo):
    ```bash
    .\venv\Scripts\activate
    ```

3.  **Ejecuta la aplicación principal:**
    ```bash
    python app.py
    ```

4.  **Accede a la aplicación:**
    El servidor se iniciará. Abre tu navegador web y navega a:
    **http://127.0.0.1:5000**

### Detener la Aplicación

1.  **Para detener el servidor web**, ve a la terminal donde se está ejecutando y presiona las teclas `Ctrl + C`.
2.  **Para desactivar el entorno virtual** y volver a la terminal normal, ejecuta:
    ```bash
    deactivate
    ```
---
## 📂 Estructura del Proyecto
## 📂 Estructura del Proyecto

```
/
├── app.py                  # Servidor Flask, maneja las rutas y la lógica principal.
├── core_logic.py           # Contiene toda la IA (reconocimiento facial, pose, audio).
├── database.py             # Gestiona la base de datos SQLite.
├── llm_processor.py        # Módulo para interactuar con el modelo de lenguaje.
├── requirements.txt        # Lista de dependencias de Python.
├── .gitignore              # Archivos y carpetas a ignorar por Git (como venv).
├── /modelos/               # (Creada manualmente) Carpeta para los modelos de IA.
├── /static/                # Archivos CSS y JavaScript.
├── /venv/                  #Entorno virtual de python con todas las librerias para que funcione el proyecto
└── /templates/             # Archivos HTML de la aplicación.
```
