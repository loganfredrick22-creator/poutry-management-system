from __future__ import annotations

from datetime import date, datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="admin")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Flock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    house_location = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(30), nullable=False)  # Broiler/Layer/Breeder
    start_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    birds = relationship("Bird", back_populates="flock", cascade="all, delete-orphan")


class Bird(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    leg_band_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    breed = db.Column(db.String(80), nullable=False)
    category = db.Column(db.String(30), nullable=False)  # Broiler/Layer/Breeder
    hatch_date = db.Column(db.Date, nullable=False)
    flock_id = db.Column(db.Integer, db.ForeignKey("flock.id"), nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default="alive")  # alive/sold/dead
    registration_date = db.Column(db.Date, nullable=False, default=date.today)
    weight_kg = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    flock = relationship("Flock", back_populates="birds")
    health_events = relationship("HealthEvent", back_populates="bird", cascade="all, delete-orphan")
    mortality_log = relationship("MortalityLog", back_populates="bird", cascade="all, delete-orphan")
    weight_records = relationship("WeightRecord", back_populates="bird", cascade="all, delete-orphan")
    egg_production = relationship("EggProduction", back_populates="bird", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="bird", cascade="all, delete-orphan")


class HealthEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bird_id = db.Column(db.Integer, db.ForeignKey("bird.id"), nullable=False, index=True)
    event_type = db.Column(db.String(20), nullable=False)  # vaccination/disease/treatment/checkup
    event_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=False)
    medicine_used = db.Column(db.String(120), nullable=True)
    dose = db.Column(db.String(80), nullable=True)
    recorded_by = db.Column(db.String(80), nullable=False)
    severity = db.Column(db.String(10), nullable=False, default="Low")  # Low/Medium/High
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    bird = relationship("Bird", back_populates="health_events")


class MortalityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bird_id = db.Column(db.Integer, db.ForeignKey("bird.id"), nullable=False, index=True)
    death_date = db.Column(db.Date, nullable=False)
    cause = db.Column(db.String(120), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    recorded_by = db.Column(db.String(80), nullable=False)

    bird = relationship("Bird", back_populates="mortality_log")


class WeightRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bird_id = db.Column(db.Integer, db.ForeignKey("bird.id"), nullable=False, index=True)
    recorded_date = db.Column(db.Date, nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)

    bird = relationship("Bird", back_populates="weight_records")


class EggProduction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bird_id = db.Column(db.Integer, db.ForeignKey("bird.id"), nullable=False, index=True)
    flock_id = db.Column(db.Integer, db.ForeignKey("flock.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    count = db.Column(db.Integer, nullable=False, default=0)

    bird = relationship("Bird", back_populates="egg_production")


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bird_id = db.Column(db.Integer, db.ForeignKey("bird.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    field_changed = db.Column(db.String(80), nullable=False)
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    bird = relationship("Bird", back_populates="audit_logs")

