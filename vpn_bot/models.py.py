from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    tablename = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    username = Column(String)
    lang = Column(String, default="ru")
    reg_date = Column(DateTime, default=datetime.utcnow)
    referrer_id = Column(Integer, nullable=True)
    total_stars_spent = Column(Integer, default=0)

class Subscription(Base):
    tablename = "subscriptions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    key_id = Column(Integer, ForeignKey("keys.id"))
    server_id = Column(Integer)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    is_active = Column(Boolean, default=True)

class Key(Base):
    tablename = "keys"
    id = Column(Integer, primary_key=True)
    key_string = Column(String)
    config_text = Column(String)
    outline_key_id = Column(String)
    server_id = Column(Integer)

class Payment(Base):
    tablename = "payments"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    amount_stars = Column(Integer)
    status = Column(String)
    telegram_payload = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Ticket(Base):
    tablename = "tickets"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    message = Column(String)
    status = Column(String, default="open")
    created_at = Column(DateTime, default=datetime.utcnow)

class Referral(Base):
    tablename = "referrals"
    id = Column(Integer, primary_key=True)
    referrer_id = Column(Integer)
    referred_id = Column(Integer)
    bonus_days_awarded = Column(Integer)