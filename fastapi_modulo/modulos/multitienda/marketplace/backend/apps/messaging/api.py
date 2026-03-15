from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, desc, asc, func
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import json
import asyncio
from collections import defaultdict

# MODELOS Y DEPENDENCIAS LOCALES
from .models import Conversation, Message, MessageAttachment, MessageTemplate, MessageAnalytics
from backend.apps.vendors.models import Vendor
from backend.apps.users.models import User
from backend.core.dependencies import get_db, get_current_user, get_current_vendor, get_support_user
from .schemas import ConversationCreate, MessageCreate, ConversationStatusUpdate, MessageTemplateCreate, SupportAssign
# from backend.tasks.notifications import send_message_email_notification
# from backend.core.utils import should_send_email_notification

router = APIRouter(prefix="/api/messaging", tags=["messaging"])

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = defaultdict(list)
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id].append(websocket)
    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass
    async def broadcast(self, message: dict, user_ids: List[int]):
        for user_id in user_ids:
            await self.send_personal_message(message, user_id)

manager = ConnectionManager()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


# --- INICIO ENDPOINTS MENSAJERÍA ---

@router.get("/conversations")
async def get_conversations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    conversation_type: Optional[str] = None,
    unread_only: bool = Query(False),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Obtener IDs de conversaciones donde el usuario es participante
    conversation_ids = db.query(Conversation.id).join(
        Conversation.participants
    ).filter(
        User.id == current_user.id
    )
    if status:
        conversation_ids = conversation_ids.filter(Conversation.status == status)
    if conversation_type:
        conversation_ids = conversation_ids.filter(Conversation.conversation_type == conversation_type)
    if search:
        conversation_ids = conversation_ids.filter(
            or_(
                Conversation.subject.ilike(f'%{search}%'),
                Conversation.reference_id.ilike(f'%{search}%')
            )
        )
    query = db.query(Conversation).filter(
        Conversation.id.in_(conversation_ids)
    ).options(
        selectinload(Conversation.participants),
        joinedload(Conversation.product),
        joinedload(Conversation.order),
        joinedload(Conversation.vendor),
        joinedload(Conversation.last_message_by)
    )
    if unread_only:
        unread_conversations = []
        conversations = query.all()
        for conv in conversations:
            if conv.get_unread_count(current_user) > 0:
                unread_conversations.append(conv)
        total = len(unread_conversations)
        start_idx = (page - 1) * limit
        paginated = unread_conversations[start_idx:start_idx + limit]
    else:
        query = query.order_by(desc(Conversation.last_message_at))
        total = query.count()
        paginated = query.offset((page - 1) * limit).limit(limit).all()
    conversations_data = []
    for conv in paginated:
        other_participants = [p for p in conv.participants if p.id != current_user.id]
        other_participant = other_participants[0] if other_participants else None
        last_message = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).order_by(desc(Message.created_at)).first()
        conversations_data.append({
            "id": conv.id,
            "uuid": str(conv.uuid),
            "reference_id": conv.reference_id,
            "type": conv.conversation_type,
            "status": conv.status,
            "subject": conv.subject,
            "participants": [
                {
                    "id": p.id,
                    "name": f"{p.first_name} {p.last_name}",
                    "email": p.email,
                    "is_vendor": hasattr(p, 'vendor') and p.vendor is not None
                }
                for p in conv.participants
            ],
            "other_participant": {
                "id": other_participant.id,
                "name": f"{other_participant.first_name} {other_participant.last_name}",
                "avatar": other_participant.avatar_url if hasattr(other_participant, 'avatar_url') else None,
                "is_vendor": hasattr(other_participant, 'vendor') and other_participant.vendor is not None
            } if other_participant else None,
            "product": {
                "id": conv.product.id,
                "name": conv.product.name,
                "image": conv.product.primary_image
            } if conv.product else None,
            "order": {
                "id": conv.order.id,
                "order_number": conv.order.order_number
            } if conv.order else None,
            "message_count": conv.message_count,
            "unread_count": conv.get_unread_count(current_user),
            "last_message": {
                "content": last_message.content[:100] + "..." if last_message and len(last_message.content) > 100 else last_message.content if last_message else None,
                "sender_name": f"{last_message.sender.first_name} {last_message.sender.last_name}" if last_message else None,
                "created_at": last_message.created_at if last_message else None
            } if last_message else None,
            "last_message_at": conv.last_message_at,
            "created_at": conv.created_at,
            "tags": conv.tags
        })
    return {
        "conversations": conversations_data,
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }

@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.participants.any(id=current_user.id)
    ).options(
        selectinload(Conversation.participants),
        joinedload(Conversation.product),
        joinedload(Conversation.order),
        joinedload(Conversation.vendor)
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied")
    conversation.mark_as_read(current_user)
    messages_query = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).options(
        joinedload(Message.sender),
        joinedload(Message.recipient),
        selectinload(Message.attachments),
        joinedload(Message.parent_message),
        joinedload(Message.replied_to)
    ).order_by(desc(Message.created_at))
    total = messages_query.count()
    messages = messages_query.offset((page - 1) * limit).limit(limit).all()
    messages = list(reversed(messages))
    messages_data = []
    for msg in messages:
        if msg.recipient and msg.recipient.id == current_user.id and not msg.is_read:
            msg.mark_as_read(current_user)
        messages_data.append({
            "id": msg.id,
            "uuid": str(msg.uuid),
            "conversation_id": msg.conversation_id,
            "sender": {
                "id": msg.sender.id,
                "name": f"{msg.sender.first_name} {msg.sender.last_name}",
                "avatar": msg.sender.avatar_url if hasattr(msg.sender, 'avatar_url') else None,
                "is_vendor": hasattr(msg.sender, 'vendor') and msg.sender.vendor is not None
            },
            "recipient": {
                "id": msg.recipient.id,
                "name": f"{msg.recipient.first_name} {msg.recipient.last_name}"
            } if msg.recipient else None,
            "type": msg.message_type,
            "content": msg.content,
            "is_read": msg.is_read,
            "read_at": msg.read_at,
            "attachments": [
                {
                    "id": att.id,
                    "file_name": att.file_name,
                    "file_size": att.file_size,
                    "file_type": att.file_type,
                    "file_url": att.file.url if hasattr(att.file, 'url') else None,
                    "thumbnail_url": att.thumbnail.url if att.thumbnail else None,
                    "description": att.description
                }
                for att in msg.attachments
            ],
            "parent_message": {
                "id": msg.parent_message.id,
                "content": msg.parent_message.content[:100] + "..." if len(msg.parent_message.content) > 100 else msg.parent_message.content
            } if msg.parent_message else None,
            "replied_to": {
                "id": msg.replied_to.id,
                "content": msg.replied_to.content[:100] + "..." if len(msg.replied_to.content) > 100 else msg.replied_to.content
            } if msg.replied_to else None,
            "created_at": msg.created_at,
            "updated_at": msg.updated_at
        })
    other_participants = [p for p in conversation.participants if p.id != current_user.id]
    other_participant = other_participants[0] if other_participants else None
    return {
        "conversation": {
            "id": conversation.id,
            "uuid": str(conversation.uuid),
            "reference_id": conversation.reference_id,
            "type": conversation.conversation_type,
            "status": conversation.status,
            "subject": conversation.subject,
            "participants": [
                {
                    "id": p.id,
                    "name": f"{p.first_name} {p.last_name}",
                    "email": p.email,
                    "is_vendor": hasattr(p, 'vendor') and p.vendor is not None
                }
                for p in conversation.participants
            ],
            "other_participant": {
                "id": other_participant.id,
                "name": f"{other_participant.first_name} {other_participant.last_name}",
                "avatar": other_participant.avatar_url if hasattr(other_participant, 'avatar_url') else None,
                "is_vendor": hasattr(other_participant, 'vendor') and other_participant.vendor is not None
            } if other_participant else None,
            "product": {
                "id": conversation.product.id,
                "name": conversation.product.name,
                "image": conversation.product.primary_image
            } if conversation.product else None,
            "order": {
                "id": conversation.order.id,
                "order_number": conversation.order.order_number
            } if conversation.order else None,
            "message_count": conversation.message_count,
            "last_message_at": conversation.last_message_at,
            "created_at": conversation.created_at,
            "tags": conversation.tags
        },
        "messages": messages_data,
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }

@router.post("/conversations/start")
async def start_conversation(
    conversation_data: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verificar permisos basado en el tipo de conversación
    if conversation_data.conversation_type == 'customer_vendor':
        if not conversation_data.vendor_id:
            raise HTTPException(status_code=400, detail="Vendor ID is required for customer-vendor conversation")
        vendor = db.query(Vendor).filter(Vendor.id == conversation_data.vendor_id).first()
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        existing_conversation = None
        if conversation_data.product_id:
            existing_conversation = db.query(Conversation).filter(
                Conversation.conversation_type == 'customer_vendor',
                Conversation.product_id == conversation_data.product_id,
                Conversation.vendor_id == conversation_data.vendor_id,
                Conversation.participants.any(id=current_user.id),
                Conversation.status == 'active'
            ).first()
        if existing_conversation:
            return {
                "message": "Conversation already exists",
                "conversation_id": existing_conversation.id,
                "existing": True
            }
        conversation = Conversation(
            conversation_type='customer_vendor',
            subject=conversation_data.subject,
            vendor_id=conversation_data.vendor_id,
            product_id=conversation_data.product_id,
            order_id=conversation_data.order_id,
            tags=conversation_data.tags or []
        )
        db.add(conversation)
        db.commit()
        conversation.add_participant(current_user)
        conversation.add_participant(vendor.user)
    elif conversation_data.conversation_type == 'customer_support':
        conversation = Conversation(
            conversation_type='customer_support',
            subject=conversation_data.subject,
            tags=conversation_data.tags or []
        )
        db.add(conversation)
        db.commit()
        conversation.add_participant(current_user)
        support_admins = db.query(User).filter(
            User.is_staff == True,
            User.groups.any(name='Support')
        ).all()
        for admin in support_admins:
            conversation.add_participant(admin)
    else:
        raise HTTPException(status_code=400, detail="Unsupported conversation type")
    if conversation_data.initial_message:
        message = Message(
            conversation_id=conversation.id,
            sender_id=current_user.id,
            content=conversation_data.initial_message,
            message_type='text'
        )
        db.add(message)
        db.commit()
        await notify_new_message(message, db)
    return {
        "message": "Conversation started successfully",
        "conversation_id": conversation.id,
        "reference_id": conversation.reference_id,
        "existing": False
    }

@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: int,
    message_data: MessageCreate,
    files: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.participants.any(id=current_user.id)
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied")
    if not conversation.can_send_message(current_user):
        raise HTTPException(status_code=403, detail="Cannot send message in this conversation")
    other_participants = [p for p in conversation.participants if p.id != current_user.id]
    if not other_participants:
        raise HTTPException(status_code=400, detail="No recipient found")
    recipient = other_participants[0]
    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        recipient_id=recipient.id,
        content=message_data.content,
        message_type=message_data.message_type or 'text',
        parent_message_id=message_data.parent_message_id,
        replied_to_id=message_data.replied_to_id
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    if files and conversation.allow_attachments:
        for file in files:
            try:
                max_size = 10 * 1024 * 1024
                if file.size > max_size:
                    continue
                file_path = f"media/messages/{conversation_id}/{message.id}/{file.filename}"
                attachment = MessageAttachment(
                    message_id=message.id,
                    file_name=file.filename,
                    file_size=file.size,
                    file_type=file.content_type
                )
                db.add(attachment)
            except Exception as e:
                print(f"Error uploading attachment: {e}")
                continue
        db.commit()
    await notify_new_message(message, db)
    # check_auto_reply_rules(conversation, message, db)  # Implementar si es necesario
    return {
        "message": "Message sent successfully",
        "message_id": message.id,
        "conversation_id": conversation_id
    }

async def notify_new_message(message: Message, db: Session):
    conversation = message.conversation
    message_data = {
        "type": "new_message",
        "conversation_id": conversation.id,
        "message": {
            "id": message.id,
            "sender_id": message.sender_id,
            "content": message.content,
            "created_at": message.created_at.isoformat()
        }
    }
    for participant in conversation.participants:
        if participant.id != message.sender_id:
            await manager.send_personal_message(message_data, participant.id)
            # if should_send_email_notification(participant, conversation):
            #     send_message_email_notification.delay(
            #         participant.id,
            #         conversation.id,
            #         message.id
            #     )

@router.post("/conversations/{conversation_id}/status")
async def update_conversation_status(
    conversation_id: int,
    status_data: ConversationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.participants.any(id=current_user.id)
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if status_data.status == 'blocked' and not current_user.is_staff:
        raise HTTPException(status_code=403, detail="Only staff can block conversations")
    old_status = conversation.status
    conversation.status = status_data.status
    if status_data.status == 'resolved':
        conversation.closed_at = datetime.now()
    db.commit()
    system_message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=f"Conversation status changed from {old_status} to {status_data.status}",
        message_type='system'
    )
    db.add(system_message)
    db.commit()
    return {
        "message": f"Conversation status updated to {status_data.status}",
        "conversation_id": conversation_id
    }

@router.get("/templates")
async def get_message_templates(
    template_type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_vendor: Vendor = Depends(get_current_vendor)
):
    query = db.query(MessageTemplate).filter(
        MessageTemplate.vendor_id == current_vendor.id
    )
    if template_type:
        query = query.filter(MessageTemplate.template_type == template_type)
    if search:
        query = query.filter(
            or_(
                MessageTemplate.name.ilike(f'%{search}%'),
                MessageTemplate.content.ilike(f'%{search}%')
            )
        )
    templates = query.order_by(MessageTemplate.template_type, MessageTemplate.name).all()
    return {
        "templates": [
            {
                "id": t.id,
                "type": t.template_type,
                "name": t.name,
                "subject": t.subject,
                "content": t.content,
                "variables": t.variables,
                "use_count": t.use_count,
                "is_active": t.is_active
            }
            for t in templates
        ]
    }

@router.post("/templates")
async def create_message_template(
    template_data: MessageTemplateCreate,
    db: Session = Depends(get_db),
    current_vendor: Vendor = Depends(get_current_vendor)
):
    template = MessageTemplate(
        vendor_id=current_vendor.id,
        template_type=template_data.template_type,
        name=template_data.name,
        subject=template_data.subject,
        content=template_data.content,
        variables=template_data.variables or []
    )
    db.add(template)
    db.commit()
    return {
        "message": "Template created successfully",
        "template_id": template.id
    }

@router.get("/analytics")
async def get_messaging_analytics(
    period: str = Query("week", regex="^(day|week|month|quarter|year)$"),
    db: Session = Depends(get_db),
    current_vendor: Vendor = Depends(get_current_vendor)
):
    end_date = datetime.now().date()
    if period == 'day':
        start_date = end_date - timedelta(days=7)
        group_by = func.date_trunc('day', MessageAnalytics.date)
    elif period == 'week':
        start_date = end_date - timedelta(days=30)
        group_by = func.date_trunc('week', MessageAnalytics.date)
    elif period == 'month':
        start_date = end_date - timedelta(days=90)
        group_by = func.date_trunc('month', MessageAnalytics.date)
    else:
        start_date = end_date - timedelta(days=365)
        group_by = func.date_trunc('month', MessageAnalytics.date)
    analytics = db.query(
        group_by.label('period'),
        func.sum(MessageAnalytics.total_conversations).label('conversations'),
        func.sum(MessageAnalytics.total_messages).label('messages'),
        func.avg(MessageAnalytics.avg_response_time_minutes).label('avg_response_time'),
        func.avg(MessageAnalytics.customer_satisfaction_score).label('satisfaction_score')
    ).filter(
        MessageAnalytics.vendor_id == current_vendor.id,
        MessageAnalytics.date >= start_date,
        MessageAnalytics.date <= end_date
    ).group_by(group_by).order_by('period').all()
    current_stats = db.query(MessageAnalytics).filter(
        MessageAnalytics.vendor_id == current_vendor.id
    ).order_by(MessageAnalytics.date.desc()).first()
    active_conversations = db.query(Conversation).filter(
        Conversation.vendor_id == current_vendor.id,
        Conversation.status == 'active'
    ).count()
    avg_response = db.query(
        func.avg(
            func.extract('epoch', Message.created_at - Message.delivered_at) / 60
        ).label('avg_response')
    ).join(Conversation).filter(
        Conversation.vendor_id == current_vendor.id,
        Message.sender_id == current_vendor.user_id,
        Message.delivered_at.isnot(None)
    ).scalar() or 0
    return {
        "trend": [
            {
                "period": str(a.period),
                "conversations": a.conversations or 0,
                "messages": a.messages or 0,
                "avg_response_time": float(a.avg_response_time or 0),
                "satisfaction_score": float(a.satisfaction_score or 0)
            }
            for a in analytics
        ],
        "current_stats": {
            "active_conversations": active_conversations,
            "avg_response_time_minutes": float(avg_response),
            "customer_satisfaction_score": float(current_stats.customer_satisfaction_score if current_stats else 0),
            "conversation_resolution_rate": float(current_stats.conversation_resolution_rate if current_stats else 0),
            "auto_replies_sent": current_stats.auto_replies_sent if current_stats else 0
        }
    }

@router.get("/support/conversations")
async def get_support_conversations(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    assigned_to_me: bool = Query(False),
    unassigned: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_support_user)
):
    query = db.query(Conversation).filter(
        Conversation.conversation_type == 'customer_support'
    ).options(
        selectinload(Conversation.participants),
        joinedload(Conversation.product),
        joinedload(Conversation.order)
    )
    if status:
        query = query.filter(Conversation.status == status)
    if assigned_to_me:
        query = query.filter(Conversation.participants.any(id=current_user.id))
    elif unassigned:
        support_users = db.query(User).filter(
            User.is_staff == True,
            User.groups.any(name='Support')
        ).all()
        support_user_ids = [u.id for u in support_users]
        query = query.filter(
            ~Conversation.participants.any(User.id.in_(support_user_ids))
        )
    query = query.order_by(desc(Conversation.last_message_at))
    total = query.count()
    conversations = query.offset((page - 1) * limit).limit(limit).all()
    return {
        "conversations": conversations,
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }

@router.post("/support/conversations/{conversation_id}/assign")
async def assign_support_conversation(
    conversation_id: int,
    assign_data: SupportAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_support_user)
):
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.conversation_type == 'customer_support'
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Support conversation not found")
    existing_agent = None
    for participant in conversation.participants:
        if participant.is_staff and hasattr(participant, 'groups') and getattr(participant, 'groups', None) and any(getattr(g, 'name', None) == 'Support' for g in getattr(participant, 'groups', [])):
            existing_agent = participant
            break
    if existing_agent and not assign_data.reassign:
        raise HTTPException(status_code=400, detail="Conversation already assigned")
    new_agent = db.query(User).filter(User.id == assign_data.agent_id).first()
    if not new_agent or not hasattr(new_agent, 'groups') or not any(getattr(g, 'name', None) == 'Support' for g in getattr(new_agent, 'groups', [])):
        raise HTTPException(status_code=400, detail="Invalid support agent")
    conversation.add_participant(new_agent)
    system_message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=f"Conversation assigned to {new_agent.first_name} {new_agent.last_name}",
        message_type='system'
    )
    db.add(system_message)
    db.commit()
    return {
        "message": "Conversation assigned successfully",
        "conversation_id": conversation_id,
        "agent_id": new_agent.id
    }

# --- FIN ENDPOINTS MENSAJERÍA ---
