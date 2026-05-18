---
name: project-backlog
description: Items de backlog del proyecto — decisiones congeladas y mejoras pendientes para versiones futuras
metadata:
  type: project
---

## [ML-001] Modelo K-Means 1D → 5 features (congelado)

El modelo actual `pipeline_fatiga_1D_v1.pkl` usa solo `bpm_mean` como feature.
El diseño original contemplaba 5: `bpm_mean`, `bpm_std`, `bpm_p25`, `bpm_p75`, `bpm_max`.

**Why:** El paper académico fue redactado sobre el modelo 1D. Cambiar el modelo invalida los resultados publicados.

**How to apply:** No modificar `inference_engine.py` ni el modelo sin un ciclo formal de reentrenamiento y actualización del paper. Cuando se retome, solo hay que: reentrenar, renombrar el artefacto a `pipeline_fatiga_5D_v1.pkl`, actualizar `_compute_features` para pasar 5 features, y cambiar `MODEL_PATH` en `.env`. La API no cambia.

Documentado en: `docs/BACKLOG.md` y `docs/plan-001.md` sección 3.4.

## [SEC-001] Rotación KEK/DEK para cifrado biométrico

Columna `users.encryption_key` reservada en el schema para evolución futura a clave por usuario.
**Why:** Actualmente hay una única clave maestra (`BIOMETRIC_KEY`). Para producción real se necesita aislamiento por usuario.

## [FEAT-001] Reportes PDF/Excel

Generación de reportes del historial excluida del alcance actual.
