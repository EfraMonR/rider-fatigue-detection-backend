# Especificación Funcional: Sistema Backend (Python)
## Roadmap y Visión General: Sistema Preventivo de Seguridad Vial - Bloque 1


### Propósito del Documento
Este documento detalla los requisitos funcionales, casos de uso, viajes de usuario (user journeys) y casos de borde para el módulo de backend del Sistema Preventivo de Seguridad Vial. Se enfoca en definir *qué* debe hacer el sistema, sin especificar *cómo* implementarlo técnicamente (lo cual se deja para la Especificación Técnica).


---


### 1. Visión General de Alto Nivel


El sistema es una plataforma de apoyo a la decisión que analiza datos fisiológicos del conductor (ritmo cardíaco) y condiciones ambientales para determinar la idoneidad para conducir. Proporciona alertas en tiempo real, análisis histórico y guía de intervención.


**Tecnología Base:** El sistema está implementado como una aplicación monolítica modular en **Python**, utilizando **FastAPI** como marco de trabajo principal y **SQLite** como base de datos relacional para el prototipo. SQLite vive en un archivo local persistido vía volumen Docker. Si el proyecto escala a producción, el cambio a PostgreSQL es una sola línea en `.env` sin modificar el código.


**Valor Central:** Prevenir accidentes identificando el estrés del conductor antes de ingresar a la vía, considerando factores fisiológicos y ambientales.


---


## 2. Requisitos Funcionales (RF)


### **RF-001: Análisis de Datos Fisiológicos**
**Descripción:** El sistema debe procesar datos fisiológicos cargados (CSV, JSON) o entrada manual para determinar el estado de idoneidad.


**Criterios de Éxito:**
- Aceptar archivos CSV/JSON vía carga o formulario de entrada manual.
- Validar la integridad de los datos (ej., rechazar valores de BPM imposibles como >220).
- Limpiar los datos (eliminar entradas corruptas o vacías).
- Cargar un **modelo de Machine Learning pre-entrenado (archivo .pkl)** utilizando Scikit-Learn y clasificar niveles de estrés (`"Low"`, `"Moderate"`, `"High"`). El modelo recibe **features absolutas** derivadas de la sesión (media, desviación estándar y percentiles de BPM). El campo `baseline_bpm` del usuario **no es input del modelo**; se usa en la capa de negocio post-inferencia para ajustar el semáforo.
- Generar un veredicto de idoneidad (`"Fit"`/`"Unfit"`) con indicadores de luz de tráfico (`"Green"`/`"Yellow"`/`"Red"`) determinados **exclusivamente por el clúster fisiológico** detectado. Incluir `confidence_score` en la respuesta: almacenado internamente como `FLOAT 0.0–1.0`, expuesto en la API como **entero 0–100** (ej: `0.95` → `95`).
- Generar un **mensaje secundario de impacto climático** (`weather_impact`) independiente del semáforo, que contextualiza cómo las condiciones ambientales modulan el riesgo fisiológico detectado (ver RF-002).
- Guardar resultados en la base de datos configurada vía `DATABASE_URL` (SQLite para prototipo, PostgreSQL para producción).


**Casos de Borde:**
- *Error de Formato de Archivo:* Si el archivo cargado está corrupto o no es un CSV/JSON válido, devolver un 400 Bad Request con un mensaje de error descriptivo.
- *Error de Integridad de Datos:* Si el CSV contiene columnas esenciales faltantes (ej., `timestamp`, `bpm`), rechazar y sugerir el formato correcto.
- *Carga de Archivo Grande:* Para CSV >5MB, limitar el procesamiento para evitar tiempo de espera; devolver estado de procesamiento parcial si es soportado.
- *Entrada Vacía:* Si no se proporcionan datos, devolver un error 400 con una solicitud de cargar datos válidos.


---


### **RF-002: Integración de Contexto Ambiental**
**Descripción:** El sistema debe enriquecer el resultado fisiológico con condiciones climáticas en tiempo real, generando un mensaje de impacto secundario. El semáforo principal **no depende del clima**; el clima produce únicamente el campo `weather_impact`.


**Criterios de Éxito:**
- Aceptar coordenadas GPS y timestamp.
- Consultar una API climática (ej., Open-Meteo) para obtener precipitación, temperatura, viento y visibilidad.
- Aplicar un **mecanismo de caché persistente** (tabla `weather_cache`) para datos climáticos, con expiración automática cada 15 minutos.
- Generar un campo `weather_impact` con `severity` y `message` según la condición detectada:


| Condición climática | `severity` | Ejemplo de `message` |
| :--- | :--- | :--- |
| Tormenta / lluvia intensa | `critical` | "Tormenta activa. Visibilidad reducida, riesgo elevado." |
| Lluvia leve | `moderate` | "Lluvia leve. Considera aumentar la distancia de frenado." |
| Sol fuerte / alta temperatura | `moderate` | "Temperatura alta. El calor puede incrementar la fatiga." |
| Viento fuerte | `moderate` | "Vientos fuertes detectados. Precaución en vías expuestas." |
| Niebla / baja visibilidad | `high` | "Baja visibilidad por niebla. Reduce la velocidad." |
| Clima normal / nublado | `none` | `null` — no se emite mensaje. |


- El campo `weather_impact` es **siempre devuelto junto al semáforo** en la respuesta de análisis, permitiendo al frontend mostrar ambos resultados de forma independiente.


**Casos de Borde:**
- *API No Disponible:* Si la API climática falla, devolver los datos de caché últimos o condiciones predeterminadas con una advertencia.
- *Ubicación No Encontrada:* Si las coordenadas son inválidas, devolver un error genérico con una solicitud de ingresar ubicación válida.


---


### **RF-003: Seguimiento Histórico**
**Descripción:** El sistema debe rastrear el historial de análisis y exponer estadísticas agregadas.


**Criterios de Éxito:**
- Almacenar todos los resultados de análisis en la base de datos (SQLite para prototipo, PostgreSQL para producción — controlado por `DATABASE_URL`).
- Proporcionar recuperación paginada para historial de análisis.
- Generar estadísticas agregadas (ej., promedio de estrés por mes).
- Soportar filtrado por rango de fecha y etiquetas (ej., "tráfico", "lluvia").


> **BACKLOG:** La generación y descarga de reportes en formato PDF/Excel queda fuera del alcance actual. Ver backlog para retomar en una fase posterior.


**Casos de Borde:**
- *No hay Historial Disponible:* Si no existen registros, mostrar un mensaje amable solicitando al usuario cargar datos.
- *Confirmación de Eliminación:* Al eliminar un registro, solicitar confirmación para evitar pérdida accidental de datos.
- *Base de Datos Corrupta:* Implementar procedimientos de recuperación para restaurar datos si hay corrupción.


---


### **RF-004: Alertas en Tiempo Real**
**Descripción:** El sistema debe emitir alertas cuando detecta condiciones de riesgo fisiológico alto.


**Criterios de Éxito:**
- Activar alerta cuando el **clúster fisiológico detectado** corresponda a estrés alto (`traffic_light: "Red"`). El clima no es condición para activar la alerta; es contexto adicional.
- Emitir alertas mediante sonido (simulado).
- Enviar notificación por **correo electrónico** al contacto de confianza del usuario vía SendGrid.
- Permitir superposición manual del usuario para continuar conduciendo bajo condiciones seguras.


**Casos de Borde:**
- *Alerta No Entregada:* Si no es posible notificar (ej., conexión perdida), guardar el registro para notificación posterior.
- *Falsas Alarmas:* Permite al usuario ajustar umbrales de alerta para minimizar alertas falsas.


---


> **RF-005 — BACKLOG:** Generación y entrega de informes descargables (PDF/Excel/CSV) queda fuera del alcance actual. Todos los servicios, endpoints, tablas y modelos relacionados con esta funcionalidad se omiten de la implementación presente y se retoman en una fase posterior.


---


### **RF-006: Entrega de Datos Estructurados para Visualización**
**Descripción:** El sistema debe proveer datos estructurados y optimizados para la generación de gráficas en la interfaz de usuario.


**Criterios de Éxito:**
- **Datos Estructurados:** Para análisis históricos, el sistema debe devolver un JSON con arrays de datos (ej., `timestamps`, `values`, `labels`) para que el frontend pueda renderizar gráficas.
- **Optimización:** Las respuestas deben estar paginadas (ej., 10 puntos de datos por página) para evitar sobrecargas y garantizar un rendimiento eficiente.
- **Manejo de Errores:** Si falla la fuente de datos climáticos, el sistema debe devolver los últimos datos válidos disponibles con una advertencia, en lugar de colapsar completamente.


**Casos de Borde:**
- *Datos Insuficientes:* Si hay menos de 2 puntos de datos para generar la gráfica, devolver un JSON vacío con un mensaje de "Datos insuficientes para generar gráfica".
- *Fuente de Datos Externa Fallida:* Si la API climática falla durante el procesamiento, devolver los últimos datos de caché (si existen) con una advertencia visual.
- *Solicitud de Datos Invalida:* Si la solicitud de datos no incluye parámetros válidos (ej., rango de fechas), devolver error 400 Bad Request con un mensaje descriptivo.


---


### **RF-007: Gestión de Configuración del Usuario y Calibración**
**Descripción:** El sistema debe permitir a los usuarios personalizar su perfil fisiológico (línea base) y agregar contextos manuales. Toda configuración con valores por defecto se gestiona mediante variables de entorno (`.env`) para evitar hardcodeo.


**Criterios de Éxito:**
- **Calibración de Ritmo Basal:** Proporcionar un endpoint seguro para actualizar el `baseline_bpm` del usuario. Este valor se usa **post-inferencia** en la lógica de negocio para ajustar el semáforo, no como input directo al modelo K-Means.
- **Configuración por `.env`:** Los valores por defecto del sistema se toman de variables de entorno: `DEFAULT_BASELINE_BPM` (BPM basal para usuarios nuevos), `KMEANS_SCALER_MEAN` y `KMEANS_SCALER_STD` (parámetros del scaler de entrenamiento), umbrales de semáforo, y claves de servicios externos. Ningún valor de configuración se hardcodea en el código.
- **Etiquetado de Actividad (Tags):** Permitir al usuario añadir etiquetas contextuales al analizar (ej., "Trancón", "Lluvia", "Velocidad Alta", "Susto"). Esto permite filtrar y correlacionar eventos específicos en el historial.
- **Persistencia:** Guardar estas configuraciones en la tabla `users` (persistida vía volumen Docker para SQLite; no se pierde en reinicios).
- **Estado de Perfil:** El sistema debe mantener un campo `profile_status` en la tabla `users` con los siguientes valores posibles:
 - `new`: usuario sin `baseline_bpm` ni historial.
 - `calibrating`: usuario con datos pero < 5 sesiones registradas.
 - `stable`: usuario con ≥ 5 sesiones y desviación del BPM < 10% en los últimos 7 días.
- **Contador de Sesiones:** Incrementar `session_count` en `users` al guardar cada sesión de análisis exitosa. El endpoint `GET /user/profile` debe retornar `profile_status`, `session_count` y `last_stability_check`.


**Casos de Borde:**
- *Valor de Línea Base Inválido:* Si el usuario ingresa un BPM <30 o >220 para su línea base, rechazar y solicitar un valor fisiológico plausible.
- *Etiqueta Duplicada:* Si el usuario intenta crear una etiqueta con el mismo nombre existente, devolver un mensaje de error 409 Conflict o actualizar el registro existente con un 200 OK.
- *Modo Sin Conexión:* Si la conexión a internet falla pero la app necesita guardar el usuario, permitir guardar la línea base en caché local (si es soportado) o mostrar advertencia y permitir guardado posterior.


---


### **RF-008: Validación de Datos y Manejo de Calidad**
**Descripción:** El sistema debe limpiar datos antes de procesarlos, especialmente para el modelo de IA.


**Criterios de Éxito:**
- **Filtro de Ruido:** Antes de procesar el CSV, filtrar registros con `bpm` extremos (ej., >220 o <30 BPM) o duración inconsistente. Devolver una lista de registros rechazados con la razón del error.
- **Logs de Auditoría Interna:** Generar registros en la tabla `audit_logs` que capturen:
 - Fecha de carga.
 - Estado del modelo (`"Success"`, `"Fallback"`, `"Error"`).
 - Mensaje de error (ej., "CSV corrupto", "Datos insuficientes para análisis").
 - Usuario afectado.


---


### **RF-009: Mensajes de Error Humanos y Feedback**
**Descripción:** El sistema debe garantizar que cualquier error detectado por el backend sea presentado al usuario final con un lenguaje claro, empático y libre de tecnicismos, evitando la exposición de mensajes crudos de la infraestructura.


**Criterios de Éxito:**
- **Traducción Contextual de Errores:**
 - Cuando el backend detecta un error técnico (ej., `FileNotFound`, `DatabaseLocked`, `InvalidSchema`), debe responder con un código HTTP estándar y un cuerpo JSON con `error_code` y `message`: `{"error_code": "ERROR_CODE", "message": "Descripción breve legible."}`.
 - El campo `message` debe ser claro para el desarrollador que consulta el endpoint (ej., en Postman) pero no es el texto que el usuario final ve. El frontend usa `error_code` como clave para su diccionario i18n, ignorando `message` en la UI.
 - **NO** se deben exponer stack traces, rutas internas, nombres de columnas de BD ni mensajes del sistema operativo.
 - **Excepción explícita — endpoints de autenticación (RF-010):** Los endpoints `/auth/register`, `/auth/login`, `/auth/refresh` y `/auth/logout` siguen el mismo esquema `error_code + message`, sin excepción al formato. La diferencia es que en auth el `message` también puede ser mostrado directamente al usuario por el frontend cuando sea apropiado (ej., "Email o contraseña incorrectos").


- **Feedback de Procesamiento (MVP — solo síncrono):**
 - Todo análisis se ejecuta de forma **síncrona** dentro de los límites duros definidos en RF-012. El cliente espera la respuesta completa (`200 OK` con resultado, o error 4xx/5xx).
 - **No hay `202 Accepted`** en MVP: el procesamiento asíncrono backend está fuera de alcance. Archivos grandes los procesa el frontend localmente (RF-012).
 - Si el modelo `.pkl` no está disponible al arrancar el servidor, las requests de análisis devuelven `503 Service Unavailable` con `{"error_code": "MODEL_NOT_AVAILABLE", "message": "El servicio de análisis no está disponible temporalmente. Intentá nuevamente en unos minutos."}`.
 - El frontend muestra una animación de carga durante la espera del request síncrono.


- **Manejo de Tiempos de Espera (Timeout):**
 - En caso de `APITimeout`, el backend responde con `504 Gateway Timeout`.
 - El mensaje al usuario debe ser: *"La solicitud tomó más tiempo del esperado. Por favor, intente nuevamente en unos minutos"*, ocultando cualquier detalle sobre el estado del servidor o la cola de tareas.


---


### **RF-010: Autenticación y Gestión de Sesión**
**Descripción:** El sistema debe gestionar el acceso de usuarios mediante autenticación segura basada en JWT. Todos los usuarios tienen el mismo nivel de acceso y solo pueden ver sus propios datos.


**Criterios de Éxito:**
- Permitir registro de nuevos usuarios con email y contraseña.
- Validar credenciales y emitir un **access token** (JWT, expiración: 1 hora) y un **refresh token** (expiración: 7 días).
- Proteger todos los endpoints con autenticación obligatoria, excepto `POST /auth/register`, `POST /auth/login` y `GET /health`.
- Proveer endpoint de refresh para renovar el access token sin re-autenticación mientras el refresh token sea válido.
- Implementar logout invalidando el refresh token en base de datos.
- Aislar los datos por usuario: cada consulta filtra por `user_id` del token activo. Un usuario nunca puede acceder a datos de otro.


**Casos de Borde:**
- *Credenciales inválidas:* `401 Unauthorized` con `{"error_code": "INVALID_CREDENTIALS", "message": "Email o contraseña incorrectos."}`.
- *Access token expirado:* `401 Unauthorized` con `{"error_code": "TOKEN_EXPIRED", "message": "La sesión expiró. Renovando..."}`. El cliente debe intentar refresh automáticamente.
- *Refresh token expirado o inválido:* `401 Unauthorized` con `{"error_code": "REFRESH_TOKEN_INVALID", "message": "Sesión expirada. Por favor, volvé a ingresar."}`.
- *Email duplicado en registro:* `409 Conflict` con `{"error_code": "EMAIL_ALREADY_EXISTS", "message": "Este email ya está registrado."}`.
- *Contraseña débil:* `400 Bad Request` con `{"error_code": "WEAK_PASSWORD", "message": "La contraseña debe tener al menos 8 caracteres e incluir un carácter especial."}`.


---


### **RF-011: Pipeline ETL para Procesamiento de Datos Fisiológicos**
**Descripción:** El sistema debe procesar archivos CSV de distintos formatos extrayendo únicamente los datos de ritmo cardíaco, preservando la serie temporal completa.


**Criterios de Éxito:**
- **Detección de Formato Apple Health:**
 - Si el CSV contiene las columnas `timestamp`, `type`, `value`, `unit`, `sourceName`, `sourceVersion`, identificarlo automáticamente como formato Apple Health.
 - Filtrar únicamente las filas donde `type == 'HKQuantityTypeIdentifierHeartRate'`.
 - Usar `value` como BPM y `timestamp` como marca de tiempo.
- **Detección de Formato Simple:**
 - Si no se detecta el formato Apple Health, escanear nombres de columnas buscando coincidencias con: `bpm`, `heart_rate`, `heartrate`, `hr`, `ritmo`, `frecuencia_cardiaca`, `FC`, `HeartRate`, `value`.
 - Si se detecta más de una coincidencia posible, retornar la lista al frontend para que el usuario seleccione.
 - Si no se detecta ninguna, retornar la lista completa de columnas del CSV al frontend.
- **Reglas de Filtrado (lo único que se descarta):**
 - Filas con BPM nulo o en formato no numérico.
 - Filas con timestamp nulo o en formato no parseable.
 - Filas con BPM fuera del rango `[30, 220]`.
 - **NO** eliminar filas con el mismo valor de BPM en timestamps distintos — son lecturas válidas en momentos diferentes.
- **Registro de Rechazos:** Retornar junto al resultado una lista de filas rechazadas con razón específica (ej., `{"row": 45, "reason": "BPM_OUT_OF_RANGE", "value": 250}`).
- **Contrato de entrada al modelo:** El modelo recibe la serie limpia de pares `(timestamp, bpm)` ordenados cronológicamente.


**Casos de Borde:**
- *Columna no identificada automáticamente:* Retornar `400 Bad Request` con `{"error_code": "COLUMN_SELECTION_REQUIRED", "message": "No se pudo identificar la columna de ritmo cardíaco. Seleccioná la columna correcta.", "columns": ["col1", "col2", ...]}`. El frontend muestra un selector al usuario y reenvía la request con la columna elegida.
- *Sin filas válidas tras el filtrado:* `400 Bad Request` con `{"error_code": "NO_VALID_ROWS", "message": "El archivo no contiene datos de ritmo cardíaco válidos tras el filtrado."}`.
- *Archivo con solo encabezados:* Mismo tratamiento que sin filas válidas.


---


### **RF-012: Procesamiento de Archivos — Límite Síncrono y Fallback Offline en Frontend**
**Descripción:** El backend procesa archivos **exclusivamente de forma síncrona** dentro de un límite duro. Archivos que excedan ese límite, o situaciones sin conectividad, son responsabilidad del frontend (ver `spec-002-front-functional.md §RF-008`), que ejecuta el modelo en su variante `.tflite` local.


**Criterios de Éxito (Backend MVP):**
- **Procesamiento síncrono único:** archivos `≤ MAX_UPLOAD_SIZE_MB` (default 2MB) **y** `≤ 5.000 filas válidas tras ETL` → `200 OK` con el resultado completo en la misma request.
- **Rechazo de archivos grandes:** archivos `> MAX_UPLOAD_SIZE_MB` (verificado vía `Content-Length` antes de leer el body) **o** `> 5.000 filas válidas` (verificado tras ETL) → `413 Payload Too Large` con `{"error_code": "FILE_TOO_LARGE", "message": "Archivo excede el límite de procesamiento online. Procesar localmente en la app."}`.
- **Sin endpoint `/analysis/status/{id}`** en MVP. No hay `BackgroundTasks`, no hay polling, no hay sesiones en estado `processing` persistidas en BD (la columna existe en el schema pero solo se usa el valor `'completed'`).


**Responsabilidad del Frontend (delegada — ver `spec-002-*`):**
- Cuando recibe `413 FILE_TOO_LARGE`, o cuando detecta ausencia de conectividad antes de enviar la request → procesa el análisis localmente con el modelo `.tflite`.
- La sincronización del resultado pre-calculado offline hacia el backend (endpoint dedicado para upload de resultados ya calculados por el cliente) queda en **Backlog v1.x**.


**Casos de Borde:**
- *Archivo de tamaño en bytes aceptable pero con > 5.000 filas válidas tras ETL:* el endpoint igualmente devuelve `413 FILE_TOO_LARGE`.
- *CSV grande sin conexión:* el frontend lo procesa local con `.tflite`. Si excede el límite que el frontend pueda manejar offline, el frontend le pide al usuario reducir el archivo.
- *Reactivación futura de procesamiento asíncrono backend:* las columnas `processing_status` y `error_code` de `analysis_sessions` quedan reservadas para esta evolución, evitando una migración futura.


---


## 3. Requisitos No Funcionales (RNF)


### **RNF-001: Rendimiento**
- Las consultas climáticas deben ser cacheadas para reducir latencia (meta: <500ms para llamadas API).
- El procesamiento de datos debe completarse en menos de 3 segundos para tamaños de archivo estándar.
- **Entrega de Datos (RF-006):** Los endpoints de gráficas deben responder en menos de 200ms.


### **RNF-002: Disponibilidad**
- El backend debe ejecutar 99.9% de tiempo de actividad.
- Manejar apagados inesperados de forma elegante y asegurar la persistencia de datos.


### **RNF-003: Seguridad de Datos**
- Todos los endpoints de API deben estar protegidos con autenticación (ej., claves API o tokens).
- Los datos sensibles del usuario (ritmo cardíaco) deben estar encriptados en tránsito (HTTPS).


### **RNF-004: Accesibilidad**
- Las respuestas de API deben devolver errores en un formato legible por humanos (no rastros de Python crudos).
- Los registros deben estar sanitizados para evitar filtrar información sensible.


### **RNF-005: Rendimiento de Gráficas**
- La generación de gráficas debe ser asincrónica para archivos grandes (ej., >100k puntos de datos).


### **RNF-006: Configuración por Variables de Entorno**
- Todos los valores configurables del sistema (credenciales, umbrales, parámetros del modelo, BPM por defecto) deben leerse desde variables de entorno definidas en `.env`. Ningún valor de configuración debe estar hardcodeado en el código fuente.


---


## 4. Contexto del Sistema y Viajes de Usuario (J-001 a J-003)


### **J-001: Carga y Análisis del Conductor**
1. El conductor carga un archivo CSV o ingresa datos manualmente.
2. El sistema procesa los datos y obtiene el clima.
3. El sistema muestra el resultado (luz de tráfico, recomendaciones).
4. El sistema guarda el registro en el historial.


### **J-002: Revisión Diaria**
1. El conductor inicia sesión.
2. El sistema muestra el último análisis y el clima actual.
3. El conductor revisa las recomendaciones.
4. El conductor decide conducir o descansar.


### **J-003: Alerta de Emergencia**
1. El sistema detecta un clúster fisiológico de estrés alto (`traffic_light: "Red"`). El campo `weather_impact` se adjunta como contexto si las condiciones climáticas son relevantes, pero no es condición para activar la alerta.
2. El sistema alerta al conductor mediante sonido.
3. El sistema permite compartir el estado con un contacto de confianza.


---


## 5. Casos de Borde y Manejo de Errores (Perspectiva Funcional)


| Escenario | Comportamiento Esperado |
| :--- | :--- |
| **Carga de Archivo >500MB** | Devolver mensaje de error; sugerir dividir el archivo o usar carga incremental. |
| **Carga del Modelo Falla** | Devolver mensaje de error; sugerir reiniciar o volver a descargar el modelo. |
| **API Climática Caída** | Devolver datos caché últimos con advertencia; permitir superposición manual. |
| **Usuario Elimina Todo el Historial** | El sistema muestra un estado vacío con solicitud de volver a cargar datos. |
| **Columnas CSV Corruptas** | Rechazar archivo; proporcionar guía sobre estructura correcta de CSV. |
| **Base de Datos Bloqueada** | Implementar lógica de reintentos; devolver 503 Servicio No Disponible si el bloqueo persiste. |
| **Generación de Informe (PDF/Excel)** | Funcionalidad en BACKLOG. No aplica en implementación actual. |
| **Datos Insuficientes para Gráfica** | Devolver JSON vacío con mensaje de "Datos insuficientes". |
| **Almacenamiento Lleno** | Devolver 507 Insufficient Storage y sugerir limpiar caché. |
| **Fallo de Conexión a Base de Datos** | Al iniciar la aplicación, si no se puede establecer conexión con la base de datos configurada en `DATABASE_URL` (archivo SQLite inaccesible, servidor PostgreSQL caído, credenciales inválidas), retornar error 500 con mensaje: *"No se pudo conectar a la base de datos. Verifique la configuración de DATABASE_URL."* |


---


**Estado del Documento:** 3.0 (Ajustes: K-Means con features absolutas + .env config, semáforo dual output, reportes a backlog, alertas solo email, alineación offline TFLite frontend).
**Próximo Pasos:** Revisión de stakeholders -> Redacción de Especificación Técnica.