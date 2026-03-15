// ui.js
// Semáforo visual por riesgo
function renderRiskBadge(riesgo) {
  const colors = {
    bajo: '#15803d',
    medio: '#a16207',
    alto: '#c2410c',
    critico: '#dc2626',
  };
  return `<span class="aud-badge ${riesgo}" style="background:${getRiskBg(riesgo)};color:${colors[riesgo]}">${riesgo.toUpperCase()}</span>`;
}
function getRiskBg(riesgo) {
  return {
    bajo: '#dcfce7',
    medio: '#fef9c3',
    alto: '#ffedd5',
    critico: '#fee2e2',
  }[riesgo] || '#f1f5f9';
}

// Alertas de vencimiento
function renderVencimiento(fecha, hoy = new Date()) {
  if (!fecha) return '';
  const f = new Date(fecha);
  if (f < hoy) return '<span class="aud-badge is-danger">Vencido</span>';
  const diff = Math.ceil((f - hoy) / (1000*60*60*24));
  if (diff <= 7) return '<span class="aud-badge is-warning">Próximo</span>';
  return '';
}

// Tarjetas de acciones urgentes
function renderUrgentes(items) {
  return items.filter(i => i.vencido || i.proximo).map(i => `<div class="aud-card urgent">${i.descripcion}</div>`).join('');
}

// Vista cronológica de seguimiento
function renderSeguimientoTimeline(seguimientos) {
  return `<ul class="aud-timeline">${seguimientos.map(s => `<li><strong>${s.fecha}</strong>: ${s.descripcion} (${s.porcentaje_avance}%)</li>`).join('')}</ul>`;
}

// Detalle expandible por auditoría
function renderAuditoriaDetalle(auditoria, detalles) {
  return `<div class="aud-card aud-expandable">
    <h3>${auditoria.nombre} <button onclick="toggleDetalle(this)">Detalle</button></h3>
    <div class="aud-detalle" style="display:none;">${detalles}</div>
  </div>`;
}
function toggleDetalle(btn) {
  const detalle = btn.parentElement.parentElement.querySelector('.aud-detalle');
  detalle.style.display = detalle.style.display === 'none' ? 'block' : 'none';
}

// Filtros por área, responsable, estado, tipo, periodo
function renderFiltros(filtros) {
  return `<div class="aud-filtros">${Object.entries(filtros).map(([k, vals]) => `<select name="${k}">${vals.map(v => `<option value="${v}">${v}</option>`).join('')}</select>`).join('')}</div>`;
}

// Búsqueda por texto
function renderBusqueda() {
  return `<input type="text" class="aud-busqueda" placeholder="Buscar..." oninput="filtrarPorTexto(this.value)" />`;
}
function filtrarPorTexto(texto) {
  // Implementar filtrado en la UI
}
