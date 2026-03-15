
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse

from strategic_planning.backend.app.templates.MAIN_template import render_MAIN
from strategic_planning.backend.app.models.permission import Role
from strategic_planning.backend.app.models.user import User, UserRole
from strategic_planning.backend.app.core.permissions import PermissionManager
from strategic_planning.backend.app.dataMAIN import get_db
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/roles-permisos", response_class=HTMLResponse)
async def roles_permisos(request: Request):
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
    from jinja2 import Template
    with open("strategic_planning/backend/app/templates/permissions/roles_permissions.html", encoding="utf-8") as f:
        template = Template(f.read())
    content = template.render(roles=roles, permissions=permissions)
    return render_MAIN(request, title="Roles y Permisos", content=content)


@router.get("/superadmin-status")
def superadmin_status(db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.name == UserRole.SUPER_ADMIN.value).first()
    user = None
    if role:
        user = db.query(User).filter(User.role_string == UserRole.SUPER_ADMIN.value).first()

    return JSONResponse(
        {
            "role": {
                "name": role.name if role else None,
                "display_name": role.display_name if role else None,
                "is_system": role.is_system if role else False,
                "description": role.description if role else None,
            },
            "user": {
                "id": user.id if user else None,
                "username": user.username if user else None,
                "email": user.email if user else None,
                "status": user.status.value if user else None,
            },
            "has_role": bool(role),
            "has_user": bool(user),
        }
    )
