# Estructura de modulos SIPET

## Objetivo

Definir una estructura estandar para todos los modulos del sistema tomando como referencia la organizacion de SIPET.

La regla principal es:

- Cada modulo debe ser totalmente independiente.
- Un modulo solo puede usar otro modulo si esa relacion se declara de forma explicita en el manifiesto.
- Ningun modulo debe depender de archivos internos de otro modulo por acceso directo.

## Referencia MAIN

La carpeta de referencia actual es:

- `fastapi_modulo/modulos/main`

Su estructura MAIN observada es:

```text
main/
├── controladores/
├── data/
├── imagenes/
├── modelos/
├── reportes/
├── seguridad/
├── static/
├── vistas/
└── wizards/
```

Esta sera la MAIN conceptual para ordenar todos los modulos.

## Estructura objetivo de un modulo

```text
modulo_x/
├── __manifest__.py
├── __init__.py
├── controladores/
├── modelos/
├── vistas/
├── seguridad/
├── data/
├── reportes/
├── wizards/
├── imagenes/
└── static/
    ├── css/
    ├── description/
    ├── js/
    └── img/
```

## Descripcion de cada elemento

### `__manifest__.py`

Archivo obligatorio del modulo.

Debe declarar como minimo:

- `name`: nombre tecnico y/o funcional del modulo
- `summary`: descripcion corta
- `description`: descripcion extendida del modulo, puede quedar vacia
- `version`: version del modulo
- `sequence`: orden relativo de presentacion o carga, puede quedar vacio
- `website`: sitio web del autor o del modulo, puede quedar vacio
- `depends`: lista de modulos de los que depende
- `data`: archivos de datos, vistas, seguridad o configuracion que deben cargarse
- `assets`: css, js e imagenes publicos del modulo, cuando aplique
- `installable`: indica si el modulo puede instalarse
- `application`: indica si es modulo principal o complemento

Este archivo controla la relacion formal entre modulos.

### Estructura MAIN sugerida del manifiesto

```python
{
    "name": "modulo_x",
    "summary": "Descripcion corta del modulo",
    "description": "",
    "version": "1.0.0",
    "category": "Operaciones",
    "author": "SIPET",
    "sequence": "",
    "website": "https://avancoop.org",
    "depends": ["main"],
    "data": [
        "seguridad/permisos.json",
        "vistas/modulo_x.html"
    ],
    "assets": {
        "css": [
            "static/css/modulo_x.css"
        ],
        "js": [
            "static/js/modulo_x.js"
        ],
        "description": [
            "static/description/modulo_x.svg"
        ],
        "img": [
            "static/img/modulo_x.png"
        ]
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
```

### Criterios del manifiesto

- `depends` define la relacion oficial entre modulos
- `data` declara archivos funcionales cargables del modulo
- `assets` declara los recursos frontend propios del modulo
- `assets.description` puede usarse para iconos o recursos descriptivos del modulo, por ejemplo `static/description/modulo_x.svg`
- `description` permite documentar el alcance funcional del modulo y puede quedar vacio
- `sequence` permite reservar un orden visual o funcional y puede quedar vacio
- `website` documenta el sitio oficial del modulo o del autor y puede quedar vacio
- `installable` controla si el modulo puede activarse
- `application` distingue si es modulo principal o complemento
- `auto_install` solo debe usarse cuando una dependencia funcional justifique la instalacion automatica

## `__init__.py`

Archivo de inicializacion del modulo.

Su funcion es registrar las partes internas del modulo que deben cargarse.

## `controladores/`

Contiene los controladores o rutas del modulo.

Aqui vive la capa de entrada:

- endpoints HTTP
- routers
- acciones del modulo
- integracion con vistas o APIs

No debe contener logica de negocio compleja.

## `modelos/`

Contiene los modelos de datos del modulo.

Aqui deben vivir:

- modelos ORM
- entidades del dominio
- definiciones estructurales de datos

Solo debe modelar el dominio del modulo.

## `vistas/`

Contiene las vistas del modulo.

Aqui deben ubicarse:

- templates HTML
- vistas parciales
- componentes visuales propios del modulo

Las vistas de un modulo no deben depender de templates internos de otro modulo, salvo que exista una dependencia declarada y un contrato claro de reutilizacion.

## `seguridad/`

Contiene la definicion de seguridad del modulo.

Aqui deben vivir:

- permisos
- grupos
- reglas de acceso
- configuraciones de autorizacion

Toda regla de acceso del modulo debe centralizarse aqui.

## `data/`

Contiene datos iniciales o configuraciones cargables.

Ejemplos:

- catalogos MAIN
- configuraciones iniciales
- semillas de datos
- registros necesarios para instalar el modulo

No debe mezclarse con logica de negocio.

## `reportes/`

Contiene reportes y plantillas de salida del modulo.

Ejemplos:

- reportes PDF
- exportaciones
- plantillas imprimibles
- definiciones de formatos

## `wizards/`

Contiene flujos asistidos o procesos temporales.

Ejemplos:

- asistentes de configuracion
- formularios paso a paso
- procesos guiados
- acciones transitorias del usuario

Su funcion es orquestar interacciones, no reemplazar modelos permanentes.

## `imagenes/`

Contiene imagenes propias del modulo.

Ejemplos:

- iconos
- logos del modulo
- ilustraciones
- recursos visuales internos

## `static/`

Contiene los recursos estaticos del modulo usados por la interfaz o por integraciones backend.

Subcarpetas recomendadas:

- `static/css/`: hojas de estilo del modulo
- `static/description/`: iconos o recursos descriptivos del modulo para manifiesto, catalogos o vistas institucionales
- `static/js/`: scripts del modulo
- `static/img/`: imagenes publicas o de uso frontend
- `static/vendor/`: librerias de terceros, solo si realmente se necesitan

Reglas:

- Todo asset reutilizable del modulo debe vivir aqui
- El HTML no debe contener CSS o JS grande embebido si puede separarse en `static/`
- Los assets de un modulo deben permanecer aislados de otros modulos

## Reglas de independencia entre modulos

Cada modulo debe cumplir estas reglas:

1. Debe poder entenderse, instalarse y mantenerse de forma aislada.
2. No debe importar archivos internos de otro modulo sin dependencia declarada.
3. No debe reutilizar modelos, vistas o controladores de otro modulo por acceso directo al archivo.
4. Toda dependencia funcional debe declararse en `depends` dentro del manifiesto.
5. Si un modulo requiere funcionalidades compartidas, estas deben moverse a un modulo MAIN o comun.

## Regla de dependencias

La dependencia entre modulos debe declararse solo en el manifiesto.

Ejemplo conceptual:

```python
{
    "name": "capacitacion",
    "version": "1.0.0",
    "depends": ["main", "empleados", "notificaciones"],
    "data": [],
    "installable": True,
    "application": True,
}
```

Significado:

- `capacitacion` puede usar funcionalidades de `main`, `empleados` y `notificaciones`
- Si no aparece en `depends`, la relacion no debe existir

## Orden recomendado dentro de cada modulo

Orden de responsabilidades:

1. `__manifest__.py`
2. `controladores/`
3. `modelos/`
4. `vistas/`
5. `seguridad/`
6. `data/`
7. `reportes/`
8. `wizards/`
9. `imagenes/`
10. `static/`

## Criterios de organizacion

- Un modulo debe agrupar una sola capacidad funcional principal.
- Si una carpeta crece demasiado, se puede subdividir por dominio interno.
- Los nombres de carpetas y archivos deben ser consistentes en todos los modulos.
- La estructura debe repetirse en todos los modulos para facilitar mantenimiento, instalacion y escalabilidad.

## Aplicacion en SIPET

La meta es que todos los modulos de `fastapi_modulo/modulos/` adopten esta misma estructura MAIN.

`main` se toma como referencia inicial de organizacion.

En adelante:

- cada modulo tendra su propio manifiesto
- cada modulo declarara sus dependencias
- cada modulo sera independiente
- la relacion entre modulos sera explicita, nunca implicita

## Resultado esperado

Con esta estructura se obtiene:

- mejor mantenimiento
- modulos desacoplados
- orden uniforme
- dependencias claras
- mayor facilidad para escalar el sistema
- una arquitectura mas cercana al enfoque modular de SIPET
