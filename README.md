# Plataforma de Identificación de Riesgos Contractuales mediante IA

Proyecto **038** de estadía · Develop Talent & Technology (PluriOne S.A. de C.V.)
Andrus Raziel de la Rosa García · Ingeniería de Software, UPTap · 480 h

Analiza contratos con IA para identificar cláusulas de riesgo, y **ancla cada
hallazgo a su ubicación exacta en el documento** para que el área jurídica pueda
verificarlo.

---

## Cómo levantarlo

```bash
cp .env.example .env
# Pon tu XAI_API_KEY en .env y cambia SECRET_KEY
docker compose up -d --build
```

Migraciones y carga inicial:

```bash
docker compose exec api alembic upgrade head
docker compose exec api alembic revision --autogenerate -m "esquema inicial"
docker compose exec api alembic upgrade head
docker compose exec -e ADMIN_PASSWORD='tu-password' api python scripts/seed.py
```

> La primera migración (`0001_pgvector`) solo habilita la extensión `vector`;
> las tablas se generan con `--autogenerate` a partir de `app/models.py`.

| Servicio | URL |
|---|---|
| API + docs | http://localhost:8000/docs |
| Frontend | http://localhost:5173 |
| MinIO (consola) | http://localhost:9001 |

El worker descarga el modelo de embeddings (~2 GB) en el primer análisis. Queda
en el volumen `hfcache`, así que solo pasa una vez.

## Tests

```bash
docker compose exec api python -m pytest tests/ -q
```

## Cómo funciona

```
Subida  →  Extracción  →  Segmentación  →  Análisis  →  Verificación  →  Hallazgos
 API        PyMuPDF        clause_id       Grok 4.7      rapidfuzz       + resaltado
            + OCR          + bboxes        (por lotes)
```

Todo después de la subida corre en **Celery**: entre el OCR y varias llamadas al
modelo, un contrato largo tarda minutos y no cabe en un request HTTP.

### La pieza que sostiene el proyecto: verificación de citas

Grok no cita documentos propios — sus *citations* solo cubren búsqueda web y de
X — y tampoco acepta PDF de entrada. La trazabilidad que el 038 pide se
construye así:

1. PyMuPDF extrae cada bloque con **página y coordenadas**.
2. El segmentador agrupa bloques en cláusulas con un `clause_id` estable.
3. Al modelo se le manda solo texto, con cada cláusula rotulada `[C-001]`.
4. El schema Pydantic lo obliga a devolver `clause_id` + `cita_textual`.
5. **`rapidfuzz` confronta esa cita contra el texto real de la cláusula.**
6. Con el `clause_id` se recuperan las coordenadas → resaltado en el visor.

El paso 5 es lo que distingue un dato de una afirmación. Cada hallazgo queda
marcado como:

| Estado | Significado |
|---|---|
| `verificada` | La cita existe textualmente (similitud ≥ 95%). Es evidencia. |
| `aproximada` | Coincidencia parcial (≥ 80%), probablemente ruido de OCR. A revisión. |
| `no_verificada` | No se encontró en el documento. **Posible alucinación.** |

El frontend lo muestra explícitamente y permite filtrar. Un hallazgo no
verificado nunca se le presenta al abogado como evidencia.

## Estructura

```
backend/
  app/
    config.py            Settings (pydantic-settings)
    db.py                Engine perezoso + sesiones
    enums.py             Enums del dominio, sin dependencias de ORM
    models.py            SQLAlchemy 2.0
    schemas.py           Schemas HTTP
    security.py          JWT + argon2
    deps.py              Auth y autorización por rol
    storage.py           MinIO
    audit.py             Registro de auditoría
    tasks.py             Pipeline Celery
    routers/             auth · contratos · hallazgos
    ingest/
      documento.py       Block / Documento (datos puros)
      extract.py         PyMuPDF + OCRmyPDF
      clauses.py         Segmentación y clause_id
    ai/
      client.py          Envoltura del SDK de xAI
      schemas.py         Schema de salida del modelo
      analyze.py         Prompt, lotes y puntuación de riesgo
      verify.py          Verificación de citas
      embeddings.py      bge-m3 local
  seeds/risk_types.json  Catálogo inicial de 18 tipos de riesgo
  scripts/seed.py        Admin + catálogo (idempotente)
  tests/                 Verificador y segmentador

frontend/
  src/
    lib/api.ts           Cliente HTTP
    lib/tipos.ts         Tipos compartidos
    components/
      VisorContrato.tsx  react-pdf + capa de resaltado
      PanelHallazgos.tsx Lista, filtro y estado de cita
    pages/               Login · Contratos · Detalle
```

## Decisiones y por qué

- **pgvector en Postgres**, no un motor de búsqueda aparte: un servicio menos
  que operar y desplegar.
- **Embeddings locales (`bge-m3`)**: xAI no expone endpoint de embeddings, y
  bge-m3 rinde bien en español sin costo por token.
- **Sin LangChain**: en este alcance el SDK directo es menos código y más control.
- **Enums fuera del ORM** (`app/enums.py`): la lógica pura —verificación,
  puntuación— se prueba sin levantar base de datos ni instalar el driver.
- **La puntuación de riesgo la manda el hallazgo más grave**, no el promedio: un
  contrato con una cláusula crítica es riesgoso aunque las otras cuarenta estén
  limpias. Los hallazgos no verificados pesan la mitad.

## Riesgos abiertos

1. **Calidad del OCR.** Los modelos de texto de Grok no tienen visión, así que
   si Tesseract falla en un escaneo no hay plan B. Hay que medirlo con
   documentos reales de PluriOne cuanto antes.
2. **Catálogo de riesgos.** Los 18 tipos del seed son un punto de partida; el
   área jurídica tiene que validarlos y ajustarlos.
3. **Set de evaluación.** El objetivo específico #4 del 038 exige validar
   precisión. Sin contratos etiquetados por un abogado no hay cifra que reportar
   en la defensa.

## Pendiente

- [ ] Dashboard con Recharts (el endpoint `/api/hallazgos/resumen/dashboard` ya existe)
- [ ] Búsqueda semántica sobre cláusulas (pgvector ya está, falta exponerlo)
- [ ] Exportar reporte de revisión a PDF
- [ ] Langfuse para trazas del modelo
- [ ] GitHub Actions (lint + tests)
- [ ] Set de evaluación etiquetado y métricas de precisión
