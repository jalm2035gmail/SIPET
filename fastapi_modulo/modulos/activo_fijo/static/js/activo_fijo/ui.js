export const $ = (id) => document.getElementById(id);

export const state = {
  activos: [],
  asignaciones: [],
  mantenimientos: [],
};

export const labels = {
  estado: {
    activo: 'Activo',
    asignado: 'Asignado',
    en_mantenimiento: 'En mantenimiento',
    dado_de_baja: 'Dado de baja',
  },
  metodo: {
    linea_recta: 'Linea recta',
    saldo_decreciente: 'Saldo decreciente',
  },
  tipo: {
    preventivo: 'Preventivo',
    correctivo: 'Correctivo',
    reparacion: 'Reparacion',
  },
  estadoMantenimiento: {
    pendiente: 'Pendiente',
    en_proceso: 'En proceso',
    completado: 'Completado',
  },
  motivoBaja: {
    obsolescencia: 'Obsolescencia',
    dano: 'Dano',
    venta: 'Venta',
    robo: 'Robo/Extravio',
    donacion: 'Donacion',
    otro: 'Otro',
  },
};

export function fmt(value) {
  return value != null
    ? Number(value).toLocaleString('es-MX', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })
    : '—';
}

export function fmtDate(value) {
  return value ? value.slice(0, 10) : '—';
}

export function badge(cls, label) {
  return `<span class="af-badge badge-${cls}">${label}</span>`;
}

export function showError(message) {
  alert('Error: ' + message);
}

export function openModal(id) {
  $(id).classList.add('open');
}

export function closeModal(id) {
  $(id).classList.remove('open');
}

export function bindModalEvents() {
  document.querySelectorAll('.af-modal-backdrop').forEach((modal) => {
    modal.addEventListener('click', (event) => {
      if (event.target === modal) {
        modal.classList.remove('open');
      }
    });
  });

  [
    ['modal-activo-close', 'modal-activo'],
    ['btn-activo-cancel', 'modal-activo'],
    ['modal-dep-close', 'modal-depreciar'],
    ['btn-dep-cancel', 'modal-depreciar'],
    ['modal-asig-close', 'modal-asignacion'],
    ['btn-asig-cancel', 'modal-asignacion'],
    ['modal-mant-close', 'modal-mant'],
    ['btn-mant-cancel', 'modal-mant'],
    ['modal-baja-close', 'modal-baja'],
    ['btn-baja-cancel', 'modal-baja'],
  ].forEach(([triggerId, modalId]) => {
    const trigger = $(triggerId);
    if (trigger) {
      trigger.addEventListener('click', () => closeModal(modalId));
    }
  });
}

export function rebuildActivoSelects() {
  const selectIds = [
    'filter-activo-dep',
    'filter-activo-asig',
    'filter-activo-mant',
    'dep-activo-id',
    'asig-activo-id',
    'mant-activo-id',
  ];
  selectIds.forEach((id) => {
    const select = $(id);
    if (!select) {
      return;
    }
    const currentValue = select.value;
    const isFilter = id.startsWith('filter-');
    select.innerHTML = `<option value="">${
      isFilter ? 'Todos los activos' : 'Seleccionar activo…'
    }</option>`;
    state.activos
      .filter((activo) => activo.estado !== 'dado_de_baja')
      .forEach((activo) => {
        const option = document.createElement('option');
        option.value = activo.id;
        option.textContent = `${activo.codigo} – ${activo.nombre}`;
        select.appendChild(option);
      });
    select.value = currentValue || '';
  });
}

export function bindNavigation(loaders) {
  document.querySelectorAll('.af-nav-btn').forEach((button) => {
    button.addEventListener('click', () => {
      document
        .querySelectorAll('.af-nav-btn')
        .forEach((item) => item.classList.remove('active'));
      document
        .querySelectorAll('.af-panel')
        .forEach((panel) => panel.classList.remove('active'));
      button.classList.add('active');
      const panel = document.getElementById('panel-' + button.dataset.panel);
      if (panel) {
        panel.classList.add('active');
      }
      const loader = loaders[button.dataset.panel];
      if (loader) {
        loader();
      }
    });
  });
}
