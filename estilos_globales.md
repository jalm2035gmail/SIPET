# Guía de Estilos Globales — SIPET

> **Regla principal:** Todo el CSS de componentes reutilizables debe vivir en  
> `static/css/global.css`.  
> Los módulos **no** deben redefinir clases globales ni añadir estilos inline a
> elementos ya cubiertos por este sistema.

---

## 1. Variables CSS (`:root`)

Estas variables son inyectadas dinámicamente por el superadministrador desde
`/ajustes/colores`. **Nunca usar colores hexadecimales fijos** para los
elementos de layout — usar siempre las variables.

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `--navbar-bg` | Fondo de la barra superior | `#ffffff` |
| `--navbar-text` | Texto de la navbar | `#1f172a` |
| `--sidebar-top` | Color superior del gradiente del sidebar | `#1f2a3d` |
| `--sidebar-bottom` | Color inferior del sidebar (también sirve como color principal de UI) | `#0f172a` |
| `--sidebar-text` | Texto e íconos del sidebar | `#ffffff` |
| `--sidebar-icon` | Color de íconos del sidebar | `#f5f7fb` |
| `--sidebar-hover` | Color de hover en items del sidebar | `#16a34a` |
| `--page-bg` | Fondo general de la página | `#f4f6fb` |
| `--content-bg` | Fondo de tarjetas/contenido | `#ffffff` |
| `--body-text` | Texto base del cuerpo | `#0f172a` |
| `--button-bg` | **Fondo de botones** (configurable en ajustes) | `#0f172a` |
| `--button-text` | **Texto de botones** (configurable en ajustes) | `#ffffff` |
| `--field-color` | Fondo de campos de formulario | `#ffffff` |

### Uso correcto

```css
/* ✅ Correcto */
background: var(--button-bg, #0f172a);
color: var(--button-text, #ffffff);
border: 1px solid color-mix(in srgb, var(--button-bg, #0f172a) 20%, #ffffff 80%);

/* ❌ Incorrecto — valor fijo */
background: #16a34a;
color: #ffffff;
```

---

## 2. Sidebar

### Clases
| Clase | Uso |
|---|---|
| `.sidebar` | Contenedor principal fijo, 220 px de ancho |
| `.sidebar-header` | Zona del logo/avatar arriba del sidebar |
| `.sidebar-user` | Avatar circular del usuario |
| `.sidebar-block` | Bloque de sección del menú |
| `.sidebar-main-link` | Ítem principal del menú |
| `.sidebar-main-icon` | Ícono SVG del ítem |
| `.sidebar-main-label` | Texto del ítem |
| `.sidebar-main-caret` | Flecha de acordeón |
| `.sidebar-submenu` | Submenú desplegable |
| `.sidebar-submenu-group` | Grupo dentro del submenú |
| `.sidebar-submenu-level3` | Tercer nivel de menú |
| `.sidebar-section` | Sección colapsable |
| `.sidebar-section-content` | Contenido de la sección |
| `.accordion-header` | Encabezado del acordeón |

### Notificaciones del sidebar
`.sidebar-notifications-panel` · `.sidebar-notifications-header` ·
`.sidebar-notifications-list` · `.notification-item` · `.notification-item-title` ·
`.notification-item-msg` · `.notification-item-date`

---

## 3. Navbar

### Clases
| Clase | Uso |
|---|---|
| `.navbar` | Barra superior fija |
| `.navbar-inner` | Contenedor interno con flex |
| `.navbar-left` | Lado izquierdo (hamburger + título) |
| `.navbar-hamburger` | Botón de toggle del sidebar |
| `.navbar-title` | Título de la sección activa |
| `.navbar-menu-name` | Nombre del menú activo |
| `.navbar-avatar` | Avatar del usuario (navbar) |
| `.navbar-avatar-icon` | Ícono dentro del avatar |
| `.navbar-user-menu` | Menú desplegable del usuario |
| `.user-dropdown` | Dropdown de opciones del usuario |
| `.navbar-notifications-btn` | Botón de notificaciones |
| `.navbar-notifications-badge` | Badge con número de notificaciones |
| `.navbar-ia-btn` | Botón de acceso a IA |
| `.navbar-ia-icon` | Ícono del botón IA |
| `.navbar-route` | Breadcrumb / ruta de navegación |

---

## 4. Layout de contenido

```
.main-content        — área principal (con padding-left para sidebar)
  .content-shell     — wrapper interior con max-width y padding
    .page-header     — encabezado de página (título + botones de vista)
      .page-header-text
        .page-header-subtitle
        .page-title
        .page-description
    .content-section — tarjeta de sección (borde, sombra, fondo)
      .content-section-head
        .content-section-kicker
        .content-section-title
      .content-section-body
        .subsection-grid
          .subsection-card
```

---

## 5. Botones de vista (parte superior de módulos)

> ⚠️ Estos botones son **exclusivamente** para cambiar la vista (lista, kanban,
> formulario, organigrama…). **No confundir** con los botones de acción
> (Nuevo / Editar / Guardar / Eliminar).

```html
<!-- Estructura correcta -->
<div class="view-buttons">
  <button class="view-pill" data-view="form" aria-label="Formulario">
    <span class="view-pill-icon-mask" style="--action-icon-url: url('/icon/...')"></span>
  </button>
  <button class="view-pill" data-view="list" aria-label="Lista">...</button>
</div>
```

| Clase | Uso |
|---|---|
| `.view-buttons` | Contenedor flex centrado de las píldoras |
| `.view-pill` | Botón de vista — tamaño fijo 46 × 46 px, redondo |
| `.view-pill.active` | Estado activo (usa `--sidebar-bottom` como fondo) |
| `.view-pill-icon-mask` | Máscara SVG del ícono con `--action-icon-url` |

---

## 6. Botones de acción (Nuevo / Editar / Guardar / Eliminar)

> Estos botones están en la parte **inferior** del formulario de cada módulo.

### Contenedor obligatorio

```html
<div class="action-buttons-group">
  <button type="button" class="action-button" data-hover-label="Nuevo" aria-label="Nuevo" title="Nuevo">
    <img src="/icon/boton/nuevo.svg" alt="Nuevo">
    <span class="action-label">Nuevo</span>
  </button>
  <button type="button" class="action-button" data-hover-label="Editar" aria-label="Editar" title="Editar">
    <img src="/icon/boton/editar.svg" alt="Editar">
    <span class="action-label">Editar</span>
  </button>
  <button type="submit" class="action-button" data-hover-label="Guardar" aria-label="Guardar" title="Guardar">
    <img src="/icon/boton/guardar.svg" alt="Guardar">
    <span class="action-label">Guardar</span>
  </button>
  <button type="button" class="action-button" data-hover-label="Eliminar" aria-label="Eliminar" title="Eliminar">
    <img src="/icon/boton/eliminar.svg" alt="Eliminar">
    <span class="action-label">Eliminar</span>
  </button>
</div>
```

### Clases

| Clase | Descripción |
|---|---|
| `.action-buttons-group` | **Contenedor.** `flex`, fila horizontal centrada, `gap: 10px`, `width: 100%`, `margin-top: 12px` |
| `.action-button` | Botón circular 44×44 px. Usa `--button-bg` / `--button-text` |
| `.action-label` | Texto oculto (accesibilidad) — `display: none` en pantalla |

### Íconos disponibles en `/icon/boton/`

| Archivo | Acción |
|---|---|
| `nuevo.svg` | Nuevo |
| `editar.svg` | Editar |
| `guardar.svg` | Guardar |
| `eliminar.svg` | Eliminar |
| `cancelar.svg` | Cancelar |

### Color

Los botones de acción usan **el mismo color global** que el resto de botones.
El color lo define el superadministrador en `/ajustes/colores → Campos y botones`.
No añadir colores fijos ni clases de color por acción.

```css
/* ✅ Así está en global.css — no modificar */
.action-button {
    background: var(--button-bg, #0f172a);
    color: var(--button-text, #ffffff);
    border: 1px solid var(--button-bg, #0f172a);
}
.action-button:hover,
.action-button:focus-visible {
    background: var(--button-text, #ffffff);
    color: var(--button-bg, #0f172a);
    border-color: var(--button-bg, #0f172a);
}
```

---

## 7. Campos de formulario

```html
<!-- Estructura de campo recomendada -->
<div class="form-row">
  <label for="mi-campo">Etiqueta</label>
  <input type="text" id="mi-campo" name="mi-campo">
</div>
```

| Clase | Uso |
|---|---|
| `.form-row` | `flex-direction: column`, `gap: 4px` |
| `.form-field` | Variante con separación mayor entre campos |
| `.section-grid` | Grid responsive para grupos de campos |
| `.form-section` | Sección con título dentro de un formulario |

### Border de campos

```css
/* ✅ Correcto — borde vinculado al color del botón */
border: 1px solid color-mix(in srgb, var(--button-bg, #0f172a) 20%, #ffffff 80%);
border-radius: 10px;
background: var(--field-color, #ffffff);
color: var(--navbar-text, #1f172a);
```

---

## 8. Tarjetas y secciones

| Clase | Descripción |
|---|---|
| `.content-section` | Tarjeta principal con borde, sombra, fondo blanco |
| `.subsection-grid` | Grid de 2 columnas para sub-tarjetas |
| `.subsection-card` | Tarjeta secundaria |
| `.subsection-chip` | Etiqueta/badge de estado |
| `.message-box` | Caja de mensaje (info, error, ok) |

---

## 9. Floating actions (panel lateral de botones)

> Sistema de panel flotante fijo a la derecha usada en módulos complejos.
> **Diferente** al `.action-buttons-group` del formulario.

```
.floating-actions-wrapper
  .floating-actions
    .floating-toggle        — botón de abrir/cerrar
    .floating-actions-group[data-floating-screen="..."]
      .action-button
      .floating-actions-separator
```

---

## 10. Tabla oficial

```html
<div class="tabla-oficial-wrap">
  <table class="tabla-oficial view-list-excel">
    <thead>...</thead>
    <tbody>...</tbody>
  </table>
</div>
```

| Clase | Uso |
|---|---|
| `.tabla-oficial-wrap` | Overflow horizontal |
| `.tabla-oficial` | Tabla base con bordes y hover |
| `.tabla-oficial-input` | Input incrustado en celda editable |

---

## 11. Reglas para módulos nuevos

1. **No crear un `<style>` local** para clases que ya existen en `global.css`.
2. **Sí se permite** una sección `<style>` para clases **exclusivas** del módulo
   (prefijo con el nombre del módulo, ej. `mi-modulo-card`).
3. Los contenedores de botones de acción siempre deben usar `.action-buttons-group`.
4. Los botones de acción siempre son `<button class="action-button" data-hover-label="...">`.
5. Los botones de vista siempre son `.view-pill` dentro de `.view-buttons`.
6. Los bordes de campos usan `color-mix(in srgb, var(--button-bg) N%, #ffffff M%)`.
7. Nunca hardcodear `#16a34a`, `#dc2626`, `#2563eb` u otros acentos en módulos.
8. Las tipografías ya están definidas en `body` — no redefinir `font-family`.

---

## 12. Referencia rápida de la paleta semántica (solo para textos de estado)

Estos colores se usan únicamente en mensajes de éxito/error dentro de JS
(`.style.color = ...`), no en CSS de componentes:

| Significado | Color |
|---|---|
| Éxito / guardado | `#166534` |
| Error | `#b91c1c` |
| Neutro / info | `#334155` |
| Atención / warning | `#92400e` |
