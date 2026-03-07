# Poblacion y Etiquetas - Fase 1.5

## Universo inicial
- Socios activos.
- Creditos vigentes.
- Historial de creditos cerrados (pagados/rechazados/incumplidos).

## Entidades base
- Socio
- Credito
- HistorialPago
- Cuenta de ahorro / Transaccion (para variables complementarias)

## Etiqueta de incumplimiento (propuesta)
- Incumplimiento 30d: atraso >= 30 dias en ventana objetivo.
- Incumplimiento 60d: atraso >= 60 dias.
- Incumplimiento 90d: atraso >= 90 dias.

## Ventanas sugeridas
- Observacion: 6 a 12 meses historicos.
- Prediccion: siguientes 30/60/90 dias segun caso.

## Exclusiones iniciales
- Registros sin `id_socio` o `id_credito`.
- Fechas inconsistentes (desembolso > vencimiento).
- Monto/plazo no validos.
- Datos duplicados no reconciliados.
