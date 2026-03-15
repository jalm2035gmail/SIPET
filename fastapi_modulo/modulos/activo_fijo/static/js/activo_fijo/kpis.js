import { api } from './api.js';
import { $, fmt } from './ui.js';

export async function loadKpis() {
  try {
    const data = await api('GET', '/api/activo-fijo/resumen');
    $('kpi-total').textContent = data.total_activos;
    $('kpi-asignados').textContent = data.activos_asignados;
    $('kpi-mant').textContent = data.activos_en_mantenimiento;
    $('kpi-baja').textContent = data.activos_dados_baja;
    $('kpi-valor-libro').textContent = '$' + fmt(data.valor_libro_total);
    $('kpi-dep-acum').textContent = '$' + fmt(data.depreciacion_acumulada);
  } catch (_) {
  }
}
