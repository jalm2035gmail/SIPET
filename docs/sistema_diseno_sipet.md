# Sistema de Diseno Unico — SIPET

Este documento define el sistema oficial de colores y su uso en la interfaz de SIPET.
Es la referencia funcional para diseno, frontend y personalizacion institucional.

## Fuente de verdad

La fuente tecnica de verdad del sistema es:

- [fastapi_modulo/modulos/personalizacion/theme_system.py](/Users/jalm/Dropbox/Apps/SIPET/fastapi_modulo/modulos/personalizacion/theme_system.py)
- [fastapi_modulo/colores.json](/Users/jalm/Dropbox/Apps/SIPET/fastapi_modulo/colores.json)
- [static/css/global.css](/Users/jalm/Dropbox/Apps/SIPET/static/css/global.css)
- [estilos_globales.md](/Users/jalm/Dropbox/Apps/SIPET/estilos_globales.md)

Regla institucional: los modulos no deben introducir colores hexadecimales fijos para layout, botones, campos o navegacion. Deben consumir variables CSS del sistema.

## Arquitectura del tema

SIPET no trabaja con una paleta plana. Trabaja con una paleta MAIN corta y una paleta derivada.

### 1. Colores MAIN oficiales

Estos son los unicos colores que se configuran de forma directa:

| Token | Funcion | Valor oficial vigente |
|---|---|---|
| `--navbar-bg` | Fondo de la barra superior | `#661414` |
| `--sidebar-top` | Inicio del gradiente del sidebar | `#1f2a3d` |
| `--sidebar-bottom` | Fin del gradiente del sidebar y acento principal | `#0f172a` |
| `--button-bg` | Fondo principal de botones | `#0f172a` |
| `--field-color` | Fondo MAIN de campos y superficies claras | `#ffffff` |

Notas:

- `--button-bg` y `--field-color` no aparecen guardados hoy en [fastapi_modulo/colores.json](/Users/jalm/Dropbox/Apps/SIPET/fastapi_modulo/colores.json), por lo que el sistema usa sus valores por defecto definidos en [fastapi_modulo/modulos/personalizacion/theme_system.py](/Users/jalm/Dropbox/Apps/SIPET/fastapi_modulo/modulos/personalizacion/theme_system.py#L15).
- `--sidebar-bottom` es el color institucional dominante de la interfaz.

### 2. Colores derivados oficiales

Estos tokens no deben definirse a mano en modulos. El sistema los calcula a partir de la paleta MAIN.

| Token | Funcion | Valor efectivo vigente |
|---|---|---|
| `--navbar-text` | Texto e iconos sobre navbar | `#ffffff` |
| `--sidebar-text` | Texto sobre sidebar | `#ffffff` |
| `--sidebar-icon` | Iconografia del sidebar | `#756f63` |
| `--sidebar-hover` | Hover/activo suave del sidebar | `#141925` |
| `--button-text` | Texto sobre botones | `#ffffff` |
| `--field-text` | Texto sobre campos | `#0f172a` |
| `--field-border` | Borde neutral de campos | `#ffffff` |
| `--field-focus` | Estado de foco de campos | `#151924` |
| `--page-bg` | Fondo general de pagina | `#5f1b1b` |
| `--content-bg` | Fondo de tarjetas y paneles | `#ffffff` |
| `--body-text` | Texto MAIN del contenido | `#3f4555` |
| `--page-title-color` | Titulo principal | `#0f172a` |
| `--institutional-accent` | Acento institucional principal | `#0f172a` |
| `--institutional-accent-contrast` | Contraste complementario del acento | `#2a220f` |
| `--institutional-navbar-accent` | Contraste complementario de navbar | `#146666` |
| `--institutional-button-hover` | Hover de boton | `#131926` |
| `--institutional-button-active` | Estado activo de boton | `#151924` |
| `--institutional-field-soft` | Variante suave de superficies de campo | `#ffffff` |
| `--institutional-panel-soft` | Variante suave de panel institucional | `#631514` |

## Paleta limpia oficial

Para uso humano, la paleta oficial queda resumida asi:

### Navegacion

| Nombre | Hex | Uso |
|---|---|---|
| Vino institucional | `#661414` | Fondo de navbar |
| Azul petroleo oscuro | `#1f2a3d` | Inicio de gradiente del sidebar |
| Azul nocturno institucional | `#0f172a` | Fin de gradiente del sidebar, acento principal y botones |
| Blanco | `#ffffff` | Texto sobre navbar y sidebar |

### Superficies y contenido

| Nombre | Hex | Uso |
|---|---|---|
| Blanco MAIN | `#ffffff` | Campos, tarjetas y superficies limpias |
| Gris texto profundo | `#3f4555` | Texto MAIN del contenido |
| Vino profundo de pagina | `#5f1b1b` | Fondo general derivado de la aplicacion |

### Estados institucionales derivados

| Nombre | Hex | Uso |
|---|---|---|
| Hover boton | `#131926` | Hover de botones principales |
| Activo/focus institucional | `#151924` | Focus de campos y estado activo |
| Hover sidebar | `#141925` | Hover de items del sidebar |
| Contraste complementario | `#2a220f` | Recursos graficos derivados, contraste institucional |

## Sistema de uso

### Jerarquia cromatica

1. `--sidebar-bottom` es el color institucional principal.
2. `--navbar-bg` define la identidad de la barra superior.
3. `--button-bg` reutiliza el acento institucional para accion primaria.
4. `--field-color` y `--content-bg` sostienen la legibilidad.
5. Los estados hover, focus y contrastes se derivan, no se inventan por modulo.

### Reglas obligatorias

1. Usar siempre variables CSS del sistema (`var(--token)`).
2. No usar hex fijos en componentes reutilizables.
3. No asignar un color distinto por accion como Guardar, Editar o Eliminar si el sistema ya define `--button-bg`.
4. No redefinir colores globales dentro de modulos si el componente ya existe en [static/css/global.css](/Users/jalm/Dropbox/Apps/SIPET/static/css/global.css).
5. Si cambia la identidad institucional, solo deben actualizarse los 5 colores MAIN.

## Mapa de tokens por componente

| Componente | Tokens obligatorios |
|---|---|
| Navbar | `--navbar-bg`, `--navbar-text` |
| Sidebar | `--sidebar-top`, `--sidebar-bottom`, `--sidebar-text`, `--sidebar-icon`, `--sidebar-hover` |
| Botones principales | `--button-bg`, `--button-text`, `--institutional-button-hover`, `--institutional-button-active` |
| Inputs y selects | `--field-color`, `--field-text`, `--field-border`, `--field-focus` |
| Pagina MAIN | `--page-bg`, `--body-text` |
| Tarjetas y contenedores | `--content-bg`, `--body-text` |
| Titulos | `--page-title-color` |

## Ejemplos correctos

```css
.navbar {
    background: var(--navbar-bg);
    color: var(--navbar-text);
}

.action-button {
    background: var(--button-bg);
    color: var(--button-text);
}

.form-row input {
    background: var(--field-color);
    color: var(--field-text);
    border: 1px solid color-mix(in srgb, var(--button-bg) 20%, #ffffff 80%);
}
```

## Ejemplos incorrectos

```css
.action-button--save {
    background: #16a34a;
}

.sidebar {
    background: #111827;
}

.custom-card {
    color: #222;
}
```

## Procedimiento oficial de cambio

Cuando la institucion quiera cambiar identidad visual:

1. Ajustar solo `navbar-bg`, `sidebar-top`, `sidebar-bottom`, `button-bg` y `field-color`.
2. Dejar que [fastapi_modulo/modulos/personalizacion/theme_system.py](/Users/jalm/Dropbox/Apps/SIPET/fastapi_modulo/modulos/personalizacion/theme_system.py#L95) regenere el resto.
3. Validar contraste visual en navbar, sidebar, botones y formularios.
4. Verificar que ningun modulo use hex fijos.

## Decision oficial actual

La identidad visual oficial vigente de SIPET queda definida por esta combinacion:

- Navbar vino institucional: `#661414`
- Sidebar azul petroleo a azul nocturno: `#1f2a3d` -> `#0f172a`
- Acento principal y botones: `#0f172a`
- Superficies y campos: `#ffffff`
- Texto principal de contenido: `#3f4555`

Esta es la paleta limpia que debe usarse como referencia institucional hasta que se actualicen los 5 colores MAIN del sistema.
