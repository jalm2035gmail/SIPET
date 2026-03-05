/**
 * Tailwind CSS v4 — Configuración de tema
 *
 * En v4 el escaneo de fuentes se hace con directivas @source en el CSS:
 *   static/src/input.css
 *
 * Este archivo se reserva para personalizaciones de tema.
 * Para usarlo: añade `@config "../../tailwind.config.js"` en input.css.
 *
 * @type {import('tailwindcss').Config}
 */
module.exports = {
  theme: {
    extend: {
      // Aquí puedes extender colores, fuentes, breakpoints, etc.
      // Ejemplo:
      // colors: {
      //   brand: { DEFAULT: 'var(--button-bg)', hover: 'var(--sidebar-hover)' },
      // },
    },
  },
};
