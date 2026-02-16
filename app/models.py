from datetime import datetime, timezone
from flask_login import UserMixin
from app import db, login_manager


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    birth_date = db.Column(db.Date, nullable=True)
    gender = db.Column(db.Enum("male", "female", "other", name="gender_enum"), nullable=True)
    sexual_preference = db.Column(
        db.Enum("heterosexual", "homosexual", "bisexual", name="sexual_preference_enum"), nullable=True
    )
    biography = db.Column(db.Text, nullable=True)
    profile_picture_id = db.Column(db.Integer, db.ForeignKey("user_images.id", use_alter=True), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    location_enabled = db.Column(db.Boolean, default=False)
    fame_rating = db.Column(db.Integer, default=0)
    email_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(128), nullable=True)
    reset_token = db.Column(db.String(128), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    is_online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    profile_picture = db.relationship("UserImage", foreign_keys=[profile_picture_id])
    images = db.relationship("UserImage", backref="user", foreign_keys="UserImage.user_id", lazy="dynamic")


class UserImage(db.Model):
    __tablename__ = "user_images"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    is_profile_picture = db.Column(db.Boolean, default=False)
    upload_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=utcnow)


class Tag(db.Model):
    __tablename__ = "tags"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def __init__(self, name=None, **kwargs):
        if name is not None:
            name = name.lower().strip()
        super(Tag, self).__init__(name=name, **kwargs)


class UserTag(db.Model):
    __tablename__ = "user_tags"
    __table_args__ = (db.Index("ix_user_tags_tag_id", "tag_id"),)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey("tags.id"), primary_key=True)


class Like(db.Model):
    __tablename__ = "likes"
    id = db.Column(db.Integer, primary_key=True)
    liker_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    liked_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    __table_args__ = (db.UniqueConstraint("liker_id", "liked_id", name="uq_liker_liked"),)


class ProfileView(db.Model):
    __tablename__ = "profile_views"
    __table_args__ = (db.Index("ix_profile_views_viewed_at", "viewed_id", "viewed_at"),)
    id = db.Column(db.Integer, primary_key=True)
    viewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    viewed_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    viewed_at = db.Column(db.DateTime, default=utcnow)


class Block(db.Model):
    __tablename__ = "blocks"
    id = db.Column(db.Integer, primary_key=True)
    blocker_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    blocked_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    __table_args__ = (db.UniqueConstraint("blocker_id", "blocked_id", name="uq_blocker_blocked"),)


class Report(db.Model):
    __tablename__ = "reports"
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reported_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)


class Message(db.Model):
    __tablename__ = "messages"
    __table_args__ = (db.Index("ix_messages_receiver_read_created", "receiver_id", "is_read", "created_at"),)
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow)


class Notification(db.Model):
    __tablename__ = "notifications"
    __table_args__ = (db.Index("ix_notifications_user_read_created", "user_id", "is_read", "created_at"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    type = db.Column(
        db.Enum("like", "view", "message", "match", "unlike", "event", name="notification_type_enum"), nullable=False
    )
    related_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    message_id = db.Column(db.Integer, db.ForeignKey("messages.id"), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow)


class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    invitee_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    event_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(300), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    status = db.Column(
        db.Enum("pending", "accepted", "declined", "cancelled", name="event_status_enum"),
        default="pending"
    )
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    creator = db.relationship("User", foreign_keys=[creator_id], backref="created_events")
    invitee = db.relationship("User", foreign_keys=[invitee_id], backref="invited_events")
