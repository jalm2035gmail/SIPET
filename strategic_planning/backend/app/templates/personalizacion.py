from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.templates.MAIN_template import render_MAIN
from app.models.permission import Role
from app.core.permissions import PermissionManager

router = APIRouter()

@router.get("/personalizacion/roles-permisos", response_class=HTMLResponse)
def roles_permisos(request: Request):
    # Obtener roles y permisos
    roles = Role.query.all() if hasattr(Role, 'query') else []
    permissions = [
        {
            "code": p.value,
            "name": p.name,
            "category": p.name.split('_')[0],
            "description": PermissionManager.get_permission_description(p)
        }
        for p in PermissionManager.get_role_permissions("super_admin")
    ]
    return render_MAIN(
        request,
        title="Roles y Permisos",
        content=render_roles_permisos_html(roles, permissions)
    )

def render_roles_permisos_html(roles, permissions):
    from jinja2 import Template
    with open("strategic_planning/backend/app/templates/permissions/roles_permissions.html") as f:
        template = Template(f.read())
    return template.render(roles=roles, permissions=permissions)
