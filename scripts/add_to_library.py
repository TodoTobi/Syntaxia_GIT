# scripts/add_to_library.py
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "models"
INDEX = ASSETS / "index.json"

def main():
    if len(sys.argv) < 3:
        print("Uso: python scripts/add_to_library.py <clase> <ruta_al_obj> [name] [license] [source] [author]")
        sys.exit(1)
    clase = sys.argv[1].lower()
    src = Path(sys.argv[2]).resolve()
    if not src.exists():
        raise SystemExit(f"No existe: {src}")

    # destino relativo
    dest_rel = Path("library") / clase / src.name
    dest = ASSETS / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(src.read_bytes())

    meta = {"file": str(dest_rel).replace("\\", "/")}
    if len(sys.argv) > 3: meta["name"] = sys.argv[3]
    if len(sys.argv) > 4: meta["license"] = sys.argv[4]
    if len(sys.argv) > 5: meta["source"] = sys.argv[5]
    if len(sys.argv) > 6: meta["author"] = sys.argv[6]

    data = {}
    if INDEX.exists():
        data = json.loads(INDEX.read_text(encoding="utf-8"))
    data.setdefault(clase, []).append(meta)
    INDEX.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"OK → {dest_rel}")

if __name__ == "__main__":
    main()
