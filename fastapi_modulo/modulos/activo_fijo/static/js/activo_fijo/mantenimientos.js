import { api } from './api.js';
import { $, badge, fmt, fmtDate, labels, openModal, showError, state } from './ui.js';

export async function loadMantenimientos() {
  const activoId = $('filter-activo-mant').value;
  const estado = $('filter-estado-mant').value;
  let url = '/api/activo-fijo/mantenimientos?';
  if (activoId) {
    url += `activo_id=${activoId}&`;
  }
  if (estado) {
    url += `estado=${estado}&`;
  }
  try {
    state.mantenimientos = await api('GET', url);
    const tbody = $('tbody-mantenimiento');
    if (!state.mantenimientos.length) {
      tbody.innerHTML =
        '<tr><td colspan="7" class="af-empty">Sin mantenimientos registrados.</td></tr>';
      return;
    }
    tbody.innerHTML = state.mantenimientos
      .map(
        (item) => `
        <tr>
          <td>${item.activo_codigo ? item.activo_codigo + ' – ' : ''}${item.activo_nombre || '—'}</td>
          <td>${badge(item.tipo, labels.tipo[item.tipo] || item.tipo)}</td>
          <td>${item.descripcion || '—'}</td>
          <td>${fmtDate(item.fecha_inicio)}</td>
          <td>${item.costo != null ? '$' + fmt(item.costo) : '—'}</td>
          <td>${badge(item.estado, labels.estadoMantenimiento[item.estado] || item.estado)}</td>
          <td class="af-nowrap">
            <button class="af-btn af-btn-secondary af-btn-sm" data-af-action="edit-mant" data-id="${item.id}">Editar</button>
            <button class="af-btn af-btn-danger af-btn-sm" data-af-action="delete-mant" data-id="${item.id}">Eliminar</button>
          </td>
        </tr>`
      )
      .join('');
  } catch (error) {
    showError(error.message);
  }
}

export function bindMantenimientos({ refreshAll }) {
  $('filter-activo-mant').addEventListener('change', loadMantenimientos);
  $('filter-estado-mant').addEventListener('change', loadMantenimientos);

  $('btn-nuevo-mant').addEventListener('click', () => {
    $('modal-mant-title').textContent = 'Registrar mantenimiento';
    $('form-mant').reset();
    $('mant-id').value = '';
    $('mant-fecha-inicio').value = new Date().toISOString().slice(0, 10);
    openModal('modal-mant');
  });

  $('tbody-mantenimiento').addEventListener('click', async (event) => {
    const button = event.target.closest('[data-af-action]');
    if (!button) {
      return;
    }
    const id = Number(button.dataset.id);
    if (button.dataset.afAction === 'edit-mant') {
      const mantenimiento = state.mantenimientos.find((item) => item.id === id);
      if (!mantenimiento) {
        return;
      }
      $('modal-mant-title').textContent = 'Editar mantenimiento';
      $('mant-id').value = id;
      $('mant-activo-id').value = mantenimiento.activo_id;
      $('mant-tipo').value = mantenimiento.tipo || 'preventivo';
      $('mant-estado').value = mantenimiento.estado || 'pendiente';
      $('mant-fecha-inicio').value = mantenimiento.fecha_inicio
        ? mantenimiento.fecha_inicio.slice(0, 10)
        : '';
      $('mant-fecha-fin').value = mantenimiento.fecha_fin
        ? mantenimiento.fecha_fin.slice(0, 10)
        : '';
      $('mant-proveedor').value = mantenimiento.proveedor || '';
      $('mant-costo').value = mantenimiento.costo || '';
      $('mant-descripcion').value = mantenimiento.descripcion || '';
      $('mant-obs').value = mantenimiento.observaciones || '';
      openModal('modal-mant');
      return;
    }
    if (!confirm('¿Eliminar este registro de mantenimiento?')) {
      return;
    }
    try {
      await api('DELETE', `/api/activo-fijo/mantenimientos/${id}`);
      await loadMantenimientos();
      refreshAll();
    } catch (error) {
      showError(error.message);
    }
  });

  $('form-mant').addEventListener('submit', async (event) => {
    event.preventDefault();
    const id = $('mant-id').value;
    const payload = {
      activo_id: parseInt($('mant-activo-id').value, 10),
      tipo: $('mant-tipo').value,
      estado: $('mant-estado').value,
      fecha_inicio: $('mant-fecha-inicio').value || null,
      fecha_fin: $('mant-fecha-fin').value || null,
      proveedor: $('mant-proveedor').value.trim() || null,
      costo: $('mant-costo').value ? parseFloat($('mant-costo').value) : null,
      descripcion: $('mant-descripcion').value.trim(),
      observaciones: $('mant-obs').value.trim() || null,
    };
    try {
      if (id) {
        await api('PUT', `/api/activo-fijo/mantenimientos/${id}`, payload);
      } else {
        await api('POST', '/api/activo-fijo/mantenimientos', payload);
      }
      document.getElementById('modal-mant').classList.remove('open');
      await loadMantenimientos();
      refreshAll();
    } catch (error) {
      showError(error.message);
    }
  });
}
