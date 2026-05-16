---
name: project-phase5-state
description: Estado exacto del proyecto rider-fatigue-detection-backend antes de iniciar Fase 5. Todas las fases 1-4 completadas y verificadas.
metadata:
  type: project
---

## Estado al 2026-05-15

Proyecto: Sistema Preventivo de Seguridad Vial — backend Python/FastAPI
Branch: feature/initial-specs
Stack: Python 3.12, FastAPI, SQLAlchemy Core, SQLite, Docker

### Fases completadas y verificadas con curl/docker

- **Fase 1** [x]: estructura, config, schema 7 tablas, /health, Docker funcionando
- **Fase 2** [x]: auth completa — register/login/refresh/logout, JWT HS256, bcrypt cost=12, cookie HttpOnly, router protegido con Depends(get_current_user)
- **Fase 3** [x]: ETL (Apple Health + simple), inference K-Means, AES-256-GCM por BPM, upload-file, manual-input
- **Fase 4** [x]: weather_repository + weather_service (Open-Meteo, cache 15min, fallback), alerts_service (SendGrid), /alerts/send, CRUD /user/contacts

### Archivos creados (estructura completa)

app/config.py, app/main.py
app/db/database.py, app/db/schema.sql (7 tablas)
app/api/health.py, app/api/routes.py, app/api/dependencies.py
app/api/auth/schemas.py, api_register.py, api_login.py, api_refresh.py, api_logout.py
app/api/analysis/api_upload.py, api_manual.py
app/api/alerts/api_send.py
app/api/user/api_contacts.py
app/services/auth_service.py, etl_service.py, analysis_service.py, weather_service.py, alerts_service.py
app/repositories/user_repository.py, token_repository.py, session_repository.py, biometric_repository.py, contact_repository.py, weather_repository.py
app/models_ai/model_loader.py, inference_engine.py, modelo.pkl (K-Means 3 clusters prueba)
app/utils/logging.py, validators.py, encryption.py

### Lo que falta — Fase 5

**5A — Historial (RF-003):** tareas 5.1–5.4
- 5.1: Ampliar session_repository: list_sessions (paginado, filtros dinámicos con bindparams), get_session_detail, delete_session
- 5.2: GET /history/summary
- 5.3: GET /history/{id} (?raw_data=true descifra biométricos)
- 5.4: DELETE /history/{id}

**5B — Stats (RF-006):** tareas 5.5–5.8
- 5.5: get_trends, get_distribution, get_correlations en session_repository
- 5.6: GET /stats/trends?period=week|month
- 5.7: GET /stats/distribution
- 5.8: GET /stats/correlations

**5C — Perfil y Calibración (RF-007):** tareas 5.9–5.13
- 5.9: update_baseline_bpm, get_profile, recalculate_profile_status en user_repository
- 5.10: tags repository (evaluar si se necesita tabla nueva o JSON en analysis_sessions)
- 5.11: GET /user/profile
- 5.12: PUT /user/profile/calibrate (400 si BPM <30 o >220)
- 5.13: GET/POST/DELETE /user/tags

**5D — Auditoría (RF-008):** tarea 5.14–5.15
- 5.14: audit_repository.log_event()
- 5.15: Conectar log_event en upload, login, alert_sent, model_failure

**5E — Error handlers (RF-009):** tarea 5.16
- 5.16: error_handlers.py completo con todos los mapeos (FileNotFoundError, OperationalError, httpx.TimeoutException, InvalidTag→DATA_INTEGRITY_ERROR, OSError ENOSPC, Exception genérico)

### Criterio de Done Fase 5
- GET /history/summary?page=1&limit=10 → solo sesiones del user autenticado
- GET /history/<id_de_otro_user> → 404 SESSION_NOT_FOUND
- GET /stats/trends?period=week con 10k sesiones → <200ms
- PUT /user/profile/calibrate con BPM=250 → 400
- Cualquier error interno → {error_code, message}, nunca stack trace

### Convenciones críticas (no olvidar)
- SQL: text() + parámetros nombrados + bindparams() en filtros dinámicos. Whitelist de columnas.
- Repos: toda función con session_id/contact_id/tag_id recibe también user_id y filtra.
- 404 uniforme para "no existe" vs "es de otro user" (anti-IDOR).
- Logger NUNCA recibe bpm, email, password, token.
- Errores al cliente: solo {error_code, message}.
- Un commit por tarea, formato [Fase N.M] descripción.
- Marcar [~] al empezar, [x] solo tras verificar con curl/sqlite3/docker.

**Why:** contexto de 156k tokens agotado, se retoma en nueva conversación.
**How to apply:** Leer este archivo al inicio de la nueva sesión para retomar desde Fase 5.
