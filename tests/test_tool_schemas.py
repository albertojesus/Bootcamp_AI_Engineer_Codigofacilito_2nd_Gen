from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from contracts import BUSCAR_TICKET, CONSULTAR_PROVEEDOR, BuscarTicketArgs, ConsultarProveedorArgs
from tools.proveedores import consultar_proveedor
from tools.tickets import buscar_ticket

ROOT = Path(__file__).resolve().parents[1]
PROVEEDORES = json.loads((ROOT / "data" / "proveedores.json").read_text(encoding="utf-8"))
TICKETS = json.loads((ROOT / "data" / "tickets_db.json").read_text(encoding="utf-8"))


def test_to_openai_shape():
    definition = BUSCAR_TICKET.to_openai()
    assert definition["type"] == "function"
    function = definition["function"]
    assert set(function) == {"name", "description", "parameters"}
    assert function["name"] == "buscar_ticket"
    assert "solo si el usuario menciona un ID" in function["description"]
    params = function["parameters"]
    assert params["type"] == "object"
    assert params["required"] == ["ticket_id"]
    assert params["properties"]["ticket_id"]["type"] == "string"


@pytest.mark.parametrize("bad_id", ["1042", "T-12345", "t-1042", "T-10a2"])
def test_buscar_ticket_args_reject_bad_ids(bad_id):
    with pytest.raises(ValidationError):
        BuscarTicketArgs(ticket_id=bad_id)


def test_buscar_ticket_finds_t1042():
    result = buscar_ticket(BuscarTicketArgs(ticket_id="T-1042"))
    assert result["id"] == "T-1042"
    assert result["estado"] == "en revisión"
    assert result["equipo"] == "Finanzas"
    assert set(result) == {
        "id",
        "asunto",
        "estado",
        "equipo",
        "prioridad",
        "proveedor",
        "historial",
    }
    assert 1 <= len(result["historial"]) <= 3


def test_buscar_ticket_unknown_returns_error():
    assert buscar_ticket(BuscarTicketArgs(ticket_id="T-9999")) == {
        "error": "ticket T-9999 no existe"
    }


def test_t1042_supplier_exists_with_sla():
    result = buscar_ticket(BuscarTicketArgs(ticket_id="T-1042"))
    proveedor = next(p for p in PROVEEDORES if p["nombre"] == result["proveedor"])
    assert isinstance(proveedor["sla_horas"], int)


def test_tickets_db_shape():
    assert [t["id"] for t in TICKETS] == [f"T-{n}" for n in range(1001, 1051)]
    names = {p["nombre"] for p in PROVEEDORES}
    with_supplier = [t for t in TICKETS if t["proveedor"] is not None]
    assert len(with_supplier) >= 12
    assert {t["proveedor"] for t in with_supplier} <= names
    estados = {"abierto", "en revisión", "esperando proveedor", "resuelto"}
    assert {t["estado"] for t in TICKETS} <= estados
    assert len(PROVEEDORES) == 6
    assert all(p["contacto"].endswith(".example") for p in PROVEEDORES)


def test_tickets_db_keeps_class_one_tickets():
    ejemplo = [
        json.loads(line)
        for line in (ROOT / "data" / "tickets_ejemplo.jsonl").read_text("utf-8").splitlines()
    ]
    by_id = {t["id"]: t for t in TICKETS}
    for ticket in ejemplo:
        if ticket["id"] in by_id:
            assert by_id[ticket["id"]]["asunto"] == ticket["asunto"]
            assert by_id[ticket["id"]]["descripcion"] == ticket["descripcion"]


@pytest.mark.parametrize("nombre", ["PagosRed", "pagosred", "  PAGOSRED ", "Empaques del Bajio"])
def test_consultar_proveedor_ignores_case_and_accents(nombre):
    result = consultar_proveedor(ConsultarProveedorArgs(nombre=nombre))
    assert "error" not in result
    assert isinstance(result["sla_horas"], int)


def test_consultar_proveedor_unknown_returns_clear_error():
    result = consultar_proveedor(ConsultarProveedorArgs(nombre="Proveedor Fantasma"))
    assert result["error"] == "proveedor Proveedor Fantasma no existe"
    assert "PagosRed" in result["disponibles"]


def test_consultar_proveedor_args_reject_short_names():
    with pytest.raises(ValidationError):
        ConsultarProveedorArgs(nombre="P")


def test_consultar_proveedor_spec():
    function = CONSULTAR_PROVEEDOR.to_openai()["function"]
    assert function["name"] == "consultar_proveedor"
    assert "buscar_ticket" in function["description"]
    assert function["parameters"]["required"] == ["nombre"]


def test_t1042_supplier_sla_via_tools():
    ticket = buscar_ticket(BuscarTicketArgs(ticket_id="T-1042"))
    proveedor = consultar_proveedor(ConsultarProveedorArgs(nombre=ticket["proveedor"]))
    assert proveedor["nombre"] == ticket["proveedor"]
    assert proveedor["sla_horas"] == 4
