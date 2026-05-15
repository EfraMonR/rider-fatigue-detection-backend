# Especificación Técnica: Sistema Backend (Python)


## 1. Introducción
Este documento proporciona una visión general del sistema backend, incluyendo la arquitectura, componentes y tecnologías utilizadas, así como las implementaciones específicas para cumplir con los requisitos funcionales definidos en `spec-001-back-functional.md`.


## 2. Arquitectura del Sistema
El sistema backend está diseñado como una **aplicación monolítica modular** (Monolith) utilizando Python y FastAPI como framework principal. Esta arquitectura permite una organización clara del código en capas (API, Servicios, Repositorios) sin la complejidad de despliegues distribuidos, desplegada en un servidor remoto accesible vía **HTTPS**.


Se utiliza **SQLAlchemy Core** (sin ORM) para ejecutar queries SQL directas contra la base de datos. **Para el prototipo se usa SQLite** — cero costo, cero infraestructura adicional, archivo local persistido vía volumen Docker. Si el proyecto escala a producción, el cambio a PostgreSQL es una sola línea en `.env`; el código no se modifica.


> **Escalabilidad:** SQLite maneja bien la concurrencia de lectura y escrituras secuenciales. El límite práctico para este sistema es múltiples usuarios enviando análisis simultáneamente — escenario improbable en un prototipo de conductores individuales. Si ese escenario ocurre, `DATABASE_URL` se cambia a `postgresql://...` y se ejecuta la migración.


**Requisito de deploy:** El servidor debe exponer únicamente HTTPS (puerto 443). HTTP debe redirigir permanentemente a HTTPS (301). Se recomienda Let's Encrypt para el certificado.


**Configuración por variables de entorno:** Toda configuración del sistema se gestiona mediante un archivo `.env` (nunca hardcodeada en el código). Variables obligatorias:
```
# Base de datos
# Prototipo (SQLite — archivo local persistido vía volumen Docker)
DATABASE_URL=sqlite:///./data/segvial.db
# Producción (descomentar y ajustar cuando se migre a PostgreSQL)
# DATABASE_URL=postgresql://user:password@host:5432/segvial


# JWT
JWT_SECRET_KEY=<clave secreta>
JWT_ACCESS_EXPIRE_MINUTES=60
JWT_REFRESH_EXPIRE_DAYS=7


# Modelo K-Means
MODEL_PATH=app/models_ai/modelo.pkl
KMEANS_SCALER_MEAN=78.5
KMEANS_SCALER_STD=12.3
DEFAULT_BASELINE_BPM=72


# Umbrales de semáforo (post-inferencia)
STRESS_THRESHOLD_MODERATE=0.4
STRESS_THRESHOLD_HIGH=0.7


# API Climática
WEATHER_API_URL=https://api.open-meteo.com/v1/forecast
WEATHER_CACHE_TTL_MINUTES=15


# Alertas
SENDGRID_API_KEY=<clave sendgrid>
SENDGRID_FROM_EMAIL=alertas@segvial.app


# Cifrado de datos biométricos (AES-256-GCM)
BIOMETRIC_KEY=<32 bytes base64>


# Uploads
MAX_UPLOAD_SIZE_MB=2
```


**`docker-compose.yml` — persistencia del archivo SQLite:**
```yaml
services:
 backend:
   build: .
   ports:
     - "8000:8000"
   env_file:
     - .env
   volumes:
     - ./data:/app/data    # carpeta en el servidor físico → contenedor
   restart: unless-stopped


# La carpeta ./data/ en el servidor físico persiste el archivo segvial.db
# fuera del contenedor. Los reinicios, rebuilds y actualizaciones de imagen
# no afectan el archivo de base de datos.
```


> **Backup manual:** `cp ./data/segvial.db ./data/segvial_backup_$(date +%Y%m%d).db`


### 2.1 Componentes Principales (Lógica Interna)
Aunque es una aplicación monolítica, la lógica interna se divide conceptualmente en tres servicios:
- **Servicio de Análisis**: Encapsula la lógica de negocio para el procesamiento de datos fisiológicos, la entrada de datos (archivos o manuales) y la integración con el modelo de IA.
- **Servicio de Almacenamiento**: Gestiona la persistencia de datos ejecutando queries SQL directas vía SQLAlchemy Core contra SQLite (`analysis_sessions`, `biometric_data_raw`, etc.).
- **Servicio de Alertas y Estado**: Maneja la lógica para determinar el estado de idoneidad (`"Fit"`/`"Unfit"`) y genera notificaciones o señales visuales (semáforo `traffic_light`) basadas en los umbrales configurados.


### 2.2 Integración con Servicios Externos
El sistema se integra con servicios externos para enriquecer el análisis:
- **APIs Climáticas**: Se conecta con APIs externas (como Open-Meteo o similar) para obtener datos meteorológicos actuales o históricos.
- **Gestión de Caché**: Para evitar saturar las llamadas externas y reducir la latencia, los datos climáticos se almacenan en caché en la tabla `weather_cache` de SQLite (con expiración automática cada 15 minutos).
- **Servicio de Alertas Externas**: Se integra con **SendGrid** para notificar por correo electrónico a contactos de confianza en caso de alertas. SMS (Twilio) queda fuera del alcance actual.


### 2.3 Estructura del Proyecto
El sistema está organizado siguiendo una arquitectura modular en capas para separar la lógica de API, modelos de datos, servicios de análisis de IA y gestión de almacenamiento.


```
.
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── README.md
└── app/
   ├── __init__.py
   ├── main.py                       # Punto de entrada (FastAPI)
   ├── config.py                     # Configuración (DB, JWT secrets, Keys API, etc.)
   │
   ├── db/                           # Capa de Base de Datos
   │   ├── __init__.py
   │   ├── database.py               # Engine SQLAlchemy Core + función get_connection()
   │   └── schema.sql                # DDL completo — fuente de verdad del schema
   |
   ├── api/                          # Capa de Controladores (Endpoints)
   │   ├── __init__.py
   │   ├── routes.py                 # Registro de endpoints (Router Central)
   │   ├── auth/                     # Endpoints de Autenticación (RF-010)
   │   │   ├── api_register.py       # POST /auth/register
   │   │   ├── api_login.py          # POST /auth/login
   │   │   ├── api_refresh.py        # POST /auth/refresh
   │   │   └── api_logout.py         # POST /auth/logout
   │   ├── analysis/                 # Endpoints Core (RF-001, RF-011)
   │   │   ├── api_upload.py         # POST /analysis/upload-file
   │   │   └── api_manual.py         # POST /analysis/manual-input
   │   ├── history/                  # Endpoints Historial
   │   │   ├── api_summary.py        # GET /history/summary
   │   │   ├── api_detail.py         # GET /history/{id}
   │   │   └── api_delete.py         # DELETE /history/{id}
   │   ├── user/                     # Endpoints Perfil, Calibración y Contactos
   │   │   ├── api_profile.py        # GET /user/profile
   │   │   ├── api_calibrate.py      # PUT /user/profile/calibrate
   │   │   ├── api_tags.py           # GET/POST/DELETE /user/tags
   │   │   └── api_contacts.py       # GET/POST/PUT/DELETE /user/contacts
   │   ├── stats/                    # Endpoints para Gráficas
   │   │   ├── api_trends.py         # GET /stats/trends
   │   │   ├── api_distribution.py   # GET /stats/distribution
   │   │   └── api_correlations.py   # GET /stats/correlations
   │   ├── alerts/                   # Endpoints de Alertas
   │   │   └── api_send.py           # POST /alerts/send (RF-004)
   │   └── health.py                 # GET /health
   |
   ├── services/                     # Lógica de Negocio
   │   ├── __init__.py
   │   ├── auth_service.py           # Hash de passwords, emisión y validación de JWT
   │   ├── etl_service.py            # Pipeline ETL: detección de formato, filtrado (RF-011)
   │   ├── analysis_service.py       # Orquestación: ETL + Inferencia IA + weather_impact + persistencia
   │   ├── weather_service.py        # Llamadas a API Climática + caché + generación weather_impact
   │   └── alerts_service.py         # Notificación por email (SendGrid) a contactos de confianza
   |
   ├── repositories/                 # Queries SQL directas por dominio
   │   ├── user_repository.py        # INSERT/SELECT/UPDATE sobre users
   │   ├── session_repository.py     # INSERT/SELECT sobre analysis_sessions
   │   ├── biometric_repository.py   # INSERT/SELECT sobre biometric_data_raw
   │   ├── contact_repository.py     # CRUD sobre trusted_contacts
   │   └── weather_repository.py     # SELECT/INSERT/DELETE sobre weather_cache
   |
   ├── models_ai/                    # Gestión de Modelo de IA
   │   ├── __init__.py
   │   ├── model_loader.py           # Carga del modelo .pkl pre-entrenado
   │   └── inference_engine.py       # Input: [(timestamp, bpm)] → stress_level + verdict
   |
   └── utils/                        # Utilidades
       ├── __init__.py
       ├── encryption.py             # Cifrado de datos biométricos
       ├── validators.py             # Validación de inputs CSV/JSON
       └── formatters.py             # Formato de fechas y JSON
```


#### Descripción de las Capas Principales (Alineadas a la Especificación)


1.  **Capa API (`api/`)**:
   *   **Core**: Maneja la carga de archivos (`.csv`, `.json`) y entrada manual (RF-001).
   *   **Historial**: Gestiona la persistencia y lectura de la tabla `analysis_sessions` y `biometric_data_raw`.
   *   **Stats**: Provee datos agregados para visualización.
   *   **Alertas**: Gestiona la notificación de contactos externos.
2.  **Capa de Servicios (`services/`)**:
   *   **Análisis**: Integra el repositorio de biométricos con el `inference_engine` (Modelo de IA) para obtener el nivel de estrés y estado de idoneidad. Post-inferencia aplica `baseline_bpm` del usuario para ajustar el semáforo y adjunta el `weather_impact` generado por el `weather_service`.
   *   **Clima**: Conecta con la API externa, gestiona la lógica de caché en la tabla `weather_cache` y genera el campo `weather_impact` según la condición detectada.
   *   **Alertas**: Notifica por correo electrónico (SendGrid) a contactos de confianza.
3.  **Capa de Base de Datos (`db/`)**:
   *   `database.py` inicializa el engine de SQLAlchemy Core y expone `get_connection()` para que los repositorios ejecuten queries directas.
   *   `schema.sql` es la fuente de verdad del schema — contiene el DDL completo. Se ejecuta una vez al inicializar la app si las tablas no existen.
   *   No hay clases ORM ni mapeo objeto-relacional. Los repositorios trabajan con SQL directo y devuelven diccionarios o listas de diccionarios.
4.  **Capa de IA (`models_ai/`)**:
   *   Responsable de cargar el modelo `.pkl` y ejecutar la inferencia para clasificar el estrés.
   *   El `inference_engine` recibe **features absolutas** de la sesión: `[bpm_mean, bpm_std, bpm_p25, bpm_p75, bpm_max]`. Los parámetros del scaler (`KMEANS_SCALER_MEAN`, `KMEANS_SCALER_STD`) se leen desde `.env`.
   *   La salida del `inference_engine` incluye: `stress_level` (`"Low"`/`"Moderate"`/`"High"`), `confidence_score` (`FLOAT 0.0–1.0` internamente). La capa de API lo convierte a **entero 0–100** antes de serializar la respuesta JSON.
   *   El `analysis_service` aplica post-inferencia: usa `baseline_bpm` del usuario para validar el clúster y determina `traffic_light` (`"Green"`/`"Yellow"`/`"Red"`) y `verdict` (`"Fit"`/`"Unfit"`).
   *   **Nota de exportación:** El mismo modelo debe poder exportarse como `.tflite` para uso offline en el cliente Ionic. Este proceso es responsabilidad del equipo de ML (tooling externo) y no forma parte del backend.
5.  **Capa de Utilidades (`utils/`)**:
   *   Maneja la validación de datos crudos, el cifrado de datos biométricos y el formato de fechas y JSON.




## 3. Implementación de Requisitos Funcionales


### 3.1 Análisis de Datos Fisiológicos (RF-001)
#### 3.1.1 Carga de Archivos
Los archivos CSV o JSON se cargan a través de una API REST, siendo validados para asegurar su integridad y limpios antes de ser almacenados en la base de datos (SQLite para prototipo, PostgreSQL para producción). Un modelo pre-entrenado clasifica el nivel de estrés del conductor.


### 3.2 Especificación Técnica (SDD)
#### 3.2.1 Overview Técnico del Sistema
El sistema backend es una **aplicación monolítica modular** que procesa datos fisiológicos y ambientales para evaluar la idoneidad del conductor. Utiliza Python con FastAPI como framework para crear servicios RESTful, interactúa con SQLite vía SQLAlchemy Core (queries SQL directas, sin ORM) para almacenar los datos, y se conecta con APIs externas para obtener información climática y enviar alertas. Toda la lógica corre en un único proceso desplegado vía Docker; no hay microservicios ni comunicación entre procesos independientes.


### 3.3 Arquitectura (Alto Nivel)
El backend monolítico modular está compuesto por los siguientes servicios lógicos:
- **Servicio de Análisis**: Procesa datos fisiológicos y ambientales.
- **Servicio de Almacenamiento**: Gestiona la persistencia de los resultados del análisis.
- **Servicio de Alertas**: Maneja notificaciones en tiempo real basadas en el análisis realizado.


### 3.4 Componentes del Sistema
- **Backend (Python, API REST)**: Utiliza FastAPI para crear endpoints que permiten la carga y procesamiento de datos.
- **Servicios Externos**: APIs climáticas para obtener información meteorológica actual o histórica y APIs de notificación para alertas.


### 3.5 Patrón de Acceso a Datos (SQL Directo)


No se usa ORM. Los repositorios ejecutan SQL directamente via SQLAlchemy Core y mapean los resultados manualmente. El schema `db/schema.sql` es la fuente de verdad — no hay clases Python que definan tablas.


**`db/database.py`:**
```python
from sqlalchemy import create_engine, text
from app.config import settings


engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})


def get_connection():
   return engine.connect()
```


**Ejemplo de repositorio (`repositories/user_repository.py`):**
```python
from sqlalchemy import text
from app.db.database import get_connection


def get_user_by_email(email: str) -> dict | None:
   with get_connection() as conn:
       row = conn.execute(
           text("SELECT * FROM users WHERE email = :email"),
           {"email": email}
       ).mappings().first()
       return dict(row) if row else None


def create_user(id: str, name: str, email: str, password_hash: str) -> dict:
   with get_connection() as conn:
       conn.execute(
           text("""
               INSERT INTO users (id, name, email, password_hash)
               VALUES (:id, :name, :email, :password_hash)
           """),
           {"id": id, "name": name, "email": email, "password_hash": password_hash}
       )
       conn.commit()
   return get_user_by_email(email)
```


**Inicialización del schema al arrancar (`main.py`):**
```python
from pathlib import Path
from sqlalchemy import text
from app.db.database import engine


def init_db():
   schema = Path("app/db/schema.sql").read_text()
   with engine.connect() as conn:
       conn.executescript(schema)  # SQLite; para PostgreSQL: conn.execute(text(schema))
```


---


### 3.5 Modelo de Datos (Entidades y Tablas Físicas)


A continuación, se detallan las entidades lógicas y cómo se mapean a las tablas físicas en SQLite (prototipo) / PostgreSQL (producción) para evitar redundancia y mejorar la integridad.


#### **1. Entidad: Usuario y Configuración**
*   **Tabla Física:** `users`
*   **Propósito:** Guarda el perfil del conductor y sus umbrales de calibración.
*   **Atributos:**
   *   `id`: Identificador único.
   *   `name`: Nombre del usuario.
   *   `baseline_bpm`: Ritmo cardíaco basal (`INTEGER`, ej: 70). Valor por defecto desde `.env` (`DEFAULT_BASELINE_BPM`).
   *   `threshold_config`: JSON con límites personalizados de estrés.
   *   `created_at`: Timestamp de creación.
   *   `last_login`: Timestamp del último inicio de sesión para auditoría y seguridad.
   *   `encryption_key`: Clave maestra para cifrado de datos biométricos (ej., hash derivado del password).
   *   `session_count`: Contador de sesiones de análisis exitosas (`INTEGER`, default `0`).
   *   `profile_status`: Estado del perfil (`TEXT`, enum: `'new'`, `'calibrating'`, `'stable'`, default `'new'`).
   *   `last_stability_check`: Timestamp de la última verificación de estabilidad del perfil.


#### **2. Entidad: Sesión de Análisis (Resultado Principal)**
*   **Tabla Física:** `analysis_sessions`
*   **Propósito:** Guarda el resultado final de la evaluación ("Fit"/"Unfit") y el contexto global. **No** guarda los datos crudos de BPM aquí, sino el resultado de la agregación.
*   **Atributos:**
   *   `id`: Identificador único (UUID de la sesión).
   *   `user_id`: Referencia al usuario (`users.id`).
   *   `timestamp`: Hora exacta del análisis.
   *   `verdict`: Estado de idoneidad (`"Fit"` o `"Unfit"`).
   *   `stress_level`: Clasificación por IA (`"Low"`, `"Moderate"`, `"High"`).
   *   `traffic_light`: Color del semáforo fisiológico (`"Green"`, `"Yellow"`, `"Red"`). Determinado exclusivamente por el clúster fisiológico.
   *   `weather_snapshot`: Snapshot JSON del clima en el momento del análisis.
   *   `risk_score`: Calificación numérica del riesgo (0–100).
   *   `confidence_score`: Confianza del modelo (`FLOAT`, 0.0–1.0, ej: `0.95`). La API serializa este campo como entero multiplicando por 100 (ej: `95`). El frontend siempre recibe y muestra un entero 0–100.
   *   `tags`: **JSON array** con múltiples etiquetas/contextos (ej: `["Rain","Traffic"]`).
   *   `weather_impact`: **JSON** con el impacto climático secundario, ej: `{"severity": "moderate", "message": "Light rain detected. Consider increasing braking distance."}`. `null` si el clima es normal.
   *   `processing_status`: Estado del procesamiento (`TEXT`, enum: `'processing'`, `'completed'`, `'failed'`). **En MVP siempre `'completed'`** (procesamiento síncrono); los otros estados quedan reservados para evolución futura. Ver §3.8.8.
   *   `error_code`: Código de error si `processing_status='failed'`. **No usado en MVP** (las fallas no se persisten en esta tabla, se loguean en `audit_logs`).


#### **3. Entidad: Datos Biométricos Crudos (Serie de Tiempo) - Cifrado**
*   **Tabla Física:** `biometric_data_raw`
*   **Propósito:** Almacena cada lectura individual de frecuencia cardíaca para renderizar gráficas y calcular tendencias.
*   **Atributos:**
   *   `id`: Identificador único de la lectura.
   *   `session_id`: Referencia a la sesión (`analysis_sessions.id`).
   *   `timestamp`: Marca de tiempo global absoluta de la lectura.
   *   `bpm_encrypted`: Frecuencia cardíaca instantánea cifrada con Fernet/AES (campo `TEXT` con valor encriptado).
   *   `iv_encrypted`: IV (Initialization Vector) utilizado para el cifrado de esta lectura.
   *   `relative_timestamp`: Tiempo transcurrido desde el inicio de la sesión (milisegundos).
   *   `source`: Origen de los datos (`"Sensor"`, `"API"`, `"Manual"`).


#### **4. Entidad: Cache Climática**
*   **Tabla Física:** `weather_cache`
*   **Propósito:** Optimiza las consultas a la API externa almacenando datos de clima por región.
*   **Atributos:**
   *   `coordinates_key`: Clave primaria (concatenación de `region_lat` y `region_lon`, redondeados a 2 decimales).
   *   `weather_data_json`: Respuesta cruda de la API.
   *   `expires_at`: Fecha y hora de expiración de los datos.
   *   **Nota técnica:** El `weather_service` debe implementar un worker o tarea planificada para limpiar registros con `expires_at < CURRENT_TIMESTAMP` (cada 15 min).


> **Entidad Reportes — BACKLOG:** La tabla `generated_reports` y todo lo relacionado con generación/descarga de archivos PDF/Excel se omite de la implementación actual.


#### **5. Entidad: Contactos de Confianza**
*   **Tabla Física:** `trusted_contacts`
*   **Propósito:** Almacena los contactos de emergencia del conductor para notificaciones de alerta (RF-004).
*   **Atributos:**
   *   `id`: Identificador único (UUID).
   *   `user_id`: Referencia al usuario (`users.id`).
   *   `name`: Nombre del contacto (`TEXT`, requerido).
   *   `email`: Dirección de correo electrónico (`TEXT`, requerido). Canal exclusivo de notificación de alertas.
   *   `phone`: Número de teléfono (`TEXT`, opcional). Solo referencia, no se usa para alertas automatizadas.
   *   `created_at`: Timestamp de creación.


#### **6. Entidad: Refresh Tokens**
*   **Tabla Física:** `refresh_tokens`
*   **Propósito:** Almacena los refresh tokens hasheados para la rotación de sesiones JWT (RF-010). Permite revocar sesiones sin invalidar el `JWT_SECRET_KEY` global.
*   **Atributos:**
   *   `id`: Identificador único (UUID).
   *   `user_id`: Referencia al usuario (`users.id`). Se elimina en cascada si el usuario es eliminado.
   *   `token_hash`: Hash del refresh token — nunca almacenado en claro.
   *   `expires_at`: Timestamp de expiración (ISO 8601).
   *   `revoked`: Booleano (`INTEGER 0/1`, default `0`). Se marca `1` al hacer logout o al rotar el token.
   *   `created_at`: Timestamp de creación.


#### **7. Entidad: Logs de Auditoría (RF-008)**
*   **Tabla Física:** `audit_logs`
*   **Propósito:** Registra todos los eventos del sistema para auditoría interna y trazabilidad.
*   **Atributos:**
   *   `id`: Identificador único (UUID).
   *   `user_id`: Referencia al usuario (`users.id`).
   *   `timestamp`: Timestamp del evento.
   *   `event_type`: Tipo de evento (`"upload"`, `"model_failure"`, `"api_error"`, `"alert_sent"`, `"login"`, etc.).
   *   `model_status`: Estado del modelo de IA (`"Success"`, `"Fallback"`, `"Error"`).
   *   `error_message`: Mensaje técnico interno de error (si aplica).
   *   `details`: Campo `JSON` con contexto adicional (payload, respuesta API, stack trace, etc.).
   *   `FOREIGN KEY(user_id) REFERENCES users(id)`.


### 3.6 Schema DDL (SQLite)


Full schema ready to execute. SQLite-compatible (prototype). To migrate to PostgreSQL: replace `TEXT` primary keys with `UUID DEFAULT gen_random_uuid()`, `INTEGER` booleans with `BOOLEAN`, `TEXT` timestamps with `TIMESTAMPTZ`, and `strftime(...)` with `NOW()`.


```sql
-- ─────────────────────────────────────────
-- TABLE: users
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
   id                   TEXT    PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
   name                 TEXT    NOT NULL,
   email                TEXT    NOT NULL UNIQUE,
   password_hash        TEXT    NOT NULL,
   baseline_bpm         INTEGER DEFAULT 72,              -- default from .env DEFAULT_BASELINE_BPM
   threshold_config     TEXT    NOT NULL DEFAULT '{}',   -- JSON: custom stress thresholds
   session_count        INTEGER NOT NULL DEFAULT 0,
   profile_status       TEXT    NOT NULL DEFAULT 'new'
                        CHECK (profile_status IN ('new', 'calibrating', 'stable')),
   last_stability_check TEXT    DEFAULT NULL,            -- ISO 8601
   last_login           TEXT    DEFAULT NULL,            -- ISO 8601
   encryption_key       TEXT    DEFAULT NULL,
   created_at           TEXT    NOT NULL
                        DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);


-- ─────────────────────────────────────────
-- TABLE: refresh_tokens
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS refresh_tokens (
   id          TEXT    PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
   user_id     TEXT    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
   token_hash  TEXT    NOT NULL UNIQUE,
   expires_at  TEXT    NOT NULL,                         -- ISO 8601
   revoked     INTEGER NOT NULL DEFAULT 0,               -- 0 = false, 1 = true
   created_at  TEXT    NOT NULL
               DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);


-- ─────────────────────────────────────────
-- TABLE: analysis_sessions
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analysis_sessions (
   id                TEXT    PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
   user_id           TEXT    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
   timestamp         TEXT    NOT NULL
                     DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
   verdict           TEXT    NOT NULL CHECK (verdict IN ('Fit', 'Unfit')),
   stress_level      TEXT    NOT NULL CHECK (stress_level IN ('Low', 'Moderate', 'High')),
   traffic_light     TEXT    NOT NULL CHECK (traffic_light IN ('Green', 'Yellow', 'Red')),
   weather_snapshot  TEXT    NOT NULL DEFAULT '{}',      -- JSON: weather state at analysis time
   weather_impact    TEXT    DEFAULT NULL,               -- JSON: {severity, message} or null
   risk_score        REAL    DEFAULT NULL,               -- 0–100
   confidence_score  REAL    DEFAULT NULL,               -- 0.0–1.0 internal; API exposes 0–100
   tags              TEXT    NOT NULL DEFAULT '[]',      -- JSON array: ["Rain","Traffic"]
   processing_status TEXT    NOT NULL DEFAULT 'completed'
                     CHECK (processing_status IN ('processing', 'completed', 'failed')),
                     -- MVP: solo se insertan filas en estado 'completed' (procesamiento síncrono).
                     -- Los estados 'processing' y 'failed' quedan reservados para evolución futura
                     -- a procesamiento asíncrono (ver §3.8.8 y Backlog).
   error_code        TEXT    DEFAULT NULL,
   created_at        TEXT    NOT NULL
                     DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id   ON analysis_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status    ON analysis_sessions(processing_status);
CREATE INDEX IF NOT EXISTS idx_sessions_timestamp ON analysis_sessions(timestamp);


-- ─────────────────────────────────────────
-- TABLE: biometric_data_raw
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS biometric_data_raw (
   id                 TEXT    PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
   session_id         TEXT    NOT NULL REFERENCES analysis_sessions(id) ON DELETE CASCADE,
   timestamp          TEXT    NOT NULL,                  -- absolute ISO 8601
   bpm_encrypted      TEXT    NOT NULL,                  -- Fernet/AES encrypted value
   iv_encrypted       TEXT    NOT NULL,                  -- encryption IV
   relative_timestamp INTEGER DEFAULT NULL,              -- ms from session start
   source             TEXT    NOT NULL DEFAULT 'Manual'
                      CHECK (source IN ('Sensor', 'API', 'Manual'))
);
CREATE INDEX IF NOT EXISTS idx_biometric_session ON biometric_data_raw(session_id);


-- ─────────────────────────────────────────
-- TABLE: weather_cache
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS weather_cache (
   coordinates_key  TEXT PRIMARY KEY,                    -- "{lat},{lon}" rounded to 2 decimals
   weather_data_json TEXT NOT NULL,                      -- JSON: raw API response
   expires_at        TEXT NOT NULL                       -- ISO 8601; TTL 15 min
);
CREATE INDEX IF NOT EXISTS idx_weather_cache_expires ON weather_cache(expires_at);


-- ─────────────────────────────────────────
-- TABLE: trusted_contacts
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS trusted_contacts (
   id         TEXT    PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
   user_id    TEXT    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
   name       TEXT    NOT NULL,
   email      TEXT    NOT NULL,                          -- required: SendGrid alert channel
   phone      TEXT    DEFAULT NULL,                      -- optional: reference only, not used for alerts
   created_at TEXT    NOT NULL
              DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_contacts_user ON trusted_contacts(user_id);


-- ─────────────────────────────────────────
-- TABLE: audit_logs
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
   id            TEXT    PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
   user_id       TEXT    DEFAULT NULL
                 REFERENCES users(id) ON DELETE SET NULL,
   timestamp     TEXT    NOT NULL
                 DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
   event_type    TEXT    NOT NULL,                       -- 'upload','login','alert_sent', etc.
   model_status  TEXT    DEFAULT NULL
                 CHECK (model_status IN ('Success', 'Fallback', 'Error')),
   error_message TEXT    DEFAULT NULL,                   -- internal, never exposed to user
   details       TEXT    NOT NULL DEFAULT '{}'           -- JSON: payload, API response, etc.
);
CREATE INDEX IF NOT EXISTS idx_audit_user      ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_event     ON audit_logs(event_type);
```


> **PostgreSQL migration note:** replace `TEXT DEFAULT (lower(hex(randomblob(16))))` with `UUID DEFAULT gen_random_uuid()`, `INTEGER` booleans with `BOOLEAN`, `TEXT` timestamps with `TIMESTAMPTZ`, and `strftime(...)` with `NOW()`. The rest of the schema is compatible without changes.


---


### 3.7 Flujo de Datos
El sistema sigue una arquitectura de procesamiento de datos en tres fases principales:


#### 1. Ingesta y Validación
- **Carga de Archivos:** Los archivos CSV o JSON se cargan a través de la API REST (`/analysis/upload-file`), donde se validan las columnas y se limpian valores nulos o erróneos antes de la persistencia.
- **Persistencia Cruda:** Los datos de frecuencia cardíaca (BPM) se cifran y almacenan en la tabla `biometric_data_raw` para mantener el historial granular de la sesión.


#### 2. Procesamiento e Inferencia (Core)
- **Agregación y Clasificación:**
   1. Se agrupan las lecturas de BPM por sesión (o rango de tiempo).
   2. El **Modelo de IA pre-entrenado**, persistente como un archivo `.pkl`, recibe estos datos agregados y ejecuta la inferencia para clasificar el nivel de estrés (`"Low"`, `"Moderate"`, `"High"`).
   > **Nota técnica:** Este archivo `.pkl` es el activo intelectual que contiene la lógica matemática entrenada; no se "hardcodea" el agotamiento en el código de la API, sino que el modelo lo predice basado en los patrones de entrada.
- **Correlación Contextual:**
   - Se consulta la tabla `weather_cache` (actualizada por el `weather_service`) para obtener las condiciones ambientales vigentes.
   - El `weather_service` genera el campo `weather_impact` basado en las condiciones climáticas actuales (ej: lluvia intensa → `severity: critical`). Este campo es **independiente del semáforo** — no lo modifica ni redefine. El `traffic_light` es determinado exclusivamente por el clúster fisiológico del paso anterior. El `weather_impact` se adjunta al resultado como contexto adicional para el usuario.


#### 3. Persistencia del Resultado
- **Veredicto Final:** El resultado consolidado (`traffic_light`, `stress_level`, `verdict`, `risk_score`, `weather_impact`) se guarda en la tabla `analysis_sessions`. El `traffic_light` refleja exclusivamente el clúster fisiológico; `weather_impact` es el campo independiente con el contexto climático.
- **Auditoría:** Se registran eventos en la tabla `audit_logs` para auditoría interna.
- **Consulta:** Los datos enriquecidos permiten consultas rápidas para el historial del usuario (`GET /history/{id}`).


### 3.8 Diseño de Endpoints
Este apartado describe la implementación detallada de todos los endpoints del sistema backend, incluyendo sus solicitudes (requests) y respuestas (responses). Los endpoints se categorizan según su función principal dentro del sistema.


#### 3.8.1 Gestión de Análisis (Core)
Estos endpoints son fundamentales para la funcionalidad central del sistema:
- **POST /analysis/upload-file**:
 - **Lógica de Validación:** Verifica el BPM en cada fila contra el rango [30, 220].
 - **Comportamiento de Error:** Si el BPM es inválido, devuelve `400 Bad Request` con un `error_code` estructurado (ej. `{"error_code": "INVALID_BPM_RANGE"}`) según RF-009. El frontend mapea este código a texto humano.
 - **Manejo de Etiquetas:** Filtra las etiquetas del usuario contra la lista blanca (`ALLOWED_TAGS`). Si una etiqueta no está permitida, la descarta silenciosamente o reporta el error global según la configuración.
 - **Límite duro de tamaño:** archivos `> MAX_UPLOAD_SIZE_MB` (default 2MB) o con `> 5000 filas válidas` tras ETL → `413 FILE_TOO_LARGE`. El procesamiento offline de archivos grandes es responsabilidad del frontend (ver §3.8.8).
 - **Estados de Respuesta:**
   - `200 OK`: Análisis completo y exitoso.
   - `400 Bad Request`: Datos inválidos (BPM fuera de rango, etiquetas prohibidas, ETL falla, filename inválido).
   - `413 Payload Too Large`: `{"error_code": "FILE_TOO_LARGE", "message": "Archivo excede el límite de procesamiento online. Procesar localmente en la app."}`.
   - `415 Unsupported Media Type`: Content-Type no es `text/csv` ni `application/json`.


- **POST /analysis/manual-input**:
 - Implementación idéntica a `/upload-file` para inputs manuales. Mismo límite de 5000 puntos en el JSON.


#### 3.8.2 Historial y Persistencia (SQLite)
Endpoints que gestionan la persistencia de datos y la consulta del historial:
- **GET /history/summary**: Devuelve un resumen paginado de los últimos análisis (fecha, `verdict`, `traffic_light`, resumen climático). Soporta `?page=1&limit=10` y `?tags=Rain,Traffic` para filtrado.
- **GET /history/{id}**: Proporciona el detalle completo de un análisis específico, incluyendo snapshot de clima y, opcionalmente (`?raw_data=true`), los datos biométricos crudos des-cifrados.
- **DELETE /history/{id}**: Permite al usuario borrar un registro individual del historial.
- **GET /history/stats**: Estadísticas agregadas (promedio de estrés, distribución por semáforo, tendencias) utilizadas por los endpoints de gráficas del frontend.


#### 3.8.3 Perfil y Calibración
Para personalizar la experiencia del usuario según sus necesidades fisiológicas:
- **GET /user/profile**: Obtiene el perfil del usuario. La respuesta debe incluir `profile_status` (`new`/`calibrating`/`stable`), `session_count`, `baseline_bpm` y `last_stability_check` para que el frontend renderice el estado correcto de calibración.
- **PUT /user/profile/calibrate**: Permite al usuario ajustar su ritmo cardíaco basal. Recalcula `profile_status` tras actualizar.
- **GET /user/tags**: Devuelve la lista de etiquetas personalizadas configuradas por el usuario.
- **POST /user/tags**: Crea una nueva etiqueta personalizada asociada al usuario actual.
- **DELETE /user/tags/{id}**: Elimina una etiqueta personalizada específica del usuario.
- **GET /user/contacts**: Devuelve la lista de contactos de confianza del usuario (tabla `trusted_contacts`).
- **POST /user/contacts**: Crea un nuevo contacto de confianza. Campos requeridos: `name`, `email` (canal de notificación SendGrid). Campo opcional: `phone` (solo referencia, no se usa para alertas automatizadas).
- **PUT /user/contacts/{id}**: Actualiza un contacto de confianza existente.
- **DELETE /user/contacts/{id}**: Elimina un contacto de confianza específico.


#### 3.8.4 Utilidades
- **GET /health**: Endpoint de verificación del estado del backend. Retorna `{"status": "ok"}` cuando el sistema está operativo.


> **BACKLOG:** Los endpoints `POST /reports/generate` y `GET /reports/download/{file_id}` se omiten de la implementación actual.


#### 3.8.5 Endpoints para Gráficas (Visualización Dinámica)
Para una visualización dinámica y eficiente de datos:
- **GET /stats/trends?period=week|month**: Devuelve un resumen de los niveles promedio de estrés según el período seleccionado, útil para gráficas en tiempo real.
- **GET /stats/distribution**: Muestra la distribución porcentual del estado de estrés (`"Green"`, `"Yellow"`, `"Red"`) para análisis específicos o generales.
- **GET /stats/correlations**: Analiza las correlaciones entre el clima y los niveles de estrés, proporcionando insights valiosos.


#### 3.8.6 Autenticación (RF-010)
- **POST /auth/register**:
 - **Input:** `{"email": "string", "password": "string"}`.
 - **Lógica:** Validar unicidad de email. Hashear contraseña con `bcrypt` (cost factor 12). Crear registro en tabla `users`. Emitir access token (JWT, exp 1h) y refresh token (JWT opaco, exp 7d). Guardar el refresh token hasheado en tabla `refresh_tokens`.
 - **Respuesta `201 Created`:** `{"access_token": "...", "token_type": "bearer", "profile_status": "new|calibrating|stable", "session_count": 0}`. El refresh token se envía exclusivamente como httpOnly cookie (`Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Strict`).
 - **Error `409`:** `{"error_code": "EMAIL_ALREADY_EXISTS", "message": "Este email ya está registrado."}`.
 - **Error `400`:** `{"error_code": "WEAK_PASSWORD", "message": "La contraseña debe tener al menos 8 caracteres e incluir un carácter especial."}`.


- **POST /auth/login**:
 - **Input:** `{"email": "string", "password": "string"}`.
 - **Lógica:** Buscar usuario por email. Verificar password con `bcrypt.checkpw()`. Si válido, emitir nuevos tokens. Invalidar refresh tokens previos del usuario (rotación de tokens).
 - **Respuesta `200 OK`:** Mismo esquema que `/register` — incluye `access_token`, `profile_status` y `session_count`.
 - **Error `401`:** `{"error_code": "INVALID_CREDENTIALS", "message": "Email o contraseña incorrectos."}`.


- **POST /auth/refresh**:
 - **Input:** Refresh token leído desde httpOnly cookie.
 - **Lógica:** Verificar que el token existe en `refresh_tokens` y no está expirado ni revocado. Emitir nuevo access token. Rotar el refresh token (invalidar el actual, emitir uno nuevo).
 - **Error `401`:** `{"error_code": "REFRESH_TOKEN_INVALID", "message": "Sesión expirada. Por favor, volvé a ingresar."}`.


- **POST /auth/logout**:
 - **Lógica:** Revocar el refresh token activo del usuario en `refresh_tokens`. Limpiar la cookie httpOnly.
 - **Respuesta `200 OK`:** `{"message": "Sesión cerrada correctamente."}`.


**Tabla `refresh_tokens`:**
- `id`: UUID.
- `user_id`: FK a `users`.
- `token_hash`: Hash del refresh token (nunca almacenar en claro).
- `expires_at`: Timestamp de expiración.
- `revoked`: Boolean, default `false`.
- `created_at`: Timestamp de creación.


**Dependencia de seguridad:** Todos los endpoints protegidos deben usar el decorador `Depends(get_current_user)` de FastAPI, que extrae y valida el JWT del header `Authorization: Bearer <token>` e inyecta el `user_id` en el contexto del request.


---


#### 3.8.7 Pipeline ETL (RF-011)


El `etl_service.py` implementa el pipeline en tres pasos secuenciales:


**Paso 1 — Detección de formato:**
```python
# Columnas que identifican formato Apple Health
APPLE_HEALTH_COLUMNS = {"timestamp", "type", "value", "unit", "sourceName", "sourceVersion"}
APPLE_HEALTH_HR_TYPE = "HKQuantityTypeIdentifierHeartRate"


# Nombres de columna candidatos para formato simple
HR_COLUMN_CANDIDATES = ["bpm", "heart_rate", "heartrate", "hr", "ritmo",
                        "frecuencia_cardiaca", "FC", "HeartRate", "value"]
```
- Si las columnas del CSV son un superset de `APPLE_HEALTH_COLUMNS` → formato Apple Health.
- Si no → buscar intersección con `HR_COLUMN_CANDIDATES`.
 - 1 coincidencia: usar esa columna automáticamente.
 - > 1 coincidencia: retornar `400 Bad Request` con `{"error_code": "COLUMN_SELECTION_REQUIRED", "columns": [...]}`.
 - 0 coincidencias: retornar `400 Bad Request` con la lista completa de columnas del CSV en el campo `columns`.


**Paso 2 — Extracción:**
- Apple Health: filtrar filas donde `type == APPLE_HEALTH_HR_TYPE`. Usar columnas `timestamp` y `value`.
- Formato simple: usar la columna identificada y la columna de timestamp (auto-detectada por nombre: `timestamp`, `time`, `fecha`, `date`).


**Paso 3 — Filtrado y validación:**
```
Reglas de descarte (solo estas):
 - BPM nulo o no numérico          → rechazar fila
 - Timestamp nulo o no parseable   → rechazar fila
 - BPM < 30 o BPM > 220           → rechazar fila


NO descartar: filas con BPM igual a otra fila pero en timestamp distinto.
```
- Retornar: serie limpia `[(timestamp_iso, bpm_float)]` ordenada cronológicamente + lista de `rejected_rows`.


**Contrato de salida hacia el modelo:**
```json
{
 "series": [
   {"timestamp": "2025-12-03T18:00:00", "bpm": 120.67},
   {"timestamp": "2025-12-03T18:10:00", "bpm": 124.18}
 ],
 "rejected_rows": [
   {"row": 45, "reason": "BPM_OUT_OF_RANGE", "value": 250}
 ]
}
```


---


#### 3.8.8 Procesamiento síncrono con fallback offline en frontend (RF-012)


**Decisión de arquitectura (MVP):** el backend procesa **exclusivamente de forma síncrona** dentro de un límite duro. Los archivos que excedan el límite o las situaciones sin conectividad son responsabilidad del frontend (ver `spec-002-front-*.md`), que ejecuta el mismo modelo en una variante `.tflite` local.


**Lógica de umbral en `POST /analysis/upload-file`:**
```python
MAX_UPLOAD_SIZE_MB = settings.MAX_UPLOAD_SIZE_MB  # default 2
MAX_ROWS = 5000


# 1) Pre-validación antes de leer el body en memoria
if content_length > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
   raise HTTPException(413, {"error_code": "FILE_TOO_LARGE",
                             "message": "Archivo excede el límite de procesamiento online. Procesar localmente en la app."})


# 2) ETL
series, rejected_rows = etl_service.run(file_bytes, filename)


# 3) Post-ETL: si la serie limpia supera el límite, también rechazar
if len(series) > MAX_ROWS:
   raise HTTPException(413, {"error_code": "FILE_TOO_LARGE", ...})


# 4) Procesamiento síncrono — no hay BackgroundTasks ni asyncio.wait_for
result = analysis_service.process(user_id, series, lat, lon)
return JSONResponse(status_code=200, content=result)
```


**Sobre el campo `processing_status` de `analysis_sessions`:**


El schema mantiene el campo (`'processing'` / `'completed'` / `'failed'`) **reservado para evolución futura a procesamiento asíncrono**. En MVP:
- Solo se insertan filas con `processing_status = 'completed'` (pasarlo explícito en el INSERT).
- Si el análisis falla, **no se inserta fila** en `analysis_sessions` — se devuelve error al cliente (4xx/5xx según corresponda) y se registra en `audit_logs` (RF-008).
- No existe `GET /analysis/status/{session_id}` en el MVP — eliminado de la API. El detalle de cualquier sesión completada se obtiene vía `GET /history/{id}`.


**Fallback offline (responsabilidad del frontend, no del backend):**
- Cuando el frontend detecta `413 FILE_TOO_LARGE` **o** ausencia de conectividad, ejecuta el modelo en su variante `.tflite` localmente.
- La sincronización del resultado offline → backend (endpoint dedicado para upload de resultados pre-calculados) queda en **Backlog v1.x**, no en MVP.


> **Si en el futuro se reactiva el procesamiento asíncrono backend**, las columnas `processing_status` y `error_code` ya existen en el schema, lo que evita migraciones. Se agregaría: (a) endpoint `GET /analysis/status/{id}`, (b) `BackgroundTasks` o worker dedicado, (c) handler de `SERVER_RESTART` en el `startup` que marque sesiones `'processing'` como `'failed'`.


---


#### 3.8.9 Endpoint de Alertas (RF-004)
- **POST /alerts/send**: Envía notificaciones a contactos de confianza en caso de incidentes detectados.
 - **Input:** JSON con `session_id` y opcionalmente `contact_ids` (array de IDs de `trusted_contacts`). Si `contact_ids` está vacío, se notifica a todos los contactos del usuario.
 - **Lógica:** El `alerts_service` recupera los contactos de la tabla `trusted_contacts`, construye el mensaje con el estado fisiológico, el `traffic_light` y el `weather_impact` de la sesión, y lo envía **exclusivamente por correo electrónico vía SendGrid** al campo `email` de cada contacto. No se usa SMS ni Twilio.
 - **Estados de Respuesta:**
   - `200 OK`: Notificación enviada exitosamente.
   - `202 Accepted`: Notificación encolada (conexión intermitente).
   - `400 Bad Request`: `{"error_code": "NO_CONTACTS_FOUND"}` si el usuario no tiene contactos registrados.
   - `503 Service Unavailable`: `{"error_code": "ALERT_SERVICE_UNAVAILABLE"}` si el proveedor externo falla.
 - **Fallback:** Si el envío falla, el evento se registra en `audit_logs` con `event_type: "alert_sent"` y `model_status: "Error"` para reintento posterior.