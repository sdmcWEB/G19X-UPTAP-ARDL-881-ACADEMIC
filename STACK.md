# Stack tecnológico — Proyecto 038

**Plataforma de Identificación de Riesgos Contractuales mediante IA**
Empresa: PluriOne S.A. de C.V. / Develop Talent & Technology · 480 h de estadía

Decisiones: contratos **digitales y escaneados** (requiere OCR) · auth de
**usuarios internos con roles** (sin SSO, sin multi-tenant) · LLM: **Grok (xAI)**.

---

## 1. Backend

| Pieza | Tecnología | Nota |
|---|---|---|
| Framework | FastAPI + Uvicorn | Async nativo, OpenAPI automático |
| Lenguaje | Python 3.12 | |
| Validación | Pydantic v2 | Schemas de request/response y de salida del LLM |
| ORM | SQLAlchemy 2.0 | Estilo `select()`, no el legacy |
| Migraciones | Alembic | |
| Cola de trabajos | Celery + Redis | El análisis de un contrato tarda minutos: **no va en el request** |
| Tests | pytest + httpx + pytest-asyncio | |

## 2. Datos

| Pieza | Tecnología | Nota |
|---|---|---|
| Base de datos | PostgreSQL 16 | |
| Búsqueda semántica | **pgvector** | Extensión de Postgres: reemplaza Azure AI Search sin sumar servicio |
| Embeddings | **`bge-m3` local** (`sentence-transformers`) | xAI **no ofrece embeddings**: se resuelve local. Fuerte en español y sin costo por token |
| Archivos | MinIO (S3-compatible) | Los PDFs originales no van en la BD |

## 3. Ingesta de documentos

| Pieza | Tecnología | Nota |
|---|---|---|
| PDF con texto | PyMuPDF (`pymupdf`) | Extracción rápida + coordenadas de cada bloque |
| Word | `python-docx` | |
| **OCR (escaneados)** | OCRmyPDF + Tesseract (`spa`) | **Obligatorio, sin red de seguridad**: los modelos de texto de Grok no tienen visión, así que no hay fallback de "mandar la imagen al modelo" |
| Segmentación | Regex + heurística de cláusulas | Cortar por "CLÁUSULA", numerales, artículos |

> Las **coordenadas** son clave: sin ellas no puedes resaltar la cláusula de
> riesgo en el visor del frontend.

## 4. IA

| Pieza | Tecnología | Nota |
|---|---|---|
| Modelo | **Grok `grok-4.7`** (xAI) | 500k de contexto, con razonamiento. El default que xAI recomienda |
| SDK | `xai_sdk` (oficial, Python) | `Client(api_key=...)` → `client.chat.create(model="grok-4.7")` |
| Salida estructurada | `chat.parse(ModeloPydantic)` | Fuerza el JSON del hallazgo (tipo, severidad, cláusula, recomendación) |
| Anclaje de cláusulas | **Propio** — `clause_id` + verificación de cita | Ver abajo: Grok no cita documentos propios |
| Verificación de citas | `rapidfuzz` | Confirma que la cita textual existe de verdad en la cláusula |
| Trazas | Langfuse (self-hosted) | Cada llamada auditada: cubre el requisito de auditoría del 038 |
| Evaluación | Set de contratos etiquetados + pytest | **Objetivo específico #4** del 038: "validar precisión y desempeño" |

**LangChain: no.** El SDK directo es menos código y más control en este alcance.
Se menciona en el documento del 038 como capa opcional.

### 4.1 Anclaje y trazabilidad de cláusulas (trabajo propio)

Las *citations* de xAI solo cubren fuentes de búsqueda web y de X — **no citan
spans de un documento que tú envías**. Tampoco acepta PDF como entrada. La
trazabilidad "hallazgo → cláusula → página", que el 038 pide para la revisión
jurídica, hay que construirla:

1. PyMuPDF extrae cada bloque con sus **coordenadas** y número de página.
2. El segmentador agrupa bloques en cláusulas y asigna un `clause_id` estable.
3. Se envía a Grok **solo el texto de las cláusulas, cada una con su `clause_id`**.
4. El schema Pydantic obliga a devolver `clause_id` + `cita_textual` por hallazgo.
5. Se valida con `rapidfuzz` que `cita_textual` aparezca en esa cláusula. Si no
   coincide, el hallazgo se marca como **no verificado** y no se le muestra al
   abogado como cita.
6. Con el `clause_id` se recuperan las coordenadas → el resaltado en `react-pdf`.

El paso 5 es el que sostiene la defensa del proyecto: convierte una cita
posiblemente inventada en un dato verificado.

## 5. Frontend

| Pieza | Tecnología | Nota |
|---|---|---|
| Base | React 19 + Vite + TypeScript | |
| Estado servidor | TanStack Query | Polling del estado de análisis |
| UI | Tailwind + shadcn/ui | |
| Visor de contratos | **react-pdf (pdf.js)** + capa de resaltado | El corazón de la UI: el hallazgo se ve sobre el documento |
| Gráficas | Recharts | Dashboard de puntuación de riesgo |
| Formularios | React Hook Form + Zod | |

## 6. Seguridad

| Pieza | Tecnología |
|---|---|
| Auth | JWT (access + refresh) con `fastapi-users` |
| Hash de contraseñas | argon2 (`passlib[argon2]`) |
| Roles | admin · jurídico · lector |
| Secretos | Variables de entorno + `pydantic-settings` |
| Auditoría | Tabla `audit_log` (quién, qué, cuándo) |

## 7. DevOps

| Pieza | Tecnología |
|---|---|
| Contenedores | Docker + Docker Compose |
| CI/CD | GitHub Actions (lint, tests, build) |
| Lint/format | Ruff (Python) · ESLint + Prettier (TS) |
| Logs | structlog (JSON estructurado) |
| Metodología | Scrum, sprints de 2 semanas |

---

## Servicios en Docker Compose

```
api        FastAPI
worker     Celery
db         Postgres 16 + pgvector
redis      Broker de Celery
minio      Storage de archivos
langfuse   Trazas de LLM
web        React (Vite)
```

## Pendientes de definir

- [ ] Catálogo de tipos de riesgo contractual (lo define el área jurídica de PluriOne)
- [ ] Contratos de muestra para el set de evaluación
- [ ] Volumen esperado: ¿contratos/mes? Define si Celery basta o hace falta escalar
- [ ] Verificar si xAI expone caching de prompt explícito (su precio cambia por
      encima de 200k tokens). Mientras tanto: mantener estable el prefijo del prompt
- [ ] Medir calidad de OCR con escaneos reales de PluriOne: es el riesgo técnico #1
