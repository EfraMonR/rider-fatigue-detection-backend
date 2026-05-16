# Sistema Preventivo de Seguridad Vial — Backend

API REST para evaluación de fatiga del conductor. Procesa datos fisiológicos (BPM), clasifica el nivel de estrés con un modelo K-Means y emite alertas a contactos de confianza.

## Stack

| Capa | Tecnología |
|------|-----------|
| Framework | FastAPI (Python 3.12) |
| Base de datos | SQLite (prototipo) / PostgreSQL (producción) |
| ORM | SQLAlchemy Core — SQL directo, sin ORM |
| IA | scikit-learn K-Means (`.pkl`) |
| Cifrado biométrico | AES-256-GCM (`cryptography`) |
| Auth | JWT HS256 + refresh token hasheado (SHA-256) en cookie HttpOnly |
| Clima | Open-Meteo API (caché 15 min en SQLite) |
| Alertas | SendGrid (email) |
| Despliegue | Docker + docker-compose |

## Requisitos

- Docker y docker-compose
- Python 3.12 (solo para desarrollo local sin Docker)

## Levantar en local

```bash
# 1. Copiar variables de entorno
cp .env.example .env

# 2. Editar .env con tus claves reales (ver sección Variables de entorno)

# 3. Levantar
docker compose up --build

# 4. Verificar
curl http://localhost:8000/health
# → {"status": "ok"}
```

La base de datos SQLite se crea automáticamente en `./data/segvial.db` al primer arranque.

## Variables de entorno

| Variable | Descripción | Requerida |
|----------|-------------|-----------|
| `DATABASE_URL` | SQLite: `sqlite:///./data/segvial.db` | Sí |
| `JWT_SECRET_KEY` | Mínimo 32 caracteres | Sí |
| `JWT_ACCESS_EXPIRE_MINUTES` | Expiración del access token (default: 60) | No |
| `JWT_REFRESH_EXPIRE_DAYS` | Expiración del refresh token (default: 7) | No |
| `BIOMETRIC_KEY` | 32 bytes en base64 para AES-256-GCM | Sí |
| `MODEL_PATH` | Ruta al archivo `.pkl` del modelo | Sí |
| `KMEANS_SCALER_MEAN` | Media del scaler de entrenamiento | Sí |
| `KMEANS_SCALER_STD` | Desviación estándar del scaler | Sí |
| `DEFAULT_BASELINE_BPM` | BPM basal por defecto (default: 72) | No |
| `STRESS_THRESHOLD_MODERATE` | Umbral para stress Moderate (default: 0.4) | No |
| `STRESS_THRESHOLD_HIGH` | Umbral para stress High (default: 0.7) | No |
| `WEATHER_API_URL` | URL de Open-Meteo | No |
| `WEATHER_CACHE_TTL_MINUTES` | TTL del caché climático (default: 15) | No |
| `SENDGRID_API_KEY` | API key de SendGrid | Sí (alertas) |
| `SENDGRID_FROM_EMAIL` | Email remitente verificado en SendGrid | Sí (alertas) |
| `MAX_UPLOAD_SIZE_MB` | Límite de upload (default: 2) | No |

Generar `BIOMETRIC_KEY`:
```bash
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

## Endpoints

### Autenticación (públicos)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/auth/register` | Registrar usuario. Devuelve `access_token` + cookie `refresh_token` |
| `POST` | `/auth/login` | Iniciar sesión |
| `POST` | `/auth/refresh` | Rotar tokens (lee cookie HttpOnly) |
| `POST` | `/auth/logout` | Cerrar sesión, revocar refresh token |
| `GET` | `/health` | Estado del servidor |

### Análisis (requieren JWT)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/analysis/upload-file` | Subir CSV/JSON con datos BPM. Límite: 2 MB y 5 000 filas |
| `POST` | `/analysis/manual-input` | Ingresar serie BPM manualmente (JSON). Límite: 5 000 puntos |

Respuesta de análisis incluye: `verdict` (Fit/Unfit), `stress_level`, `traffic_light`, `confidence_score`, `risk_score`, `weather_impact`.

### Historial

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/history/summary` | Lista paginada de sesiones. Params: `page`, `limit`, `tags`, `date_from`, `date_to` |
| `GET` | `/history/{id}` | Detalle de sesión. `?raw_data=true` descifra biométricos |
| `DELETE` | `/history/{id}` | Eliminar sesión |

### Estadísticas

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/stats/trends` | Tendencias por período. Param: `period=week\|month` |
| `GET` | `/stats/distribution` | Distribución porcentual por semáforo |
| `GET` | `/stats/correlations` | Correlación clima ↔ nivel de estrés |

### Perfil y calibración

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/user/profile` | Perfil del usuario (`profile_status`, `baseline_bpm`, `session_count`) |
| `PUT` | `/user/profile/calibrate` | Actualizar BPM basal. Rango válido: 30–220 |
| `GET` | `/user/tags` | Listar tags personalizados |
| `POST` | `/user/tags` | Crear tag |
| `DELETE` | `/user/tags/{id}` | Eliminar tag |
| `GET` | `/user/contacts` | Listar contactos de confianza |
| `POST` | `/user/contacts` | Crear contacto |
| `PUT` | `/user/contacts/{id}` | Actualizar contacto |
| `DELETE` | `/user/contacts/{id}` | Eliminar contacto |

### Alertas

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/alerts/send` | Enviar alerta por email a contactos de confianza vía SendGrid |

## Formatos de entrada

### CSV Apple Health
```
timestamp,type,value,unit,sourceName,sourceVersion
2026-05-15T10:00:00,HKQuantityTypeIdentifierHeartRate,75,count/min,Apple Watch,9.0
```

### CSV formato simple
```
timestamp,bpm
2026-05-15T10:00:00,75
2026-05-15T10:01:00,78
```

### JSON manual input
```json
{
  "series": [
    {"timestamp": "2026-05-15T10:00:00Z", "bpm": 75},
    {"timestamp": "2026-05-15T10:01:00Z", "bpm": 78}
  ]
}
```

## Seguridad

| Mecanismo | Detalle |
|-----------|---------|
| Passwords | bcrypt cost=12 |
| Access token | JWT HS256, expiración 1h |
| Refresh token | SHA-256 hasheado en BD, cookie `HttpOnly; Secure; SameSite=Strict; Path=/auth` |
| Biométricos | AES-256-GCM, nonce aleatorio de 96 bits por lectura |
| SQL | `text()` + `bindparams()`, whitelist de columnas filtrables |
| IDOR | Toda consulta por `session_id`, `contact_id` o `tag_id` filtra también por `user_id` |
| Errores | Solo `{error_code, message}` al cliente — nunca stack trace |
| Audit log | Tabla `audit_logs`: eventos `upload`, `login`, `alert_sent`, `model_failure` |

## Errores

Todos los errores siguen el formato:
```json
{"error_code": "EXAMPLE_CODE", "message": "Descripción legible."}
```

| Código HTTP | `error_code` | Causa |
|-------------|-------------|-------|
| 400 | `INVALID_BPM_RANGE` | BPM fuera del rango [30, 220] |
| 400 | `WEAK_PASSWORD` | Contraseña sin 8 chars o sin carácter especial |
| 400 | `FILE_NOT_FOUND` | Archivo no encontrado |
| 401 | `INVALID_CREDENTIALS` | Email o contraseña incorrectos |
| 401 | `TOKEN_EXPIRED` / `TOKEN_INVALID` | JWT inválido o expirado |
| 404 | `SESSION_NOT_FOUND` | Sesión inexistente o de otro usuario |
| 409 | `EMAIL_ALREADY_EXISTS` | Email ya registrado |
| 409 | `TAG_ALREADY_EXISTS` | Tag duplicado |
| 413 | `FILE_TOO_LARGE` | Archivo > 2 MB o > 5 000 filas |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | Content-Type no permitido |
| 500 | `DATA_INTEGRITY_ERROR` | Fallo de AEAD (posible tampering) |
| 503 | `DATABASE_BUSY` | SQLite bloqueado |
| 504 | `UPSTREAM_TIMEOUT` | API externa sin respuesta |
| 507 | `STORAGE_FULL` | Disco lleno |

## Backup de la base de datos

```bash
cp ./data/segvial.db ./data/segvial_backup_$(date +%Y%m%d).db
```

## Migración a PostgreSQL

Cambiar en `.env`:
```
DATABASE_URL=postgresql://user:password@host:5432/segvial
```
El código no requiere modificaciones. El schema DDL es compatible con ajustes mínimos de tipos (`TEXT` → `UUID`, `INTEGER` booleans → `BOOLEAN`, timestamps → `TIMESTAMPTZ`).
