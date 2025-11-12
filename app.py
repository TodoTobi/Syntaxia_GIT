# app.py
from flask import Flask, request, jsonify, render_template, send_from_directory, abort
from voice_module.text_to_speech import hablar
from api_client.mistral_client import responder_mensaje_texto
from api_client.yolo_client import analizar_imagen_yolo

import os
import json
import datetime
import traceback
from urllib.parse import urlparse

app = Flask(__name__)

# --- carpetas ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
UPLOADS_DIR = os.path.join(BASE_DIR, "data", "uploads")
MODELOS_DIR = os.path.join(BASE_DIR, "data", "modelos3d")
PEDIDOS_DIR = os.path.join(BASE_DIR, "data", "pedidos_modelado")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(MODELOS_DIR, exist_ok=True)
os.makedirs(PEDIDOS_DIR, exist_ok=True)


# --- util: guardar pedido de modelado si el bot lo sugiere ---
def guardar_instruccion_modelado(descripcion, instruccion):
    try:
        datos = {
            "timestamp": datetime.datetime.now().isoformat(),
            "descripcion": descripcion,
            "instrucciones_modelado": instruccion,
            "modelo_sugerido": (descripcion or "modelo").replace(" ", "_")[:25],
        }
        path_json = os.path.join(PEDIDOS_DIR, "entrada.json")
        with open(path_json, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
        print(f"📝 Pedido guardado en: {path_json}")
    except Exception:
        print("⚠ No se pudo guardar el pedido de modelado:")
        traceback.print_exc()


# -------------------------- PÁGINAS --------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/viewer")
def viewer_page():
    return render_template("viewer.html")


# -------------------------- ESTÁTICOS (OBJ) --------------------------

@app.route("/modelos/<path:filename>")
def modelos(filename):
    modelos_dir = os.path.join(app.root_path, "data", "modelos3d")
    return send_from_directory(modelos_dir, filename)



# -------------------------- API: IMAGEN --------------------------

@app.route("/api/imagen", methods=["POST"])
def recibir_imagen():
    """
    Recibe:
      - 'imagen': archivo
      - 'nota': (opcional) texto del usuario
    Hace:
      1) Corre YOLO sobre la imagen
      2) Si hay 'nota', genera respuesta del LLM combinada con las detecciones
      3) (opcional) habla el resumen YOLO
    Devuelve: JSON con {descripcion, respuesta, objetos, modelo_url, respuesta_llm}
    """
    try:
        if "imagen" not in request.files:
            return jsonify({"error": "No se envió ninguna imagen"}), 400

        img_file = request.files["imagen"]
        nota = (request.form.get("nota") or "").strip()

        img_path = os.path.join(UPLOADS_DIR, "entrada.jpg")
        img_file.save(img_path)
        print(f"📥 Imagen guardada en: {img_path}")
        if nota:
            print(f"📝 Nota adjunta: {nota}")

        # 1) YOLO
        resultado_yolo = analizar_imagen_yolo(img_path)
        print("🔎 Resultado YOLO:", resultado_yolo)

        descripcion = resultado_yolo.get("descripcion", "")
        respuesta_yolo = resultado_yolo.get("respuesta", "No se obtuvo respuesta del modelo.")
        modelo_url = resultado_yolo.get("modelo_url")
        objetos = resultado_yolo.get("objetos", [])

        # 2) Si vino nota, combinamos con LLM
        respuesta_llm = None
        if nota:
            prompt = (
                "Actúa como tutor de TICs. Te paso detecciones de una imagen y una nota del estudiante.\n"
                "1) Resume brevemente lo que ves a partir de las detecciones.\n"
                "2) Responde la nota del estudiante en relación con lo que se ve.\n"
                "3) Si procede, sugiere actividades o conceptos TICs relacionados.\n\n"
                f"Detecciones: {descripcion if descripcion else 'sin objetos relevantes'}\n"
                f"Nota del estudiante: {nota}\n"
            )
            try:
                respuesta_llm = responder_mensaje_texto(prompt)
                print("🧠 LLM OK")
            except Exception:
                print("⚠ Error consultando al LLM con la nota:")
                traceback.print_exc()
                respuesta_llm = None

        # 3) TTS (no bloquear si falla)
        try:
            if respuesta_yolo:
                hablar(respuesta_yolo)
        except Exception:
            pass

        # 4) Guardar pedido de modelado si el texto lo sugiere
        if "modelo 3d" in (respuesta_yolo or "").lower():
            guardar_instruccion_modelado(descripcion, respuesta_yolo)

        return jsonify({
            "descripcion": descripcion,
            "respuesta": respuesta_yolo,
            "objetos": objetos,
            "modelo_url": modelo_url,        # ej: /modelos/person_1234.obj
            "respuesta_llm": respuesta_llm,
        })

    except Exception as e:
        print("❌ Error en /api/imagen:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# -------------------------- API: MENSAJE TEXTO --------------------------

@app.route("/api/mensaje", methods=["POST"])
def recibir_mensaje():
    try:
        data = request.get_json(force=True) or {}
        mensaje = (data.get("mensaje") or "").strip()
        if not mensaje:
            return jsonify({"error": "Mensaje vacío"}), 400

        resultado = responder_mensaje_texto(mensaje)

        if isinstance(resultado, dict):
            respuesta = resultado.get("respuesta", "")
            modelo_url = resultado.get("modelo_url")
        else:
            respuesta = str(resultado)
            modelo_url = None

        if "modelo 3d" in (respuesta or "").lower():
            guardar_instruccion_modelado(mensaje, respuesta)

        try:
            if respuesta:
                hablar(respuesta)
        except Exception:
            pass

        return jsonify({
            "respuesta": respuesta,
            "modelo_url": modelo_url
        })

    except Exception as e:
        print("❌ Error en /api/mensaje:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# -------------------------- MAIN --------------------------

if __name__ == "__main__":
    # host='0.0.0.0' si querés acceder desde otro dispositivo de tu red
    app.run(debug=True)
