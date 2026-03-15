import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Dict

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

from fastapi_modulo.module_registry import list_modules_payload, set_module_enabled

router = APIRouter()
_MODULES_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_MODULE_UPLOAD_TARGETS = {
    "backend": ("fastapi_modulo/modulos/frontend",),
    "conversaciones": ("fastapi_modulo/modulos/notificaciones",),
    "organizacion": ("fastapi_modulo/modulos/empleados",),
    "estrategia_tactica": ("fastapi_modulo/modulos/planificacion",),
    "datos_financieros": ("fastapi_modulo/modulos/proyectando",),
    "intelicoop": ("fastapi_modulo/modulos/intelicoop",),
    "brujula": ("fastapi_modulo/modulos/brujula",),
    "crm": ("fastapi_modulo/modulos/crm",),
    "encuestas": ("fastapi_modulo/modulos/encuestas",),
    "auditoria": ("fastapi_modulo/modulos/auditoria",),
    "activo_fijo": ("fastapi_modulo/modulos/activo_fijo",),
    "control_seguimiento": ("fastapi_modulo/modulos/control_interno",),
    "kpis": ("fastapi_modulo/modulos/kpis",),
    "reportes": ("reportes",),
    "capacitacion": ("fastapi_modulo/modulos/capacitacion",),
    "multiempresa": ("fastapi_modulo/modulos/multiempresa",),
}


def _get_module_image_path(module_key: str) -> str | None:
    target_root = _get_module_upload_root(module_key)
    if not target_root:
        return None
    image_root = Path(target_root) / "imagenes"
    if not image_root.is_dir():
        return None
    preferred_stems = [str(module_key or "").strip().lower()]
    for candidate in image_root.iterdir():
        if not candidate.is_file():
            continue
        if candidate.suffix.lower() not in {".svg", ".png", ".jpg", ".jpeg", ".backendp", ".ico"}:
            continue
        if candidate.stem.strip().lower() in preferred_stems:
            return str(candidate)
    for candidate in sorted(image_root.iterdir()):
        if candidate.is_file() and candidate.suffix.lower() in {".svg", ".png", ".jpg", ".jpeg", ".backendp", ".ico"}:
            return str(candidate)
    return None


class _ModuleStateIn(BaseModel):
    enabled: bool


def _require_superadmin(request: Request) -> None:
    from fastapi_modulo.main import get_current_role

    role = (get_current_role(request) or "").strip().lower()
    if role not in {"superadministrador", "superadmin"}:
        raise HTTPException(status_code=403, detail="Acceso restringido a superadministrador")


def _get_module_upload_root(module_key: str) -> str | None:
    relative_path = _MODULE_UPLOAD_TARGETS.get(str(module_key or "").strip())
    if not relative_path:
        return None
    target_root = os.path.abspath(os.path.join(_PROJECT_ROOT, *relative_path))
    if not os.path.isdir(target_root):
        return None
    return target_root


def _iter_zip_members(archive: zipfile.ZipFile, target_root: str):
    target_dir_name = os.path.MAINname(os.path.normpath(target_root))
    file_infos = [info for info in archive.infolist() if not info.is_dir()]
    file_infos = [info for info in file_infos if not PurePosixPath(info.filename.replace("\\", "/")).name.startswith(".DS_Store")]
    file_infos = [info for info in file_infos if not info.filename.replace("\\", "/").startswith("__MACOSX/")]
    if not file_infos:
        raise HTTPException(status_code=400, detail="El archivo ZIP no contiene archivos válidos.")

    normalized_parts: list[tuple[zipfile.ZipInfo, tuple[str, ...]]] = []
    for info in file_infos:
        raw_name = info.filename.replace("\\", "/").lstrip("/")
        path = PurePosixPath(raw_name)
        if raw_name == "" or path.is_absolute() or ".." in path.parts:
            raise HTTPException(status_code=400, detail="El ZIP contiene rutas inválidas.")
        normalized_parts.append((info, tuple(part for part in path.parts if part not in {"", "."})))

    first_parts = {parts[0] for _, parts in normalized_parts if parts}
    strip_first_segment = len(first_parts) == 1 and next(iter(first_parts)) in {target_dir_name, "src", "package"}

    for info, parts in normalized_parts:
        rel_parts = parts[1:] if strip_first_segment and len(parts) > 1 else parts
        if not rel_parts:
            continue
        destination = os.path.abspath(os.path.join(target_root, *rel_parts))
        if os.path.commonpath([target_root, destination]) != target_root:
            raise HTTPException(status_code=400, detail="El ZIP intenta escribir fuera del módulo.")
        yield info, destination


def _extract_module_zip(module_key: str, zip_path: str) -> Dict[str, Any]:
    target_root = _get_module_upload_root(module_key)
    if not target_root:
        raise HTTPException(status_code=400, detail="Este módulo todavía no admite actualización por ZIP.")

    extracted_files = 0
    with zipfile.ZipFile(zip_path, "r") as archive:
        for info, destination in _iter_zip_members(archive, target_root):
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            with archive.open(info, "r") as source, open(destination, "wb") as target:
                shutil.copyfileobj(source, target)
            extracted_files += 1
    if extracted_files == 0:
        raise HTTPException(status_code=400, detail="El ZIP no contiene archivos para actualizar.")
    return {
        "module_key": module_key,
        "target_root": target_root,
        "updated_files": extracted_files,
    }


def _render_page(modules: list[Dict[str, Any]]) -> str:
    bootstrap = json.dumps({"modules": modules}, ensure_ascii=True)
    return f"""
<section class="mod-shell" id="system-modules-root" data-bootstrap='{bootstrap}'>
  <style>
    .mod-shell {{
      display: grid;
      gap: 22px;
      padding: 24px;
    }}
    .mod-hero {{
      display: grid;
      gap: 10px;
      padding: 24px 28px;
      border: 1px solid rgba(15,23,42,.08);
      border-radius: 24px;
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 48%, #ea580c 100%);
      color: #fff;
    }}
    .mod-hero h1 {{
      margin: 0;
      font-size: clamp(28px, 4vw, 44px);
      line-height: .95;
      letter-spacing: -.03em;
    }}
    .mod-hero p {{
      margin: 0;
      max-width: 780px;
      color: rgba(255,255,255,.82);
      font-size: 15px;
      line-height: 1.65;
    }}
    .mod-note {{
      padding: 14px 16px;
      border-radius: 18px;
      background: #fff7ed;
      border: 1px solid #fdba74;
      color: #9a3412;
      font-size: 14px;
      line-height: 1.55;
    }}
    .kanban-item[data-enabled="false"] {{
      opacity: .82;
      background: linear-gradient(180deg, #fff, #f8fafc);
    }}
    .mod-color {{
      background: #fff;
      color: #0f172a;
      border-right: 1px solid rgba(15, 23, 42, .08);
      position: relative;
      overflow: hidden;
    }}
    .mod-color img {{
      width: 58px;
      height: 58px;
      object-fit: contain;
      display: block;
      position: relative;
      z-index: 1;
    }}
    .mod-color-text {{
      position: relative;
      z-index: 1;
    }}
    .mod-color-icon {{
      position: relative;
      z-index: 1;
      font-size: 52px;
      line-height: 1;
    }}
    .mod-copy {{
      display: grid;
      gap: 8px;
    }}
    .mod-badges {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .mod-badge {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: .05em;
      text-transform: uppercase;
    }}
    .mod-badge.active {{
      background: #dcfce7;
      color: #166534;
    }}
    .mod-badge.inactive {{
      background: #fee2e2;
      color: #991b1b;
    }}
    .mod-badge.meta {{
      background: #eff6ff;
      color: #1d4ed8;
    }}
    .mod-card-foot {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding-top: 10px;
      margin-top: 2px;
      border-top: 1px solid rgba(15,23,42,.08);
    }}
    .mod-switch {{
      display: inline-flex;
      align-items: center;
      gap: 12px;
      font-size: 14px;
      color: #0f172a;
      font-weight: 600;
    }}
    .mod-switch input {{
      width: 18px;
      height: 18px;
    }}
    .mod-link {{
      font-size: 13px;
      color: #2563eb;
      text-decoration: none;
      font-weight: 700;
    }}
    .mod-actions {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }}
    .mod-btn {{
      border: 0;
      border-radius: 999px;
      padding: 9px 14px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      background: #0f172a;
      color: #fff;
    }}
    .mod-btn[disabled] {{
      cursor: not-allowed;
      opacity: .55;
    }}
    .mod-empty {{
      grid-column: 1 / -1;
    }}
    .mod-toast {{
      position: fixed;
      right: 24px;
      bottom: 24px;
      z-index: 9999;
      padding: 12px 16px;
      border-radius: 14px;
      background: #0f172a;
      color: #fff;
      opacity: 0;
      pointer-events: none;
      transition: opacity .2s ease;
    }}
    .mod-toast.show {{
      opacity: 1;
    }}
  </style>
  <header class="mod-hero">
    <div>Módulos del sistema</div>
    <h1>Activa o desactiva módulos</h1>
    <p>Los módulos activos se registran al arrancar la aplicación. Desactivar un módulo lo oculta del sidebar y evita registrar sus routers en el siguiente reinicio, lo que reduce carga de arranque y consumo innecesario.</p>
  </header>
  <div class="mod-note">Los cambios se guardan de inmediato, pero para liberar recursos y desmontar rutas debes reiniciar la aplicación con <code>./reiniciar.sh</code>.</div>
  <div class="kanban" id="mod-grid"></div>
  <input type="file" id="mod-upload-input" accept=".zip,application/zip" hidden>
  <div class="mod-toast" id="mod-toast"></div>
  <script>
    (function () {{
      var root = document.getElementById('system-modules-root');
      if (!root) return;
      var initial = JSON.parse(root.getAttribute('data-bootstrap') || '{{"modules":[]}}');
      var modules = Array.isArray(initial.modules) ? initial.modules : [];
      var grid = document.getElementById('mod-grid');
      var toastNode = document.getElementById('mod-toast');
      var uploadInput = document.getElementById('mod-upload-input');
      var activeUploadModule = '';

      function toast(message) {{
        if (!toastNode) return;
        toastNode.textContent = message || '';
        toastNode.classList.add('show');
        clearTimeout(toast._timer);
        toast._timer = setTimeout(function () {{ toastNode.classList.remove('show'); }}, 2600);
      }}

      function esc(value) {{
        return String(value == null ? '' : value)
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;')
          .replace(/'/g, '&#39;');
      }}

      function render() {{
        var items = modules.filter(function (item) {{ return item.manageable; }});
        if (!items.length) {{
          grid.innerHTML = '<div class="kanban-empty mod-empty">No hay módulos administrables disponibles.</div>';
          return;
        }}
        grid.innerHTML = items.map(function (item) {{
          var label = String(item.label || '');
          var initials = esc(label.split(/\s+/).filter(Boolean).slice(0, 2).map(function (part) {{
            return part.charAt(0);
          }}).join('').toUpperCase() || 'M');
          var colorHtml = item.image_url
            ? '<img src="' + esc(item.image_url) + '" alt="' + esc(item.label) + '">'
            : (item.icon
              ? '<i class="' + esc(item.icon) + ' mod-color-icon" aria-hidden="true"></i>'
              : '<span class="mod-color-text">' + initials + '</span>');
          return '' +
            '<article class="kanban-item" data-enabled="' + (item.enabled ? 'true' : 'false') + '">' +
              '<div class="kanban-color mod-color">' + colorHtml + '</div>' +
              '<div class="kanban-content">' +
                '<div class="mod-copy">' +
                  '<h3 class="kanban-title">' + esc(item.label) + '</h3>' +
                  '<p class="kanban-meta">' + esc(item.description || '') + '</p>' +
                '</div>' +
              '<div class="mod-badges">' +
                '<span class="mod-badge ' + (item.enabled ? 'active' : 'inactive') + '">' + (item.enabled ? 'Activo' : 'Inactivo') + '</span>' +
                '<span class="mod-badge meta">' + esc(item.boot_strategy === 'builtin' ? 'Integrado en main' : 'Router diferido') + '</span>' +
                '<span class="mod-badge meta">' + esc(String(item.router_count || 0) + ' router(s)') + '</span>' +
              '</div>' +
              '<div class="mod-card-foot">' +
                '<label class="mod-switch">' +
                  '<input type="checkbox" data-toggle-module="' + esc(item.key) + '"' + (item.enabled ? ' checked' : '') + '>' +
                  '<span>' + (item.enabled ? 'Desactivar' : 'Activar') + '</span>' +
                '</label>' +
                '<div class="mod-actions">' +
                  '<button class="mod-btn" type="button" data-upload-module="' + esc(item.key) + '"' + (item.package_upload_enabled ? '' : ' disabled title="Disponible solo para módulos extraídos a directorio propio"') + '>Actualizar</button>' +
                  (item.route ? '<a class="mod-link" href="' + esc(item.route) + '">Abrir</a>' : '<span></span>') +
                '</div>' +
              '</div>' +
              (item.package_upload_enabled ? '<div class="kanban-meta">ZIP destino: ' + esc(item.package_target_label || '') + '</div>' : '<div class="kanban-meta">Actualización por ZIP pendiente de extraer desde main.py.</div>') +
              '</div>' +
            '</article>';
        }}).join('');
      }}

      async function updateModule(key, enabled, input) {{
        try {{
          var res = await fetch('/api/system/modules/' + encodeURIComponent(key), {{
            method: 'PUT',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ enabled: !!enabled }})
          }});
          var data = await res.json();
          if (!res.ok) throw new Error(data.detail || data.error || 'No se pudo actualizar el módulo.');
          modules = modules.map(function (item) {{
            return item.key === key ? Object.assign({{}}, item, data) : item;
          }});
          render();
          toast('Módulo actualizado. Reinicia la aplicación para aplicar el cambio.');
        }} catch (error) {{
          if (input) input.checked = !enabled;
          toast(error.message || 'No se pudo actualizar el módulo.');
        }} finally {{
          if (input) input.disabled = false;
        }}
      }}

      grid.addEventListener('change', function (event) {{
        var input = event.target.closest('[data-toggle-module]');
        if (!input) return;
        input.disabled = true;
        updateModule(input.getAttribute('data-toggle-module') || '', !!input.checked, input);
      }});

      async function uploadModulePackage(key, file, button) {{
        if (!key || !file) return;
        try {{
          if (button) {{
            button.disabled = true;
            button.textContent = 'Subiendo...';
          }}
          var formData = new FormData();
          formData.append('package', file);
          var res = await fetch('/api/system/modules/' + encodeURIComponent(key) + '/upload', {{
            method: 'POST',
            body: formData
          }});
          var data = await res.json();
          if (!res.ok) throw new Error(data.detail || data.error || 'No se pudo actualizar el módulo.');
          toast('ZIP aplicado en ' + (data.updated_files || 0) + ' archivo(s). Reinicia la aplicación para cargar los cambios.');
        }} catch (error) {{
          toast(error.message || 'No se pudo actualizar el módulo.');
        }} finally {{
          if (button) {{
            button.disabled = false;
            button.textContent = 'Actualizar';
          }}
          if (uploadInput) uploadInput.value = '';
          activeUploadModule = '';
        }}
      }}

      grid.addEventListener('click', function (event) {{
        var button = event.target.closest('[data-upload-module]');
        if (!button || button.disabled || !uploadInput) return;
        activeUploadModule = button.getAttribute('data-upload-module') || '';
        uploadInput.click();
      }});

      uploadInput && uploadInput.addEventListener('change', function () {{
        var file = uploadInput.files && uploadInput.files[0];
        if (!file || !activeUploadModule) return;
        if (!/\.zip$/i.test(file.name || '')) {{
          toast('Selecciona un archivo ZIP.');
          uploadInput.value = '';
          activeUploadModule = '';
          return;
        }}
        var button = grid.querySelector('[data-upload-module="' + CSS.escape(activeUploadModule) + '"]');
        uploadModulePackage(activeUploadModule, file, button);
      }});

      render();
    }})();
  </script>
</section>
"""


def _decorate_modules_payload(items: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    for item in items:
        target_root = _get_module_upload_root(str(item.get("key") or ""))
        item["package_upload_enabled"] = bool(target_root)
        item["package_target_label"] = os.path.relpath(target_root, _PROJECT_ROOT) if target_root else ""
        image_path = _get_module_image_path(str(item.get("key") or ""))
        if image_path and os.path.exists(image_path):
            item["image_url"] = f"/api/system/modules/assets/{item['key']}/{os.path.MAINname(image_path)}"
    return items


@router.get("/modulos", response_class=HTMLResponse)
def system_modules_page(request: Request):
    _require_superadmin(request)
    from fastapi_modulo.main import render_backend_page

    modules = _decorate_modules_payload(list_modules_payload())
    content = _render_page(modules)
    return render_backend_page(
        request,
        title="Módulos",
        description="Activa o desactiva módulos del sistema.",
        content=content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/api/system/modules")
def system_modules_list(request: Request):
    _require_superadmin(request)
    return JSONResponse(_decorate_modules_payload(list_modules_payload()))


@router.put("/api/system/modules/{module_key}")
def system_modules_update(module_key: str, body: _ModuleStateIn, request: Request):
    _require_superadmin(request)
    try:
        return JSONResponse(_decorate_modules_payload([set_module_enabled(module_key, body.enabled)])[0])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/api/system/modules/{module_key}/upload")
async def system_modules_upload(module_key: str, request: Request, package: UploadFile = File(...)):
    _require_superadmin(request)
    filename = str(package.filename or "").strip()
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Debes subir un archivo .zip.")

    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
            temp_path = temp_file.name
            while True:
                chunk = await package.read(1024 * 1024)
                if not chunk:
                    break
                temp_file.write(chunk)
        try:
            with zipfile.ZipFile(temp_path, "r") as archive:
                if archive.testzip() is not None:
                    raise HTTPException(status_code=400, detail="El archivo ZIP está corrupto.")
        except zipfile.BadZipFile as exc:
            raise HTTPException(status_code=400, detail="El archivo ZIP no es válido.") from exc
        result = _extract_module_zip(module_key, temp_path)
        return JSONResponse(result)
    finally:
        await package.close()
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@router.get("/api/system/modules/assets/{module_key}/{filename}")
def system_module_asset(module_key: str, filename: str, request: Request):
    _require_superadmin(request)
    image_path = _get_module_image_path(str(module_key or "").strip())
    if not image_path:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    if filename != os.path.MAINname(image_path):
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    return FileResponse(image_path)
