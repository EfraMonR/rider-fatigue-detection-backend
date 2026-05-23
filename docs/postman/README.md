# Postman — Rider Fatigue Detection API

## Importar colección y entorno

1. Abrir Postman → **File → Import**.
2. Seleccionar `rider-fatigue-detection.postman_collection.json`.
3. Repetir con `rider-fatigue-detection.postman_environment.json`.
4. En la esquina superior derecha de Postman, seleccionar el entorno **"Rider Fatigue Detection — Local"**.

## Configurar variables antes de correr

Editar el entorno (ícono del ojo → Edit) y completar los valores:

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `base_url` | URL del servidor | `http://localhost:8000` |
| `user_email` | Email del usuario principal | `rider1@example.com` |
| `user_password` | Contraseña (≥8 chars, 1 especial) | `SecurePass@1` |
| `user_email_2` | Email del segundo usuario (IDOR) | `rider2@example.com` |
| `user_password_2` | Contraseña del segundo usuario | `SecurePass@2` |

Las variables `access_token`, `session_id`, `contact_id`, `tag_id` y `access_token_user2` se llenan automáticamente por los scripts de los requests.

## Orden de ejecución manual

Ejecutar los requests en este orden para que las variables automáticas estén disponibles:

1. `Auth → POST /auth/register` — crea el usuario
2. `Auth → POST /auth/login` — obtiene el token
3. `Analysis → POST /analysis/upload-file` — sube el CSV, guarda `session_id`
4. `Analysis → POST /analysis/manual-input` — alternativa a upload
5. `History → GET /history/summary` — lista sesiones
6. `History → GET /history/{id}` — detalle de la sesión guardada
7. `Stats → GET /stats/trends`, `distribution`, `correlations`
8. `User → GET /user/profile`
9. `User → PUT /user/profile/calibrate`
10. `User → GET/POST/DELETE /user/tags`
11. `User → GET/POST/PUT/DELETE /user/contacts`
12. `Alerts → POST /alerts/send`

## Usar el Collection Runner (flujo completo)

1. En Postman, hacer clic en los tres puntos junto a la colección → **Run collection**.
2. Seleccionar todos los requests o solo los de la carpeta deseada.
3. Asegurarse de que el entorno **"Rider Fatigue Detection — Local"** esté seleccionado.
4. Hacer clic en **Run Rider Fatigue Detection API**.

El runner ejecuta los requests en orden. Los scripts `test` transfieren `access_token` y `session_id` entre requests automáticamente.

## Scripts automáticos

### Login y Register
Tras una respuesta exitosa, el script guarda `access_token` en la variable de entorno:

```javascript
const res = pm.response.json();
if (res.access_token) {
  pm.environment.set('access_token', res.access_token);
}
```

Todos los requests protegidos usan `Authorization: Bearer {{access_token}}` en el header.

### Upload-file y Manual-input
Tras un análisis exitoso, el script guarda `session_id`:

```javascript
const res = pm.response.json();
if (res.session_id) {
  pm.environment.set('session_id', res.session_id);
}
```

Los requests `GET /history/{{session_id}}` y `POST /alerts/send` usan este valor automáticamente.

## Pruebas de IDOR

La carpeta **IDOR Tests** verifica que un usuario no puede acceder a datos de otro:

1. Ejecutar `POST /auth/register — user2` con `user_email_2` / `user_password_2`.
2. Ejecutar `POST /auth/login — user2` → guarda `access_token_user2`.
3. Ejecutar `GET /history/{id} con token de user2` — usa `session_id` de user1 con el token de user2.
4. Verificar que la respuesta es **404 SESSION_NOT_FOUND**.
5. Ejecutar `DELETE /history/{id} con token de user2` — mismo resultado esperado.

Si alguna de estas respuestas devuelve 200 en lugar de 404, hay una vulnerabilidad IDOR.

## Usar los CSVs de ejemplo en upload

Los archivos de muestra están en `docs/postman/samples/`.

### En Postman (manual)

1. Abrir `Analysis → POST /analysis/upload-file`.
2. En la pestaña **Body**, seleccionar **form-data**.
3. En la fila `file`, cambiar el tipo a **File** (menú desplegable al lado del key).
4. Hacer clic en **Select Files** y seleccionar:
   - `sample_simple.csv` para el formato simple (`timestamp,bpm`)
   - `sample_apple_health.csv` para el formato Apple Health

### Formatos aceptados

**CSV simple** (`sample_simple.csv`):
```
timestamp,bpm
2026-05-15T10:00:00,72
```

**CSV Apple Health** (`sample_apple_health.csv`):
```
timestamp,type,value,unit,sourceName,sourceVersion
2026-05-15T10:00:00,HKQuantityTypeIdentifierHeartRate,72,count/min,Apple Watch,9.0
```

El ETL del backend detecta el formato automáticamente. Las filas con `type` distinto de `HKQuantityTypeIdentifierHeartRate` se descartan silenciosamente en el formato Apple Health.

## Códigos de error frecuentes

| HTTP | `error_code` | Causa |
|------|-------------|-------|
| 400 | `INVALID_BPM_RANGE` | BPM < 30 o > 220 |
| 400 | `WEAK_PASSWORD` | Contraseña insuficiente |
| 401 | `INVALID_CREDENTIALS` | Email o password incorrecto |
| 404 | `SESSION_NOT_FOUND` | Sesión de otro usuario o inexistente |
| 409 | `EMAIL_ALREADY_EXISTS` | Email ya registrado |
| 413 | `FILE_TOO_LARGE` | Archivo > 2 MB o > 5 000 filas |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | Formato de archivo no soportado |
