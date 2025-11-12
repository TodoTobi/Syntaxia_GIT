# modelado_3d/generar_modelo.py
from __future__ import annotations
from pathlib import Path
import shutil

# Raíz del proyecto (sube dos niveles: modelado_3d/ -> / -> proyecto)
ROOT = Path(__file__).resolve().parents[1]
BASE_MODELS = ROOT / "data" / "base_models"

# Mapeo simple clase YOLO -> archivo .obj de placeholder
MAPEO = {
    "laptop": "laptop.obj",
    "notebook": "laptop.obj",
    "computer": "laptop.obj",
    "pc": "laptop.obj",
    "router": "router.obj",
    "keyboard": "teclado.obj",
    "mouse": "mouse.obj",
}

def _asegurar_base_models():
    """
    Garantiza que exista data/base_models con al menos 'laptop.obj'.
    Si faltan, crea un cubo simple como placeholder.
    """
    BASE_MODELS.mkdir(parents=True, exist_ok=True)
    laptop_obj = BASE_MODELS / "laptop.obj"

    if not laptop_obj.exists():
        # Un cubo muy simple como placeholder (OBJ válido)
        laptop_obj.write_text(
            "o laptop\n"
            "v -0.5 -0.5 -0.5\nv 0.5 -0.5 -0.5\nv 0.5 0.5 -0.5\nv -0.5 0.5 -0.5\n"
            "v -0.5 -0.5 0.5\nv 0.5 -0.5 0.5\nv 0.5 0.5 0.5\nv -0.5 0.5 0.5\n"
            "f 1 2 3 4\nf 5 6 7 8\nf 1 2 6 5\nf 2 3 7 6\nf 3 4 8 7\nf 4 1 5 8\n",
            encoding="utf-8"
        )

def _buscar_modelo_placeholder(clase: str) -> Path:
    """
    Devuelve la ruta al .obj placeholder más adecuado para la clase detectada.
    Si no encuentra, usa 'laptop.obj' como fallback.
    """
    _asegurar_base_models()
    clase = (clase or "").lower()

    for k, fname in MAPEO.items():
        if k in clase:
            p = BASE_MODELS / fname
            if p.exists():
                return p

    # Fallback
    p = BASE_MODELS / "laptop.obj"
    if p.exists():
        return p
    raise FileNotFoundError(
        f"No se encontró ningún placeholder en {BASE_MODELS}. "
        f"Agrega al menos 'laptop.obj'."
    )

def generar_modelo_3d_desde_imagen(
    path_imagen: str,
    salida_obj: str,
    clase_objeto: str | None = None,
) -> str:
    """
    MVP seguro: NO reconstruye; solo copia un .obj placeholder a la salida.
    - clase_objeto: clase detectada por YOLO (ej.: 'laptop'), para elegir el placeholder.
    - salida_obj: ruta donde se guardará el .obj final que verá el visor.
    Devuelve la ruta del .obj generado.
    """
    src = _buscar_modelo_placeholder(clase_objeto or "")
    dst = Path(salida_obj)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return str(dst)
