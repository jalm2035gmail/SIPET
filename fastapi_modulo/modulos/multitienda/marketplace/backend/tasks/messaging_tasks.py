from celery import shared_task
from datetime import datetime, timedelta, date
import logging
from sqlalchemy.orm import Session
from backend.core.db import SessionLocal
from backend.apps.messaging.models import Message, Conversation, AutoReplyRule, MessageAnalytics
from backend.apps.vendors.models import Vendor
# from backend.apps.notifications.utils import send_email_notification
# from backend.apps.surveys.models import Survey

logger = logging.getLogger(__name__)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@shared_task
def send_message_notification(message_id: int):
    """Enviar notificación por email de nuevo mensaje (placeholder)"""
    db = SessionLocal()
    try:
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message or not message.recipient:
            return
        # if not message.recipient.notification_preferences.get('new_messages', True):
        #     return
        # subject = f"New message from {message.sender.first_name}"
        # context = {...}
        # send_email_notification(to_email=message.recipient.email, subject=subject, template_name='new_message', context=context)
        logger.info(f"Would send message notification to {message.recipient.email}")
    except Exception as e:
        logger.error(f"Error sending message notification: {e}")
    finally:
        db.close()

@shared_task
def send_auto_reply(rule_id: int, conversation_id: int, trigger_message_id: int):
    """Enviar respuesta automática basada en reglas"""
    db = SessionLocal()
    try:
        rule = db.query(AutoReplyRule).filter(AutoReplyRule.id == rule_id).first()
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        trigger_message = db.query(Message).filter(Message.id == trigger_message_id).first()
        if not rule or not conversation or not trigger_message:
            return
        if conversation.status != 'active':
            return
        # context = {...}
        reply_content = rule.template or "Auto-reply"
        auto_message = Message(
            conversation_id=conversation.id,
            sender_id=rule.vendor_id,
            recipient_id=trigger_message.sender_id,
            content=reply_content,
            message_type='text'
        )
        db.add(auto_message)
        db.commit()
        logger.info(f"Sent auto-reply to conversation {conversation_id}")
    except Exception as e:
        logger.error(f"Error sending auto-reply: {e}")
    finally:
        db.close()

@shared_task
def close_inactive_conversations():
    """Cerrar conversaciones inactivas automáticamente"""
    db = SessionLocal()
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=72)
        inactive_conversations = db.query(Conversation).filter(
            Conversation.status == 'active',
            Conversation.last_message_at < cutoff_time
        ).all()
        closed_count = 0
        for conversation in inactive_conversations:
            conversation.status = 'closed'
            conversation.closed_at = datetime.utcnow()
            db.add(conversation)
            closed_count += 1
        db.commit()
        logger.info(f"Closed {closed_count} inactive conversations")
    except Exception as e:
        logger.error(f"Error closing inactive conversations: {e}")
    finally:
        db.close()

@shared_task
def update_message_analytics():
    """Actualizar analíticas de mensajería"""
    db = SessionLocal()
    try:
        today = date.today()
        vendors = db.query(Vendor).filter(Vendor.status == 'approved').all()
        for vendor in vendors:
            analytics = db.query(MessageAnalytics).filter(
                MessageAnalytics.vendor_id == vendor.id,
                MessageAnalytics.date == today
            ).first()
            if not analytics:
                analytics = MessageAnalytics(vendor_id=vendor.id, date=today)
                db.add(analytics)
            conversations = db.query(Conversation).filter(Conversation.vendor_id == vendor.id)
            today_conversations = conversations.filter(Conversation.created_at >= datetime.combine(today, datetime.min.time()))
            today_messages = db.query(Message).filter(
                Message.conversation.has(vendor_id=vendor.id),
                Message.created_at >= datetime.combine(today, datetime.min.time())
            )
            analytics.total_conversations = conversations.count()
            analytics.new_conversations = today_conversations.count()
            analytics.total_messages = db.query(Message).filter(Message.conversation.has(vendor_id=vendor.id)).count()
            analytics.messages_sent = today_messages.filter(Message.sender_id == vendor.user_id).count()
            analytics.messages_received = today_messages.filter(Message.sender_id != vendor.user_id).count()
            # Tiempo promedio de respuesta (simplificado)
            analytics.avg_response_time_minutes = 0
            db.commit()
            logger.info(f"Updated messaging analytics for vendor {vendor.id}")
    except Exception as e:
        logger.error(f"Error updating messaging analytics: {e}")
    finally:
        db.close()

@shared_task
def send_conversation_followup(conversation_id: int):
    """Enviar seguimiento automático después de conversación resuelta (placeholder)"""
    db = SessionLocal()
    try:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation or conversation.status != 'resolved':
            return
        # if conversation.closed_at > datetime.utcnow() - timedelta(hours=24):
        #     return
        # survey = Survey(...)
        # followup_message = Message(...)
        logger.info(f"Would send follow-up survey for conversation {conversation_id}")
    except Exception as e:
        logger.error(f"Error sending conversation follow-up: {e}")
    finally:
        db.close()
