import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Date, Enum, Text, JSON, UniqueConstraint, Index, Time
from sqlalchemy.orm import relationship, backref
from core.db import Base

class ConversationType(str, enum.Enum):
    customer_vendor = "customer_vendor"
    vendor_vendor = "vendor_vendor"
    customer_support = "customer_support"
    admin_broadcast = "admin_broadcast"

class ConversationStatus(str, enum.Enum):
    active = "active"
    archived = "archived"
    blocked = "blocked"
    resolved = "resolved"

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    reference_id = Column(String(50), unique=True, nullable=True)
    conversation_type = Column(Enum(ConversationType), nullable=False)
    status = Column(Enum(ConversationStatus), default=ConversationStatus.active)
    subject = Column(String(200), default="")
    tags = Column(JSON, default=list)
    message_count = Column(Integer, default=0)
    last_message_at = Column(DateTime, nullable=True)
    last_message_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    auto_close_hours = Column(Integer, default=72)
    allow_attachments = Column(Boolean, default=True)
    is_read_by_participants = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    # Foreign keys for context
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    # Relationships
    last_message_by = relationship("User", foreign_keys=[last_message_by_id])
    product = relationship("Product")
    order = relationship("Order")
    vendor = relationship("VendorStore")
    messages = relationship("Message", back_populates="conversation")
    notes = relationship("ConversationNote", back_populates="conversation")
    participants = relationship("User", secondary="conversation_participants", back_populates="conversations")
    __table_args__ = (
        Index("ix_conversation_uuid", "uuid"),
        Index("ix_conversation_status_lastmsg", "status", "last_message_at"),
        Index("ix_conversation_type_status", "conversation_type", "status"),
        Index("ix_conversation_product_status", "product_id", "status"),
        Index("ix_conversation_order_status", "order_id", "status"),
    )

class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"
    conversation_id = Column(Integer, ForeignKey("conversations.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    joined_at = Column(DateTime, default=datetime.utcnow)
    # Relationships
    conversation = relationship("Conversation", backref=backref("conversation_participants"))
    user = relationship("User", backref=backref("conversation_participants"))

class MessageType(str, enum.Enum):
    text = "text"
    image = "image"
    file = "file"
    system = "system"
    order_update = "order_update"
    product_update = "product_update"

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    message_type = Column(Enum(MessageType), default=MessageType.text)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    parent_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    replied_to_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])
    recipient = relationship("User", foreign_keys=[recipient_id])
    parent_message = relationship("Message", remote_side=[id], foreign_keys=[parent_message_id], backref="replies")
    replied_to = relationship("Message", remote_side=[id], foreign_keys=[replied_to_id], backref="replies_to")
    attachments = relationship("MessageAttachment", back_populates="message")
    __table_args__ = (
        Index("ix_message_conversation_created", "conversation_id", "created_at"),
        Index("ix_message_sender_created", "sender_id", "created_at"),
        Index("ix_message_recipient_isread", "recipient_id", "is_read"),
        Index("ix_message_created", "created_at"),
    )

class MessageAttachment(Base):
    __tablename__ = "message_attachments"
    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey("messages.id"))
    file = Column(String, nullable=False)
    file_name = Column(String(255))
    file_size = Column(Integer)
    file_type = Column(String(50))
    thumbnail = Column(String, nullable=True)
    description = Column(String(200), default="")
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    message = relationship("Message", back_populates="attachments")

class MessageTemplateType(str, enum.Enum):
    greeting = "greeting"
    order_confirmation = "order_confirmation"
    shipping_update = "shipping_update"
    customer_service = "customer_service"
    product_inquiry = "product_inquiry"
    follow_up = "follow_up"

class MessageTemplate(Base):
    __tablename__ = "message_templates"
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    template_type = Column(Enum(MessageTemplateType))
    name = Column(String(100))
    subject = Column(String(200), default="")
    content = Column(Text, nullable=False)
    variables = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    use_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    vendor = relationship("VendorStore")

class ConversationNote(Base):
    __tablename__ = "conversation_notes"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    author_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    conversation = relationship("Conversation", back_populates="notes")
    author = relationship("User")

class AutoReplyRuleType(str, enum.Enum):
    keyword = "keyword"
    time = "time"
    absence = "absence"
    first_message = "first_message"

class AutoReplyRule(Base):
    __tablename__ = "auto_reply_rules"
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    rule_type = Column(Enum(AutoReplyRuleType))
    name = Column(String(100))
    keywords = Column(JSON, default=list)
    trigger_time = Column(Time, nullable=True)
    response_delay_minutes = Column(Integer, default=30)
    template_id = Column(Integer, ForeignKey("message_templates.id"))
    is_active = Column(Boolean, default=True)
    last_triggered = Column(DateTime, nullable=True)
    trigger_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    vendor = relationship("VendorStore")
    template = relationship("MessageTemplate")

class MessageAnalytics(Base):
    __tablename__ = "message_analytics"
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    date = Column(Date, nullable=False)
    total_conversations = Column(Integer, default=0)
    new_conversations = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    messages_sent = Column(Integer, default=0)
    messages_received = Column(Integer, default=0)
    avg_response_time_minutes = Column(Integer, default=0)
    first_response_time_minutes = Column(Integer, default=0)
    customer_satisfaction_score = Column(Integer, default=0)
    conversation_resolution_rate = Column(Integer, default=0)
    auto_replies_sent = Column(Integer, default=0)
    template_usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    vendor = relationship("VendorStore")
    __table_args__ = (
        UniqueConstraint('vendor_id', 'date', name='uq_vendor_date'),
        Index("ix_message_analytics_vendor_date", "vendor_id", "date"),
    )
