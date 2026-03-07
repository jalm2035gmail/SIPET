# 2.2 Perfilamiento de Datos

## Dimensiones de calidad a medir
- Completitud
- Unicidad
- Consistencia
- Actualidad (frescura)

## Reglas minimas por dominio

### Socios
- `email` unico y con formato valido.
- `nombre` no nulo.

### Creditos
- `monto > 0`
- `plazo > 0`
- `deuda_actual >= 0`
- `antiguedad_meses >= 0`

### Pagos
- `monto > 0`
- `fecha` valida y asociada a credito existente.

## Reporte esperado por corrida
| Tabla | % nulos campos criticos | % duplicados clave | % fuera de rango | Fecha corte |
|---|---|---|---|---|
| socios |  |  |  |  |
| creditos |  |  |  |  |
| historial_pagos |  |  |  |  |
| cuentas |  |  |  |  |
| transacciones |  |  |  |  |

## Resultado
Definir semaforo por tabla: Verde (apta), Amarillo (ajustes), Rojo (bloqueo de uso analitico).
