import { api } from './api.js';
import { $, badge, fmt, labels, openModal, showError, state } from './ui.js';

export async function loadDepreciaciones() {
  const activoId = $('filter-activo-dep').value;
  const periodo = $('filter-periodo-dep').value;
  let url = '/api/activo-fijo/depreciaciones?';
  if (activoId) {
    url += `activo_id=${activoId}&`;
  }
  if (periodo) {
    url += `periodo=${periodo.slice(0, 7)}&`;
  }
  try {
    const rows = await api('GET', url);
    const tbody = $('tbody-depreciaciones');
    if (!rows.length) {
      tbody.innerHTML =
        '<tr><td colspan="7" class="af-empty">Sin depreciaciones registradas.</td></tr>';
      return;
    }
    tbody.innerHTML = rows
      .map(
        (item) => `
        <tr>
          <td>${item.periodo}</td>
          <td>${item.activo_codigo ? item.activo_codigo + ' – ' : ''}${item.activo_nombre || '—'}</td>
          <td>${labels.metodo[item.metodo] || item.metodo}</td>
          <td>$${fmt(item.valor_depreciacion)}</td>
          <td>$${fmt(item.valor_libro_anterior)}</td>
          <td>$${fmt(item.valor_libro_nuevo)}</td>
          <td><button class="af-btn af-btn-danger af-btn-sm" data-af-action="delete-dep" data-id="${item.id}">Revertir</button></td>
        </tr>`
      )
      .join('');
  } catch (error) {
    showError(error.message);
  }
}

export function bindDepreciaciones({ refreshAll }) {
  $('filter-activo-dep').addEventListener('change', loadDepreciaciones);
  $('filter-periodo-dep').addEventListener('change', loadDepreciaciones);

  $('btn-depreciar').addEventListener('click', () => {
    $('form-depreciar').reset();
    const now = new Date();
    $('dep-periodo').value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    openModal('modal-depreciar');
  });

  $('dep-activo-id').addEventListener('change', () => {
    const id = parseInt($('dep-activo-id').value, 10);
    const activo = state.activos.find((item) => item.id === id);
    $('dep-tasa-group').style.display =
      activo && activo.metodo_depreciacion === 'saldo_decreciente' ? '' : 'none';
  });
  $('dep-tasa-group').style.display = 'none';

  $('form-depreciar').addEventListener('submit', async (event) => {
    event.preventDefault();
    const activoId = $('dep-activo-id').value;
    const periodo = $('dep-periodo').value;
    const tasa = $('dep-tasa').value;
    const payload = {};
    if (periodo) {
      payload.periodo = periodo.slice(0, 7);
    }
    if (tasa) {
      payload.tasa_saldo_decreciente = parseFloat(tasa);
    }
    try {
      await api('POST', `/api/activo-fijo/activos/${activoId}/depreciar`, payload);
      document.getElementById('modal-depreciar').classList.remove('open');
      refreshAll();
      loadDepreciaciones();
    } catch (error) {
      showError(error.message);
    }
  });

  $('tbody-depreciaciones').addEventListener('click', async (event) => {
    const button = event.target.closest('[data-af-action="delete-dep"]');
    if (!button) {
      return;
    }
    if (!confirm('¿Revertir esta depreciacion? Se restaurara el valor en libros anterior.')) {
      return;
    }
    try {
      await api('DELETE', `/api/activo-fijo/depreciaciones/${button.dataset.id}`);
      refreshAll();
      loadDepreciaciones();
    } catch (error) {
      showError(error.message);
    }
  });
}
