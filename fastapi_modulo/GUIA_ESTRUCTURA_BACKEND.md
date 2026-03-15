# Estructura estandar de pantallas backend

Todas las pantallas backend renderizadas con `MAIN.html` siguen este formato:

1. Titulo
2. Descripcion
3. Seccion
4. Titulo de seccion
5. Contenido

## Parametros de backend

En cada endpoint usa `render_backend_page(...)` o `backend_screen(...)`:

- `title`: Titulo principal de la pagina
- `description`: Descripcion principal de la pagina
- `section_label` (opcional): etiqueta corta de la seccion (default: `Seccion`)
- `section_title` (opcional): titulo de seccion (default: `Contenido`)
- `content`: HTML del contenido de la seccion

Ejemplo:

```python
return render_backend_page(
    request,
    title="Configuracion",
    description="Administra colores, estilos y preferencias",
    section_label="Seccion",
    section_title="Colores",
    content=HTML_CONTENIDO,
)
```

## Clases CSS de contenido

La MAIN ya incluye estas clases para mantener formato uniforme:

- `.content-section`
- `.content-section-head`
- `.content-section-kicker`
- `.content-section-title`
- `.content-section-body`
- `.subsection-grid`
- `.subsection-card`
- `.subsection-head`
- `.subsection-title`
- `.subsection-description`
- `.subsection-value`
- `.subsection-chip`

Si en `content` agregas sub-bloques internos, usa esta estructura recomendada:

```html
<article class="content-section">
  <header class="content-section-head">
    <p class="content-section-kicker">Seccion</p>
    <h2 class="content-section-title">Titulo de seccion</h2>
  </header>
  <div class="content-section-body">
    <!-- contenido -->
  </div>
</article>
```

Ejemplo con subsecciones tipo dashboard:

```html
<article class="content-section">
  <header class="content-section-head">
    <div>
      <p class="content-section-kicker">Seccion</p>
      <h2 class="content-section-title">Proyeccion Financiera (12 meses)</h2>
    </div>
    <span class="subsection-chip">Activo</span>
  </header>
  <div class="content-section-body">
    <div class="subsection-grid">
      <article class="subsection-card">
        <div class="subsection-head">
          <p class="subsection-description">Ingresos proyectados</p>
          <span class="subsection-chip">+ 2.5% / mes</span>
        </div>
        <p class="subsection-value">$1,172,622</p>
        <p class="subsection-description">Total acumulado en 12 meses</p>
      </article>

      <article class="subsection-card">
        <div class="subsection-head">
          <p class="subsection-description">Costos proyectados</p>
          <span class="subsection-chip">Inflacion +4.0%</span>
        </div>
        <p class="subsection-value">$757,543</p>
        <p class="subsection-description">Total acumulado en 12 meses</p>
      </article>
    </div>
  </div>
</article>
```

## Colores personalizables (Configuracion/Colores)

Estas clases usan variables ya configurables por usuario:

- Fondo de seccion: `--field-color`
- Borde y acentos: `--button-bg`
- Texto de etiqueta: `--button-text`
- Titulo de seccion: `--sidebar-bottom`
- Texto del contenido: `--navbar-text`
- Fondo general del contenedor: `--navbar-bg`

Los valores se ajustan desde la pantalla de configuracion sin tocar CSS.
