# scripts/ver_modelos.py
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.config import settings

print("Config OK. Modelo LLM:", settings.llm_model)
