# Plataforma de Identificación de Riesgos Contractuales mediante IA

Proyecto **038** de estadía · Develop Talent & Technology (PluriOne S.A. de C.V.)
Andrus Raziel de la Rosa García · Ingeniería de Software, UPTap · 480 h

Analiza contratos con IA para identificar cláusulas de riesgo, y **ancla cada
hallazgo a su ubicación exacta en el documento** para que el área jurídica pueda
verificarlo.

---

## Puesta en marcha

Guía completa para correr el sistema en una máquina nueva. Probada de principio
a fin el 20-oct-2026.

### Requisitos

| Qué | Versión | Nota |
|---|---|---|
| Docker | 24 o superior | Docker Desktop, OrbStack o Colima. Es lo único indispensable |
| Git | cualquiera | Para clonar |
| Espacio en disco | ~8 GB | La imagen del backend pesa 3.7 GB (incluye PyTorch) y el modelo de embeddings otros 2 GB |
| RAM libre | 6 GB | Postgres, Redis, API, worker y frontend a la vez |

No hace falta instalar Python, Node, Postgres ni Tesseract: todo corre en
contenedores.

### Paso 1 — Clonar

```bash
git clone https://github.com/sdmcWEB/G19X-UPTAP-ARDL-881-ACADEMIC.git
cd G19X-UPTAP-ARDL-881-ACADEMIC
```

### Paso 2 — Configurar el entorno

```bash
cp .env.example .env
```

Abre `.env` y cambia dos valores:

- `SECRET_KEY` — genera uno con `openssl rand -hex 32`. Firma los tokens de sesión.
- `XAI_API_KEY` — tu llave de [console.x.ai](https://console.x.ai).

**Sin la llave el sistema arranca igual.** Sube contratos, extrae el texto,
aplica OCR, segmenta en cláusulas y genera los embeddings; solo falla en el paso
del análisis, con un mensaje explícito en la ficha del contrato. Sirve para
evaluar todo lo demás.

### Paso 3 — Levantar

```bash
docker compose up -d --build
```

La primera vez tarda entre 5 y 15 minutos: descarga las imágenes base y compila
el backend con PyTorch. Las siguientes son de segundos.

Comprueba que los cinco servicios estén arriba:

```bash
docker compose ps
```

### Paso 4 — Crear el esquema y los datos iniciales

```bash
docker compose exec api alembic upgrade head
docker compose exec -e ADMIN_PASSWORD='TuPassword123!' api python scripts/seed.py
```

Esto crea las 7 tablas, habilita la extensión `vector` y carga el catálogo con
18 tipos de riesgo contractual más el usuario administrador
(`admin@develop.com.mx` con la contraseña que acabas de poner).

### Paso 5 — Entrar

| Servicio | URL |
|---|---|
| Aplicación | http://localhost:5173 |
| API y documentación interactiva | http://localhost:8000/docs |

Inicia sesión con `admin@develop.com.mx` y tu contraseña.

### Paso 6 — Probar que funciona

Sube un contrato en PDF desde **Contratos → Subir contrato**. La lista se
actualiza sola mientras se procesa.

**La primera subida tarda unos 3 minutos de más**: el worker descarga el modelo
de embeddings `bge-m3` (~2 GB). Queda guardado en el volumen `hfcache` y las
siguientes son inmediatas.

Al terminar, abre el contrato: a la izquierda el documento original, a la
derecha los hallazgos. Al hacer clic en uno, el visor salta a su página y
resalta la cláusula exacta.

También hay un recorrido automatizado:

```bash
ADMIN_PASSWORD='TuPassword123!' ./scripts/smoke.sh ruta/al/contrato.pdf
```

Recorre salud, login, subida, pipeline y tablero, e imprime el avance.

---

## Probarlo desde otro dispositivo

Para que alguien más lo revise desde su laptop o su teléfono sin instalar nada,
basta con que esté en la **misma red** que la máquina donde corre.

### Paso 1 — Averiguar la IP de la máquina anfitriona

```bash
ipconfig getifaddr en0
```

En Linux: `hostname -I | awk '{print $1}'`. En Windows: `ipconfig` y busca
"Dirección IPv4". Da algo como `192.168.1.12`.

### Paso 2 — Abrirla desde el otro dispositivo

```
http://192.168.1.12:5173
```

Sustituye la IP por la tuya. No hace falta configurar nada más: el frontend ya
escucha en todas las interfaces y reenvía las llamadas a la API por dentro, así
que el otro dispositivo solo necesita ese puerto.

### Si no carga

1. **Firewall.** En macOS, Ajustes del Sistema → Red → Firewall: permite las
   conexiones entrantes de Docker. En Windows, autoriza Docker Desktop en el
   Firewall de Windows.
2. **Red distinta.** Comprueba que ambos equipos estén en el mismo Wi-Fi. Muchas
   redes de invitados aíslan los dispositivos entre sí y nunca van a verse.
3. **Comprueba desde la anfitriona primero.** `curl http://TU_IP:5173/api/health`
   debe responder `{"status":"ok"}`. Si falla ahí, el problema no es el otro
   dispositivo.

> Esto es para evaluación en red local. No expongas estos puertos a internet:
> el sistema corre en modo desarrollo, sin HTTPS.

---

## Problemas conocidos

**El llavero de macOS bloquea la descarga de imágenes.** Si `docker compose up`
falla con `error getting credentials … Keychain Error` o se queda colgado sin
avanzar, la credencial guardada de Docker Hub no autoriza al binario actual de
`docker` (pasa al cambiar de Docker Desktop a OrbStack). Las imágenes del
proyecto son públicas, así que la credencial no hace falta:

```bash
docker logout
```

**La primera búsqueda o el primer análisis tardan.** Es la carga del modelo de
embeddings. La API lo precalienta al arrancar en segundo plano; el worker lo
descarga en su primer contrato.

**Un contrato se queda en "Analizando".** Revisa el log del worker:

```bash
docker compose logs worker --tail 50
```

**Empezar de cero.** Borra los volúmenes y repite desde el paso 3:

```bash
docker compose down -v
```

---

## Detener

```bash
docker compose down
```

Los datos sobreviven en los volúmenes. Para borrarlos también, `docker compose down -v`.

## Estado verificado

Lo que se ha comprobado ejecutando, no suponiendo (20-oct-2026):

- La pila completa levanta con `docker compose up`, los cinco servicios.
- Las migraciones crean las 7 tablas con la extensión `vector` 0.8.7.
- El seed carga 18 tipos de riesgo y el usuario administrador.
- Un PDF de 3 páginas produjo 18 cláusulas con sus coordenadas y 18 embeddings
  de 1024 dimensiones.
- La búsqueda semántica responde y ordena por significado.
- El visor renderiza el PDF y, al seleccionar un hallazgo, salta a su página y
  resalta la cláusula correcta.
- El acceso desde otro dispositivo de la red funciona: aplicación, proxy y
  login real a través de la IP de la máquina anfitriona.
- CI en verde: ruff, 130 pruebas, `tsc` y el build de ambas imágenes.

**El único paso sin ejercitar es la llamada al modelo de Grok**, que necesita
una `XAI_API_KEY` válida.

## Búsqueda semántica

`GET /api/busqueda?q=...` vectoriza la consulta con el mismo modelo que las
cláusulas y pgvector ordena por distancia coseno. Busca por significado:
*"cómo se capacita al personal"* encuentra *"Capacitar administradores y
personal jurídico"* sin compartir palabras.

El filtrado usa dos cortes. Uno absoluto, y otro **relativo al mejor
resultado**: dentro de un mismo contrato todas las cláusulas se parecen un poco
entre sí, así que un umbral fijo devuelve el documento entero. Ambos están
calibrados contra un solo documento — hay que reajustarlos con un corpus real.

El modelo se precalienta en un hilo al arrancar la API; sin eso la primera
búsqueda tardaba ~25 s en cargar bge-m3.

## Reporte de revisión en PDF

Desde la ficha de un contrato, **Descargar reporte** genera el documento que el
abogado se lleva: resumen por severidad y cada hallazgo con su cláusula,
página, cita, explicación y recomendación.

La decisión de diseño que manda sobre el resto: **una cita que no se pudo
confirmar se ve distinta en el papel**. Si en el documento impreso un hallazgo
verificado y uno inventado se leen igual, el reporte traiciona el propósito del
sistema. El encabezado dice cuántas citas quedaron sin confirmar y cada una
lleva su sello.

```
GET /api/contratos/{id}/reporte.pdf
```

## Evaluación de precisión

El objetivo específico que sostiene la hipótesis del proyecto. Mide dos cosas:

- **Detección** — precisión, exhaustividad y F1 contra contratos que etiquetó
  un abogado, con desglose por tipo de riesgo.
- **Calidad de la evidencia** — de los hallazgos equivocados, qué proporción
  trae el verificador marcada. Es la métrica central: un falso positivo con
  cita impecable es justo lo que este sistema existe para evitar.

```bash
docker compose exec api python scripts/evaluar.py
```

El formato de etiquetado y el flujo para el área jurídica están en
[`backend/evaluacion/README.md`](backend/evaluacion/README.md). Hace falta que
PluriOne entregue los contratos etiquetados; el arnés ya está listo para
recibirlos.

## Tests

```bash
docker compose exec api python -m pytest tests/ -q
```

Dos clases de prueba:

- **Lógica pura** — verificador de citas, segmentador, almacén, métricas y
  generación del PDF. No necesitan base de datos.
- **API** — autenticación, control de acceso por rol, validación de subidas y
  los endpoints del tablero. Corren contra **Postgres real**, no SQLite: los
  modelos usan tipos del dialecto de Postgres y pgvector, y una prueba sobre
  otro motor verifica un sistema que no existe.

Cada prueba de API se ejecuta dentro de una transacción que se revierte al
terminar, y cada petición abre su propia sesión igual que en producción. Sin
eso, una sola sesión compartida deja objetos en el mapa de identidad y la
prueba ve datos que ya se borraron.

Sin Docker, las de lógica pura corren solas y las de API se saltan con un
mensaje explícito:

```bash
cd backend && pip install -e ".[dev]" && pytest tests/ -q
```

`sentence-transformers` vive en el extra `ml` porque arrastra PyTorch (~2 GB) y
solo el worker lo usa. El Dockerfile instala `.[dev,ml]`; CI instala `.[dev]`
y levanta un Postgres con pgvector para las pruebas de API.

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
  scripts/evaluar.py     Reporte de precisión contra contratos etiquetados
  evaluacion/            Formato de etiquetado y guía para el área jurídica
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

- [ ] Langfuse para trazas del modelo
- [ ] Contratos etiquetados por el área jurídica (el arnés de medición ya está)
