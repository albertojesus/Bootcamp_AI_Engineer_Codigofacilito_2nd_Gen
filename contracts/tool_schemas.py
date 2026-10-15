"""Contratos de las herramientas: qué recibe cada una y cómo se le describe al modelo."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, Field

from contracts.structured_output import sanitize_schema
from tools.proveedores import consultar_proveedor
from tools.tickets import buscar_ticket


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    args_model: type[BaseModel]
    handler: Callable[[BaseModel], dict]

    def to_openai(self) -> dict:
        """Definición de la herramienta en el formato `tools` de la API compatible con OpenAI.

        `parameters` sale del modelo Pydantic, sin `pattern`, `maxLength`, etc. (ver
        `sanitize_schema`): esas reglas se validan localmente en `execute_tool`.
        """
        parameters = sanitize_schema(self.args_model.model_json_schema(), strict=False)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters,
            },
        }


class BuscarTicketArgs(BaseModel):
    ticket_id: str = Field(pattern=r"^T-\d{4}$")


class ConsultarProveedorArgs(BaseModel):
    nombre: str = Field(
        min_length=2, description="Nombre del proveedor, tal como aparece en el ticket"
    )


BUSCAR_TICKET = ToolSpec(
    name="buscar_ticket",
    description=(
        "Obtiene estado e historial de un ticket por su ID. "
        "Úsala solo si el usuario menciona un ID."
    ),
    args_model=BuscarTicketArgs,
    handler=buscar_ticket,
)

CONSULTAR_PROVEEDOR = ToolSpec(
    name="consultar_proveedor",
    description=(
        "Obtiene servicio, SLA en horas, estado y contacto de un proveedor por su nombre. "
        "Úsala solo con un nombre que venga de un ticket (buscar_ticket) o que el usuario "
        "haya dado. No adivines nombres de proveedores."
    ),
    args_model=ConsultarProveedorArgs,
    handler=consultar_proveedor,
)
