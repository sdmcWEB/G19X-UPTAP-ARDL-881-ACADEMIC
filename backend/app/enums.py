"""Enumeraciones del dominio.

Viven aparte de `app/models.py` a propósito: la lógica pura (verificación de
citas, puntuación de riesgo, schemas del modelo) necesita estos valores sin
tener que arrastrar SQLAlchemy ni el driver de Postgres.
"""

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    JURIDICO = "juridico"
    LECTOR = "lector"


class ContractStatus(StrEnum):
    RECIBIDO = "recibido"
    EXTRAYENDO = "extrayendo"
    ANALIZANDO = "analizando"
    LISTO = "listo"
    ERROR = "error"


class Severity(StrEnum):
    CRITICA = "critica"
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"
    INFORMATIVA = "informativa"


class VerificationStatus(StrEnum):
    """Resultado del anclaje de la cita devuelta por el modelo."""

    VERIFICADA = "verificada"  # la cita existe textualmente en la cláusula
    APROXIMADA = "aproximada"  # coincidencia parcial, revisar
    NO_VERIFICADA = "no_verificada"  # no se encontró: posible alucinación


class ReviewStatus(StrEnum):
    """Dictamen del abogado sobre un hallazgo.

    Separado de `VerificationStatus`: aquel dice si la *cita* existe en el
    documento, esto dice si el *riesgo* es real. Un hallazgo puede tener la
    cita perfectamente verificada y aun así ser descartado porque en ese
    contrato esa cláusula no representa un problema.
    """

    PENDIENTE = "pendiente"
    CONFIRMADO = "confirmado"
    DESCARTADO = "descartado"
