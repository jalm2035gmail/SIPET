



## Objetivo
Documentar el proceso y las mejores prácticas para migrar módulos grandes desde main.py/MAIN.html a una estructura modular y desacoplada, reutilizable para otros módulos.
## Etapas de migración
1. **Planeación y documentación**
- Registrar dependencias, rutas, funciones y archivos involucrados.
- Confirmar la ruta destino y crear la estructura de carpetas/archivos.
2. **Extracción de vistas y estilos**
- Mover el HTML relevante a un archivo .html (Jinja2 o similar).
- Mover CSS embebido a un archivo .css dedicado.
3. **Modularización de lógica backend**
- Mover funciones y endpoints a un archivo .py propio.
- Adaptar imports y dependencias.
4. **Refactorización de JS**
- Mover JS específico a la plantilla o a un archivo .js.
- Asegurar funcionamiento de eventos y lógica.
5. **Integración y pruebas**
- Actualizar main.py/MAIN.html para consumir el nuevo módulo.
- Probar toda la funcionalidad migrada.
6. **Limpieza y documentación**
- Eliminar código duplicado o migrado.
- Documentar la nueva arquitectura y dependencias.
## Notas y recomendaciones
- Mantener la documentación actualizada en cada etapa.
- Validar dependencias cruzadas antes de eliminar código antiguo.
- Usar nombres consistentes y rutas claras para facilitar futuras migraciones.
- Probar cada funcionalidad migrada antes de continuar con la siguiente.
- **Importante:** Al instalar el sidebar, el contenido de la pantalla puede desaparecer si el layout o el CSS global no están correctamente adaptados. Revisar el uso de la clase `main-content` y el margen del layout para evitar este problema.
## Registro de migración real
## Problemas encontrados y soluciones en la migración de departamentos
### 1. ImportError y rutas de modelos
- **Problema:** Al migrar endpoints y lógica de departamentos, los modelos y SessionLocal estaban definidos en main.py. Al intentar importarlos desde departamentos.py, se generó un error de importación circular.
- **Solución:** Se creó un archivo independiente `fastapi_modulo/db.py` para definir `SessionLocal` y el modelo `DepartamentoOrganizacional`. Ahora ambos módulos importan desde `db.py`, evitando circularidad.
### 2. ModuleNotFoundError en rutas relativas
- **Problema:** Al usar rutas relativas como `from ..models import DepartamentoOrganizacional` o `from ..db import SessionLocal`, se generaban errores porque esos módulos no existían o no estaban en la ruta correcta.
- **Solución:** Se corrigieron las importaciones para usar la ruta absoluta `from fastapi_modulo.db import SessionLocal, DepartamentoOrganizacional`.
### 3. Duplicidad de definiciones
- **Problema:** Al migrar, existían definiciones duplicadas de modelos y SessionLocal en main.py y en el nuevo archivo db.py.
- **Solución:** Se eliminó la duplicidad, dejando la definición única en db.py y adaptando los imports en main.py y departamentos.py.
### 4. Integración y pruebas
- **Problema:** Al registrar el router de departamentos en main.py, si las importaciones no estaban correctamente modularizadas, el servidor no iniciaba.
- **Solución:** Se modularizó la arquitectura siguiendo el protocolo de migración, asegurando que cada módulo importe solo lo necesario desde archivos independientes.
# Fases detalladas para la migración del módulo Departamentos
Planeación y análisis:
Identificar todas las funciones, endpoints y rutas de departamentos en main.py y MAIN.html.
Listar dependencias, variables globales y archivos involucrados.
Confirmar la estructura destino: modulos/empleados/departamentos.html, .py, .css.
Documentar el flujo actual y puntos de integración.
Extracción de vistas y estilos:
Revisar el HTML y CSS de departamentos en MAIN.html y áreas relacionadas.
Unificar todas las vistas (formulario, listado, kanban, organigrama) en departamentos.html.
Eliminar archivos vacíos o redundantes.
Adaptar clases y estilos para evitar conflictos con el CSS global.
Modularización backend:
Revisar funciones y endpoints en main.py para departamentos.
Adaptar imports y dependencias antes de moverlos.
Refactorización JS:
Identificar JS específico de departamentos en MAIN.html o main.js.
Revisar eventos y lógica para que funcionen en el nuevo contexto.
Integración y pruebas:
Registrar el nuevo router en main.py.
Actualizar MAIN.html para enlazar la nueva plantilla y estilos.
Probar la funcionalidad migrada.
Limpieza y documentación:
Eliminar archivos vacíos o migrados (departamentos_list.html, departamentos_kanban.html, departamentos_organigrama.html).
Documentar la nueva arquitectura y dependencias.
---

# Migración y desarrollo del módulo Reportes

## Planeación y análisis
- Se identificó la necesidad de un módulo independiente para reportes.
- Se decidió crear los archivos `reportes.py` (lógica backend) y `reportes.html` (plantilla frontend) en la carpeta `/reportes`.
- Se analizaron funciones existentes en `fastapi_modulo/main.py` relacionadas con generación de reportes, encabezados y exportaciones (por ejemplo: `_build_report_export_html_document`, helpers de plantillas y contexto).
- No existen endpoints dedicados a reportes, pero sí lógica reutilizable para exportación y visualización.
- Próximo paso: migrar esta lógica a `reportes.py` y dejar solo los imports en `main.py`.

## Estructura creada
- `/reportes/reportes.py`: Archivo principal para la lógica de generación de reportes.
- `/reportes/reportes.html`: Plantilla HTML para la visualización de reportes.

## Desarrollo
- Se creó `reportes.py` como punto de entrada para futuras funciones de generación y exportación de reportes.
- Se creó `reportes.html` como plantilla MAIN para mostrar los reportes generados.
- Ambas estructuras están listas para ser integradas con FastAPI y Jinja2.

## Integración con FastAPI
- Se importó la función `_build_report_export_html_document` desde `reportes.py` en `main.py`.
- Se creó un endpoint `/reportes/exportar-html` que devuelve el HTML del reporte consolidado.
- El router de reportes se registró en la app principal.

## Buenas prácticas aplicadas
- Separación clara entre lógica backend y presentación frontend.
- Uso de nombres descriptivos y consistentes.
- Documentación de cada paso en este archivo.

## Próximos pasos
- Implementar endpoints en `reportes.py` para generar y servir reportes.
- Integrar la plantilla `reportes.html` con el backend.
- Añadir pruebas y documentación adicional según se avance en el desarrollo.
