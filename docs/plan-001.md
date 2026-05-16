# Plan de Implementación — spec-001 Backend Python


**Sistema:** Preventivo de Seguridad Vial
**Stack:** Python · FastAPI · SQLAlchemy Core · SQLite (proto) · Docker
**Fecha:** 2026-05-08
**Estado:** En planificación


---


## Reglas para el agente implementador


> **Lee este bloque entero antes de escribir código.** Estas reglas no son sugerencias.


### Operativas


1. **Trabajo secuencial por fase.** Empezás Fase N solo cuando la Fase N-1 está completa y su "Criterio de Done" fue verificado con comandos reales (curl, sqlite3, docker), no por inspección visual del código.
2. **Checkboxes son contrato.** Cada tarea pasa por tres estados:
  - `[ ]` pendiente
  - `[~]` en progreso (marcar al empezar)
  - `[x]` completada (marcar **solo después de probar funcionamiento real**, nunca solo por haber escrito código)
3. **Un commit por tarea completada.** Mensaje formato: `[Fase N.M] descripción breve`. No agrupar varias tareas en un commit.
4. **Antes de crear un archivo:** verificar que no exista (`ls` o `find`). Si existe, preguntar antes de sobreescribir.
5. **Inputs y outputs de las tareas:** los archivos a crear y su contenido salen del plan + `spec-001-back-technical.md`. Si una tarea menciona `§X.Y`, leé esa sección del spec técnico antes de codear.


### De alcance (anti-scope-creep)


6. **No agregar dependencias** fuera de las listadas en tarea 1.2 (`requirements.txt`). Si una tarea pareciera requerir una librería extra, pausar y preguntar.
7. **No agregar features fuera del plan.** Prohibido sin aprobación explícita: `slowapi` (rate limiting), CSRF tokens, retry con backoff, Celery/RQ, Alembic/migrations, WebSockets, Prometheus/OpenTelemetry, schedulers, SQLAlchemy ORM (acá se usa Core), websockets, GraphQL.
8. **No agregar archivos** fuera de la estructura definida en `spec-001-back-technical.md §2.3`. Si creés que falta uno, proponelo en el Backlog del plan, no lo crees.
9. **No reinterpretar decisiones previas.** Si encontrás una alternativa que creés mejor (ej: argon2id en vez de bcrypt, AESGCMSIV en vez de AESGCM), escribila como propuesta en el Backlog. **No la apliques.**


### Técnicas (alineamiento con specs)


10. **Convenciones del código** (siguiente sección): obligatorias en cada tarea — logger sin PII, filtro `user_id` en repos, formato `{error_code, message}`, SQL parametrizado, 404 uniforme para "no existe" y "no tuyo".
11. **Respuestas JSON:** keys en `snake_case` (convención Python). Inputs aceptan `snake_case`.
12. **Timestamps:** ISO 8601 en UTC con sufijo `Z` (ej: `"2026-05-15T14:30:00Z"`). Nunca timestamps locales ni epoch.
13. **Errores nunca incluyen** stack trace, rutas internas, nombres de columnas de BD ni mensajes del SO. Solo `{error_code, message}`. El stack trace va a logs.
14. **Validaciones de seguridad son bloqueantes.** Si una tarea no cumple con: auth obligatoria en endpoints protegidos, filtro por `user_id` en repos, parametrización SQL (`text()` + `bindparams`), validación Pydantic en inputs → **no marcar `[x]`**, aunque el feature "funcione".
15. **Cifrado:** usar **exactamente** `cryptography.hazmat.primitives.ciphers.aead.AESGCM` con clave de 32 bytes y nonce aleatorio de 12 bytes (`os.urandom(12)`) por llamada. No reusar nonces. No cambiar el algoritmo.


### Cuando hay dudas


16. **Ante ambigüedad técnica → pausar y preguntar.** No asumir. Ejemplos típicos: "¿qué encoding uso para serializar el float antes de cifrar?", "¿este endpoint debe ser público o protegido?", "¿este campo es nullable?", "¿cuál es el formato exacto del JSON de respuesta para X?".
17. **Tests automatizados:** **no se requieren en MVP.** Los "Criterios de Done" se verifican con `curl` + inspección de BD vía `sqlite3 data/segvial.db`. Si querés agregar pytest, proponelo como fase aparte aprobada — no lo metas dentro de una tarea existente.
18. **Logs de progreso:** al completar cada fase, generar un breve resumen en el chat con: tareas marcadas `[x]`, comandos del Criterio de Done ejecutados y sus salidas, y problemas encontrados (si hubo).


---


## Decisiones previas (resueltas en revisión)


1. **Cifrado de biométricos:** AES-256-GCM (AEAD) vía `cryptography.hazmat.primitives.ciphers.aead.AESGCM` con una **única clave maestra** `BIOMETRIC_KEY` en `.env` (32 bytes base64). Nonce aleatorio de 96 bits por lectura → se guarda en `iv_encrypted`. Tag AEAD gestionado por `AESGCM` detecta tampering. La columna `users.encryption_key` del schema queda reservada para evolución futura a KEK/DEK (ver backlog).
2. **Procesamiento solo síncrono (límite duro):** archivos `> MAX_UPLOAD_SIZE_MB` (default 2MB) **o** `> 5000 filas` → `413 FILE_TOO_LARGE`. **No hay `BackgroundTasks`, no hay `processing_status`, no hay `GET /analysis/status/{id}` en MVP.** El frontend (spec-002) procesa local con `.tflite` cuando: (a) el archivo excede los límites, o (b) no hay conectividad. La sincronización del resultado offline → backend queda en Backlog.
3. **Router protegido por defecto:** `APIRouter` raíz con `Depends(get_current_user)`. Solo `/auth/register`, `/auth/login` y `/health` son públicos.


---


## Convenciones del código


Reglas transversales que aplican a todas las fases (no se repiten por tarea):


- **Logger:** nunca pasar `bpm`, `email`, `password`, `token` ni `Authorization` como argumento del logger (RNF-004).
- **Repositorios:** toda función que reciba `session_id`, `contact_id` o `tag_id` recibe también `user_id` y filtra por él (anti-IDOR, CWE-639).
- **Respuestas de error:** siempre `{error_code, message}` — nunca stack trace al cliente (RF-009 + RNF-004).
- **SQL parametrizado:** `text()` con parámetros nombrados + `bindparams()` en filtros dinámicos. Whitelist de columnas filtrables (anti-SQLi, CWE-89).
- **Mismo 404 para "no existe" vs "es de otro user"** (anti user/resource enumeration, CWE-204).


---


## Resumen de Fases


| # | Fase | RFs | Prerequisito |
|---|------|-----|-------------|
| 1 | Fundación | — | Ninguno |
| 2 | Autenticación | RF-010 | Fase 1 |
| 3 | Core Data (ETL + IA, síncrono) | RF-001, RF-011 | Fase 2 |
| 4 | Enriquecimiento (Weather + Alertas) | RF-002, RF-004 | Fase 3 |
| 5 | Historial, Perfil y Calidad | RF-003, RF-006, RF-007, RF-008, RF-009 | Fase 3 |


> **RF-012** (procesamiento de archivos grandes) está **delegado al frontend (spec-002)**: se procesa local con `.tflite` cuando el archivo excede `MAX_UPLOAD_SIZE_MB` o no hay conectividad. El backend solo acepta procesamiento síncrono dentro del límite.


---


## Fase 1 — Fundación


> Objetivo: proyecto corre, BD inicializada, `/health` responde, secretos validados al startup.


### Tareas


- [x] **1.1** Crear estructura de carpetas según `spec-001-back-technical.md §2.3`:
 ```
 app/ api/ services/ repositories/ models_ai/ db/ utils/
 ```
- [x] **1.2** Crear `requirements.txt`:
 - `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `pydantic-settings`, `pydantic[email]`
 - `bcrypt`, `python-jose[cryptography]`, `cryptography` (AES-GCM)
 - `scikit-learn`, `pandas`, `numpy`
 - `sendgrid`, `httpx`
 - `python-multipart`
- [x] **1.3** Crear `.env.example` con todas las variables del §2 técnico **+** `BIOMETRIC_KEY` (32 bytes base64) y `MAX_UPLOAD_SIZE_MB=2`. `JWT_SECRET_KEY` documentada con mínimo 32 chars.
- [x] **1.4** Crear `app/config.py` con `pydantic-settings` y validators al startup:
 - `JWT_SECRET_KEY` longitud ≥ 32 → si no, `ValueError`.
 - `BIOMETRIC_KEY` decodificable base64 y exactamente 32 bytes → si no, `ValueError`.
- [x] **1.5** Crear `app/db/schema.sql` con DDL del §3.6 técnico (las 7 tablas, todas con `CREATE TABLE IF NOT EXISTS`).
- [x] **1.6** Crear `app/db/database.py` — engine SQLAlchemy Core + `get_connection()` (`check_same_thread=False`).
- [x] **1.7** Crear `app/utils/logging.py` — logger estándar de Python a stdout, formato `[level] timestamp message` (la regla anti-sensitive-data está en "Convenciones del código").
- [x] **1.8** Crear `app/main.py`:
 - `startup`: ejecutar `schema.sql` (idempotente).
 - Registrar router central + handler global de errores (5.16).
- [x] **1.9** Crear `app/api/health.py` — `GET /health` → `{"status": "ok"}` (público).
- [x] **1.10** Crear `Dockerfile` con usuario no-root y `HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1`.
- [x] **1.11** Crear `docker-compose.yml` con volumen `./data:/app/data` y `restart: unless-stopped`.
- [x] **1.12** Verificar: `docker compose up` → `GET /health` devuelve 200, `data/segvial.db` con las 7 tablas.


### Criterio de Done
- `curl http://localhost:8000/health` → `{"status": "ok"}`.
- Startup falla si `JWT_SECRET_KEY` < 32 chars o `BIOMETRIC_KEY` no es base64 de 32 bytes.


---


## Fase 2 — Autenticación (RF-010)


> Objetivo: register/login/refresh/logout con cookies seguras y router protegido por defecto.


### Tareas


- [x] **2.1** Crear `app/repositories/user_repository.py`:
 - `get_user_by_email(email)` → `dict | None`.
 - `create_user(id, name, email, password_hash)` → `dict`.
 - `update_last_login(user_id)` → `None`.


- [x] **2.2** Crear `app/repositories/token_repository.py`:
 - `save_refresh_token(user_id, token_hash, expires_at)` → `None`.
 - `get_refresh_token(token_hash)` → `dict | None`.
 - `revoke_refresh_token(token_hash)` → `None`.
 - `revoke_all_user_tokens(user_id)` → `None`.


- [x] **2.3** Crear `app/services/auth_service.py`:
 - `hash_password(plain)` → bcrypt cost=12.
 - `verify_password(plain, hashed)` → bool.
 - `create_access_token(user_id)` → JWT HS256, exp 1h.
 - `create_refresh_token(user_id)` → `(token_raw, sha256_hash)`. Persistir solo el hash.
 - `decode_access_token(token)` → `dict | None`.
 - Validador de password: ≥8 chars + 1 carácter especial.


- [x] **2.4** Crear modelo Pydantic `RegisterIn(email: EmailStr, password: str, name: str)`.


- [~] **2.5** Crear `app/api/auth/api_register.py` — `POST /auth/register` (público):
 - Unicidad de email → 409 `EMAIL_ALREADY_EXISTS`.
 - Password débil → 400 `WEAK_PASSWORD`.
 - Emitir tokens. Cookie: `Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Strict; Path=/auth; Max-Age=604800`.
 - 201: `{access_token, token_type, profile_status, session_count}`.


- [ ] **2.6** Crear `app/api/auth/api_login.py` — `POST /auth/login` (público):
 - Buscar usuario, verificar bcrypt. Mensaje **uniforme** en error (no diferenciar email-no-existe vs password-mala).
 - Revocar tokens previos del usuario, emitir nuevos.
 - 401: `INVALID_CREDENTIALS`.


- [ ] **2.7** Crear `app/api/auth/api_refresh.py` — `POST /auth/refresh`:
 - Leer refresh token de cookie httpOnly.
 - Verificar en BD: hash existe, no expirado, no revocado.
 - Rotar (revocar actual, emitir nuevo par).
 - 401: `REFRESH_TOKEN_INVALID`.


- [ ] **2.8** Crear `app/api/auth/api_logout.py` — `POST /auth/logout`:
 - Revocar refresh token de cookie.
 - Limpiar cookie con `Max-Age=0` y mismas flags.


- [ ] **2.9** Crear `app/api/dependencies.py` — `get_current_user()`:
 - Extraer JWT de `Authorization: Bearer <token>`, decodificar, inyectar `user_id`.
 - 401: `TOKEN_EXPIRED` o `TOKEN_INVALID`.


- [ ] **2.10** Crear `app/api/routes.py` (router central):
 - `protected_router = APIRouter(dependencies=[Depends(get_current_user)])` para todo.
 - `public_router = APIRouter()` solo para `health`, `auth.register`, `auth.login`.
 - El resto (refresh, logout, analysis, history, user, stats, alerts) va al protegido.


### Criterio de Done
- `POST /auth/register` con email duplicado → 409.
- `POST /auth/login` con email inexistente vs password mala → mismo 401.
- Endpoint protegido sin token → 401.
- Cookie `refresh_token` no se envía en peticiones a `/analysis/*` (gracias a `Path=/auth`).


---


## Fase 3 — Core Data: ETL + IA, síncrono (RF-001, RF-011)


> Objetivo: subir CSV → ETL limpia datos → modelo predice estrés → resultado cifrado y guardado. Solo procesamiento síncrono dentro del límite duro; archivos grandes los rechaza con 413 y los procesa el frontend.


### 3A — Pipeline ETL (RF-011)


- [ ] **3.1** Crear `app/utils/validators.py`:
 - `validate_bpm(value)` → bool (30–220).
 - `validate_timestamp(value)` → bool (parseable ISO 8601).
 - `validate_csv_filename(name)` → bool (sin path separators).


- [ ] **3.2** Crear `app/services/etl_service.py`:
 - Constantes: `APPLE_HEALTH_COLUMNS`, `APPLE_HEALTH_HR_TYPE`, `HR_COLUMN_CANDIDATES`.
 - `detect_format(df)` → `"apple_health" | "simple" | error con `COLUMN_SELECTION_REQUIRED`.
 - `extract_series(df, format)` → `list[tuple[str, float]]`.
 - `filter_series(series)` → `{"series": [...], "rejected_rows": [...]}`.
 - `run_etl(file_bytes, filename)` → resultado o error estructurado.
 - Lectura con `pandas.read_csv(io.BytesIO(...), nrows=1_000_000)` como tope duro.


### 3B — Modelo de IA (RF-001)


- [ ] **3.3** Crear `app/models_ai/model_loader.py`:
 - Cargar `modelo.pkl` desde `MODEL_PATH` una sola vez al arrancar.
 - Si no existe: log + `ModelNotAvailableError`.


- [ ] **3.4** Crear `app/models_ai/inference_engine.py`:
 - Input: `series: list[tuple[str, float]]`.
 - Features: `bpm_mean`, `bpm_std`, `bpm_p25`, `bpm_p75`, `bpm_max`.
 - Escalar con `KMEANS_SCALER_MEAN`/`STD` de `.env`.
 - Output: `{"stress_level": "Low|Moderate|High", "confidence_score": 0.0–1.0}`.


### 3C — Repositorios y cifrado


- [ ] **3.5** Crear `app/repositories/session_repository.py`. Toda función que reciba `session_id` recibe también `user_id` y filtra por él:
 - `create_session(user_id, result_dict)` → `session_id`. Inserta la sesión solo cuando el análisis fue exitoso (insert directo en estado `completed`).
 - `get_session_by_id(session_id, user_id)` → `dict | None`.


 > **Nota:** la columna `processing_status` del schema permanece. En MVP siempre se inserta con `processing_status='completed'` (pasarlo explícito en el INSERT para no quedar en el default `'processing'` del DDL). Si el análisis falla, no se guarda fila — se devuelve error al cliente y se loguea en `audit_logs` (RF-008).


- [ ] **3.6** Crear `app/repositories/biometric_repository.py`:
 - `save_biometric_series(session_id, series)` → cifra cada BPM con `BIOMETRIC_KEY` antes de insertar.
 - `get_biometric_series(session_id, user_id)` → verifica ownership (join con `analysis_sessions.user_id`) y descifra.


- [ ] **3.7** Crear `app/utils/encryption.py` (AES-256-GCM):
 - Lee `BIOMETRIC_KEY` del config una sola vez al importar.
 - `encrypt_bpm(bpm: float)` → `(ciphertext_b64, nonce_b64)`. Nonce aleatorio de 96 bits por llamada (`os.urandom(12)`).
 - `decrypt_bpm(ciphertext_b64, nonce_b64)` → `float`. Si `InvalidTag` → propaga (handler global lo mapea a `DATA_INTEGRITY_ERROR` + audit log).


### 3D — Orquestación y endpoints


- [ ] **3.8** Crear `app/services/analysis_service.py`:
 - `process(user_id, series, lat=None, lon=None)` → `dict`:
   1. Inferencia (`inference_engine`).
   2. Aplicar `baseline_bpm` post-inferencia → ajustar `traffic_light`.
   3. (Si `lat`/`lon` → `weather_service.generate_weather_impact()`, se integra en Fase 4A).
   4. Persistir en `analysis_sessions` (con `processing_status='completed'`) + `biometric_data_raw` cifrados.
   5. `session_count++`, recalcular `profile_status`.
   6. `audit_logs.log_event("upload", "Success")`.
   7. Retornar el resultado completo (sirve directo como response del endpoint).
 - Si falla: `audit_logs.log_event("upload", "Error", message=...)` y propagar excepción al handler global.


- [ ] **3.9** Crear `app/api/analysis/api_upload.py` — `POST /analysis/upload-file` (protegido):
 - **Validar antes de leer en memoria** (orden importante):
   - `Content-Length` > `MAX_UPLOAD_SIZE_MB * 1024 * 1024` (default 2MB) → 413 `FILE_TOO_LARGE`.
   - `content_type` ∉ `{"text/csv", "application/json"}` → 415 `UNSUPPORTED_MEDIA_TYPE`.
   - `validate_csv_filename(filename)` falso → 400 `INVALID_FILENAME`.
 - Correr ETL → si falla, 400 estructurado con el `error_code` del ETL (`NO_VALID_ROWS`, `COLUMN_SELECTION_REQUIRED`, etc).
 - Si `len(series) > 5000` → 413 `FILE_TOO_LARGE` con mensaje: `"Archivo excede el límite de procesamiento online. Procesar localmente en la app."`.
 - Llamar `analysis_service.process(user_id, series, lat, lon)` → retornar `200 OK` con el resultado.
 - **No usar `BackgroundTasks` ni `asyncio.wait_for`.** Si el procesamiento es lento, el límite de filas ya lo acota.


 > **Nota arquitectónica:** los archivos que superen los límites los procesa el frontend (spec-002) con `.tflite`. La sincronización offline→backend del resultado está en Backlog.


- [ ] **3.10** Crear `app/api/analysis/api_manual.py` — `POST /analysis/manual-input` (protegido). Mismo flujo que 3.9, sin parseo de archivo. Tope de puntos en JSON: 5.000 (consistente con CSV).


### Criterio de Done
- CSV Apple Health ≤ 2MB y ≤ 5000 filas → 200 con resultado completo.
- Archivo > `MAX_UPLOAD_SIZE_MB` (Content-Length) → 413 `FILE_TOO_LARGE` **antes** de leer el body en memoria.
- CSV con > 5000 filas válidas tras ETL → 413 `FILE_TOO_LARGE`.
- BPM fuera de rango [30, 220] → en `rejected_rows`, no en el resultado.
- Usuario A consulta sesión de B vía `/history/{id}` → 404 `SESSION_NOT_FOUND`.
- Ciphertext biométrico alterado manualmente en BD → falla descifrado con `DATA_INTEGRITY_ERROR` (AEAD detecta tampering).


---


## Fase 4 — Enriquecimiento: Weather + Alertas (RF-002, RF-004)


> Objetivo: análisis incluye `weather_impact`. Alertas Red → email.


### 4A — Weather Service (RF-002)


- [ ] **4.1** Crear `app/repositories/weather_repository.py`:
 - `get_cached_weather(lat, lon)` → `dict | None`. **Antes de devolver, borra los expirados** (limpieza on-read, sin scheduler).
 - `save_weather(lat, lon, data, ttl_minutes=15)` → `None`.


- [ ] **4.2** Crear `app/services/weather_service.py`:
 - Validar `lat ∈ [-90, 90]`, `lon ∈ [-180, 180]` con Pydantic antes de hacer request.
 - `httpx.AsyncClient(timeout=5.0, follow_redirects=False)`.
 - `get_weather(lat, lon)` con caché de 15 min.
 - `generate_weather_impact(data)` → `{"severity", "message"} | None` según tabla del RF-002.
 - Fallback si la API falla: último caché disponible + `warning: true`.


- [ ] **4.3** Integrar en `analysis_service.process()`:
 - `lat`, `lon` opcionales en el request (ya están en la firma desde 3.8).
 - Adjuntar `weather_impact` antes de persistir; `null` si clima normal o sin coordenadas.


### 4B — Alertas (RF-004)


- [ ] **4.4** Crear `app/repositories/contact_repository.py`. Todas las funciones reciben `user_id` y filtran por él:
 - `get_contacts_by_user(user_id)`.
 - `get_contact_by_id(contact_id, user_id)`.
 - `create_contact(user_id, name, email, phone)`.
 - `update_contact(contact_id, user_id, data)`.
 - `delete_contact(contact_id, user_id)`.


- [ ] **4.5** Crear `app/services/alerts_service.py`:
 - `send_alert(user_id, session_id, contact_ids=[])`.
 - Construir email con `traffic_light`, `stress_level`, `weather_impact`. Sin BPMs crudos.
 - Enviar vía SendGrid (free tier: 100 emails/día).
 - Si falla: `audit_logs.log_event("alert_sent", "Error")`.


 > **Entornos de email:**
 > - **Dev/testing:** usar **Mailtrap (sandbox)** — gratis, los emails caen en una bandeja virtual sin llegar a destinatarios reales. Solo cambia `SENDGRID_API_KEY` y el host SMTP en `.env`.
 > - **Producción:** SendGrid free tier con `SENDGRID_FROM_EMAIL` verificado.
 > - El código del servicio es el **mismo en ambos casos** — solo cambian variables de entorno.


- [ ] **4.6** Crear `app/api/alerts/api_send.py` — `POST /alerts/send` (protegido):
 - Validar que `session_id` y cada `contact_id` pertenecen al `user_id` del token.
 - 400 `NO_CONTACTS_FOUND` · 503 `ALERT_SERVICE_UNAVAILABLE` · 202 si encolado.


- [ ] **4.7** Crear `app/api/user/api_contacts.py` (protegidos, todos pasan `user_id` al repo):
 - `GET /user/contacts` · `POST /user/contacts` (email validado con `EmailStr`) · `PUT /user/contacts/{id}` · `DELETE /user/contacts/{id}`.


### Criterio de Done
- Análisis con coordenadas → respuesta incluye `weather_impact`.
- `lat=999` → 422 (Pydantic).
- API Open-Meteo caída → caché + warning.
- `POST /alerts/send` con `contact_ids` de otro user → 404.


---


## Fase 5 — Historial, Perfil, Calidad y Errores


> Objetivo: historial paginado, stats para gráficas, perfil, audit logs, errores humanos.


### 5A — Historial (RF-003)


- [ ] **5.1** Ampliar `session_repository.py` (todo filtra por `user_id`):
 - `list_sessions(user_id, page, limit, tags, date_from, date_to)`.
   - Filtros dinámicos con `bindparams` siempre. Whitelist de columnas filtrables.
 - `get_session_detail(session_id, user_id, include_raw)`.
 - `delete_session(session_id, user_id)`.


- [ ] **5.2** `GET /history/summary` (protegido). Query params validados con Pydantic: `page≥1`, `limit∈[1,100]`, `date_from/date_to` ISO 8601.


- [ ] **5.3** `GET /history/{id}` (protegido). `?raw_data=true` descifra biométricos con `BIOMETRIC_KEY`. 404 si no existe o es de otro user.


- [ ] **5.4** `DELETE /history/{id}` (protegido). 404 si no pertenece al user.


### 5B — Stats para Gráficas (RF-006)


- [ ] **5.5** Queries en `session_repository.py` (todas con `user_id`):
 - `get_trends(user_id, period)`.
 - `get_distribution(user_id)`.
 - `get_correlations(user_id)`.
 - Usar índices `idx_sessions_user_id` y `idx_sessions_timestamp` ya en schema.


- [ ] **5.6** `GET /stats/trends?period=week|month` (protegido).
- [ ] **5.7** `GET /stats/distribution` (protegido).
- [ ] **5.8** `GET /stats/correlations` (protegido).
 - Todos < 200ms (RNF-001), paginados a 10 puntos.
 - Datos insuficientes (<2 puntos): JSON vacío + mensaje.


### 5C — Perfil y Calibración (RF-007)


- [ ] **5.9** Ampliar `user_repository.py`:
 - `update_baseline_bpm(user_id, bpm)` (validar 30–220).
 - `get_profile(user_id)`.
 - `recalculate_profile_status(user_id)` (regla 5 sesiones / desv <10%).


- [ ] **5.10** Tags repository (CRUD filtrando por `user_id`).


- [ ] **5.11** `GET /user/profile` (protegido).
- [ ] **5.12** `PUT /user/profile/calibrate` (protegido). 400 si BPM <30 o >220.
- [ ] **5.13** `GET/POST/DELETE /user/tags` (protegido). 409 si duplicada. 404 si `tag_id` no es del user.


### 5D — Auditoría (RF-008)


- [ ] **5.14** Crear `app/repositories/audit_repository.py`:
 - `log_event(user_id, event_type, model_status, error_message, details)` → `None`.


- [ ] **5.15** Llamar `log_event()` en los 4 eventos que pide RF-008:
 - `upload` (Success / Fallback / Error).
 - `login` (incluye fallos).
 - `alert_sent` (Success / Error).
 - `model_failure` cuando `.pkl` no carga o inferencia falla.


### 5E — Manejo de Errores Humanos (RF-009)


- [ ] **5.16** Crear `app/api/error_handlers.py` con handler global FastAPI, registrarlo en `main.py` y verificar que todos los endpoints devuelven `{error_code, message}` sin stack trace. Mapeos:
 - `FileNotFoundError` → 400 `FILE_NOT_FOUND`.
 - `OperationalError` (DB lock) → 503 `DATABASE_BUSY`.
 - `httpx.TimeoutException` → 504 `UPSTREAM_TIMEOUT`.
 - `InvalidTag` (cripto) → 500 `DATA_INTEGRITY_ERROR` + audit log.
 - `OSError` con `errno.ENOSPC` → 507 `STORAGE_FULL` (disco lleno al escribir SQLite/uploads).
 - `Exception` → 500 `INTERNAL_ERROR` (stack trace solo a logs).


### Criterio de Done
- `GET /history/summary?page=1&limit=10` → solo del usuario autenticado.
- `GET /history/<id_de_otro_user>` → 404.
- `GET /stats/trends?period=week` con 10k sesiones → <200ms.
- `PUT /user/profile/calibrate` con BPM=250 → 400.
- Cualquier error interno → JSON `{error_code, message}`, nunca stack trace.


---


## Dependencias Cruzadas


```
Fase 1 (DB, Docker, secretos validados)
 └── Fase 2 (Auth + router protegido por defecto)
       └── Fase 3 (ETL + IA + Async + AES-GCM)
             ├── Fase 4A (Weather)        ← se integra en analysis_service
             ├── Fase 4B (Alertas)        ← depende de sesiones guardadas
             └── Fase 5 (Historial, Stats, Perfil, Audit, Error handler)
```


---


## Seguridad implementada (resumen)


| Categoría | Mecanismo |
|---|---|
| Transporte | HTTPS-only en producción (HTTP→301 a nivel reverse proxy) |
| Passwords | bcrypt cost=12 |
| Sesiones | JWT HS256 (1h) + refresh hasheado SHA-256 (7d), cookie `HttpOnly + Secure + SameSite=Strict + Path=/auth` |
| Autorización | Router protegido por defecto. Repos filtran por `user_id` (anti-IDOR) |
| SQL | Parámetros nombrados via `text()` + `bindparams`. Whitelist en filtros dinámicos |
| Cifrado de BPM | AES-256-GCM con clave maestra `BIOMETRIC_KEY` (32 bytes en `.env`). Nonce de 96 bits por lectura. Tag AEAD verificado |
| Inputs | Pydantic en todas las requests (`EmailStr`, rangos numéricos, ISO 8601) |
| Uploads | `Content-Length` máx, MIME, filename validados. `nrows` cap en pandas |
| Errores | Handler global → `{error_code, message}`. Nunca stack trace al cliente |
| Logs aplicación | `logging` estándar a stdout. Regla: nunca pasar BPM, email, password ni token al logger |
| Audit logs (RF-008) | Tabla `audit_logs`, 4 eventos: `upload`, `login`, `alert_sent`, `model_failure` |
| Secretos | Validados al startup (`JWT_SECRET_KEY` ≥ 32 chars, `BIOMETRIC_KEY` 32 bytes base64) |


---


## Backlog (fuera de alcance actual)


- RF-005: Reportes PDF/Excel.
- Migración a PostgreSQL.
- `.tflite` para cliente Ionic (equipo ML).
- SMS/Twilio para alertas.
- Rate limiting en `/auth/login` (`slowapi`) — agregar si hay abuso real.
- Endpoint admin para consultar `audit_logs`.
- `POST /auth/logout-all` (revocar todas las sesiones).
- KMS externo + modelo KEK/DEK (DEK per-user) para `BIOMETRIC_KEY` en producción. La columna `users.encryption_key` ya está reservada en el schema para esta evolución.
- Migración a `argon2id` si bcrypt cost=12 deja de ser suficiente.


---


**Leyenda de estado:** `[ ]` pendiente · `[~]` en progreso · `[x]` completado



