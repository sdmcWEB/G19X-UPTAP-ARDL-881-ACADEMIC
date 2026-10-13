"""El almacén recibe nombres de archivo que subió un usuario.

Sin confinamiento, una llave como `../../etc/passwd` escribe fuera del
volumen. Estas pruebas cubren ese borde.
"""

import pytest

from app import storage


@pytest.fixture(autouse=True)
def raiz_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(storage.settings, "storage_dir", str(tmp_path))
    return tmp_path


def test_guarda_y_recupera():
    storage.put("abc-123/contrato.pdf", b"%PDF-1.7 contenido", "application/pdf")
    assert storage.get("abc-123/contrato.pdf") == b"%PDF-1.7 contenido"


def test_crea_los_directorios_intermedios(raiz_temporal):
    storage.put("una/ruta/profunda/x.pdf", b"ok", "application/pdf")
    assert (raiz_temporal / "una/ruta/profunda/x.pdf").is_file()


def test_un_objeto_inexistente_levanta():
    with pytest.raises(FileNotFoundError):
        storage.get("no-existe/x.pdf")


@pytest.mark.parametrize(
    "llave",
    [
        "../fuera.pdf",
        "abc/../../fuera.pdf",
        "/etc/passwd",
        "abc/../../../../../../tmp/fuera.pdf",
    ],
)
def test_rechaza_llaves_que_salen_de_la_raiz(llave):
    with pytest.raises(ValueError, match="fuera de la raíz"):
        storage.put(llave, b"malicioso", "application/pdf")
    with pytest.raises(ValueError, match="fuera de la raíz"):
        storage.get(llave)


def test_un_nombre_con_puntos_que_no_escapa_sí_pasa(raiz_temporal):
    """`..` dentro del nombre no es un escape mientras no salga de la raíz."""
    storage.put("abc/v1..2/contrato.final.pdf", b"ok", "application/pdf")
    assert (raiz_temporal / "abc/v1..2/contrato.final.pdf").is_file()


def test_borrar_es_idempotente():
    storage.put("abc/x.pdf", b"ok", "application/pdf")
    storage.delete("abc/x.pdf")
    storage.delete("abc/x.pdf")  # no debe levantar
    with pytest.raises(FileNotFoundError):
        storage.get("abc/x.pdf")
