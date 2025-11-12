# test_yolo.py
from __future__ import annotations
import argparse
import sys
from pathlib import Path
import platform

import cv2
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="Prueba aislada de YOLO (Ultralytics).")
    parser.add_argument("--image", "-i", type=str, default="data/uploads/entrada.jpg",
                        help="Ruta a la imagen a probar.")
    parser.add_argument("--model", "-m", type=str, default="yolov5su.pt",
                        help="Ruta al modelo local .pt (si no existe, se usará 'yolov8n.pt').")
    parser.add_argument("--save", action="store_true",
                        help="Guardar imagen anotada en data/uploads/out.jpg")
    args = parser.parse_args()

    img_path = Path(args.image).resolve()
    model_path = Path(args.model).resolve()

    print("========== DIAGNÓSTICO ==========")
    print(f"SO                 : {platform.system()} {platform.release()}")
    print(f"Python             : {sys.version.split()[0]}")
    try:
        import torch
        print(f"Torch              : {torch.__version__}")
        print(f"CUDA disponible    : {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"CUDA device        : {torch.cuda.get_device_name(0)}")
    except Exception as e:
        print("Torch               : NO INSTALADO o falló la importación ->", e)

    print(f"Imagen             : {img_path} (existe={img_path.exists()})")
    print(f"Modelo solicitado  : {model_path} (existe={model_path.exists()})")

    # 1) Verificar imagen
    if not img_path.exists():
        print("\n❌ No se encontró la imagen. Pasá otra con --image RUTA.jpg")
        sys.exit(2)

    # 2) Cargar imagen con OpenCV
    img = cv2.imread(str(img_path))
    if img is None:
        print("\n❌ OpenCV no pudo leer la imagen (formato no soportado o archivo corrupto).")
        sys.exit(3)
    print("✔ OpenCV cargó la imagen correctamente.")

    # 3) Cargar modelo
    try:
        if model_path.exists():
            print(f"✔ Cargando modelo local: {model_path}")
            model = YOLO(str(model_path))
        else:
            # Fallback: usa un modelo público de Ultralytics (se descarga automático)
            print("⚠ Modelo local no encontrado. Usando 'yolov8n.pt' (auto-download).")
            model = YOLO("yolov8n.pt")
    except Exception as e:
        print("\n❌ Falló la carga del modelo YOLO:", repr(e))
        sys.exit(4)

    # 4) Predicción
    try:
        results = model.predict(img, verbose=False)
        if not results:
            print("\n❌ El modelo no devolvió resultados.")
            sys.exit(5)

        r = results[0]
        names = getattr(r, "names", getattr(model, "names", {}))
        print("\n===== DETECCIONES =====")
        count = 0
        if getattr(r, "boxes", None) is not None and len(r.boxes) > 0:
            for box in r.boxes:
                cls_idx = int(box.cls[0].item()) if hasattr(box.cls[0], "item") else int(box.cls[0])
                conf = float(box.conf[0].item()) if hasattr(box.conf[0], "item") else float(box.conf[0])
                clase = names.get(cls_idx, str(cls_idx))
                print(f"- {clase:15s} conf={conf:.2f}")
                count += 1
        else:
            print("(sin cajas)")

        if count == 0:
            print("\nℹ No se detectaron objetos. Esto no es error, pero confirma que el pipeline corre.")

        # 5) Guardar imagen anotada (opcional)
        if args.save:
            out_dir = Path("data/uploads")
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / "out.jpg"
            # Ultralytics tiene .plot() para obtener imagen con cajas
            annotated = r.plot()  # numpy array BGR
            cv2.imwrite(str(out_path), annotated)
            print(f"\n✔ Imagen anotada guardada en: {out_path}")

        print("\n✅ TEST OK (el backend no es el problema).")
        sys.exit(0)

    except Exception as e:
        print("\n❌ Excepción durante la predicción:", repr(e))
        sys.exit(6)


if __name__ == "__main__":
    main()
