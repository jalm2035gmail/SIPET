import { api } from './api.js';
import {
  $,
  badge,
  fmt,
  labels,
  openModal,
  rebuildActivoSelects,
  showError,
  state,
} from './ui.js';

function renderActivos() {
  const query = $('filter-nombre-activo').value.toLowerCase();
  const rows = state.activos.filter((activo) => {
    return (
      !query ||
      activo.nombre.toLowerCase().includes(query) ||
      (activo.codigo || '').toLowerCase().includes(query)
    );
  });
  const tbody = $('tbody-activos');
  if (!rows.length) {
    tbody.innerHTML =
      '<tr><td colspan="8" class="af-empty">Sin activos registrados.</td></tr>';
    return;
  }
  tbody.innerHTML = rows
    .map(
      (activo) => `
      <tr>
        <td>${activo.codigo || '—'}</td>
        <td>${activo.nombre}</td>
        <td>${activo.categoria || '—'}</td>
        <td>$${fmt(activo.valor_adquisicion)}</td>
        <td>$${fmt(activo.valor_libro)}</td>
        <td>${labels.metodo[activo.metodo_depreciacion] || activo.metodo_depreciacion}</td>
        <td>${badge(activo.estado, labels.estado[activo.estado] || activo.estado)}</td>
        <td class="af-nowrap">
          <button class="af-btn af-btn-secondary af-btn-sm" data-af-action="edit-activo" data-id="${activo.id}">Editar</button>
          <button class="af-btn af-btn-warning af-btn-sm" data-af-action="baja-activo" data-id="${activo.id}">Baja</button>
          <button class="af-btn af-btn-danger af-btn-sm" data-af-action="delete-activo" data-id="${activo.id}">Eliminar</button>
        </td>
      </tr>`
    )
    .join('');
}

export async function loadActivos() {
  const estado = $('filter-estado-activo').value;
  try {
    const url = '/api/activo-fijo/activos' + (estado ? `?estado=${estado}` : '');
    state.activos = await api('GET', url);
    rebuildActivoSelects();
    renderActivos();
  } catch (error) {
    showError(error.message);
  }
}

export function bindActivos({ refreshAll }) {
  $('filter-estado-activo').addEventListener('change', loadActivos);
  $('filter-nombre-activo').addEventListener('input', renderActivos);

  $('btn-nuevo-activo').addEventListener('click', () => {
    $('modal-activo-title').textContent = 'Nuevo activo';
    $('form-activo').reset();
    $('activo-id').value = '';
    $('activo-vida-util').value = '60';
    $('activo-valor-residual').value = '0';
    openModal('modal-activo');
  });

  $('tbody-activos').addEventListener('click', async (event) => {
    const button = event.target.closest('[data-af-action]');
    if (!button) {
      return;
    }
    const id = Number(button.dataset.id);
    if (button.dataset.afAction === 'edit-activo') {
      const activo = state.activos.find((item) => item.id === id);
      if (!activo) {
        return;
      }
      $('modal-activo-title').textContent = 'Editar activo';
      $('activo-id').value = id;
      $('activo-codigo').value = activo.codigo || '';
      $('activo-nombre').value = activo.nombre || '';
      $('activo-categoria').value = activo.categoria || '';
      $('activo-marca').value = activo.marca || '';
      $('activo-modelo').value = activo.modelo || '';
      $('activo-serie').value = activo.numero_serie || '';
      $('activo-proveedor').value = activo.proveedor || '';
      $('activo-fecha-adq').value = activo.fecha_adquisicion
        ? activo.fecha_adquisicion.slice(0, 10)
        : '';
      $('activo-valor-adq').value = activo.valor_adquisicion || '0';
      $('activo-valor-residual').value = activo.valor_residual || '0';
      $('activo-vida-util').value = activo.vida_util_meses || 60;
      $('activo-metodo-dep').value = activo.metodo_depreciacion || 'linea_recta';
      $('activo-ubicacion').value = activo.ubicacion || '';
      $('activo-responsable').value = activo.responsable || '';
      $('activo-estado').value = activo.estado || 'activo';
      $('activo-descripcion').value = activo.descripcion || '';
      openModal('modal-activo');
      return;
    }
    if (button.dataset.afAction === 'baja-activo') {
      const activo = state.activos.find((item) => item.id === id);
      if (!activo) {
        return;
      }
      $('baja-activo-id').value = id;
      $('baja-activo-nombre').value = `${activo.codigo || ''} – ${activo.nombre}`;
      $('baja-fecha').value = new Date().toISOString().slice(0, 10);
      $('baja-valor-residual').value = activo.valor_residual || '0';
      $('baja-obs').value = '';
      openModal('modal-baja');
      return;
    }
    if (!confirm('¿Eliminar este activo? Se perderán todos sus registros asociados.')) {
      return;
    }
    try {
      await api('DELETE', `/api/activo-fijo/activos/${id}`);
      refreshAll();
    } catch (error) {
      showError(error.message);
    }
  });

  $('form-activo').addEventListener('submit', async (event) => {
    event.preventDefault();
    const id = $('activo-id').value;
    const payload = {
      codigo: $('activo-codigo').value.trim() || null,
      nombre: $('activo-nombre').value.trim(),
      categoria: $('activo-categoria').value.trim() || null,
      marca: $('activo-marca').value.trim() || null,
      modelo: $('activo-modelo').value.trim() || null,
      numero_serie: $('activo-serie').value.trim() || null,
      proveedor: $('activo-proveedor').value.trim() || null,
      fecha_adquisicion: $('activo-fecha-adq').value || null,
      valor_adquisicion: parseFloat($('activo-valor-adq').value) || 0,
      valor_residual: parseFloat($('activo-valor-residual').value) || 0,
      vida_util_meses: parseInt($('activo-vida-util').value, 10) || 60,
      metodo_depreciacion: $('activo-metodo-dep').value,
      ubicacion: $('activo-ubicacion').value.trim() || null,
      responsable: $('activo-responsable').value.trim() || null,
      estado: $('activo-estado').value,
      descripcion: $('activo-descripcion').value.trim() || null,
    };
    try {
      if (id) {
        await api('PUT', `/api/activo-fijo/activos/${id}`, payload);
      } else {
        await api('POST', '/api/activo-fijo/activos', payload);
      }
      document.getElementById('modal-activo').classList.remove('open');
      refreshAll();
    } catch (error) {
      showError(error.message);
    }
  });
}
