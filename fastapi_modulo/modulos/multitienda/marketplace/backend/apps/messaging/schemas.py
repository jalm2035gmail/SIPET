from pydantic import BaseModel
from typing import Optional, List

class ConversationCreate(BaseModel):
    conversation_type: str
    subject: Optional[str] = None
    vendor_id: Optional[int] = None
    product_id: Optional[int] = None
    order_id: Optional[int] = None
    tags: Optional[List[str]] = None
    initial_message: Optional[str] = None

class MessageCreate(BaseModel):
    content: str
    message_type: Optional[str] = 'text'
    parent_message_id: Optional[int] = None
    replied_to_id: Optional[int] = None

class ConversationStatusUpdate(BaseModel):
    status: str

class MessageTemplateCreate(BaseModel):
    template_type: str
    name: str
    subject: Optional[str] = None
    content: str
    variables: Optional[List[str]] = None

class SupportAssign(BaseModel):
    agent_id: int
    reassign: Optional[bool] = False
