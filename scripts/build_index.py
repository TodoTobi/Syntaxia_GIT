# scripts/build_index.py
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB_DIR = ROOT / "assets" / "models" / "library"
INDEX_PATH = ROOT / "assets" / "models" / "index.json"

def build_index():
    index = {}
    for path in LIB_DIR.rglob("*.obj"):
        # clase = nombre de la carpeta (ej: router, laptop, monitor…)
        clase = path.parent.name.lower()
        rel_path = path.relative_to(ROOT / "assets" / "models").as_posix()

        if clase not in index:
            index[clase] = []
        index[clase].append({"file": rel_path, "name": path.stem})

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print(f"✔ Index generado en {INDEX_PATH}")

if __name__ == "__main__":
    build_index()
