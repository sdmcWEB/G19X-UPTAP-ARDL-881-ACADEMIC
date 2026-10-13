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

El worker descarga el modelo de embeddings (~2 GB) en el primer análisis. Queda
en el volumen `hfcache`, así que solo pasa una vez.

## Tests

```bash
docker compose exec api python -m pytest tests/ -q
```

Sin Docker, los tests solo necesitan el set base más `dev` — ni PyTorch ni base
de datos:

```bash
cd backend && pip install -e ".[dev]" && pytest tests/ -q
```

`sentence-transformers` vive en el extra `ml` porque arrastra PyTorch (~2 GB) y
solo el worker lo usa. El Dockerfile instala `.[dev,ml]`; CI instala `.[dev]`.

## Problema conocido: el llavero de macOS bloquea los pulls

Si `docker compose up` falla con `error getting credentials … Keychain Error` o
se queda colgado sin avanzar, macOS está mostrando un diálogo de acceso al
llavero que nadie contesta. El ítem guardado de Docker Hub no autoriza al
binario actual de `docker` (pasa al cambiar de Docker Desktop a OrbStack).

Las imágenes del proyecto son públicas, así que la credencial no hace falta:

```bash
docker logout
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
    storage.py           Archivos en volumen, con la interfaz de un almacén de objetos
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
      Layout.tsx         Cascarón con navegación
      VisorContrato.tsx  react-pdf + capa de resaltado
      PanelHallazgos.tsx Lista, filtro y estado de cita
      viz/               Tarjeta con gemela en tabla, tooltip, stat tile,
                         medidor y las cuatro gráficas del tablero
    pages/               Login · Dashboard · Contratos · Detalle
```

## El tablero

Cinco tarjetas sobre una sola rebanada de datos: el filtro de periodo vive
arriba de todo y las recalcula juntas.

| Tarjeta | Forma | Por qué esa |
|---|---|---|
| Riesgo · contratos · hallazgos · citas | Stat tiles | Son cifras sueltas. Una barra de un solo dato no es una gráfica. |
| Calidad de la evidencia | Barra apilada horizontal | Parte-todo de tres clases con polaridad. Usa la paleta de estado porque *es* estado. |
| Hallazgos por severidad | Columnas, rampa ordinal | La severidad es una categoría **ordenada**: un solo tono, más severo = más oscuro. |
| Tipos de riesgo | Barras horizontales, un solo color | Categorías **nominales**: oscurecer la barra más larga doblaría en el color lo que el largo ya dice. |
| Actividad | Múltiplos pequeños | Contratos y hallazgos viven en escalas distintas. Dos ejes en un plot inventan una correlación que no está en los datos. |
| Contratos de mayor riesgo | Tabla con medidores | Cinco filas con nombre y puntuación: se lee mejor en tabla que en barras. |

Cada gráfica tiene su **gemela en tabla** (botón "Ver tabla"): ningún valor
queda accesible solo por color o solo por tooltip. Las rampas están validadas
con el verificador de la guía de visualización — la ordinal de severidad pasa
las cuatro comprobaciones en modo claro y oscuro; el trío de estado pasa
separación CVD (ΔE 11.3) y visión normal (ΔE 27.6), y su contraste bajo en
claro lleva la mitigación prescrita: etiquetas visibles y vista de tabla.

Los pasos oscuros están definidos y validados pero se activan con
`data-theme="dark"`, no con la preferencia del sistema: el resto de la app es
solo claro y seguir al sistema operativo pondría tarjetas oscuras dentro de un
cascarón blanco.

## Decisiones y por qué

- **pgvector en Postgres**, no un motor de búsqueda aparte: un servicio menos
  que operar y desplegar.
- **Archivos en un volumen**, no en MinIO: MinIO dejó de publicar imágenes
  accesibles sin registro, y a la escala de este proyecto un servicio de
  objetos aparte no se paga solo. `storage.py` conserva la interfaz de un
  almacén de objetos (`put` / `get` / `delete`), así que migrar a S3 es
  reescribir ese archivo y nada más. Las llaves se confinan a la raíz del
  volumen: el nombre del archivo lo elige quien sube el contrato.
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

- [ ] Búsqueda semántica sobre cláusulas (pgvector ya está, falta exponerlo)
- [ ] Exportar reporte de revisión a PDF
- [ ] Langfuse para trazas del modelo
- [ ] Set de evaluación etiquetado y métricas de precisión
