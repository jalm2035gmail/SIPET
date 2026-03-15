import { bindActivos, loadActivos } from './activos.js';
import { bindAsignaciones, loadAsignaciones } from './asignaciones.js';
import { bindDepreciaciones, loadDepreciaciones } from './depreciaciones.js';
import { bindBajas, loadBajas } from './bajas.js';
import { loadKpis } from './kpis.js';
import { bindMantenimientos, loadMantenimientos } from './mantenimientos.js';
import { bindModalEvents, bindNavigation } from './ui.js';

function refreshAll() {
  loadKpis();
  loadActivos();
}

bindModalEvents();
bindNavigation({
  activos: loadActivos,
  depreciaciones: loadDepreciaciones,
  asignaciones: loadAsignaciones,
  mantenimiento: loadMantenimientos,
  bajas: loadBajas,
});
bindActivos({ refreshAll });
bindDepreciaciones({ refreshAll });
bindAsignaciones({ refreshAll });
bindMantenimientos({ refreshAll });
bindBajas({ refreshAll });

loadKpis();
loadActivos();
