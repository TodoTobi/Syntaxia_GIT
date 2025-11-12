# api_client/yolo_client.py
from __future__ import annotations

import json
import os
import random
import re
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

import cv2
from ultralytics import YOLO

from utils.config import settings
from modelado_3d.generar_modelo import generar_modelo_3d_desde_imagen


# -----------------------------------------------------------
# Rutas
# -----------------------------------------------------------
ROOT: Path = settings.root
MODELOS3D_DIR: Path = settings.modelos_dir                 # /data/modelos3d
ASSETS_MODELS_DIR: Path = ROOT / "assets" / "models"       # /assets/models
INDEX_PATH: Path = ASSETS_MODELS_DIR / "index.json"        # /assets/models/index.json
YOLO_WEIGHTS: Path = settings.yolo_weights                 # /yolov5su.pt

MODELOS3D_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------------------------------------
# Cargar YOLO una vez
# -----------------------------------------------------------
_modelo_error: Optional[Exception] = None
try:
    if not YOLO_WEIGHTS.exists():
        raise FileNotFoundError(f"No se encontró YOLO en: {YOLO_WEIGHTS}")
    model = YOLO(str(YOLO_WEIGHTS))
    print(f"✔ Modelo YOLO cargado desde: {YOLO_WEIGHTS}")
except Exception as e:
    model = None
    _modelo_error = e
    print(f"❌ Error cargando modelo YOLO: {e}")


# -----------------------------------------------------------
# Normalización y whitelist TIC
# -----------------------------------------------------------
_ALIAS: Dict[str, str] = {
    "notebook": "laptop",
    "screen": "monitor",
    "tv": "monitor",
    "cell phone": "phone",
    "mobile": "phone",
    "cellphone": "phone",
    "smartphone": "phone",
    "desktop": "pc_tower",
    "pc": "pc_tower",
    "computer": "pc_tower",
    "servers": "server",
    "monitors": "monitor",
    "laptops": "laptop",
    "routers": "router",
    "switches": "switch",
    # ruido común que no queremos como modelo TIC:
    "dining table": "table",
    "table": "table",
    "chair": "chair",
}

# Clases TIC a mostrar en visor
TIC_WHITELIST = [
    "laptop", "router", "monitor", "keyboard", "mouse",
    "switch", "server", "pc_tower", "printer", "phone",
    # ampliables:
    "tablet", "projector", "camera", "firewall", "access_point",
]

def normalize_class(name: str) -> str:
    n = (name or "").strip().lower()
    return _ALIAS.get(n, n)

def is_tic_class(cls: str) -> bool:
    return normalize_class(cls) in TIC_WHITELIST


# -----------------------------------------------------------
# Helpers de copiado con soporte OBJ+MTL+Texturas
# -----------------------------------------------------------
_IMG_EXTS = {".png", ".jpg", ".jpeg", ".tga", ".bmp", ".gif", ".webp", ".tif", ".tiff"}
_MTL_EXTS = {".mtl"}

_SANITIZER = re.compile(r"[^a-zA-Z0-9_\-\.]")

# patrones de líneas de mtl con texturas
_MTL_MAP_PAT = re.compile(
    r'^\s*(map_Kd|map_Ka|map_d|map_bump|bump|disp|decal)\s+(.+?)\s*$',
    re.IGNORECASE | re.MULTILINE
)
# patrón de mtllib en obj
_OBJ_MTL_LIB = re.compile(r'^\s*mtllib\s+(.+?)\s*$', re.IGNORECASE | re.MULTILINE)

def sanitize_filename(name: str) -> str:
    # Reemplaza espacios por _ y elimina caracteres raros
    s = name.replace(" ", "_")
    s = _SANITIZER.sub("", s)
    return s

def _unique_dest_name(dest_dir: Path, filename: str) -> Path:
    base = Path(filename).stem
    ext = Path(filename).suffix
    candidate = dest_dir / f"{base}{ext}"
    if not candidate.exists():
        return candidate
    for _ in range(10000):
        rnd = random.randint(1000, 9999)
        candidate = dest_dir / f"{base}_{rnd}{ext}"
        if not candidate.exists():
            return candidate
    return dest_dir / f"{base}_{random.randint(10000,99999)}{ext}"

def _resolve_rel(base_dir: Path, rel_path: str) -> Path:
    # Quita comillas y normaliza separadores
    rel = rel_path.strip().strip('"').strip("'")
    return (base_dir / rel).resolve()

def _parse_obj_for_mtl(src_obj: Path) -> Optional[str]:
    try:
        txt = src_obj.read_text(encoding="utf-8", errors="ignore")
        m = _OBJ_MTL_LIB.search(txt)
        return m.group(1).strip() if m else None
    except Exception:
        return None

def _parse_mtl_for_textures(src_mtl: Path) -> Set[str]:
    out: Set[str] = set()
    try:
        txt = src_mtl.read_text(encoding="utf-8", errors="ignore")
        for mm in _MTL_MAP_PAT.finditer(txt):
            tex = mm.group(2).strip()
            # líneas con opciones: map_Kd -o 1 1 1 textures/xxx.jpg
            # nos quedamos con el último “token” que tenga extensión
            tokens = [t for t in tex.split() if Path(t).suffix]
            if tokens:
                out.add(tokens[-1])
    except Exception:
        pass
    return out

def _rewrite_obj_mtllib_to_basename(dest_obj: Path, dest_mtl_name: str) -> None:
    try:
        txt = dest_obj.read_text(encoding="utf-8", errors="ignore")
        if _OBJ_MTL_LIB.search(txt):
            txt2 = _OBJ_MTL_LIB.sub(f"mtllib {dest_mtl_name}", txt)
            dest_obj.write_text(txt2, encoding="utf-8")
            print(f"  • Reescribí mtllib -> {dest_mtl_name}")
    except Exception as e:
        print(f"⚠ No pude reescribir mtllib en {dest_obj}: {e}")

def _rewrite_mtl_maps_to_basenames(dest_mtl: Path) -> None:
    try:
        txt = dest_mtl.read_text(encoding="utf-8", errors="ignore")
        def _subber(m: re.Match) -> str:
            key, val = m.group(1), m.group(2)
            tokens = val.split()
            # reemplazo último token por su basename si es ruta
            if tokens and Path(tokens[-1]).suffix:
                tokens[-1] = Path(tokens[-1]).name
            return f"{key} {' '.join(tokens)}"
        txt2 = _MTL_MAP_PAT.sub(_subber, txt)
        dest_mtl.write_text(txt2, encoding="utf-8")
        print(f"  • Reescribí rutas de texturas en {dest_mtl.name}")
    except Exception as e:
        print(f"⚠ No pude reescribir texturas en {dest_mtl}: {e}")

def _copy_obj_with_assets(src_obj: Path, dest_dir: Path) -> Path:
    """
    Copia OBJ + su MTL (si existe) + texturas referenciadas a dest_dir.
    Reescribe referencias para que el OBJ apunte a <mtl_basename> y el MTL a basenames de texturas.
    """
    src_obj = src_obj.resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Copia del OBJ con nombre saneado (para evitar espacios raros)
    clean_name = sanitize_filename(src_obj.name)
    dest_obj = _unique_dest_name(dest_dir, clean_name)
    shutil.copy2(src_obj, dest_obj)

    src_dir = src_obj.parent
    # 1) localizar MTL desde el OBJ
    mtllib_rel = _parse_obj_for_mtl(src_obj)
    dest_mtl_path: Optional[Path] = None

    if mtllib_rel:
        src_mtl = _resolve_rel(src_dir, mtllib_rel)
        if src_mtl.exists():
            dest_mtl_path = dest_dir / src_mtl.name
            try:
                shutil.copy2(src_mtl, dest_mtl_path)
                print(f"  • Copiado MTL: {src_mtl.name}")
            except Exception as e:
                print(f"⚠ No pude copiar MTL {src_mtl}: {e}")
                dest_mtl_path = None
        else:
            print(f"⚠ mtllib declarado pero no encontrado: {src_mtl}")

    # 2) si hay MTL, parsear y copiar texturas declaradas
    if dest_mtl_path:
        # lee el mtl original para saber texturas (no el copiado; vale cualquiera)
        src_mtl = _resolve_rel(src_dir, mtllib_rel)
        texture_rels = _parse_mtl_for_textures(src_mtl)
        for rel_tex in texture_rels:
            src_tex = _resolve_rel(src_dir, rel_tex)
            if src_tex.exists() and src_tex.suffix.lower() in _IMG_EXTS:
                dest_tex = dest_dir / src_tex.name
                if not dest_tex.exists():
                    try:
                        shutil.copy2(src_tex, dest_tex)
                        print(f"  • Copiada textura: {src_tex.name}")
                    except Exception as e:
                        print(f"⚠ No pude copiar textura {src_tex}: {e}")

        # reescrituras para que todo mire a archivos en el mismo folder
        _rewrite_mtl_maps_to_basenames(dest_mtl_path)
        _rewrite_obj_mtllib_to_basename(dest_obj, dest_mtl_path.name)
    else:
        # fallback: copiar MTL/IMGs adyacentes (mismo directorio) por si el OBJ no declara mtllib,
        # o el mtl está en blanco. Esto no rompe nada y a veces salva casos simples.
        for entry in src_dir.iterdir():
            if not entry.is_file():
                continue
            if entry.suffix.lower() in _MTL_EXTS | _IMG_EXTS:
                dest_aux = dest_dir / entry.name
                if not dest_aux.exists():
                    try:
                        shutil.copy2(entry, dest_aux)
                        print(f"  • Copiado asset adyacente: {entry.name}")
                    except Exception as e:
                        print(f"⚠ No pude copiar asset {entry}: {e}")

    return dest_obj


# -----------------------------------------------------------
# Biblioteca curada (index.json)
# -----------------------------------------------------------
def _library_pick_obj(clase: str) -> Optional[str]:
    try:
        if not INDEX_PATH.exists():
            return None
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        key = normalize_class(clase)
        items = data.get(key, [])
        if not items:
            return None

        # Elegimos el primero; si querés aleatorio: random.choice(items)
        rel = items[0].get("file")
        if not rel:
            return None
        src = (ASSETS_MODELS_DIR / rel).resolve()
        if not src.exists():
            print(f"⚠ Asset listado no existe: {src}")
            return None

        copied_obj = _copy_obj_with_assets(src, MODELOS3D_DIR)
        return f"/modelos/{copied_obj.name}"
    except Exception as e:
        print("⚠ index.json no disponible o inválido:", e)
        return None


# -----------------------------------------------------------
# Fallback genérico (opcional)
# -----------------------------------------------------------
_FALLBACK_MAP = {
    "laptop": "laptop_basic.obj",
    "keyboard": "keyboard_basic.obj",
    "mouse": "mouse_basic.obj",
    "monitor": "monitor_basic.obj",
    "router": "router_basic.obj",
    "switch": "switch_basic.obj",
    "server": "server_rack_basic.obj",
    "pc_tower": "pc_tower_basic.obj",
    "printer": "printer_basic.obj",
    "phone": "phone_basic.obj",
}

def _fallback_generic_obj(clase: str) -> Optional[str]:
    nombre = _FALLBACK_MAP.get(normalize_class(clase))
    if not nombre:
        return None
    src = ASSETS_MODELS_DIR / nombre
    if not src.exists():
        return None
    copied_obj = _copy_obj_with_assets(src, MODELOS3D_DIR)
    return f"/modelos/{copied_obj.name}"


# -----------------------------------------------------------
# Selección de clase objetivo para el visor 3D
# -----------------------------------------------------------
def _select_target_class(dets: List[Dict[str, Any]]) -> Optional[str]:
    """
    Elige UNA clase para modelar:
      1) Entre las TIC (whitelist), por mayor confianza.
      2) Si hay varias TIC, prioriza la que tenga asset en biblioteca.
      3) Si no hay TIC, None (para no mostrar “mesa”).
    """
    if not dets:
        return None

    # Orden por confianza desc
    ordered = sorted(dets, key=lambda x: x.get("confianza", 0.0), reverse=True)

    # 1) solo TIC
    tic_only = [d for d in ordered if is_tic_class(d["clase"])]

    if not tic_only:
        return None

    # 2) Si alguna de las TIC tiene asset en index.json, elegimos esa primero
    for d in tic_only:
        if _library_pick_obj(d["clase"]):
            return d["clase"]

    # 3) Sino, devolvemos la TIC de mayor confianza
    return tic_only[0]["clase"]


# -----------------------------------------------------------
# Principal
# -----------------------------------------------------------
def analizar_imagen_yolo(path_imagen: str) -> Dict[str, Any]:
    try:
        img_path = Path(path_imagen).resolve()
        if not img_path.exists():
            return {"descripcion": "No se detectaron objetos.", "respuesta": f"No se pudo leer la imagen: {img_path}", "objetos": [], "modelo_url": None}

        if model is None:
            return {"descripcion": "No se detectaron objetos.", "respuesta": f"Error cargando modelo YOLO: {_modelo_error}", "objetos": [], "modelo_url": None}

        img = cv2.imread(str(img_path))
        if img is None:
            return {"descripcion": "No se detectaron objetos.", "respuesta": "La imagen no pudo ser decodificada.", "objetos": [], "modelo_url": None}

        results = model.predict(img, verbose=False)
        if not results:
            return {"descripcion": "No se detectaron objetos.", "respuesta": "El modelo no devolvió resultados.", "objetos": [], "modelo_url": None}

        r = results[0]
        objetos_detectados: List[Dict[str, Any]] = []
        names = getattr(r, "names", getattr(model, "names", {}))

        if getattr(r, "boxes", None) is not None and len(r.boxes) > 0:
            for box in r.boxes:
                cls_idx = int(box.cls[0].item()) if hasattr(box.cls[0], "item") else int(box.cls[0])
                conf = float(box.conf[0].item()) if hasattr(box.conf[0], "item") else float(box.conf[0])
                clase_orig = names.get(cls_idx, str(cls_idx))
                clase = normalize_class(clase_orig)
                objetos_detectados.append({"clase": clase, "confianza": round(conf * 100, 2)})

        if not objetos_detectados:
            return {"descripcion": "No se detectaron objetos.", "respuesta": "No se encontró ningún objeto relevante.", "objetos": [], "modelo_url": None}

        # Resumen
        clases_unicas = sorted({obj["clase"] for obj in objetos_detectados})
        descripcion = ", ".join(clases_unicas)
        respuesta = f"Se detectaron los siguientes objetos: {descripcion}."

        # === Seleccionamos la clase objetivo TIC ===
        target_cls = _select_target_class(objetos_detectados)

        modelo_url: Optional[str] = None

        if target_cls:
            # 1) Biblioteca (preferida)
            modelo_url = _library_pick_obj(target_cls)
            if modelo_url:
                respuesta += f" (Modelo TIC: {target_cls})"
            else:
                # 2) Procedural (si lo tenés)
                try:
                    nombre_archivo = f"{sanitize_filename(target_cls)}_{random.randint(1000,9999)}.obj"
                    ruta_modelo = MODELOS3D_DIR / nombre_archivo
                    generar_modelo_3d_desde_imagen(str(img_path), salida_obj=str(ruta_modelo))
                    if ruta_modelo.exists():
                        modelo_url = f"/modelos/{ruta_modelo.name}"
                        respuesta += " (Modelo procedural)"
                except Exception as gen_err:
                    print(f"⚠ Error en generación 3D procedural: {gen_err}")

            # 3) Fallback genérico
            if not modelo_url:
                modelo_url = _fallback_generic_obj(target_cls)
                if modelo_url:
                    respuesta += " (Modelo genérico)"
        else:
            # No hay clase TIC clara → no forzamos cubo
            respuesta += " (No se identificó un dispositivo TIC para el visor)"

        return {
            "descripcion": descripcion,
            "respuesta": respuesta,
            "objetos": objetos_detectados,
            "modelo_url": modelo_url
        }

    except Exception as e:
        print(f"❌ Error inesperado en YOLO: {e}")
        return {"descripcion": "No se detectaron objetos.", "respuesta": f"Error interno en YOLO: {e}", "objetos": [], "modelo_url": None}
