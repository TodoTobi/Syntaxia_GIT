# utils/text_to_speech.py
import pyttsx3
import threading

def hablar(texto: str):
    """Lee un texto con pyttsx3 en un thread separado para no bloquear."""
    def _leer():
        try:
            engine = pyttsx3.init()
            engine.say(texto)
            engine.runAndWait()
            engine.stop()
        except RuntimeError:
            pass  # ignorar si hay un loop en marcha

    # Lanzamos en un thread para no bloquear el servidor Flask
    hilo = threading.Thread(target=_leer, daemon=True)
    hilo.start()
