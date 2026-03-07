# Validacion de Datos - Fase 2

Fecha de generacion: 2026-02-18T03:34:15.423882+00:00

## Reglas evaluadas

| Tabla | Regla | Violaciones | Severidad | Estado |
|---|---|---:|---|---|
| socios | nombre no vacio | 0 | Alta | Cumple |
| socios | email no vacio | 0 | Alta | Cumple |
| creditos | monto > 0 | 0 | Alta | Cumple |
| creditos | plazo > 0 | 0 | Alta | Cumple |
| creditos | ingreso_mensual > 0 | 0 | Alta | Cumple |
| creditos | deuda_actual >= 0 | 0 | Alta | Cumple |
| creditos | deuda_actual <= ingreso_mensual | 0 | Media | Cumple |
| creditos | antiguedad_meses >= 0 | 0 | Media | Cumple |
| historial_pagos | monto > 0 | 0 | Alta | Cumple |
| historial_pagos | fecha <= hoy | 0 | Baja | Cumple |
| cuentas | saldo >= 0 | 0 | Media | Cumple |
| transacciones | monto > 0 | 0 | Alta | Cumple |

## Resumen
- Total de reglas: 12
- Reglas con incumplimientos: 0

## Estado para checklist Fase 2 (Punto 5 de 8)
- Estado sugerido: `En revision`.
- Cierre requerido: resolver reglas con incumplimientos y ejecutar corrida de confirmacion.
