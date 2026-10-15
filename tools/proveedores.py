from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "proveedores.json"
CAMPOS = ("nombre", "servicio", "sla_horas", "estado", "contacto")


def _norm(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_acentos.lower().strip()


@lru_cache(maxsize=1)
def _catalogo() -> dict[str, dict]:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data["proveedores"]
    return {_norm(p["nombre"]): p for p in items}


def consultar_proveedor(args) -> dict:
    proveedor = _catalogo().get(_norm(args.nombre))
    if proveedor is None:
        return {
            "error": f"proveedor {args.nombre} no existe",
            "disponibles": sorted(p["nombre"] for p in _catalogo().values()),
        }
    return {k: proveedor[k] for k in CAMPOS if k in proveedor}
