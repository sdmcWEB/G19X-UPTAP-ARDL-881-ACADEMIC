"""Almacenamiento de los archivos originales.

Guarda en disco, sobre un volumen de Docker. La interfaz (`put` / `get`) es
deliberadamente la de un almacén de objetos: cambiar a S3 o MinIO es
reescribir este archivo y nada más.

Se eligió disco porque las imágenes de MinIO dejaron de ser accesibles sin
registro en Docker Hub y en quay.io, y para el volumen de este proyecto
—decenas de contratos, un solo nodo— un servicio aparte no se paga solo.
"""

from pathlib import Path

from app.config import settings


def _raiz() -> Path:
    raiz = Path(settings.storage_dir)
    raiz.mkdir(parents=True, exist_ok=True)
    return raiz


def _ruta(object_key: str) -> Path:
    """Resuelve la llave a una ruta, confinada a la raíz de almacenamiento.

    La llave incluye el nombre de archivo que subió el usuario. Sin esta
    comprobación, un nombre como `../../etc/passwd` escribiría fuera del
    volumen.
    """
    raiz = _raiz().resolve()
    destino = (raiz / object_key).resolve()

    if not destino.is_relative_to(raiz):
        raise ValueError(f"Llave de almacenamiento fuera de la raíz: {object_key!r}")

    return destino


def put(object_key: str, data: bytes, content_type: str) -> None:
    # content_type se ignora en disco; se conserva en el parámetro porque la
    # interfaz tiene que seguir sirviendo para un almacén de objetos.
    del content_type

    destino = _ruta(object_key)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(data)


def get(object_key: str) -> bytes:
    destino = _ruta(object_key)
    if not destino.is_file():
        raise FileNotFoundError(f"No existe el objeto {object_key!r}")
    return destino.read_bytes()


def delete(object_key: str) -> None:
    _ruta(object_key).unlink(missing_ok=True)
