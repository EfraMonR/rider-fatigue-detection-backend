# Manual Testing Guide — Rider Fatigue Detection API

Guía paso a paso para probar el backend manualmente con Postman.

**Pre-requisito:** el servidor debe estar corriendo en Docker en `http://localhost:8000`.
Verificarlo con `GET /health` antes de empezar.

---

## 1. Importar colección y entorno

1. Postman → **File → Import**.
2. Importar `docs/postman/rider-fatigue-detection.postman_collection.json`.
3. Importar `docs/postman/rider-fatigue-detection.postman_environment.json`.
4. Esquina superior derecha → seleccionar entorno **"Rider Fatigue Detection — Local"**.

---

## 2. Variables del entorno

Abrir el entorno (ícono del ojo → **Edit**) y configurar:

| Variable | Qué es | Valor a usar |
|---|---|---|
| `base_url` | URL base del servidor | `http://localhost:8000` (no cambiar en local) |
| `access_token` | JWT de acceso del user1 | **No tocar** — se llena automático tras register/login |
| `refresh_token` | Token de renovación (HttpOnly cookie) | **No tocar** — referencia interna, lo maneja el navegador/Postman |
| `user_email` | Email del usuario principal | Cualquier email válido, ej. `rider1@example.com` |
| `user_name` | Nombre del usuario principal | Ej. `Rider One` (requerido solo en register) |
| `user_password` | Contraseña del usuario principal | Mínimo 8 caracteres + 1 especial, ej. `SecurePass@1` |
| `user_email_2` | Email del segundo usuario (IDOR) | Email distinto al anterior, ej. `rider2@example.com` |
| `user_name_2` | Nombre del segundo usuario | Ej. `Rider Two` |
| `user_password_2` | Contraseña del segundo usuario | Ej. `SecurePass@2` |
| `session_id` | ID de la última sesión de análisis | **No tocar** — se llena automático tras upload o manual-input |
| `contact_id` | ID del último contacto creado | **No tocar** — se llena automático tras POST /user/contacts |
| `tag_id` | ID del último tag creado | **No tocar** — se llena automático tras POST /user/tags |
| `access_token_user2` | JWT del segundo usuario | **No tocar** — se llena automático en los IDOR Tests |

> Las variables marcadas como "No tocar" son gestionadas por los scripts de test de cada request.
> Solo editar las variables de credenciales (`user_*`) antes de empezar.

---

## 3. Flujo de prueba paso a paso

### Paso 0 — Verificar servidor

**Request:** `Health → GET /health`

**Verificar:** `200 OK` con body `{"status": "ok"}`.
Si falla, el contenedor Docker no está corriendo — no continuar.

---

### Paso 1 — Registrar usuario principal

**Request:** `Auth → POST /auth/register — registro exitoso`

**Body enviado (automático desde variables):**
```json
{
  "email": "{{user_email}}",
  "name": "{{user_name}}",
  "password": "{{user_password}}"
}
```

**Verificar:**
- Código `201 Created`.
- Body contiene `access_token` (JWT largo) y `profile_status: "new"`.
- La variable `access_token` del entorno se actualiza automáticamente.

**Errores esperables:**
- `409 EMAIL_ALREADY_EXISTS` → ese email ya fue registrado. Cambiar `user_email` o limpiar la base de datos.
- `400 WEAK_PASSWORD` → contraseña sin carácter especial o menor a 8 caracteres.

---

### Paso 2 — Login (opcional si ya hiciste register)

**Request:** `Auth → POST /auth/login — login exitoso`

**Cuándo ejecutarlo:** si el registro ya fue hecho en una sesión anterior, o si el token expiró.

**Verificar:**
- Código `200 OK` con `access_token`.
- Variable `access_token` actualizada.

---

### Paso 3 — Subir CSV de análisis

**Request:** `Analysis → POST /analysis/upload-file — CSV simple`

**Cómo adjuntar el archivo:**
1. Abrir el request → pestaña **Body** → **form-data**.
2. En la fila `file`, cambiar el tipo a **File** (menú desplegable al lado del key).
3. Click en **Select Files** → seleccionar `docs/postman/samples/sample_simple.csv`.
4. Los campos `lat`, `lon` y `tags` ya tienen valores por defecto.

**Verificar:**
- Código `200 OK`.
- Body contiene los tres campos de diagnóstico:
  - `verdict`: `"Fit"` o `"Unfit"`
  - `stress_level`: `"Low"`, `"Moderate"` o `"High"`
  - `traffic_light`: `"Green"`, `"Yellow"` o `"Red"`
- Variable `session_id` actualizada automáticamente.

**Errores esperables:**
- `401` sin body especial → `access_token` vacío o expirado. Hacer login de nuevo.
- `400 INVALID_BPM_RANGE` → el CSV tiene valores BPM fuera de [30, 220].
- `413 FILE_TOO_LARGE` → archivo excede 2 MB o 5 000 filas.
- `415 UNSUPPORTED_MEDIA_TYPE` → el campo `file` no fue configurado como tipo **File**.

---

### Paso 4 — Análisis con entrada manual (alternativa al CSV)

**Request:** `Analysis → POST /analysis/manual-input — serie JSON`

**Cuándo usarlo:** para verificar el análisis sin necesidad de un archivo.

**Verificar:** mismos campos que en el paso anterior (`verdict`, `stress_level`, `traffic_light`).
La variable `session_id` también se actualiza.

---

### Paso 5 — Historial de sesiones

**Request:** `History → GET /history/summary — paginado`

**Verificar:**
- Código `200 OK`.
- Array `sessions` con al menos una entrada (la creada en el paso 3 o 4).
- Cada sesión muestra `verdict`, `traffic_light`, `stress_level` y `tags`.

**Parámetros opcionales** (deshabilitados por defecto, activar según necesidad):
- `tags=Rain,Traffic` → filtrar por tags.
- `date_from` / `date_to` → filtrar por rango de fechas (`YYYY-MM-DD`).

---

### Paso 6 — Detalle de sesión

**Request:** `History → GET /history/{id}`

**Verificar:**
- Código `200 OK` con el detalle completo de la sesión (`session_id` del entorno).
- Si se activa el parámetro `?raw_data=true`, el body incluye los datos biométricos descifrados.

**Error esperable:**
- `404 SESSION_NOT_FOUND` → `session_id` en el entorno está vacío o es inválido. Volver al paso 3.

---

### Paso 7 — Estadísticas

Ejecutar los tres requests en orden:

| Request | Qué verificar |
|---|---|
| `Stats → GET /stats/trends?period=week` | Array `trends` con fechas y `avg_stress` |
| `Stats → GET /stats/trends?period=month` | Mismo formato, rango mensual |
| `Stats → GET /stats/distribution` | Objeto con porcentajes `Green`, `Yellow`, `Red` sumando ~100 |
| `Stats → GET /stats/correlations` | Array con condiciones climáticas y `avg_stress_level` asociado |

Todos deben retornar `200 OK`. Si `trends` está vacío, es porque solo hay una sesión registrada.

---

### Paso 8 — Perfil de usuario

**Request:** `User → GET /user/profile`

**Verificar:**
- `profile_status`: `"new"` (sin calibrar) o `"calibrating"` (tras calibrar).
- `session_count`: número de sesiones analizadas hasta ahora.

---

### Paso 9 — Calibrar BPM basal

**Request:** `User → PUT /user/profile/calibrate — BPM válido`

**Body:** `{"baseline_bpm": 68}` (rango válido: 30–220).

**Verificar:**
- `200 OK` con `baseline_bpm: 68` y `profile_status: "calibrating"`.

**También probar el caso inválido:**

**Request:** `User → PUT /user/profile/calibrate — BPM inválido (< 30)`

**Verificar:** `400 INVALID_BPM_RANGE`.

---

### Paso 10 — Tags

Ejecutar en orden:

1. `User → GET /user/tags` → `200 OK`, array de tags (puede estar vacío).
2. `User → POST /user/tags — crear tag` → `201 Created`, body con `id` y `name: "NightDrive"`. Variable `tag_id` actualizada.
3. `User → DELETE /user/tags/{id}` → `200 OK` con mensaje de confirmación.

Si `POST` devuelve `409 TAG_ALREADY_EXISTS`, cambiar el nombre del tag en el body del request.

---

### Paso 11 — Contactos de confianza

Ejecutar en orden:

1. `User → GET /user/contacts` → `200 OK`, array de contactos.
2. `User → POST /user/contacts — crear contacto` → `201 Created`. Variable `contact_id` actualizada.
3. `User → PUT /user/contacts/{id}` → `200 OK` con los datos actualizados.
4. `User → DELETE /user/contacts/{id}` → **`204 No Content` sin body** — esto es correcto, no es un error.

---

### Paso 12 — Enviar alerta

**Request:** `Alerts → POST /alerts/send — todos los contactos`

**Requiere:** `session_id` y al menos un contacto registrado (paso 11).

**Verificar:**
- `200 OK` → alerta enviada (SendGrid configurado).
- `202 Accepted` → alerta encolada para envío posterior.
- **`503 ALERT_SERVICE_UNAVAILABLE`** → SendGrid no configurado en el entorno de desarrollo. **Es el resultado esperado en local**, no es un error de tu código.
- `400 NO_CONTACTS_FOUND` → no hay contactos registrados. Ejecutar el paso 11 primero.

**También probar:** `Alerts → POST /alerts/send — contacto específico` con `contact_ids: ["{{contact_id}}"]`.

---

## 4. Pruebas de seguridad — IDOR

El IDOR (Insecure Direct Object Reference) verifica que user2 no puede acceder a datos de user1.
Ejecutar la carpeta **IDOR Tests** en este orden:

1. `POST /auth/register — user2` → crea user2 con `user_email_2`. Variable `access_token_user2` actualizada.
2. `POST /auth/login — user2` → renueva `access_token_user2` si ya existía.
3. `GET /history/{id} con token de user2` → intenta leer `session_id` de user1 con el token de user2.
   - **Esperado:** `404 SESSION_NOT_FOUND`.
   - Si devuelve `200`, hay una vulnerabilidad IDOR activa.
4. `DELETE /history/{id} con token de user2` → intenta borrar la sesión de user1.
   - **Esperado:** `404 SESSION_NOT_FOUND`.

---

## 5. Verificar endpoints protegidos sin token

Para confirmar que los endpoints retornan `401` sin autenticación:

1. Copiar cualquier request protegido (ej. `GET /history/summary`).
2. En la pestaña **Headers**, deshabilitar o eliminar la fila `Authorization`.
3. Enviar → **Verificar: `401 Unauthorized`**.

---

## 6. Interpretar los campos de diagnóstico

| Campo | Valores posibles | Significado |
|---|---|---|
| `verdict` | `"Fit"` / `"Unfit"` | Apto o no apto para conducir |
| `stress_level` | `"Low"` / `"Moderate"` / `"High"` | Nivel de estrés fisiológico detectado |
| `traffic_light` | `"Green"` / `"Yellow"` / `"Red"` | Semáforo de riesgo (verde=bajo, rojo=alto) |
| `confidence_score` | 0–100 | Confianza del modelo en el diagnóstico |
| `risk_score` | Decimal | Puntuación de riesgo interna del modelo |
| `weather_impact` | `null` o string | Influencia del clima si lat/lon fueron enviados |

La combinación esperada para un conductor descansado con BPM estable (~72–82):
`verdict: "Fit"`, `stress_level: "Low"`, `traffic_light: "Green"`.

---

## 7. Errores frecuentes y soluciones

| Código | `error_code` | Causa | Solución |
|---|---|---|---|
| `400` | `INVALID_BPM_RANGE` | BPM fuera de [30, 220] | Usar el CSV de muestra o serie JSON del request |
| `400` | `WEAK_PASSWORD` | Contraseña sin carácter especial | Asegurar que `user_password` incluya `@`, `!`, etc. |
| `400` | `NO_CONTACTS_FOUND` | Sin contactos al enviar alerta | Ejecutar paso 11 antes del paso 12 |
| `401` | — | Token ausente o expirado | Hacer login de nuevo (paso 2) |
| `404` | `SESSION_NOT_FOUND` | `session_id` vacío o de otro usuario | Ejecutar análisis de nuevo (paso 3) |
| `409` | `EMAIL_ALREADY_EXISTS` | Email ya registrado | Cambiar `user_email` o borrar el usuario de la base |
| `409` | `TAG_ALREADY_EXISTS` | Tag duplicado | Cambiar el nombre del tag en el body |
| `413` | `FILE_TOO_LARGE` | Archivo > 2 MB o > 5 000 filas | Usar `sample_simple.csv` incluido |
| `415` | `UNSUPPORTED_MEDIA_TYPE` | Campo `file` no configurado como tipo File | Cambiar el tipo en form-data de Text a File |
| `503` | `ALERT_SERVICE_UNAVAILABLE` | SendGrid no configurado | Normal en entorno local, no requiere acción |
