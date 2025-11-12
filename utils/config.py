# utils/config.py
import os
from dataclasses import dataclass
from pathlib import Path

# Carga .env o api.env si existen (sin romper si falta dotenv)
def _safe_load_env():
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return
    root = Path(__file__).resolve().parents[1]
    if (root / ".env").exists():
        load_dotenv(root / ".env")
    elif (root / "api.env").exists():
        load_dotenv(root / "api.env")

_safe_load_env()

@dataclass
class Settings:
    # Groq / LLM
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    base_url:    str = os.getenv("BASE_URL", "https://api.groq.com/openai/v1")
    llm_model:   str = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")

    # Rutas útiles
    root: Path = Path(__file__).resolve().parents[1]
    uploads_dir: Path = root / "data" / "uploads"
    modelos_dir: Path = root / "data" / "modelos3d"
    pedidos_dir: Path = root / "data" / "pedidos_modelado"
    yolo_weights: Path = root / "yolov5su.pt"

    def ensure_dirs(self):
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.modelos_dir.mkdir(parents=True, exist_ok=True)
        self.pedidos_dir.mkdir(parents=True, exist_ok=True)

    def validate(self):
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY no está configurada. Definila en .env o api.env.")

settings = Settings()
settings.ensure_dirs()
settings.validate()
