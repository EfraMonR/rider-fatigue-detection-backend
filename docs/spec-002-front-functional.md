# Especificaciones Funcionales: Módulo Frontend (Angular)
## Plan de Carretera y Descripción General del Proyecto: Sistema de Seguridad Vial Preventiva - Bloque 1


### Propósito del Documento
Este documento describe las especificaciones funcionales, recorridos de usuario, especificaciones UI/UX y casos de borde para el módulo frontend del sistema de seguridad vial preventiva. Se centra en definir *qué* debe ser la experiencia del usuario sin especificar *cómo* implementarlo técnicamente (lo cual queda para las Especificaciones Técnicas).


---


## 1. Visión General Alta Nivel


La aplicación es una **aplicación móvil multiplataforma** construida con **Ionic** que proporciona un panel para conductores para verificar su estado de aptitud para conducir. Aunque técnicamente es web (Ionic/Capacitor), está diseñada y optimizada para dispositivos móviles. Se integra con la API backend para mostrar análisis en tiempo real, contexto meteorológico y tendencias históricas.


**Modo Offline:** Al iniciar la app, el sistema detecta si hay conexión disponible. Si no hay red, la app entra automáticamente en **Modo Offline Limitado**, accesible **sin necesidad de autenticación**. En este modo el usuario puede ingresar datos manualmente o cargar un archivo, y el análisis se ejecuta localmente usando el modelo exportado (`.tflite`) mediante el módulo `LocalInferenceService`. El resultado offline no incluye contexto climático ni acceso a historial o perfil — solo el análisis local.


**Valor Central:** Empoderar a los conductores para tomar decisiones informadas sobre la entrada en la carretera, considerando factores fisiológicos y ambientales — incluso sin conexión a internet.


---


## 2. Especificaciones Funcionales (RF)


### **RF-001: Carga de Datos y Entrada Manual**
**Descripción:** Los usuarios deben poder cargar datos fisiológicos (CSV/JSON) o ingresarlos manualmente. El sistema detecta automáticamente si es una instalación nueva.


**Criterios de Éxito:**
-   Proporciona una zona para arrastrar y soltar para la carga de archivos.
-   Acepta formatos CSV y JSON (con validación del esquema).
-   Proporciona un formulario de entrada manual (BPM, timestamps, ubicación).
-   Muestra barras de progreso en tiempo real para grandes cargas.
-   **Modo Primer Arranque (Inicialización Automática):**
 - El usuario debe **registrarse e iniciar sesión primero**. No hay acceso a ninguna pantalla sin autenticación, **excepto `/offline-dashboard`**: si al arrancar la app no hay red y no hay sesión activa, la app redirige directamente a esa pantalla pública de análisis local (ver RF-008).
 - Al autenticarse por primera vez (`profile_status === 'new'`), el sistema redirige automáticamente a la **Pantalla de Bienvenida Inteligente** antes de mostrar el dashboard.
 - Esta pantalla instruye al usuario a cargar su primer archivo o ingresar datos manualmente para inicializar su perfil basal.
 - El dashboard completo queda bloqueado hasta que el usuario complete la carga inicial.
 - Muestra estados de carga durante el procesamiento del primer archivo de calibración.


**Casos de Borde:**
-   *Primer Archivo Cargado:* Inmediatamente después de la carga exitosa del primer archivo, mostrar mensaje: "¡Perfil basal actualizado! Ahora puedes comenzar tus viajes".
-   *Carga de Archivo Fallida:* Mostrar un mensaje de error claro con sugerencia para corregir el archivo (ej., "Formato inválido").
-   *Archivo Demasiado Grande:* Cuando el backend devuelve `413 FILE_TOO_LARGE`, ofrecer al usuario "Procesar este archivo localmente en tu dispositivo" (usa `LocalInferenceService` con `.tflite`). El usuario no necesita dividir el archivo si la app puede procesarlo offline.
-   *Error de Conexión:* Si no hay internet al intentar subir, redirigir a Modo Offline Limitado (RF-008). El análisis se ejecuta localmente con `.tflite` y devuelve resultado inmediato. La sincronización posterior del resultado pre-calculado hacia el backend queda en Backlog v1.x.


---


### **RF-002: Visualización de Resultados y Estados de Modelo**
**Descripción:** Mostrar la valoración de aptitud con indicadores de confianza y estado del sistema.


**Criterios de Éxito:**
- **Señal de Tráfico:** Indicador grande (`"Green"`/`"Yellow"`/`"Red"`) determinado **exclusivamente por el clúster fisiológico** detectado. Proviene del campo `traffic_light` de la respuesta.
- **Mensaje de Impacto Climático:** Sección secundaria independiente del semáforo que muestra el campo `weather_impact.message` cuando `severity` es distinto de `none`. Si el clima es normal (`null`), esta sección no se renderiza.
- **Puntuación de Confianza:** Mostrar el porcentaje de confianza del modelo (ej., "95% seguro"). Este valor proviene del campo `confidence_score` de la respuesta API, que es un **entero 0–100** (el backend almacena `FLOAT 0.0–1.0` internamente y lo convierte antes de enviarlo).
- **Estados de Modelo:**
 - *Cargando:* mientras la request síncrona al backend está pendiente, mostrar barra de progreso y mensaje "Analizando datos...". El backend no usa `202 Accepted` en MVP — el análisis online es siempre síncrono y devuelve `200 OK` con el resultado completo.
 - *Modelo No Disponible:* si el backend devuelve `503` con `error_code: MODEL_NOT_AVAILABLE`, mostrar "El servicio de análisis no está disponible temporalmente. Intentá nuevamente en unos minutos." y permitir reintento.
 - *Archivo Demasiado Grande:* si el backend devuelve `413` con `error_code: FILE_TOO_LARGE`, ofrecer al usuario procesar el archivo localmente (ver RF-008).
 - *Modo Offline:* si el análisis fue ejecutado localmente (vía `.tflite`), mostrar etiqueta "Resultado local — sin datos climáticos disponibles".
 - *Modo Degradado:* si la API del tiempo falla pero hay red, mostrar "Datos meteorológicos no disponibles".


**Casos de Borde:**
- *Baja Confianza:* Si confianza <80%, mostrar advertencia "Resultados preliminares. Vuelva a probar en breve".
- *Errores de Servidor:* El frontend es responsable de mapear el `error_code` devuelto por el backend (ej., `INVALID_FILE_FORMAT`) a un mensaje humano legible usando un diccionario de errores (i18n). Nunca mostrar el código crudo ni códigos HTTP al usuario final.


---


### **RF-003: Seguimiento Histórico**
**Descripción:** El sistema debe mostrar el historial de análisis y estadísticas agregadas.


**Criterios de Éxito:**
-   Muestra una lista paginada de análisis anteriores (fecha, valoración, resumen de `weather_impact` si aplica).
-   Permite filtrar por etiquetas (ej. "tráfico", "lluvia").
-   Muestra estadísticas agregadas (ej. "Promedio de estrés este mes: Moderate").


> **BACKLOG:** La generación y descarga de informes en PDF/Excel se omite de la implementación actual.


**Casos de Borde:**
-   *Sin Historial:* Mostrar un estado vacío con sugerencia para cargar datos.
-   *Historial Dañado:* Si un registro no puede cargarse, mostrar una notificación "No se pudo cargar".


---


### **RF-004: Gestión de Perfil del Usuario y Calibración**
**Descripción:** El sistema debe permitir gestionar el perfil fisiológico y mostrar indicadores de salud del modelo. En la primera sesión, el sistema **inicializa automáticamente** la línea base con el primer dato válido recibido.


**Criterios de Éxito:**
-   **Ritmo Basal Personalizado:**
 - En la primera sesión, mostrar el valor de `baseline_bpm` **calculado automáticamente** basado en el primer dato válido ingresado.
 - Habilitar su actualización posterior solo si se cumple el umbral de datos mínimos (5 sesiones de análisis completadas).
-   **Indicador de Calibración:**
 - Visualizar si la línea base está establecida. Si es la primera sesión, mostrar: "Calibrando línea base con sus datos actuales".
 - Una vez establecido, mostrar si la línea base está actualizada o si el sistema sugiere recalibración (ej. "¿Siente que su ritmo actual es diferente?").
-   **Historial de Perfil:** Mostrar fecha de incorporación y conteo de sesiones activas.
-   **Manejo de Valores:** Validar visualmente que el BPM esté en rango fisiológico (30-220) antes de guardar.


**Casos de Borde:**
-   *Primer Dato Válido:* Si el usuario ingresa sus primeros datos, el sistema acepta el BPM, calcula el promedio inicial y guarda el perfil. No pedir confirmación de "¿Desea establecer esta línea base?".
-   *Recalibración Necesaria:* Si la desviación del promedio reciente es >15% respecto a la línea base, mostrar un modal de confirmación.
-   *Guardado Fallback:* Si la API falla, mostrar advertencia "Modo Offline: Guardado local" y sincronizar al recuperar conexión.


---


### **RF-005: Alertas de Emergencia y Seguridad (Simplificado)**
**Descripción:** El sistema debe alertar sobre riesgos altos y gestionar contacto manual.


**Criterios de Éxito:**
- **Banner de Riesgo:** Mostrar banner rojo cuando el resultado del análisis tenga `traffic_light === 'Red'`. El valor `"Red"` representa exclusivamente el clúster fisiológico de estrés alto, calculado en el backend. No duplicar esa lógica en el frontend.
- **Contacto Manual:** Permitir ingresar/definir un "Contacto de Confianza" (Nombre, Email). Al activar alerta, preparar el mensaje pre-formateado para compartir vía **correo electrónico**.
- **Modo Degradado:** Si la geolocalización/API falla, mostrar mensaje "No hay puntos de descanso cercanos" en lugar de error en blanco.


**Casos de Borde:**
- *Sin Contacto:* Mostrar sugerencia "No tienes un contacto guardado. ¿Deseas agregar uno para emergencias?"
- *Fallo en Envío:* Si el email falla, mostrar mensaje "Intento de alerta fallido. Por favor, contacte manualmente a su contacto de confianza".


---


### **RF-006: Contexto de Evento y Etiquetado Manual**
**Descripción:** El sistema debe permitir anotar el contexto de la actividad para mejorar el análisis futuro.


**Criterios de Éxito:**
- **Lista de Etiquetas:** Mostrar botones/tokens rápidos para seleccionar etiquetas como "Trancón", "Lluvia", "Velocidad Alta", "Susto".
- **Filtrado por Etiquetas:** En la lista de historial, permitir filtrar por etiquetas seleccionadas (ej., mostrar solo sesiones con "Lluvia").
- **Persistencia:** Guardar la selección en la base de datos asociada a la sesión.


**Casos de Borde:**
- *Etiqueta Duplicada:* Si el usuario intenta crear una etiqueta que ya existe, pre-selectarla en lugar de crear duplicado o mostrar error.
- *Sin Conexión:* Si no hay internet, permitir seleccionar tags para guardarlos localmente y sincronizarlos al restablecer la conexión.


---


### **RF-007: Autenticación y Gestión de Sesión**
**Descripción:** El sistema debe gestionar el acceso mediante flujos claros de registro e inicio de sesión, con renovación automática de sesión.


**Criterios de Éxito:**
- **Pantalla de Login:** Formulario con campos email y contraseña. Botón "Iniciar sesión" y enlace a registro.
- **Pantalla de Registro:** Formulario con email, contraseña y confirmación de contraseña. Indicador visual de fortaleza de contraseña (mínimo 8 caracteres + carácter especial).
- **Persistencia de Sesión:** El access token se almacena en memoria (no en localStorage). El refresh token se gestiona vía httpOnly cookie para protección contra XSS.
- **Renovación Automática:** Cuando el access token expire, renovarlo silenciosamente usando el refresh token sin interrumpir al usuario.
- **Logout:** Limpiar tokens, invalidar refresh token en el servidor y redirigir a la pantalla de login.
- **Rutas Protegidas:** Cualquier ruta que no sea `/login` o `/register` redirige automáticamente a login si no hay sesión activa.


**Casos de Borde:**
- *Refresh token expirado durante el uso:* Redirigir a login con mensaje: "Tu sesión expiró. Por favor, volvé a ingresar."
- *Error de credenciales:* Mostrar "Email o contraseña incorrectos" sin especificar cuál de los dos es incorrecto.
- *Email ya registrado:* Mostrar "Este email ya está registrado. ¿Querés iniciar sesión?" con enlace al login.
- *Contraseña débil:* Mostrar indicador visual en tiempo real mientras el usuario tipea, antes de intentar enviar el formulario.
- *Sin conexión en login:* Mostrar "Sin conexión. Verificá tu internet e intentá de nuevo." No intentar autenticar offline.


---


### **RF-008: Modo Offline Limitado y Cola de Sincronización**
**Descripción:** Al iniciar la app sin conexión, el sistema entra en Modo Offline Limitado donde permite ingresar datos y calcular el resultado usando el modelo local. Los datos se sincronizan automáticamente al recuperar internet.


**Detección de Modo Offline:**
- Al abrir la app, el sistema verifica conectividad.
- Si no hay red: activar Modo Offline Limitado con aviso prominente al usuario.
- Si hay red: flujo normal con API backend.


**Criterios de Éxito:**
- **Modo Offline Limitado:** Permite al usuario ingresar datos manualmente (uno a uno) o cargar un archivo CSV. El análisis se ejecuta localmente usando el modelo `.tflite` vía `LocalInferenceService`.
- **Resultado Local:** El resultado offline incluye `traffic_light` y `stress_level` (calculados localmente), pero **no incluye `weather_impact`** — se informa al usuario con etiqueta: "Sin datos climáticos disponibles offline".
- **Cola de Pendientes:** Los resultados calculados offline se guardan en IndexedDB con estado `pending` para sincronizar con el backend al recuperar conexión.
- **Indicador Visual:** Badge persistente en el header con el conteo de registros pendientes.
- **Sincronización Automática:** Al recuperar conexión, la app drena la cola en orden cronológico, re-procesa con el backend (para obtener `weather_impact` y persistencia oficial) y notifica al usuario.
- **Confirmación de Sync:** Toast al sincronizar exitosamente: "X registros sincronizados correctamente."
- **Restricción para Archivos Grandes:** Para CSVs ≥ 1MB offline, mostrar: "Este archivo es demasiado grande para procesar sin conexión. Intentá subirlo cuando vuelva la conexión."


**Cadena de funcionamiento:**
```
App inicia
 ├─ Con red    → API backend (K-Means .pkl + clima real) → resultado completo
 └─ Sin red    → Modo Offline Limitado
                   ├─ LocalInferenceService (.tflite) → traffic_light + stress_level
                   ├─ Sin weather_impact (aviso al usuario)
                   └─ Guardar en cola → sincronizar al recuperar red
```


**Casos de Borde:**
- *Fallo en sincronización de un registro:* Marcarlo como `failed` en IndexedDB y mostrar: "No se pudo sincronizar 1 registro. Podés intentarlo manualmente." con botón de reintento.
- *Registros pendientes al abrir con red:* Mostrar badge y ofrecer "Sincronizar ahora" automáticamente.
- *Modelo .tflite no disponible (primera instalación sin red):* Mostrar mensaje: "Para usar el modo offline, necesitás conectarte al menos una vez para descargar el módulo de análisis local."


---


## 3. Especificaciones No Funcionales (NFR)


### **RNF-001: Accesibilidad (A11y)**
-   La interfaz debe cumplir con **WCAG 2.1 Nivel AA**:
  -   Modo de alto contraste (fondo blanco, texto negro).
  -   Compatibilidad con lectores de pantalla (etiquetas Aria).
  -   Soporte para navegación con teclado.


### **RNF-002: Consideraciones UX/UI**
-   **Modo de Alto Contraste:** Paleta predeterminada (texto oscuro, fondo brillante).
-   **Compatibilidad Glove-Friendly:** Objetos grandes de toque (mín. 48x48px), sin gestos finos de motor.
-   **Día/Noche:** Toggle para condiciones de conducción en bajo nivel de luz.
-   **Estados de Carga:** Pantallas esqueléticas para todos los datos asincrónicos.


### **RNF-003: Rendimiento**
-   Tiempo de carga < 2s en redes 3G.
-   Optimización de imágenes (formato WebP, carga diferida).


### **RNF-004: Soporte para Modo Sin Conexión**
-   Al iniciar la app sin red, activar automáticamente el Modo Offline Limitado (RF-008).
-   Caché de las últimas respuestas de `GET /history/summary`, `GET /user/profile` y `GET /stats/trends` para lectura offline.
-   Mostrar barra de estado amarilla en el header cuando la API no esté disponible.
-   El modelo `.tflite` debe descargarse y almacenarse localmente en la primera sesión con red para estar disponible offline en sesiones posteriores.


### **RNF-005: Requisitos de App Móvil (Ionic/Capacitor)**
-   La aplicación se construye con **Ionic** y está optimizada para dispositivos móviles (Android e iOS).
-   Aunque es tecnológicamente web, el comportamiento, navegación y UX deben ser nativos móviles.
-   Incluir `manifest.json` para soporte de instalación en Android (Chrome) y iOS (Safari 16.4+).
-   **HTTPS obligatorio** para comunicación con el backend.


### **RNF-006: Seguridad del Cliente**
-   El access token JWT no debe almacenarse en `localStorage` ni `sessionStorage` (vulnerable a XSS). Debe vivir en memoria de la aplicación.
-   El refresh token debe enviarse y recibirse únicamente via httpOnly cookie.
-   Implementar interceptor HTTP global en Angular para adjuntar el access token en cada request y manejar el flujo de renovación automática.


---


## 4. Contexto del Sistema y Recorridos de Usuario


### **J-001: Conductor Nuevo (Inicialización y Calibración)**
*Descripción: Flujos para usuarios que acceden por primera vez o tienen un perfil vacío.*
1.  **Registro:** Conductor completa el formulario de registro (email + contraseña). El sistema crea la cuenta y autentica automáticamente.
2.  **Bienvenida Inteligente:** Al detectar `profile_status === 'new'`, el sistema redirige automáticamente a la Pantalla de Bienvenida antes de cargar el dashboard. Instruye a cargar el primer archivo CSV o ingresar datos manuales. No se permite acceso al dashboard completo hasta completar la calibración.
3.  **Carga de Datos:** Conductor arrastra un archivo CSV o completa el formulario manual con BPM, timestamp y ubicación.
4.  **Validación Inicial:** El sistema valida el esquema del archivo. Si el archivo es muy grande (>5MB), muestra advertencia para dividir; si es inválido, muestra error amigable.
5.  **Calibración Automática:** Al guardar el primer dato válido, el sistema calcula automáticamente la línea base (`baseline_bpm`) y guarda el perfil basal.
6.  **Confirmación:** El sistema muestra mensaje: "¡Perfil basal actualizado! Ahora puedes comenzar tus viajes" y habilita la navegación al Dashboard.
7.  **Dashboard Preliminar:** El usuario ve el Dashboard con indicación de "Datos Preliminares" hasta que se completen el umbral de sesiones (ej., 5 sesiones) para considerar el perfil "Estable".


### **J-002: Chequeo Diario (Uso Estándar)**
*Descripción: Flujo para usuarios con perfil calibrado y estable.*
1.  **Inicio de Sesión:** Conductor ingresa su identificador (o accede desde su dispositivo guardado). El sistema valida credenciales.
2.  **Visualización de Estado:** El sistema muestra el último análisis del día anterior, el ritmo cardíaco actual y las condiciones meteorológicas actuales.
3.  **Indicador de Calibración:** Si el perfil no está "Estable" (`session_count < 5`), mostrar advertencia suave: "Sus recomendaciones son preliminares". Si está "Estable", mostrar confianza total.
4.  **Revisión y Decisión:** Conductor revisa las recomendaciones (descansar vs. conducir). El sistema sugiere rutas o pausas seguras basadas en la línea base y el clima.
5.  **Registro de Sesión:** Conductor marca inicio de viaje o actualiza datos en tiempo real durante la conducción.


### **J-003: Alerta de Emergencia**
*Descripción: Flujo crítico cuando el sistema detecta riesgo combinado (estrés + clima).*
1.  **Detección de Riesgo:** El sistema detecta un clúster fisiológico de estrés alto (`traffic_light: "Red"`). Si además hay condiciones meteorológicas severas, se muestra el campo `weather_impact` como contexto adicional, pero no es condición para activar la alerta.
2.  **Activación de Alerta:** El sistema activa alertas visuales, sonidos y vibraciones inmediatas. Muestra una tarjeta de "ALERTA DE RIESGO CRÍTICO".
3.  **Gestión del Conductor:** El sistema sugiere puntos de estacionamiento seguros cercanos y detiene la navegación de rutas peligrosas.
4.  **Compartir Estado:** Conductor activa el botón "Pedir Ayuda". El sistema prepara un mensaje con ubicación, estado fisiológico y clima para enviar a contactos de confianza o servicios de emergencia.
5.  **Modo Offline (Si aplica):** Si no hay conexión, el sistema guarda el evento localmente y muestra mensaje: "Ayuda enviada cuando se recupere la conexión".


---


### **Notas de Implementación para los Recorridos:**
-   **J-001:** Debe detenerse inmediatamente si el usuario intenta navegar a secciones bloqueadas (ej., cambiar línea base manualmente) hasta completar la calibración inicial.
-   **J-002:** Debe mostrar el estado de la línea base (Estable/Preliminar) de manera prominente en el encabezado del dashboard.
-   **J-003:** Priorizar el envío de datos incluso si la conexión es intermitente; los datos deben encolarse primero.
---


## 5. Casos de Borde y Manejo de Errores (Perspectiva del Usuario)


| Escenario | Comportamiento Esperado |
| :--- | :--- |
| **Primer Arranque del Sistema** | Al abrir la app por primera vez (o base de datos vacía), mostrar la **Pantalla de Bienvenida Inteligente** que instruye a cargar el primer archivo o ingresar datos manuales para inicializar la línea base. No permitir navegación completa hasta completar este perfil inicial. |
| **Carga de Archivo Fallida (Backend)** | Mostrar mensaje humano (ej., "Formato inválido" en lugar de "422 Error"). Verificar sugerencia de división de archivos para >5MB. |
| **Modelo No Disponible** | Si el backend devuelve `503` con `MODEL_NOT_AVAILABLE`, mostrar "Servicio de análisis no disponible. Reintentar en unos minutos." En modo offline este caso no aplica (usa `.tflite` local). |
| **Archivo Demasiado Grande (Online)** | Si el backend devuelve `413 FILE_TOO_LARGE`, ofrecer "Procesar este archivo localmente en tu dispositivo" usando `LocalInferenceService` (ver RF-008). |
| **Tiempo Meteorológico No Disponible** | Mostrar datos cacheados con etiqueta de advertencia "Dato antiguo" o "Modo sin conexión" en lugar de pantalla en blanco. |
| **Etiqueta Duplicada** | Seleccionar automáticamente la etiqueta existente o permitir renombrado rápido. |
| **Recalibración de Perfil** | Si el BPM actual difiere mucho de la línea base, mostrar modal de confirmación con gráfico de tendencia. |
| **Alerta de Emergencia (Sin Conexión)** | Mostrar datos del contacto de confianza para que el usuario contacte manualmente. El envío de email se encola para cuando vuelva la conexión. |
| **Datos Corruptos (CSV)** | Mostrar mensaje específico de error de parseo (ej., "Faltan columnas en fila 10") en lugar de genérico. |
| **Guardar Sin Conexión** | Si la API no responde, guardar los datos localmente y mostrar notificación "Guardado en caché". Sincronizar automáticamente al recuperar internet. |
| **Modo Degradado (API Fallida)** | Si el backend está caído, mostrar mensaje: "El sistema está en modo seguro. Por favor, inténtelo más tarde" en lugar de errores técnicos. |
| **Navegación con Teclado** | Permitir acceder a todas las funciones de la aplicación usando solo el teclado (Tab, Enter, Flechas) cumpliendo con WCAG. |


### Notas de implementación:
- **Primer Arranque:** El frontend debe detectar `profile_status === 'new'` (campo del JWT/perfil de usuario) y redirigir a la pantalla de onboarding antes de cargar el dashboard.
- **Mensaje de Error:** Evitar mostrar códigos HTTP (4xx/5xx) al usuario final; siempre traducir a lenguaje natural.
- **Offline-First:** Priorizar la persistencia de datos antes que el éxito inmediato de la petición API.


---


## 6. Definición de Terminos y Guía de Estilo de la Interfaz


Para garantizar una consistencia en la implementación, se definen los siguientes estados y términos clave:


### **6.1 Estados de Usuario y Sistema**
| Término | Definición Técnica (Backend) | Interpretación para UI (Frontend) | Acción del Sistema |
| :--- | :--- | :--- | :--- |
| **Nuevo Usuario** | Usuario registrado pero sin `baseline_bpm` ni historial de datos. | La primera vez que ve la app, debe ver la pantalla de onboarding. | Redirigir inmediatamente al flujo de calibración o bienvenida. |
| **Calibrando** | El sistema ha recibido datos pero no ha establecido una línea base estable (ej. < 5 sesiones). | Mostrar indicador de progreso: "Estableciendo su perfil. Los resultados son preliminares". | Deshabilitar alertas de emergencia falsas; advertir sobre la inestabilidad de los datos. |
| **Perfil Estable** | El sistema ha detectado una desviación <10% en los últimos 7 días. | Muestra el dashboard completo con todas las métricas. | Habilitar todas las funcionalidades estándar. |
| **Modo Offline** | Sin conexión detectada al iniciar la app. | Activar Modo Offline Limitado. Mostrar barra amarilla en la cabecera con mensaje "Sin conexión — Modo offline activo". | Permitir ingreso de datos y análisis local con `.tflite`. Guardar resultados en cola para sincronizar al recuperar red. |
| **Datos No Disponibles** | Falta conexión o error de tiempo meteorológico. | Mostrar datos cacheados con etiqueta "Última vez: [Fecha]". | No lanzar alertas en falso; usar datos históricos para estimar riesgos. |


### **6.2 Guía de Estilo para Errores**
-   **Errores Técnicos:** Nunca mostrar códigos HTTP (ej., "500 Internal Server Error").
-   **Errores de Usuario:** Mostrar mensajes accionables (ej., "Formato inválido. Verifique que las columnas estén en el orden correcto").
-   **Errores de Red:** Mostrar mensajes de "Modo Offline" o "Conexión perdida" que permitan al usuario intentar de nuevo sin pánico.
-   **Errores de Calibración:** Si el sistema detecta datos erróneos, mostrar: "Dato atípico detectado. ¿Desea corregirlo o recalibrar su línea base?".


### **6.3 Nomenclatura de Pantallas**
| Pantalla | Contexto de Uso | Elementos Clave |
| :--- | :--- | :--- |
| **Bienvenida Inteligente** | `profile_status === 'new'` | Botón "Cargar Archivo", Formulario Manual, Gráfico de Ejemplo. |
| **Dashboard Principal** | `profile_status === 'calibrating'` o `'stable'` | Gráficos de BPM, Mapa de Riesgos, Resumen del Día. |
| **Pantalla de Emergencia** | `alert_triggered == true` | Botón de Pánico, Ubicación GPS, Email del Contacto de Confianza. |
| **Historial de Sesiones** | `view_history == true` | Filtros por etiquetas, Gráficos de Tendencia. |