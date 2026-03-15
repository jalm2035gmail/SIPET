import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.MAIN import MAINModel


class TokenType(str, enum.Enum):
    VERIFICATION = "verification"
    PASSWORD_RESET = "password_reset"
    REFRESH = "refresh"
    ACCESS = "access"
    API_KEY = "api_key"


class Token(MAINModel):
    __tablename__ = "tokens"

    token = Column(String(500), unique=True, index=True, nullable=False)
    token_type = Column(Enum(TokenType), nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoke_reason = Column(String(200), nullable=True)

    last_used_at = Column(DateTime(timezone=True), nullable=True)
    use_count = Column(Integer, default=0, nullable=False)

    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)

    user = relationship("User", back_populates="tokens")

    def is_valid(self) -> bool:
        if self.revoked:
            return False
        if self.expires_at < datetime.utcnow():
            return False
        return True

    def revoke(self, reason: str | None = None) -> None:
        self.revoked = True
        self.revoked_at = datetime.utcnow()
        self.revoke_reason = reason

    def record_usage(self, user_agent: str | None = None, ip_address: str | None = None) -> None:
        self.last_used_at = datetime.utcnow()
        self.use_count += 1
        if user_agent:
            self.user_agent = user_agent
        if ip_address:
            self.ip_address = ip_address

    def __repr__(self) -> str:
        return f"<Token(id={self.id}, type='{self.token_type}', user_id={self.user_id})>"
