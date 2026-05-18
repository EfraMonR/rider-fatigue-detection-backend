---
name: project-phase5-state
description: Estado exacto del proyecto rider-fatigue-detection-backend. Todas las fases 1-5 completadas y verificadas al 2026-05-15.
metadata:
  type: project
---

## Estado al 2026-05-15

Proyecto: Sistema Preventivo de Seguridad Vial — backend Python/FastAPI
Branch: feature/initial-specs
Stack: Python 3.12, FastAPI, SQLAlchemy Core, SQLite, Docker

### Todas las fases completadas y verificadas con curl/docker

- **Fase 1** [x]: estructura, config, schema 7 tablas, /health, Docker funcionando
- **Fase 2** [x]: auth completa — register/login/refresh/logout, JWT HS256, bcrypt cost=12, cookie HttpOnly
- **Fase 3** [x]: ETL (Apple Health + simple), inference K-Means, AES-256-GCM por BPM, upload-file, manual-input
- **Fase 4** [x]: weather_repository + weather_service (Open-Meteo, cache 15min, fallback), alerts_service (SendGrid), /alerts/send, CRUD /user/contacts
- **Fase 5** [x]: historial paginado, stats, perfil/calibración, tags, audit logs, error handlers completos

### Archivos creados en Fase 5

**Repos:**
- app/repositories/audit_repository.py — log_event best-effort (no relanza)
- app/repositories/tag_repository.py — CRUD sobre users.threshold_config (JSON, sin tabla nueva)
- Ampliados: session_repository.py (list_sessions+bindparams, get_session_detail, delete_session, get_trends, get_distribution, get_correlations)
- Ampliados: user_repository.py (get_profile, update_baseline_bpm, recalculate_profile_status con stddev en Python)

**API History:**
- app/api/history/api_summary.py — GET /history/summary (paginado, filtros date_from/date_to/tags)
- app/api/history/api_detail.py — GET /history/{id} (?raw_data=true descifra biométricos)
- app/api/history/api_delete.py — DELETE /history/{id}

**API Stats:**
- app/api/stats/api_trends.py — GET /stats/trends?period=week|month
- app/api/stats/api_distribution.py — GET /stats/distribution
- app/api/stats/api_correlations.py — GET /stats/correlations

**API User:**
- app/api/user/api_profile.py — GET /user/profile
- app/api/user/api_calibrate.py — PUT /user/profile/calibrate (400 si BPM <30 o >220, validación manual no Pydantic)
- app/api/user/api_tags.py — GET/POST/DELETE /user/tags

**Error handlers:**
- app/api/error_handlers.py — FileNotFoundError→400, OperationalError→503, TimeoutException→504, InvalidTag→500+audit, ENOSPC→507, Exception→500

**Servicios actualizados:**
- analysis_service.py: import directo de audit_repository (ya no lazy), model_failure event
- alerts_service.py: import directo de audit_repository
- api_login.py: log_event en login exitoso y fallido

### Decisiones técnicas clave de Fase 5

- Tags: almacenadas en users.threshold_config (JSON) — sin migración de schema
- stddev para profile_status: calculada en Python (SQLite no tiene STDDEV nativo)
- Validación BPM en calibrate: manual en el handler (HTTPException 400), no Pydantic (que devuelve 422)
- audit_repository.log_event: best-effort, nunca relanza excepciones
- Filtros dinámicos en list_sessions: json_each para tags (SQLite 3.9+), bindparams para dates

### Criterio de Done Fase 5 — VERIFICADO

- GET /history/summary?page=1&limit=10 → solo sesiones del user autenticado ✓
- GET /history/<id_de_otro_user> → 404 SESSION_NOT_FOUND ✓
- PUT /user/profile/calibrate con BPM=250 → 400 ✓
- Cualquier error interno → {error_code, message}, nunca stack trace ✓
- audit_logs con registros de login y login fallido verificados en sqlite3 ✓

**Why:** proyecto completamente implementado, listo para PR o deploy.
**How to apply:** el backend MVP está 100% completo. Próximos pasos serían PR a master o inicio de frontend (spec-002).
