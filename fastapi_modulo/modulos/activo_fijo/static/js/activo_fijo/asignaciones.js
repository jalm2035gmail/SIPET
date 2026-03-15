import { api } from './api.js';
import { $, badge, fmtDate, openModal, showError, state } from './ui.js';

async function fetchAsignaciones(url = '/api/activo-fijo/asignaciones') {
  state.asignaciones = await api('GET', url);
  return state.asignaciones;
}

export async function loadAsignaciones() {
  const activoId = $('filter-activo-asig').value;
  const estado = $('filter-estado-asig').value;
  let url = '/api/activo-fijo/asignaciones?';
  if (activoId) {
    url += `activo_id=${activoId}&`;
  }
  if (estado) {
    url += `estado=${estado}&`;
  }
  try {
    const rows = await fetchAsignaciones(url);
    const tbody = $('tbody-asignaciones');
    if (!rows.length) {
      tbody.innerHTML =
        '<tr><td colspan="7" class="af-empty">Sin asignaciones registradas.</td></tr>';
      return;
    }
    tbody.innerHTML = rows
      .map(
        (item) => `
        <tr>
          <td>${item.activo_codigo ? item.activo_codigo + ' – ' : ''}${item.activo_nombre || '—'}</td>
          <td>${item.empleado || '—'}</td>
          <td>${item.area || '—'}</td>
          <td>${fmtDate(item.fecha_asignacion)}</td>
          <td>${fmtDate(item.fecha_devolucion)}</td>
          <td>${badge(item.estado, item.estado === 'vigente' ? 'Vigente' : 'Devuelto')}</td>
          <td class="af-nowrap">
            <button class="af-btn af-btn-secondary af-btn-sm" data-af-action="edit-asig" data-id="${item.id}">Editar</button>
            <button class="af-btn af-btn-danger af-btn-sm" data-af-action="delete-asig" data-id="${item.id}">Eliminar</button>
          </td>
        </tr>`
      )
      .join('');
  } catch (error) {
    showError(error.message);
  }
}

export function bindAsignaciones({ refreshAll }) {
  $('filter-activo-asig').addEventListener('change', loadAsignaciones);
  $('filter-estado-asig').addEventListener('change', loadAsignaciones);

  $('btn-nueva-asignacion').addEventListener('click', () => {
    $('modal-asig-title').textContent = 'Nueva asignacion';
    $('form-asignacion').reset();
    $('asig-id').value = '';
    $('asig-fecha').value = new Date().toISOString().slice(0, 10);
    openModal('modal-asignacion');
  });

  $('tbody-asignaciones').addEventListener('click', async (event) => {
    const button = event.target.closest('[data-af-action]');
    if (!button) {
      return;
    }
    const id = Number(button.dataset.id);
    if (button.dataset.afAction === 'edit-asig') {
      if (!state.asignaciones.length) {
        await fetchAsignaciones();
      }
      const asignacion = state.asignaciones.find((item) => item.id === id);
      if (!asignacion) {
        return;
      }
      $('modal-asig-title').textContent = 'Editar asignacion';
      $('asig-id').value = id;
      $('asig-activo-id').value = asignacion.activo_id;
      $('asig-empleado').value = asignacion.empleado || '';
      $('asig-area').value = asignacion.area || '';
      $('asig-fecha').value = asignacion.fecha_asignacion
        ? asignacion.fecha_asignacion.slice(0, 10)
        : '';
      $('asig-fecha-dev').value = asignacion.fecha_devolucion
        ? asignacion.fecha_devolucion.slice(0, 10)
        : '';
      $('asig-estado').value = asignacion.estado || 'vigente';
      $('asig-obs').value = asignacion.observaciones || '';
      openModal('modal-asignacion');
      return;
    }
    if (!confirm('¿Eliminar esta asignacion?')) {
      return;
    }
    try {
      await api('DELETE', `/api/activo-fijo/asignaciones/${id}`);
      state.asignaciones = [];
      await loadAsignaciones();
      refreshAll();
    } catch (error) {
      showError(error.message);
    }
  });

  $('form-asignacion').addEventListener('submit', async (event) => {
    event.preventDefault();
    const id = $('asig-id').value;
    const payload = {
      activo_id: parseInt($('asig-activo-id').value, 10),
      empleado: $('asig-empleado').value.trim(),
      area: $('asig-area').value.trim() || null,
      fecha_asignacion: $('asig-fecha').value || null,
      fecha_devolucion: $('asig-fecha-dev').value || null,
      estado: $('asig-estado').value,
      observaciones: $('asig-obs').value.trim() || null,
    };
    try {
      if (id) {
        await api('PUT', `/api/activo-fijo/asignaciones/${id}`, payload);
      } else {
        await api('POST', '/api/activo-fijo/asignaciones', payload);
      }
      state.asignaciones = [];
      document.getElementById('modal-asignacion').classList.remove('open');
      await loadAsignaciones();
      refreshAll();
    } catch (error) {
      showError(error.message);
    }
  });
}
