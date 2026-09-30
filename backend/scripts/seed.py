"""Carga inicial: usuario administrador y catálogo de riesgos.

    docker compose exec api python scripts/seed.py

Es idempotente: se puede correr varias veces sin duplicar nada.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.db import SessionLocal
from app.models import RiskType, Role, Severity, User
from app.security import hash_password

SEED = Path(__file__).parent.parent / "seeds" / "risk_types.json"


def main() -> None:
    db = SessionLocal()
    try:
        # --- Administrador ---
        email = os.getenv("ADMIN_EMAIL", "admin@develop.com.mx")
        password = os.getenv("ADMIN_PASSWORD")
        if not password:
            print("Define ADMIN_PASSWORD antes de correr el seed.", file=sys.stderr)
            print("  ADMIN_PASSWORD='...' python scripts/seed.py", file=sys.stderr)
            raise SystemExit(1)

        if db.scalar(select(User).where(User.email == email)) is None:
            db.add(
                User(
                    email=email,
                    nombre="Administrador",
                    password_hash=hash_password(password),
                    role=Role.ADMIN,
                )
            )
            print(f"Usuario administrador creado: {email}")
        else:
            print(f"El usuario {email} ya existe, no se toca.")

        # --- Catálogo de riesgos ---
        nuevos = 0
        for fila in json.loads(SEED.read_text(encoding="utf-8")):
            if db.scalar(select(RiskType).where(RiskType.codigo == fila["codigo"])):
                continue
            db.add(
                RiskType(
                    codigo=fila["codigo"],
                    nombre=fila["nombre"],
                    descripcion=fila["descripcion"],
                    severidad_default=Severity(fila["severidad_default"]),
                    peso=fila["peso"],
                    activo=fila["activo"],
                )
            )
            nuevos += 1

        db.commit()
        print(f"Tipos de riesgo agregados: {nuevos}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
