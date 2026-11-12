from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User account model."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    conversations = db.relationship(
        'Conversation',
        backref='user',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='desc(Conversation.updated_at)'
    )
    feedbacks = db.relationship(
        'Feedback',
        backref='user',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def set_password(self, password: str) -> None:
        """Hash and store the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify the user's password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        """Serialize user object."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class Conversation(db.Model):
    """Conversation thread model."""
    __tablename__ = 'conversations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(255), default='New Chat', nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationships
    messages = db.relationship(
        'Message',
        backref='conversation',
        lazy='joined',
        cascade='all, delete-orphan',
        order_by='asc(Message.created_at)'
    )

    def to_dict(self, include_messages: bool = False) -> dict:
        """Serialize conversation object."""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'message_count': len(self.messages)
        }
        if include_messages:
            data['messages'] = [msg.to_dict() for msg in self.messages]
        return data

    def __repr__(self) -> str:
        return f"<Conversation {self.id}: {self.title}>"


class Message(db.Model):
    """Individual chat message model."""
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey('conversations.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    feedbacks = db.relationship(
        'Feedback',
        backref='message',
        lazy='select',
        cascade='all, delete-orphan'
    )

    def to_dict(self, current_user_id: int = None) -> dict:
        """Serialize message object."""
        user_rating = None
        if current_user_id:
            user_feedback = next((fb for fb in self.feedbacks if fb.user_id == current_user_id), None)
            if user_feedback:
                user_rating = user_feedback.rating

        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'formatted_time': self.created_at.strftime('%I:%M %p') if self.created_at else '',
            'rating': user_rating
        }

    def __repr__(self) -> str:
        return f"<Message {self.id} [{self.role}]>"


class Feedback(db.Model):
    """User feedback for messages (thumbs up / thumbs down)."""
    __tablename__ = 'feedback'

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(
        db.Integer,
        db.ForeignKey('messages.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    rating = db.Column(db.String(10), nullable=False)  # 'up' or 'down'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Ensure one feedback per user per message
    __table_args__ = (
        db.UniqueConstraint('message_id', 'user_id', name='uq_message_user_feedback'),
    )

    def to_dict(self) -> dict:
        """Serialize feedback object."""
        return {
            'id': self.id,
            'message_id': self.message_id,
            'user_id': self.user_id,
            'rating': self.rating,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self) -> str:
        return f"<Feedback msg={self.message_id} rating={self.rating}>"

