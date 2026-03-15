from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import TokenUtils
from app.crud.MAIN import CRUDMAIN
from app.models.token import Token, TokenType


class CRUDToken(CRUDMAIN[Token, dict, dict]):
    """CRUD operations for Token model."""

    def get_by_token(self, db: Session, token: str) -> Optional[Token]:
        return db.query(Token).filter(Token.token == token).first()

    def create_access_token(
        self,
        db: Session,
        *,
        user_id: int,
        expires_in_minutes: int = 30,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Token:
        expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        jwt_token = TokenUtils.create_access_token(
            data={"sub": str(user_id)}, expires_delta=timedelta(minutes=expires_in_minutes)
        )
        db_obj = Token(
            token=jwt_token,
            token_type=TokenType.ACCESS,
            user_id=user_id,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def create_refresh_token(
        self,
        db: Session,
        *,
        user_id: int,
        expires_in_days: int = 7,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Token:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        jwt_token = TokenUtils.create_refresh_token(
            data={"sub": str(user_id)}, expires_delta=timedelta(days=expires_in_days)
        )
        db_obj = Token(
            token=jwt_token,
            token_type=TokenType.REFRESH,
            user_id=user_id,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def create_password_reset_token(
        self,
        db: Session,
        *,
        user_id: int,
        expires_in_hours: int = 24,
    ) -> Token:
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        import secrets

        token = secrets.token_urlsafe(32)
        db_obj = Token(
            token=token,
            token_type=TokenType.PASSWORD_RESET,
            user_id=user_id,
            expires_at=expires_at,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def create_verification_token(
        self,
        db: Session,
        *,
        user_id: int,
        expires_in_hours: int = 24,
    ) -> Token:
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        import secrets

        token = secrets.token_urlsafe(32)
        db_obj = Token(
            token=token,
            token_type=TokenType.VERIFICATION,
            user_id=user_id,
            expires_at=expires_at,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def verify_token(
        self,
        db: Session,
        *,
        token: str,
        token_type: TokenType,
    ) -> Optional[Token]:
        db_obj = self.get_by_token(db, token=token)
        if not db_obj or db_obj.token_type != token_type or not db_obj.is_valid():
            return None
        return db_obj

    def revoke_token(self, db: Session, *, token: str, reason: Optional[str] = None) -> bool:
        db_obj = self.get_by_token(db, token=token)
        if not db_obj:
            return False
        db_obj.revoke(reason)
        db.add(db_obj)
        db.commit()
        return True

    def revoke_all_user_tokens(
        self,
        db: Session,
        *,
        user_id: int,
        token_type: Optional[TokenType] = None,
        reason: Optional[str] = None,
    ) -> int:
        query = db.query(Token).filter(Token.user_id == user_id, Token.revoked == False)
        if token_type:
            query = query.filter(Token.token_type == token_type)
        tokens = query.all()
        for token in tokens:
            token.revoke(reason)
            db.add(token)
        db.commit()
        return len(tokens)

    def cleanup_expired_tokens(self, db: Session) -> int:
        result = db.query(Token).filter(Token.expires_at < datetime.utcnow()).delete()
        db.commit()
        return result


token_crud = CRUDToken(Token)
