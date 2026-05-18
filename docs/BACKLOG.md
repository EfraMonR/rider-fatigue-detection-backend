# Backlog

Items fuera del alcance actual, documentados para retomar en versiones futuras.

---

## [ML-001] Mejorar modelo K-Means a 5 features

**Prioridad:** Media  
**Versión objetivo:** v2

**Descripción:**  
El modelo actual (`pipeline_fatiga_1D_v1.pkl`) es un `Pipeline(StandardScaler + KMeans)` entrenado con 1 sola feature (`bpm_mean`). El diseño técnico original contemplaba 5 features:

| Feature | Descripción |
|---|---|
| `bpm_mean` | Media de BPM de la sesión |
| `bpm_std` | Desviación estándar |
| `bpm_p25` | Percentil 25 |
| `bpm_p75` | Percentil 75 |
| `bpm_max` | Máximo |

**Motivo del congelamiento:**  
El paper académico fue redactado sobre la base del modelo 1D. Cambiar el modelo invalida los resultados ya publicados. La decisión es mantener el modelo actual hasta que exista una nueva versión del paper o un ciclo de reentrenamiento formal.

**Qué se necesita para implementarlo:**  
1. Reentrenar el modelo con las 5 features sobre el mismo dataset.
2. Guardar el artefacto como `pipeline_fatiga_5D_v1.pkl`.
3. Actualizar `_compute_features` en `app/models_ai/inference_engine.py` para calcular y pasar `[[bpm_mean, bpm_std, bpm_p25, bpm_p75, bpm_max]]`.
4. Actualizar `MODEL_PATH` en `.env`.
5. Las variables `KMEANS_SCALER_MEAN` y `KMEANS_SCALER_STD` del `.env` dejan de usarse (el Pipeline incluye el scaler internamente).
6. No hay cambios en la API — el contrato de entrada/salida es idéntico.

---

## [SEC-001] Rotación de clave maestra biométrica (KEK/DEK)

**Prioridad:** Baja  
**Versión objetivo:** v3

**Descripción:**  
El cifrado AES-256-GCM actual usa una única clave maestra (`BIOMETRIC_KEY`). La columna `users.encryption_key` del schema está reservada para evolucionar a un esquema KEK/DEK donde cada usuario tenga su propia clave de datos cifrada con la clave maestra.

---

## [FEAT-001] Generación de reportes PDF/Excel

**Prioridad:** Baja  
**Versión objetivo:** v3

**Descripción:**  
Generación y descarga de reportes del historial de sesiones en formato PDF o Excel. Excluido del alcance actual por complejidad y bajo impacto en el prototipo.
