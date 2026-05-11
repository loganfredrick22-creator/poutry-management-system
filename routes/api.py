from __future__ import annotations

from datetime import timedelta

import pandas as pd
from flask import Blueprint, jsonify
from flask_login import login_required
from sqlalchemy import func

from models import Bird, EggProduction, Flock, HealthEvent, MortalityLog, WeightRecord, db
from utils import today

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/population-trend")
@login_required
def population_trend():
    # 6-month labels by month start
    t = today()
    labels = []
    alive = []
    sold = []
    dead = []

    # Build month buckets ending current month
    month_starts = []
    cur = t.replace(day=1)
    for i in range(5, -1, -1):
        # approximate month shift
        d = (cur - timedelta(days=30 * i)).replace(day=1)
        month_starts.append(d)

    for ms in month_starts:
        labels.append(ms.strftime("%b %Y"))
        alive.append(db.session.query(func.count(Bird.id)).filter(Bird.status == "alive", Bird.registration_date <= ms + timedelta(days=31)).scalar() or 0)
        sold.append(db.session.query(func.count(Bird.id)).filter(Bird.status == "sold", Bird.registration_date <= ms + timedelta(days=31)).scalar() or 0)
        dead.append(db.session.query(func.count(Bird.id)).filter(Bird.status == "dead", Bird.registration_date <= ms + timedelta(days=31)).scalar() or 0)

    return jsonify({"labels": labels, "alive": alive, "sold": sold, "dead": dead})


@bp.get("/flock-composition")
@login_required
def flock_composition():
    labels = ["Broiler", "Layer", "Breeder"]
    values = []
    for c in labels:
        values.append(db.session.query(func.count(Flock.id)).filter(Flock.category == c).scalar() or 0)
    return jsonify({"labels": labels, "values": values})


@bp.get("/bird/<leg_band_number>/weights")
@login_required
def bird_weights(leg_band_number: str):
    bird = db.session.query(Bird).filter_by(leg_band_number=leg_band_number).first()
    if not bird:
        return jsonify({"labels": [], "values": []})
    recs = (
        db.session.query(WeightRecord)
        .filter(WeightRecord.bird_id == bird.id)
        .order_by(WeightRecord.recorded_date.asc())
        .all()
    )
    labels = [r.recorded_date.strftime("%Y-%m-%d") for r in recs]
    values = [float(r.weight_kg) for r in recs]
    return jsonify({"labels": labels, "values": values})


@bp.get("/bird/<leg_band_number>/eggs-weekly")
@login_required
def bird_eggs_weekly(leg_band_number: str):
    bird = db.session.query(Bird).filter_by(leg_band_number=leg_band_number).first()
    if not bird:
        return jsonify({"labels": [], "values": []})
    recs = (
        db.session.query(EggProduction)
        .filter(EggProduction.bird_id == bird.id)
        .order_by(EggProduction.date.asc())
        .all()
    )
    if not recs:
        return jsonify({"labels": [], "values": []})

    df = pd.DataFrame([{"d": r.date, "c": r.count} for r in recs])
    df["week"] = df["d"].apply(lambda x: x - timedelta(days=x.weekday()))
    weekly = df.groupby("week")["c"].sum().reset_index().sort_values("week")
    labels = [d.strftime("Wk %Y-%m-%d") for d in weekly["week"].tolist()]
    values = [int(x) for x in weekly["c"].tolist()]
    return jsonify({"labels": labels, "values": values})


@bp.get("/flock/<int:flock_id>/mortality-trend")
@login_required
def flock_mortality_trend(flock_id: int):
    # 12-week mortality rate
    t = today()
    labels = []
    values = []
    for i in range(11, -1, -1):
        start = t - timedelta(days=7 * (i + 1))
        end = t - timedelta(days=7 * i)
        labels.append(end.strftime("%b %d"))

        deaths = (
            db.session.query(func.count(MortalityLog.id))
            .join(Bird, Bird.id == MortalityLog.bird_id)
            .filter(Bird.flock_id == flock_id, MortalityLog.death_date >= start, MortalityLog.death_date < end)
            .scalar()
            or 0
        )
        total = db.session.query(func.count(Bird.id)).filter(Bird.flock_id == flock_id).scalar() or 0
        values.append(float(deaths) / float(total) if total else 0.0)
    return jsonify({"labels": labels, "values": values})

