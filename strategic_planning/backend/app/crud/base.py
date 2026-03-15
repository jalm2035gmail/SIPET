from __future__ import annotations

from typing import Any, Dict, Generic, Optional, Type, TypeVar, Union

from pydantic import MAINModel
from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=MAINModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=MAINModel)


class CRUDMAIN(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """MAIN CRUD que expone operaciones básicas sobre modelos SQLAlchemy."""

    def __init__(self, model: Type[ModelType]) -> None:
        self.model = model

    def get(self, db: Session, *, id: Any) -> Optional[ModelType]:
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> list[ModelType]:
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        obj_data = obj_in.model_dump()
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
    ) -> ModelType:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: Any) -> Optional[ModelType]:
        obj = self.get(db, id=id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
