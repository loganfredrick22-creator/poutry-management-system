from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.preprocessing import StandardScaler
from sqlalchemy import func

from models import AuditLog, Bird, EggProduction, Flock, HealthEvent, MortalityLog, WeightRecord, db
from utils import clamp_int, today


def bird_vaccination_count(bird_id: int) -> int:
    return (
        db.session.query(func.count(HealthEvent.id))
        .filter(HealthEvent.bird_id == bird_id, HealthEvent.event_type == "vaccination")
        .scalar()
        or 0
    )


def bird_health_event_count(bird_id: int) -> int:
    return db.session.query(func.count(HealthEvent.id)).filter(HealthEvent.bird_id == bird_id).scalar() or 0


def bird_last_disease_date(bird_id: int):
    return (
        db.session.query(func.max(HealthEvent.event_date))
        .filter(HealthEvent.bird_id == bird_id, HealthEvent.event_type == "disease")
        .scalar()
    )


def flock_mortality_rate_7d(flock_id: Optional[int]) -> float:
    if not flock_id:
        return 0.0
    since = today() - timedelta(days=7)
    deaths = (
        db.session.query(func.count(MortalityLog.id))
        .join(Bird, Bird.id == MortalityLog.bird_id)
        .filter(Bird.flock_id == flock_id, MortalityLog.death_date >= since)
        .scalar()
        or 0
    )
    total = db.session.query(func.count(Bird.id)).filter(Bird.flock_id == flock_id).scalar() or 0
    if total <= 0:
        return 0.0
    return float(deaths) / float(total)


def disease_event_count_7d(flock_id: Optional[int]) -> int:
    if not flock_id:
        return 0
    since = today() - timedelta(days=7)
    return (
        db.session.query(func.count(HealthEvent.id))
        .join(Bird, Bird.id == HealthEvent.bird_id)
        .filter(Bird.flock_id == flock_id, HealthEvent.event_type == "disease", HealthEvent.event_date >= since)
        .scalar()
        or 0
    )


def vaccination_coverage_pct(flock_id: Optional[int]) -> float:
    if not flock_id:
        return 0.0
    birds = db.session.query(Bird).filter(Bird.flock_id == flock_id, Bird.status == "alive").all()
    if not birds:
        return 0.0
    since = today() - timedelta(days=45)
    covered = 0
    for b in birds:
        has_recent = (
            db.session.query(func.count(HealthEvent.id))
            .filter(HealthEvent.bird_id == b.id, HealthEvent.event_type == "vaccination", HealthEvent.event_date >= since)
            .scalar()
            or 0
        )
        if has_recent > 0:
            covered += 1
    return 100.0 * covered / max(1, len(birds))


def avg_health_score_for_flock(flock_id: int) -> float:
    birds = db.session.query(Bird).filter(Bird.flock_id == flock_id, Bird.status == "alive").all()
    if not birds:
        return 0.0
    scores = [calc_bird_health_score(b) for b in birds]
    return float(np.mean(scores)) if scores else 0.0


def weight_trend_slope_kg_per_day(bird_id: int) -> float:
    recs = (
        db.session.query(WeightRecord)
        .filter(WeightRecord.bird_id == bird_id)
        .order_by(WeightRecord.recorded_date.asc())
        .all()
    )
    if len(recs) < 3:
        return 0.0
    base = recs[0].recorded_date
    X = np.array([(r.recorded_date - base).days for r in recs], dtype=float).reshape(-1, 1)
    y = np.array([r.weight_kg for r in recs], dtype=float)
    try:
        model = LinearRegression().fit(X, y)
        return float(model.coef_[0])
    except Exception:
        return 0.0


def calc_bird_health_score(bird: Bird) -> int:
    score = 88.0
    if bird.status == "dead":
        return 0
    if bird.status == "sold":
        score -= 6.0

    last_dis = bird_last_disease_date(bird.id)
    if last_dis:
        days = (today() - last_dis).days
        if days <= 7:
            score -= 26
        elif days <= 30:
            score -= 14
        else:
            score -= 6
    else:
        score += 4

    score -= min(20.0, 220.0 * flock_mortality_rate_7d(bird.flock_id))

    since = today() - timedelta(days=45)
    recent_vax = (
        db.session.query(func.count(HealthEvent.id))
        .filter(HealthEvent.bird_id == bird.id, HealthEvent.event_type == "vaccination", HealthEvent.event_date >= since)
        .scalar()
        or 0
    )
    if recent_vax <= 0:
        score -= 10
    else:
        score += 6

    slope = weight_trend_slope_kg_per_day(bird.id)
    if bird.category == "Broiler":
        if slope < 0:
            score -= 10
        elif slope < 0.001:
            score -= 4
        else:
            score += 6
    else:
        if slope < -0.0005:
            score -= 6

    since30 = today() - timedelta(days=30)
    sev_map = {"Low": 0.7, "Medium": 1.2, "High": 2.0}
    events = (
        db.session.query(HealthEvent)
        .filter(HealthEvent.bird_id == bird.id, HealthEvent.event_date >= since30)
        .all()
    )
    if events:
        impact = sum(sev_map.get(e.severity or "Low", 0.8) for e in events if e.event_type in ("disease", "treatment"))
        score -= min(16.0, 3.2 * impact)

    return clamp_int(score, 0, 100)


@dataclass
class FlockRiskResult:
    label: str
    anomaly_score: float


def flock_risk_classifier(flock: Flock) -> FlockRiskResult:
    flocks = db.session.query(Flock).all()
    if not flocks or len(flocks) < 2:
        m7 = flock_mortality_rate_7d(flock.id)
        d7 = disease_event_count_7d(flock.id)
        cov = vaccination_coverage_pct(flock.id)
        avg = avg_health_score_for_flock(flock.id)
        points = 0
        if m7 > 0.05:
            points += 3
        elif m7 > 0.02:
            points += 2
        if d7 >= 4:
            points += 3
        elif d7 >= 2:
            points += 2
        if cov < 40:
            points += 2
        if avg < 60:
            points += 2
        label = "Low Risk"
        if points >= 6:
            label = "High Risk"
        elif points >= 3:
            label = "Medium Risk"
        return FlockRiskResult(label=label, anomaly_score=float(points))

    rows = []
    for f in flocks:
        rows.append(
            {
                "flock_id": f.id,
                "mortality_rate_7d": flock_mortality_rate_7d(f.id),
                "disease_event_count_7d": disease_event_count_7d(f.id),
                "avg_health_score": avg_health_score_for_flock(f.id),
                "vaccination_coverage_pct": vaccination_coverage_pct(f.id),
            }
        )
    df = pd.DataFrame(rows).fillna(0.0)
    feats = df[["mortality_rate_7d", "disease_event_count_7d", "avg_health_score", "vaccination_coverage_pct"]].to_numpy()
    X = StandardScaler().fit_transform(feats)

    try:
        iso = IsolationForest(n_estimators=200, contamination="auto", random_state=42)
        iso.fit(X)
        anomaly = -iso.score_samples(X)  # higher = more anomalous
    except Exception:
        anomaly = np.zeros((len(df),), dtype=float)
    df["anomaly"] = anomaly

    row = df[df["flock_id"] == flock.id].iloc[0]
    a = float(row["anomaly"])
    m7 = float(row["mortality_rate_7d"])
    d7 = float(row["disease_event_count_7d"])
    avg = float(row["avg_health_score"])
    cov = float(row["vaccination_coverage_pct"])

    points = 0.0
    points += 5.0 * min(0.2, m7) / 0.2
    points += min(4.0, d7)
    points += 3.0 if avg < 60 else (1.5 if avg < 75 else 0.0)
    points += 2.5 if cov < 40 else (1.0 if cov < 70 else 0.0)
    points += min(3.0, a * 1.4)

    label = "Low Risk"
    if points >= 9:
        label = "High Risk"
    elif points >= 5:
        label = "Medium Risk"
    return FlockRiskResult(label=label, anomaly_score=a)


def productivity_forecast_layer(bird: Bird) -> Dict[str, Any]:
    if bird.category != "Layer":
        return {"enabled": False}
    since = today() - timedelta(days=30)
    recs = (
        db.session.query(EggProduction)
        .filter(EggProduction.bird_id == bird.id, EggProduction.date >= since)
        .order_by(EggProduction.date.asc())
        .all()
    )
    if len(recs) < 7:
        return {"enabled": True, "note": "Not enough history for a stable forecast.", "next_7_days": []}
    base = recs[0].date
    X = np.array([(r.date - base).days for r in recs], dtype=float).reshape(-1, 1)
    y = np.array([r.count for r in recs], dtype=float)
    model = LinearRegression()
    try:
        model.fit(X, y)
    except Exception:
        return {"enabled": True, "note": "Forecast model failed to fit.", "next_7_days": []}
    last_day = recs[-1].date
    out = []
    for i in range(1, 8):
        d = last_day + timedelta(days=i)
        pred = float(model.predict(np.array([[(d - base).days]], dtype=float))[0])
        out.append({"date": d.strftime("%Y-%m-%d"), "predicted": max(0, int(round(pred)))})
    return {"enabled": True, "next_7_days": out, "trend_per_day": float(model.coef_[0])}


def mortality_predictor(bird: Bird) -> Dict[str, Any]:
    birds = db.session.query(Bird).all()
    if len(birds) < 8:
        hs = calc_bird_health_score(bird)
        m7 = flock_mortality_rate_7d(bird.flock_id)
        base = 0.08 + (0.30 if hs < 55 else 0.12 if hs < 70 else 0.02)
        base += min(0.25, m7 * 1.8)
        return {"prob_14d": float(min(0.85, base)), "explain": "Rule-based estimate (insufficient training data)."}

    since14 = today() - timedelta(days=14)
    X_rows = []
    y = []
    for b in birds:
        hs = calc_bird_health_score(b)
        m7 = flock_mortality_rate_7d(b.flock_id)
        d7 = disease_event_count_7d(b.flock_id)
        vax = bird_vaccination_count(b.id)
        age = max(0, (today() - b.hatch_date).days) if b.hatch_date else 0
        X_rows.append([hs, m7, float(d7), float(vax), float(age), 1.0 if b.status == "sold" else 0.0])
        died_recent = (
            db.session.query(func.count(MortalityLog.id))
            .filter(MortalityLog.bird_id == b.id, MortalityLog.death_date >= since14)
            .scalar()
            or 0
        )
        y.append(1 if (b.status == "dead" or died_recent > 0) else 0)

    X = np.array(X_rows, dtype=float)
    y = np.array(y, dtype=int)
    if len(set(y.tolist())) < 2:
        hs = calc_bird_health_score(bird)
        return {"prob_14d": float(0.12 if hs < 70 else 0.05), "explain": "Model fallback (not enough label variety)."}

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    model = LogisticRegression(max_iter=2000)
    try:
        model.fit(Xs, y)
    except Exception:
        hs = calc_bird_health_score(bird)
        return {"prob_14d": float(0.10 if hs < 70 else 0.04), "explain": "Model fit error; fallback estimate."}

    hs = calc_bird_health_score(bird)
    m7 = flock_mortality_rate_7d(bird.flock_id)
    d7 = disease_event_count_7d(bird.flock_id)
    vax = bird_vaccination_count(bird.id)
    age = max(0, (today() - bird.hatch_date).days) if bird.hatch_date else 0
    x = np.array([[hs, m7, float(d7), float(vax), float(age), 1.0 if bird.status == "sold" else 0.0]], dtype=float)
    prob = float(model.predict_proba(scaler.transform(x))[0][1])
    prob = float(max(0.01, min(0.95, prob)))

    explain = []
    if hs < 60:
        explain.append("Low health score increases risk.")
    if m7 > 0.03:
        explain.append("Elevated recent flock mortality increases risk.")
    if d7 >= 3:
        explain.append("Multiple disease events in flock this week increases risk.")
    if vax == 0:
        explain.append("No vaccination history is a risk factor.")
    return {"prob_14d": prob, "explain": " ".join(explain) or "Risk estimated from flock and bird health signals."}


def ai_recommendations(limit: int = 5) -> List[str]:
    recs: List[str] = []
    flocks = db.session.query(Flock).order_by(Flock.name.asc()).all()

    for f in flocks:
        risk = flock_risk_classifier(f)
        if risk.label == "High Risk":
            recs.append(f"{f.name} shows anomalous risk signals — inspect housing, biosecurity, and feed/water systems.")
        if flock_mortality_rate_7d(f.id) > 0.03:
            recs.append(f"{f.name} mortality is elevated in the last 7 days — consider immediate health screening.")

    since = today() - timedelta(days=7)
    disease_rows = (
        db.session.query(Flock.name, HealthEvent.description, func.count(HealthEvent.id))
        .join(Bird, Bird.id == HealthEvent.bird_id)
        .join(Flock, Flock.id == Bird.flock_id)
        .filter(HealthEvent.event_type == "disease", HealthEvent.event_date >= since)
        .group_by(Flock.name, HealthEvent.description)
        .having(func.count(HealthEvent.id) >= 3)
        .all()
    )
    for flock_name, desc, cnt in disease_rows:
        recs.append(f"Disease outbreak alert: {cnt} cases of “{desc}” recorded in {flock_name} this week.")

    due_since = today() - timedelta(days=45)
    alive = db.session.query(Bird).filter(Bird.status == "alive").all()
    due = []
    for b in alive:
        recent = (
            db.session.query(func.count(HealthEvent.id))
            .filter(HealthEvent.bird_id == b.id, HealthEvent.event_type == "vaccination", HealthEvent.event_date >= due_since)
            .scalar()
            or 0
        )
        if recent == 0:
            due.append(b.leg_band_number)
    if due:
        show = ", ".join(due[:3]) + ("…" if len(due) > 3 else "")
        recs.append(f"{len(due)} birds are due for vaccination within the next week window (proxy) — e.g., {show}.")

    # At-risk bird
    candidates = db.session.query(Bird).filter(Bird.status == "alive").all()
    scored = []
    for b in candidates:
        hs = calc_bird_health_score(b)
        prob = mortality_predictor(b).get("prob_14d", 0.0)
        scored.append((b, hs, prob))
    scored.sort(key=lambda t: (t[1], -t[2]))
    if scored:
        b, hs, prob = scored[0]
        if hs < 60 or prob > 0.25:
            recs.append(f"Bird {b.leg_band_number} is elevated risk (health {hs}/100, mortality risk {int(round(prob*100))}%) — prioritize a checkup.")

    uniq = []
    for r in recs:
        if r not in uniq:
            uniq.append(r)
    if not uniq:
        uniq = [
            "All systems look stable. Keep vaccination and sanitation routines consistent.",
            "Consider weekly weight sampling for broilers to catch growth anomalies earlier.",
            "Review water line cleanliness and ventilation settings as a preventative measure.",
        ]
    return uniq[: max(3, min(limit, 8))]

