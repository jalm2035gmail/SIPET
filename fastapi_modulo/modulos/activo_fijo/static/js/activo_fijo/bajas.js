import { api } from './api.js';
import { $, fmt, fmtDate, labels, showError } from './ui.js';

export async function loadBajas() {
  try {
    const rows = await api('GET', '/api/activo-fijo/bajas');
    const tbody = $('tbody-bajas');
    if (!rows.length) {
      tbody.innerHTML =
        '<tr><td colspan="6" class="af-empty">Sin activos dados de baja.</td></tr>';
      return;
    }
    tbody.innerHTML = rows
      .map(
        (item) => `
        <tr>
          <td>${item.activo_codigo ? item.activo_codigo + ' – ' : ''}${item.activo_nombre || '—'}</td>
          <td>${labels.motivoBaja[item.motivo] || item.motivo}</td>
          <td>${fmtDate(item.fecha_baja)}</td>
          <td>${item.valor_residual_real != null ? '$' + fmt(item.valor_residual_real) : '—'}</td>
          <td>${item.observaciones || '—'}</td>
          <td><button class="af-btn af-btn-secondary af-btn-sm" data-af-action="reactivar-baja" data-id="${item.id}">Reactivar</button></td>
        </tr>`
      )
      .join('');
  } catch (error) {
    showError(error.message);
  }
}

export function bindBajas({ refreshAll }) {
  $('form-baja').addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = {
      activo_id: parseInt($('baja-activo-id').value, 10),
      motivo: $('baja-motivo').value,
      fecha_baja: $('baja-fecha').value || null,
      valor_residual_real: parseFloat($('baja-valor-residual').value) || 0,
      observaciones: $('baja-obs').value.trim() || null,
    };
    try {
      await api('POST', '/api/activo-fijo/bajas', payload);
      document.getElementById('modal-baja').classList.remove('open');
      await loadBajas();
      refreshAll();
    } catch (error) {
      showError(error.message);
    }
  });

  $('tbody-bajas').addEventListener('click', async (event) => {
    const button = event.target.closest('[data-af-action="reactivar-baja"]');
    if (!button) {
      return;
    }
    if (!confirm('¿Reactivar este activo? Se eliminara el registro de baja.')) {
      return;
    }
    try {
      await api('DELETE', `/api/activo-fijo/bajas/${button.dataset.id}`);
      await loadBajas();
      refreshAll();
    } catch (error) {
      showError(error.message);
    }
  });
}
