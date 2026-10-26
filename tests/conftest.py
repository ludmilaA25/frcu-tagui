"""Configuración de pytest: agrega la carpeta de los módulos al path de Python."""

import sys
from pathlib import Path

# La carpeta donde viven bot.py, configuracion.py, compras.py, etc.
_ejecutables = Path(__file__).resolve().parent.parent / "projects" / "2026" / "TagUI" / "team-13" / "Ejecutables"

if str(_ejecutables) not in sys.path:
    sys.path.insert(0, str(_ejecutables))
