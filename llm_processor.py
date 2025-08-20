# llm_processor.py
import os
from llama_cpp import Llama
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
llm_logger = logging.getLogger(__name__)

MODEL_NAME = "Phi-3-mini-4k-instruct-q4.gguf"
MODEL_PATH = os.path.join("modelos", MODEL_NAME)
LLM_INSTANCE = None

def _load_model():
    global LLM_INSTANCE
    if LLM_INSTANCE is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"El modelo no se encontró en {MODEL_PATH}")
        llm_logger.info("Cargando modelo LLM...")
        try:
            LLM_INSTANCE = Llama(model_path=MODEL_PATH, n_gpu_layers=-1, n_ctx=2048, verbose=False)
            llm_logger.info("✅ Modelo LLM cargado exitosamente.")
        except Exception as e:
            llm_logger.error(f"Error al cargar el modelo LLM: {e}")
            raise
    return LLM_INSTANCE

def enrich_text(text_to_enhance: str) -> str:
    try:
        llm = _load_model()
        system_prompt = """Eres un asistente académico experto. Tu tarea es tomar la siguiente transcripción de una clase y enriquecerla. No la resumas. 
        Tu objetivo es expandir los conceptos clave, añadir contexto histórico o práctico relevante, explicar términos técnicos con analogías claras y, en general, hacer el contenido más detallado y educativo para un estudiante.
        Corrige posibles errores gramaticales o de transcripción de forma sutil. Responde únicamente con el texto mejorado, en español."""
        
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": text_to_enhance}]
        response = llm.create_chat_completion(messages=messages, max_tokens=2048)
        return response['choices'][0]['message']['content']
    except Exception as e:
        llm_logger.error(f"Error durante el procesamiento del LLM: {e}")
        return f"Error al procesar el texto con la IA. Detalles técnicos: {e}"