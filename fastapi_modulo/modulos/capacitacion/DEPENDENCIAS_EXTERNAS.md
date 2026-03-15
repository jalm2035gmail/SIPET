# Dependencias externas del modulo capacitacion

## Estado actual

El modulo ya concentra sus adaptadores de integracion en `controladores/dependencies.py`.

## Dependencias globales que siguen existiendo

- `fastapi_modulo.db`
  - Provee `SessionLocal`, `engine` y la base declarativa `MAIN`.
  - Todos los servicios y modelos SQLAlchemy dependen de esta capa compartida.

- `fastapi_modulo.main`
  - Si existe, se usa para `render_backend_page`, resolver el usuario actual y leer sesion/cookies.
  - Si no existe o falla la importacion, el modulo ahora cae en modo degradado:
    - renderiza HTML directo;
    - usa `user_name` o cookies como clave del colaborador;
    - permite acceso cuando hay sesion visible aunque no pueda resolver `Usuario`.

- `modulos.encuestas`
  - Solo se usa para listar encuestas activas vinculadas a cursos/presentaciones.
  - Si no esta instalado, las rutas regresan `[]` en vez de romper.

## Trabajo pendiente si se quiere independencia total

- Crear una capa de BD local para reemplazar `fastapi_modulo.db`.
- Mover o duplicar el modelo/autenticacion de usuarios que hoy vive en `fastapi_modulo.main`.
- Si se requiere funcionalidad de encuestas, portar aqui un store local equivalente.
