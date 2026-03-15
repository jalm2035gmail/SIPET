from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, require_permission
from app.core.permissions import Permission, PermissionManager
from app.schemas.permission import (
    PermissionResponse, PermissionFilter,
    PermissionCategoryResponse, PermissionCreate,
    UserPermissionResponse
)
from app.crud.permission import permission as permission_crud
from app.crud.role import role as role_crud
from app.templates.api import ApiResponseTemplate

router = APIRouter(prefix="/permissions", tags=["permissions"])

@router.get("/system", response_model=List[PermissionResponse])
async def list_system_permissions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission(Permission.SYSTEM_MANAGE_PERMISSIONS))
):
    """
    Lista todos los permisos del sistema definidos en código
    """
    try:
        # Crear permisos del sistema si no existen
        permission_crud.create_system_permissions(db)
        
        # Obtener permisos del sistema
        permissions, total = permission_crud.get_multi_with_filters(
            db,
            filter_obj=PermissionFilter(is_system=True),
            limit=1000
        )
        
        return ApiResponseTemplate.success(
            data=permissions,
            message=f"{total} permisos del sistema obtenidos"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener permisos: {str(e)}"
        )

@router.get("/", response_model=List[PermissionResponse])
async def list_permissions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission(Permission.SYSTEM_MANAGE_PERMISSIONS)),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    is_system: Optional[bool] = Query(None)
):
    """
    Lista permisos con filtros (solo administradores)
    """
    try:
        filter_obj = PermissionFilter(
            category=category,
            search=search,
            is_system=is_system
        )
        
        permissions, total = permission_crud.get_multi_with_filters(
            db,
            filter_obj=filter_obj,
            skip=skip,
            limit=limit
        )
        
        return ApiResponseTemplate.paginated(
            data=permissions,
            total=total,
            skip=skip,
            limit=limit,
            metadata={
                "filters": filter_obj.model_dump(exclude_none=True)
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar permisos: {str(e)}"
        )

@router.get("/categories", response_model=List[PermissionCategoryResponse])
async def get_permission_categories(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission(Permission.SYSTEM_MANAGE_PERMISSIONS))
):
    """
    Obtiene permisos agrupados por categoría
    """
    try:
        categories = permission_crud.get_categories(db)
        
        response = []
        for category_name, permissions in categories.items():
            response.append({
                "category": category_name,
                "permissions": permissions,
                "count": len(permissions)
            })
        
        return ApiResponseTemplate.success(
            data=response,
            message=f"{len(categories)} categorías de permisos obtenidas"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener categorías: {str(e)}"
        )

@router.get("/available")
async def get_available_permissions(
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene lista de todos los permisos disponibles en el sistema
    """
    try:
        categories = PermissionManager.get_permission_categories()
        
        return ApiResponseTemplate.success(
            data=categories,
            message="Permisos disponibles obtenidos exitosamente",
            metadata={
                "total_permissions": len(Permission),
                "total_categories": len(categories)
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener permisos disponibles: {str(e)}"
        )

@router.get("/user/{user_id}", response_model=UserPermissionResponse)
async def get_user_permissions(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission(Permission.SYSTEM_MANAGE_USERS))
):
    """
    Obtiene todos los permisos de un usuario específico
    """
    try:
        permissions = role_crud.get_user_permissions(db, user_id=user_id)
        
        return ApiResponseTemplate.success(
            data=permissions,
            message="Permisos de usuario obtenidos exitosamente"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener permisos: {str(e)}"
        )

@router.get("/me")
async def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene los permisos del usuario actual
    """
    try:
        permissions = role_crud.get_user_permissions(db, user_id=current_user["id"])
        
        return ApiResponseTemplate.success(
            data=permissions,
            message="Tus permisos obtenidos exitosamente",
            metadata={
                "role": current_user["role"],
                "user_id": current_user["id"]
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener tus permisos: {str(e)}"
        )

@router.post("/", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(
    permission_in: PermissionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission(Permission.SYSTEM_MANAGE_PERMISSIONS))
):
    """
    Crear nuevo permiso personalizado
    """
    try:
        # Verificar si ya existe
        existing = permission_crud.get_by_code(db, code=permission_in.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un permiso con este código"
            )
        
        # Crear permiso
        permission = permission_crud.create(
            db,
            obj_in=permission_in,
            created_by=current_user["id"],
            updated_by=current_user["id"]
        )
        
        return ApiResponseTemplate.success(
            data=permission,
            message="Permiso creado exitosamente",
            status_code=status.HTTP_201_CREATED
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear permiso: {str(e)}"
        )

@router.get("/check/{permission_code}")
async def check_permission(
    permission_code: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Verifica si el usuario actual tiene un permiso específico
    """
    try:
        # Verificar en permisos del sistema
        try:
            system_perm = Permission(permission_code)
            has_perm = PermissionManager.has_permission(current_user["role"], system_perm)
            permission_name = system_perm.name
        except ValueError:
            # Verificar en permisos personalizados de la MAIN de datos
            user_perms = role_crud.get_user_permissions(db, user_id=current_user["id"])
            has_perm = permission_code in user_perms["permissions"]
            permission_name = permission_code
        
        return ApiResponseTemplate.success(
            data={
                "has_permission": has_perm,
                "permission": permission_code,
                "permission_name": permission_name,
                "user_role": current_user["role"]
            },
            message=f"Usuario {'TIENE' if has_perm else 'NO TIENE'} el permiso {permission_code}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al verificar permiso: {str(e)}"
        )

@router.get("/validate/role-assignment/{target_role}")
async def validate_role_assignment(
    target_role: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Valida si el usuario actual puede asignar un rol específico
    """
    try:
        can_assign = PermissionManager.can_assign_role(current_user["role"], target_role)
        
        return ApiResponseTemplate.success(
            data={
                "can_assign": can_assign,
                "assigner_role": current_user["role"],
                "target_role": target_role,
                "message": f"Rol {current_user['role']} {'PUEDE' if can_assign else 'NO PUEDE'} asignar rol {target_role}"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al validar asignación: {str(e)}"
        )
