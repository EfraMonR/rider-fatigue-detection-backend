# Especificación Técnica: Módulo Frontend (Ionic — Mobile First)


## 1. Introducción
Este documento define la implementación técnica del módulo frontend del Sistema de Seguridad Vial Preventiva, basado en los requisitos funcionales de `spec-001-front-functional.md`. La app está construida con **Ionic** y aunque es tecnológicamente web (Capacitor), está diseñada y optimizada exclusivamente para dispositivos móviles (Android e iOS).


**Modo Offline:** Al iniciar la app, el sistema detecta conectividad. Sin red, activa el Modo Offline Limitado donde el análisis se ejecuta localmente usando el modelo `.tflite` vía `@tensorflow/tfjs-tflite` (WebAssembly). El modelo `.tflite` se descarga y almacena en la primera sesión con red.


---


## 2. Stack Tecnológico


| Capa | Tecnología | Justificación |
|---|---|---|
| Framework | Ionic 7+ (Angular) | Mobile-first, componentes nativos iOS/Android, web-based |
| Plataforma | Capacitor 5+ | Bridge nativo para Android/iOS; acceso a sensores y filesystem |
| HTTP | `Angular HttpClient` + interceptores | Manejo centralizado de auth y errores |
| Formularios | `Reactive Forms` | Validación en tiempo real (contraseña, BPM) |
| IndexedDB | `idb` (v8+) | Wrapper tipado y Promise-based sobre la API nativa |
| Gráficas | `ng2-charts` + `Chart.js` | Visualización de series de BPM y tendencias |
| Estado | `BehaviorSubject` + Signals (Angular 16) | Sin overhead de NgRx para este scope |
| Modelo offline | `@tensorflow/tfjs-tflite` | Ejecuta `.tflite` vía WebAssembly en el dispositivo |
| Estilos | SCSS + CSS Variables + Ionic Components | Soporte para modo día/noche, alto contraste, mobile UX |
| Build | Ionic CLI + Capacitor build | Genera APK (Android) e IPA (iOS) desde la misma base de código |


---


## 3. Estructura del Proyecto


```
src/
├── main.ts                          # Bootstrap standalone
├── app/
│   ├── app.config.ts                # provideRouter, provideHttpClient, SW
│   ├── app.routes.ts                # Definición de rutas raíz
│   │
│   ├── core/                        # Servicios y lógica transversal (singleton)
│   │   ├── auth/
│   │   │   ├── auth.service.ts      # Token en memoria, login, logout, refresh
│   │   │   └── auth.guard.ts        # Protección de rutas privadas
│   │   ├── http/
│   │   │   ├── api.service.ts       # Wrapper de HttpClient (base URL, headers)
│   │   │   └── auth.interceptor.ts  # Inyecta Bearer token + maneja 401
│   │   ├── offline/
│   │   │   ├── sync-queue.service.ts  # CRUD sobre IndexedDB (cola offline)
│   │   │   └── network-status.service.ts  # Online/offline detection
│   │   └── errors/
│   │       └── error-dictionary.ts  # Mapeo error_code → mensaje humano
│   │
│   ├── features/                    # Módulos de funcionalidades (lazy-loaded)
│   │   ├── auth/
│   │   │   ├── login/
│   │   │   │   ├── login.component.ts
│   │   │   │   └── login.component.html
│   │   │   └── register/
│   │   │       ├── register.component.ts
│   │   │       └── register.component.html
│   │   ├── offline/                 # RF-008: Modo Offline Limitado (sin auth requerida)
│   │   │   └── offline-dashboard.component.ts  # Entrada de datos + LocalInferenceService
│   │   ├── onboarding/              # J-001: Bienvenida Inteligente
│   │   │   └── onboarding.component.ts
│   │   ├── dashboard/               # J-002: Chequeo diario
│   │   │   ├── dashboard.component.ts
│   │   │   ├── traffic-light/
│   │   │   │   └── traffic-light.component.ts
│   │   │   └── weather-summary/
│   │   │       └── weather-summary.component.ts
│   │   ├── upload/                  # RF-001: Carga de datos
│   │   │   ├── upload.component.ts
│   │   │   ├── dropzone/
│   │   │   │   └── dropzone.component.ts
│   │   │   └── manual-form/
│   │   │       └── manual-form.component.ts
│   │   ├── analysis/                # RF-002: Visualización de resultados
│   │   │   ├── result-card/
│   │   │   │   └── result-card.component.ts
│   │   │   └── column-selector/     # Selector cuando ETL no detecta columna
│   │   │       └── column-selector.component.ts
│   │   ├── history/                 # RF-003: Historial e informes
│   │   │   ├── history-list/
│   │   │   │   └── history-list.component.ts
│   │   │   └── history-detail/
│   │   │       └── history-detail.component.ts
│   │   ├── profile/                 # RF-004: Perfil y calibración
│   │   │   └── profile.component.ts
│   │   ├── alerts/                  # RF-005: Alertas de emergencia
│   │   │   ├── alert-banner/
│   │   │   │   └── alert-banner.component.ts
│   │   │   └── emergency-screen/
│   │   │       └── emergency-screen.component.ts
│   │   └── tags/                    # RF-006: Etiquetado
│   │       └── tag-selector/
│   │           └── tag-selector.component.ts
│   │
│   └── shared/                      # Componentes y pipes reutilizables
│       ├── components/
│       │   ├── skeleton-loader/
│       │   ├── toast-notification/
│       │   ├── offline-banner/
│       │   └── pending-badge/
│       └── pipes/
│           └── error-message.pipe.ts  # error_code → texto humano
│
├── assets/
│   ├── icons/
│   │   ├── icon-192x192.png
│   │   └── icon-512x512.png
│   └── models/
│       ├── modelo.tflite            # Modelo K-Means exportado para inferencia offline
│       └── scaler_params.json       # Media y std del scaler (KMEANS_SCALER_MEAN/STD)
│
└── manifest.webmanifest             # Configuración para instalación en Android/iOS
```


---


## 4. Configuración Ionic / Capacitor


### 4.1 manifest.webmanifest


```json
{
 "name": "Sistema de Seguridad Vial Preventiva",
 "short_name": "SegVial",
 "description": "Evaluá tu aptitud para conducir antes de salir.",
 "start_url": "/dashboard",
 "display": "standalone",
 "background_color": "#ffffff",
 "theme_color": "#1a73e8",
 "orientation": "portrait-primary",
 "icons": [
   {
     "src": "assets/icons/icon-192x192.png",
     "sizes": "192x192",
     "type": "image/png",
     "purpose": "maskable any"
   },
   {
     "src": "assets/icons/icon-512x512.png",
     "sizes": "512x512",
     "type": "image/png",
     "purpose": "maskable any"
   }
 ]
}
```


### 4.2 Detección de conectividad al inicio


Al inicializar la app (`AppComponent.ngOnInit`), el `NetworkStatusService` evalúa `navigator.onLine`:


```typescript
// app.component.ts
async ngOnInit(): Promise<void> {
 const isOnline = await this.networkStatus.checkInitialConnectivity();
 if (!isOnline) {
   await this.localInference.loadModel(); // carga modelo.tflite
   this.offlineMode.set(true);
   this.router.navigate(['/offline-dashboard']);
 }
}
```


**Cadena de inicialización:**
```
App inicia
 ├─ navigator.onLine === true  → flujo normal (API backend)
 └─ navigator.onLine === false
       ├─ LocalInferenceService.loadModel() carga modelo.tflite desde assets/
       ├─ offlineMode signal = true
       └─ Redirect a /offline-dashboard (entrada de datos + resultado local)
```


### 4.3 Descarga y persistencia del modelo .tflite


En la primera sesión con red, el modelo se descarga desde el backend y se almacena en Capacitor Filesystem:


```typescript
// local-inference.service.ts
async ensureModelDownloaded(): Promise<void> {
 const exists = await Filesystem.stat({ path: 'modelo.tflite', directory: Directory.Data })
   .then(() => true).catch(() => false);
 if (!exists) {
   const response = await fetch(`${environment.apiUrl}/assets/modelo.tflite`);
   const buffer = await response.arrayBuffer();
   await Filesystem.writeFile({
     path: 'modelo.tflite',
     data: new Uint8Array(buffer),
     directory: Directory.Data
   });
 }
}
```


---


## 5. Routing y Guards


### 5.1 Definición de rutas (`app.routes.ts`)


```typescript
export const routes: Routes = [
 // Rutas públicas (no requieren sesión)
 { path: 'login',             loadComponent: () => import('./features/auth/login/login.component') },
 { path: 'register',          loadComponent: () => import('./features/auth/register/register.component') },
 { path: 'offline-dashboard', loadComponent: () => import('./features/offline/offline-dashboard.component') },


 // Rutas protegidas (requieren sesión activa)
 {
   path: '',
   canActivate: [AuthGuard],
   children: [
     { path: 'onboarding', loadComponent: () => import('./features/onboarding/onboarding.component') },
     { path: 'dashboard',  loadComponent: () => import('./features/dashboard/dashboard.component') },
     { path: 'upload',     loadComponent: () => import('./features/upload/upload.component') },
     { path: 'history',    loadComponent: () => import('./features/history/history-list/history-list.component') },
     { path: 'history/:id',loadComponent: () => import('./features/history/history-detail/history-detail.component') },
     { path: 'profile',    loadComponent: () => import('./features/profile/profile.component') },
     { path: 'alerts',     loadComponent: () => import('./features/alerts/emergency-screen/emergency-screen.component') },
     { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
   ]
 },
 { path: '**', redirectTo: 'dashboard' }
];
```


### 5.2 AuthGuard


```typescript
export const AuthGuard: CanActivateFn = (route, state) => {
 const auth = inject(AuthService);
 const router = inject(Router);
 const network = inject(NetworkStatusService);


 // Sin red y sin sesión: redirigir a modo offline (accesible sin auth — opción B)
 if (!network.isOnline() && !auth.isAuthenticated()) {
   return router.createUrlTree(['/offline-dashboard']);
 }


 if (auth.isAuthenticated()) {
   // Redirigir a onboarding si el perfil es 'new'
   if (auth.profileStatus() === 'new' && state.url !== '/onboarding') {
     return router.createUrlTree(['/onboarding']);
   }
   return true;
 }


 return router.createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
};
```


**Regla de navegación según estado de sesión y conectividad:**


| Condición | Ruta permitida | Redirección automática |
|---|---|---|
| Sin red + sin sesión | Solo `/offline-dashboard` | Cualquier ruta protegida → `/offline-dashboard` |
| Sin red + con sesión | `/offline-dashboard` + rutas protegidas (sin historial/perfil en tiempo real) | — |
| Con red + sin sesión | `/login`, `/register` | Rutas protegidas → `/login` |
| Con red + `profile_status: new` | Solo `/onboarding` | Cualquier ruta protegida → `/onboarding` |
| Con red + `profile_status: calibrating` | Todas | Banner "Datos Preliminares" visible |
| Con red + `profile_status: stable` | Todas | Sin restricciones |


> **Nota:** `/offline-dashboard` expone únicamente entrada de datos y análisis local. No muestra historial, perfil ni estadísticas — esos requieren sesión y conexión.


---


## 6. Servicios Transversales


### 6.1 AuthService (`core/auth/auth.service.ts`)


Gestiona el ciclo de vida del access token en memoria y el refresh token via cookie httpOnly.


```typescript
@Injectable({ providedIn: 'root' })
export class AuthService {
 private accessToken = signal<string | null>(null);
 private _profileStatus = signal<'new' | 'calibrating' | 'stable'>('new');


 isAuthenticated(): boolean {
   return this.accessToken() !== null;
 }


 profileStatus() {
   return this._profileStatus();
 }


 async login(email: string, password: string): Promise<void> {
   // POST /auth/login → body: { access_token, profile_status, session_count }
   //                  → cookie: refresh_token (httpOnly, Secure)
   const res = await firstValueFrom(this.http.post<AuthResponse>('/auth/login', { email, password }));
   this.accessToken.set(res.access_token);
   this._profileStatus.set(res.profile_status);  // 'new' | 'calibrating' | 'stable'
   // session_count disponible en res.session_count si se necesita en otros componentes
 }


 async refresh(): Promise<boolean> {
   // POST /auth/refresh → usa cookie httpOnly automáticamente
   // Retorna true si renovó exitosamente, false si el refresh expiró
   try {
     const res = await firstValueFrom(this.http.post<AuthResponse>('/auth/refresh', {}));
     this.accessToken.set(res.access_token);
     return true;
   } catch {
     this.accessToken.set(null);
     return false;
   }
 }


 async logout(): Promise<void> {
   await firstValueFrom(this.http.post('/auth/logout', {}));
   this.accessToken.set(null);
 }


 getToken(): string | null {
   return this.accessToken();
 }
}
```


### 6.2 AuthInterceptor (`core/http/auth.interceptor.ts`)


Inyecta el Bearer token en cada request y maneja la renovación automática ante un `401`.


```typescript
export const authInterceptor: HttpInterceptorFn = (req, next) => {
 const auth = inject(AuthService);
 const router = inject(Router);


 const token = auth.getToken();
 const authReq = token
   ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
   : req;


 return next(authReq).pipe(
   catchError(async (error: HttpErrorResponse) => {
     if (error.status === 401 && !req.url.includes('/auth/')) {
       const refreshed = await auth.refresh();
       if (refreshed) {
         // Reintentar el request original con el nuevo token
         const retryReq = req.clone({
           setHeaders: { Authorization: `Bearer ${auth.getToken()}` }
         });
         return firstValueFrom(next(retryReq));
       } else {
         router.navigate(['/login']);
       }
     }
     throw error;
   })
 );
};
```


### 6.3 ErrorDictionary (`core/errors/error-dictionary.ts`)


Mapeo centralizado de `error_code` del backend a mensajes en español para el usuario.


```typescript
export const ERROR_MESSAGES: Record<string, string> = {
 // Auth
 INVALID_CREDENTIALS:      'Email o contraseña incorrectos.',
 TOKEN_EXPIRED:            'Tu sesión expiró. Renovando...',
 REFRESH_TOKEN_INVALID:    'Tu sesión expiró. Por favor, volvé a ingresar.',
 EMAIL_ALREADY_EXISTS:     'Este email ya está registrado.',
 WEAK_PASSWORD:            'La contraseña debe tener al menos 8 caracteres e incluir un carácter especial.',


 // ETL / Análisis
 COLUMN_SELECTION_REQUIRED:'No pudimos identificar la columna de ritmo cardíaco. Seleccioná la columna correcta.',
 NO_VALID_ROWS:            'El archivo no contiene datos de ritmo cardíaco válidos.',
 INVALID_BPM_RANGE:        'Algunos valores de ritmo cardíaco están fuera del rango fisiológico (30–220 BPM).',
 INVALID_FILE_FORMAT:      'El formato del archivo no es válido. Verificá que sea CSV o JSON.',
 INVALID_FILENAME:         'Nombre de archivo inválido.',
 UNSUPPORTED_MEDIA_TYPE:   'Formato de archivo no soportado. Usá CSV o JSON.',
 FILE_TOO_LARGE:           'Archivo demasiado grande para procesar online. Procesalo localmente desde la app.',


 // Procesamiento
 SESSION_NOT_FOUND:        'No se encontró la sesión de análisis.',
 MODEL_NOT_AVAILABLE:      'El servicio de análisis no está disponible. Intentá nuevamente en unos minutos.',


 // Reportes
 REPORT_SIZE_EXCEEDED:     'El informe generado supera el tamaño máximo permitido.',
 NO_DATA_IN_RANGE:         'No hay registros en el rango de fechas seleccionado.',


 // Alertas
 NO_CONTACTS_FOUND:        'No tenés contactos de confianza guardados. Agregá uno en tu perfil.',
 ALERT_SERVICE_UNAVAILABLE:'No se pudo enviar la alerta. Por favor, llamá directamente a tu contacto.',


 // Red / Genérico
 NETWORK_ERROR:            'Sin conexión. Verificá tu internet e intentá de nuevo.',
 SERVER_UNAVAILABLE:       'El sistema está en modo seguro. Por favor, intentalo más tarde.',
};


export function getErrorMessage(errorCode: string): string {
 return ERROR_MESSAGES[errorCode] ?? 'Ocurrió un error inesperado. Por favor, intentá de nuevo.';
}
```


**Pipe para templates (`shared/pipes/error-message.pipe.ts`):**
```typescript
@Pipe({ name: 'errorMessage', standalone: true })
export class ErrorMessagePipe implements PipeTransform {
 transform(errorCode: string): string {
   return getErrorMessage(errorCode);
 }
}
// Uso en template: {{ 'INVALID_BPM_RANGE' | errorMessage }}
```


### 6.4 LocalInferenceService (`core/offline/local-inference.service.ts`)


Ejecuta el modelo `.tflite` localmente cuando no hay conexión. Usa `@tensorflow/tfjs-tflite` vía WebAssembly.


```typescript
@Injectable({ providedIn: 'root' })
export class LocalInferenceService {
 private model: TFLiteModel | null = null;
 private scalerParams!: { mean: number; std: number };


 async loadModel(): Promise<void> {
   // Cargar parámetros del scaler
   const params = await fetch('assets/models/scaler_params.json').then(r => r.json());
   this.scalerParams = params;
   // Cargar modelo TFLite
   this.model = await loadTFLiteModel('assets/models/modelo.tflite');
 }


 async predict(series: { timestamp: string; bpm: number }[]): Promise<LocalResult> {
   if (!this.model) throw new Error('Modelo no cargado');


   const bpmValues = series.map(s => s.bpm);
   const features = this.extractFeatures(bpmValues);
   const scaled = features.map(f => (f - this.scalerParams.mean) / this.scalerParams.std);


   const inputTensor = tf.tensor2d([scaled]);
   const output = this.model.predict(inputTensor) as tf.Tensor;
   const cluster = (await output.data())[0];


   return this.clusterToResult(cluster);
 }


 private extractFeatures(bpm: number[]): number[] {
   const mean = bpm.reduce((a, b) => a + b, 0) / bpm.length;
   const std = Math.sqrt(bpm.map(v => (v - mean) ** 2).reduce((a, b) => a + b, 0) / bpm.length);
   const sorted = [...bpm].sort((a, b) => a - b);
   const p25 = sorted[Math.floor(sorted.length * 0.25)];
   const p75 = sorted[Math.floor(sorted.length * 0.75)];
   const max = sorted[sorted.length - 1];
   return [mean, std, p25, p75, max];
 }


 private clusterToResult(cluster: number): LocalResult {
   // Cluster → result mapping must match the model's training label assignment
   const map: Record<number, { stress_level: string; traffic_light: string; verdict: string }> = {
     0: { stress_level: 'Low',      traffic_light: 'Green',  verdict: 'Fit'   },
     1: { stress_level: 'Moderate', traffic_light: 'Yellow', verdict: 'Fit'   },
     2: { stress_level: 'High',     traffic_light: 'Red',    verdict: 'Unfit' }
   };
   return { ...map[cluster], weather_impact: null, offline: true };
 }
}


interface LocalResult {
 stress_level: string;
 traffic_light: 'Green' | 'Yellow' | 'Red';
 verdict: string;
 weather_impact: null;
 offline: true;
}
```


### 6.5 NetworkStatusService (`core/offline/network-status.service.ts`)




Detecta cambios de conectividad y expone un Observable para que los componentes reaccionen.


```typescript
@Injectable({ providedIn: 'root' })
export class NetworkStatusService {
 readonly isOnline$ = merge(
   of(navigator.onLine),
   fromEvent(window, 'online').pipe(map(() => true)),
   fromEvent(window, 'offline').pipe(map(() => false))
 ).pipe(distinctUntilChanged(), shareReplay(1));


 readonly isOnline = toSignal(this.isOnline$, { initialValue: navigator.onLine });
}
```


### 6.6 SyncQueueService (`core/offline/sync-queue.service.ts`)


Gestiona la cola de escrituras pendientes en IndexedDB usando la librería `idb`.


**Schema de IndexedDB:**


```typescript
interface SyncQueueDB extends DBSchema {
 sync_queue: {
   key: string;  // UUID generado en cliente
   value: {
     id: string;
     type: 'manual_input' | 'file_upload';
     payload: object;        // Body del request original
     endpoint: string;       // Ej: '/analysis/manual-input'
     status: 'pending' | 'failed';
     error_code?: string;
     created_at: string;     // ISO timestamp local
     retry_count: number;
   };
   indexes: { 'by-status': string; 'by-created': string };
 };
}
```


```typescript
@Injectable({ providedIn: 'root' })
export class SyncQueueService {
 private db!: IDBPDatabase<SyncQueueDB>;


 async init(): Promise<void> {
   this.db = await openDB<SyncQueueDB>('segvial-sync', 1, {
     upgrade(db) {
       const store = db.createObjectStore('sync_queue', { keyPath: 'id' });
       store.createIndex('by-status', 'status');
       store.createIndex('by-created', 'created_at');
     }
   });
 }


 async enqueue(type: SyncItem['type'], endpoint: string, payload: object): Promise<string> {
   const item: SyncItem = {
     id: crypto.randomUUID(),
     type, endpoint, payload,
     status: 'pending',
     created_at: new Date().toISOString(),
     retry_count: 0
   };
   await this.db.add('sync_queue', item);
   return item.id;
 }


 async getPending(): Promise<SyncItem[]> {
   return this.db.getAllFromIndex('sync_queue', 'by-status', 'pending');
 }


 async markFailed(id: string, error_code: string): Promise<void> {
   const item = await this.db.get('sync_queue', id);
   if (item) await this.db.put('sync_queue', { ...item, status: 'failed', error_code });
 }


 async remove(id: string): Promise<void> {
   await this.db.delete('sync_queue', id);
 }


 async countPending(): Promise<number> {
   return (await this.getPending()).length;
 }
}
```


**Lógica de drenado** — se ejecuta al detectar `isOnline$ = true`:


```typescript
// En AppComponent o un efecto de NetworkStatusService
networkStatus.isOnline$.pipe(filter(online => online)).subscribe(async () => {
 const pending = await syncQueue.getPending();
 for (const item of pending) {
   try {
     await firstValueFrom(api.post(item.endpoint, item.payload));
     await syncQueue.remove(item.id);
   } catch (err: any) {
     await syncQueue.markFailed(item.id, err.error?.error_code ?? 'NETWORK_ERROR');
   }
 }
 // Mostrar toast con resultados
});
```


---


## 7. Implementación por RF


### 7.1 RF-001 — Carga de Datos (`UploadComponent`)


**Flujo para detección de columna y manejo de errores (RF-011 ETL):**


```
1. Usuario suelta archivo CSV
2. POST /analysis/upload-file
  ├─ 200 OK con resultado                  → ir a RF-002 (ResultCard)
  ├─ 400 con COLUMN_SELECTION_REQUIRED     → ColumnSelectorComponent
  │     (response.columns trae la lista; usuario selecciona;
  │      reenvía POST /analysis/upload-file con la columna elegida)
  ├─ 400 con NO_VALID_ROWS / INVALID_BPM_RANGE / etc. → mensaje humano
  ├─ 413 FILE_TOO_LARGE                    → ofrecer LocalInferenceService (RF-008)
  ├─ 415 UNSUPPORTED_MEDIA_TYPE            → mensaje "Formato no soportado"
  └─ 503 MODEL_NOT_AVAILABLE               → "Servicio temporalmente no disponible"
```


> **En MVP el backend no devuelve `202 Accepted`** — el procesamiento online es siempre síncrono. Archivos que exceden el límite del backend se procesan localmente con `.tflite`.


**Validación de tamaño antes de enviar:**
```typescript
const MAX_OFFLINE_MB = 1;
if (!networkStatus.isOnline() && file.size > MAX_OFFLINE_MB * 1024 * 1024) {
 // Mostrar: "Este archivo es demasiado grande para guardar sin conexión."
 return;
}
if (!networkStatus.isOnline()) {
 await syncQueue.enqueue('file_upload', '/analysis/upload-file', { file: await toBase64(file) });
 // Mostrar badge de pendientes
 return;
}
```


### 7.2 RF-002 — Visualización de Resultados (`ResultCardComponent`)


**Flujo de respuesta del análisis online (síncrono, sin polling):**


```typescript
async submitAnalysis(payload: AnalysisRequest): Promise<void> {
 try {
   const result = await firstValueFrom(this.api.post<AnalysisResult>('/analysis/upload-file', payload));
   this.showResult(result);
 } catch (err: any) {
   const code = err.error?.error_code;
   if (code === 'FILE_TOO_LARGE') {
     // Ofrecer procesamiento local (LocalInferenceService)
     this.offerLocalProcessing();
   } else {
     this.showError(code ?? 'NETWORK_ERROR');
   }
 }
}
```


> **No hay polling de status en MVP** — la sección `startPolling()` se eliminó porque el backend devuelve siempre `200 OK` síncrono o un error 4xx/5xx. Si el backend reactiva async en v1.x, este archivo se actualiza entonces.


**Semáforo visual:**
```typescript
// traffic-light.component.ts
@Input() color: 'Green' | 'Yellow' | 'Red' = 'Green';
@Input() isOffline = false;


get cssClass(): string {
 return { Green: 'light--green', Yellow: 'light--yellow', Red: 'light--red' }[this.color];
}
```


**Mensaje de impacto climático:** Se renderiza solo si `weather_impact !== null`:
```html
<!-- result-card.component.html -->
@if (result.weather_impact) {
 <div class="weather-impact" [class]="'severity--' + result.weather_impact.severity">
   {{ result.weather_impact.message }}
 </div>
}
@if (isOffline) {
 <div class="offline-notice">Resultado local — sin datos climáticos disponibles.</div>
}
```


### 7.3 RF-003 — Historial (`HistoryListComponent`)


- Paginación: parámetros `?page=1&limit=10` en `GET /history/summary`.
- Filtro por tags: `?tags=Rain,Traffic` como query param.
- Cada item del historial muestra `traffic_light`, `stress_level` y, si existe, el `weather_impact.message`.


> **BACKLOG:** Flujo de descarga de informes PDF/Excel (`POST /reports/generate`, `GET /reports/download/{file_id}`) se omite de la implementación actual.


### 7.4 RF-004 — Perfil y Calibración (`ProfileComponent`)


`GET /user/profile` retorna `profile_status`, `session_count`, `baseline_bpm`. El componente renderiza el indicador de calibración según el valor:


```typescript
get calibrationMessage(): string {
 switch (this.profile.profile_status) {
   case 'new':         return 'Calibrando línea base con tus datos actuales.';
   case 'calibrating': return `Perfil en calibración (${this.profile.session_count}/5 sesiones). Los resultados son preliminares.`;
   case 'stable':      return 'Perfil estable. Todas las funciones habilitadas.';
 }
}
```


El botón de actualizar `baseline_bpm` se habilita solo cuando `session_count >= 5` (equivale al umbral de "5 sesiones" definido en RF-004, no "5 días").


### 7.5 RF-005 — Alertas de Emergencia (`AlertBannerComponent`, `EmergencyScreenComponent`)


**AlertBanner:** Se renderiza en el layout principal. Suscribe al resultado del análisis más reciente. Muestra el banner cuando `traffic_light === 'Red'`. El valor `'Red'` es determinado **exclusivamente por el clúster fisiológico** detectado en el backend — el frontend no re-implementa esa lógica. El clima se muestra aparte via `weather_impact`, no como condición del `traffic_light`.


**EmergencyScreen** — pantalla de pánico (`/alerts`):
- Obtiene `GET /user/contacts` para mostrar el contacto guardado.
- Botón "Pedir Ayuda" llama a `POST /alerts/send` que envía el email vía SendGrid al contacto de confianza. El mensaje incluye: nombre del usuario, `traffic_light`, `stress_level`, `weather_impact` (si aplica) y timestamp.
- Como acción local inmediata, también abre `mailto:` pre-formateado para que el usuario pueda enviar manualmente si lo desea:
 ```
 mailto:<email>?subject=ALERT SegVial&body=ALERT: <user_name> needs help.
 Status: High Stress. Time: <timestamp>.
 ```
- Si no hay contacto: mostrar CTA "Agregá un contacto de confianza en tu perfil".


### 7.6 RF-006 — Etiquetas (`TagSelectorComponent`)


- Tags predefinidos: `['Trancón', 'Lluvia', 'Velocidad Alta', 'Susto']` + los custom del usuario (`GET /user/tags`).
- Al seleccionar, se incluyen en el payload del análisis.
- Offline: guardar selección local como parte del item en `sync_queue`.


### 7.7 RF-007 — Autenticación (`LoginComponent`, `RegisterComponent`)


**Indicador de fortaleza de contraseña en tiempo real:**
```typescript
get passwordStrength(): 'weak' | 'medium' | 'strong' {
 const v = this.form.get('password')?.value ?? '';
 if (v.length < 8) return 'weak';
 if (/[^a-zA-Z0-9]/.test(v) && v.length >= 8) return 'strong';
 return 'medium';
}
```


**Formulario de login con Reactive Forms:**
```typescript
loginForm = this.fb.group({
 email:    ['', [Validators.required, Validators.email]],
 password: ['', Validators.required]
});
```


### 7.8 RF-008 — Offline Queue (`PendingBadgeComponent`, `OfflineBannerComponent`)


**PendingBadge** — en el header, muestra el conteo de items en `sync_queue` con `status: 'pending'`. Se actualiza reactivamente.


**OfflineBanner** — barra amarilla en el header que aparece cuando `NetworkStatusService.isOnline() === false`.


```html
<!-- shared/components/offline-banner/offline-banner.component.html -->
@if (!networkStatus.isOnline()) {
 <div class="offline-banner" role="alert" aria-live="polite">
   Sin conexión. Los datos se guardarán localmente.
 </div>
}
```


---


## 8. Build y Distribución (Ionic / Capacitor)


### 8.1 Comandos de build


```bash
# Desarrollo local (browser)
ionic serve


# Build web optimizado
ionic build --prod


# Build Android (genera APK/AAB)
ionic capacitor build android


# Build iOS (genera proyecto Xcode)
ionic capacitor build ios
```


### 8.2 Capacitor configuration (`capacitor.config.ts`)


```typescript
import { CapacitorConfig } from '@capacitor/cli';


const config: CapacitorConfig = {
 appId: 'app.segvial.conductor',
 appName: 'SegVial',
 webDir: 'www',
 server: {
   androidScheme: 'https'
 },
 plugins: {
   CapacitorHttp: {
     enabled: true   // HTTP nativo para mejor rendimiento en mobile
   }
 }
};


export default config;
```


### 8.3 Variables de entorno (`environment.ts`)


```typescript
// src/environments/environment.prod.ts
export const environment = {
 production: true,
 apiUrl: 'https://api.segvial.app',
 tfliteModelPath: 'assets/models/modelo.tflite',
 scalerParamsPath: 'assets/models/scaler_params.json'
};
```


### 8.4 Headers de seguridad


Aplicados en el backend (no en Nginx ya que no hay servidor de archivos estáticos separado en Ionic/Capacitor para móvil):
- `Content-Security-Policy`: configurado en el servidor FastAPI para las respuestas API.
- En web build (browser): se puede agregar un `index.html` meta CSP.


---


## 9. Accesibilidad (RNF-001)


| Requisito WCAG 2.1 AA | Implementación |
|---|---|
| Etiquetas ARIA | Todos los botones e inputs tienen `aria-label`. Alertas usan `role="alert"` y `aria-live="polite"`. |
| Contraste | Variables CSS con ratio mínimo 4.5:1. Toggle día/noche via clase `dark-mode` en `<body>`. |
| Navegación con teclado | Orden de `tabindex` natural. Modales trampa el foco con `cdkTrapFocus` (Angular CDK). |
| Touch targets | Botones y elementos interactivos: mínimo 48x48px via CSS. |
| Lectores de pantalla | Semáforo usa texto alternativo: `<span class="sr-only">Estado: Green - Fit to drive</span>`. |


---


## 10. Performance (RNF-003)


- **Lazy loading:** Todos los módulos de `features/` se cargan bajo demanda (ver routing).
- **Skeleton screens:** Cada componente de datos async muestra `SkeletonLoaderComponent` mientras carga.
- **Imágenes:** Formato WebP con `loading="lazy"` en `<img>`.
- **OnPush:** Todos los componentes usan `ChangeDetectionStrategy.OnPush` para reducir ciclos de detección.
- **Bundle budget:** Configurar en `angular.json` un presupuesto máximo de 500KB inicial para mantener carga < 2s en 3G.


---


**Estado del Documento:** 2.0 — Migración Angular PWA → Ionic mobile-first, modo offline con TFLite, semáforo dual output, reportes a backlog, alertas solo email.