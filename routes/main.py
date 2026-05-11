from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta

import numpy as np
from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import login_required, current_user
from sqlalchemy import func

from decorators import admin_required, can_edit_data
from config import Config

from ai import (
    FlockRiskResult,
    ai_recommendations,
    avg_health_score_for_flock,
    bird_health_event_count,
    bird_last_disease_date,
    bird_vaccination_count,
    calc_bird_health_score,
    flock_mortality_rate_7d,
    flock_risk_classifier,
    mortality_predictor,
    productivity_forecast_layer,
    vaccination_coverage_pct,
    weight_trend_slope_kg_per_day,
)
from models import AuditLog, Bird, EggProduction, Flock, HealthEvent, MortalityLog, WeightRecord, db
from theme import THEME
from utils import age_days, age_group, parse_date, safe_float, today

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    return redirect(url_for("main.dashboard"))


@bp.get("/dashboard")
@login_required
def dashboard():
    total_birds = db.session.query(func.count(Bird.id)).scalar() or 0
    # Active flocks: at least 1 alive bird
    active_flocks = (
        db.session.query(Flock.id)
        .join(Bird, Bird.flock_id == Flock.id)
        .filter(Bird.status == "alive")
        .group_by(Flock.id)
        .count()
    )
    start_month = today().replace(day=1)
    mort_month = db.session.query(func.count(MortalityLog.id)).filter(MortalityLog.death_date >= start_month).scalar() or 0

    flocks = db.session.query(Flock).all()
    vals = [avg_health_score_for_flock(f.id) for f in flocks] if flocks else []
    vals = [v for v in vals if v > 0]
    avg_health = int(round(float(np.mean(vals)))) if vals else 0

    recs = ai_recommendations(limit=5)

    # Recent activity
    activities = []
    birds_recent = db.session.query(Bird).order_by(Bird.registration_date.desc(), Bird.id.desc()).limit(6).all()
    for b in birds_recent:
        activities.append({"ts": datetime.combine(b.registration_date, datetime.min.time()), "type": "Bird Registered", "detail": f"Bird {b.leg_band_number} added"})
    health_recent = db.session.query(HealthEvent).order_by(HealthEvent.event_date.desc(), HealthEvent.id.desc()).limit(8).all()
    for e in health_recent:
        activities.append({"ts": datetime.combine(e.event_date, datetime.min.time()), "type": f"Health • {e.event_type.title()}", "detail": f"{e.bird.leg_band_number}: {e.description}"})
    mort_recent = db.session.query(MortalityLog).order_by(MortalityLog.death_date.desc(), MortalityLog.id.desc()).limit(6).all()
    for m in mort_recent:
        activities.append({"ts": datetime.combine(m.death_date, datetime.min.time()), "type": "Mortality Logged", "detail": f"{m.bird.leg_band_number}: {m.cause}"})
    activities.sort(key=lambda a: a["ts"], reverse=True)
    activities = activities[:10]

    flocks_all = db.session.query(Flock).order_by(Flock.name.asc()).all()
    birds_all = db.session.query(Bird).order_by(Bird.leg_band_number.asc()).all()

    return render_template(
        "dashboard.html",
        theme=THEME,
        total_birds=total_birds,
        active_flocks=active_flocks,
        mort_month=mort_month,
        avg_health=avg_health,
        recs=recs,
        activities=activities,
        flocks=flocks_all,
        birds=birds_all,
    )


@bp.post("/birds/register")
@login_required
@can_edit_data
def register_bird():
    leg = (request.form.get("leg_band_number") or "").strip()
    breed = (request.form.get("breed") or "").strip()
    category = (request.form.get("category") or "").strip()
    hatch_date = parse_date(request.form.get("hatch_date") or "")
    flock_id = request.form.get("flock_id") or ""
    weight_kg = request.form.get("weight_kg")
    notes = (request.form.get("notes") or "").strip()

    if not leg or not breed or category not in ("Broiler", "Layer", "Breeder") or not hatch_date or not flock_id:
        flash("Missing required fields for bird registration.", "danger")
        return redirect(url_for("main.dashboard"))

    if db.session.query(Bird).filter_by(leg_band_number=leg).first():
        flash("That leg band number already exists.", "danger")
        return redirect(url_for("main.dashboard"))

    flock = db.session.get(Flock, int(flock_id))
    if not flock:
        flash("Invalid flock selected.", "danger")
        return redirect(url_for("main.dashboard"))

    w = safe_float(weight_kg, default=None) if weight_kg not in (None, "", " ") else None
    bird = Bird(
        leg_band_number=leg,
        breed=breed,
        category=category,
        hatch_date=hatch_date,
        flock_id=flock.id,
        status="alive",
        registration_date=today(),
        weight_kg=w,
        notes=notes or None,
    )
    db.session.add(bird)
    db.session.commit()

    if w is not None:
        db.session.add(WeightRecord(bird_id=bird.id, recorded_date=today(), weight_kg=float(w)))
        db.session.commit()

    flash(f"Bird {leg} registered successfully.", "success")
    return redirect(url_for("main.birds"))


@bp.post("/flocks/create")
@login_required
@can_edit_data
def create_flock():
    name = (request.form.get("name") or "").strip()
    house = (request.form.get("house_location") or "").strip()
    category = (request.form.get("category") or "").strip()
    start_date = parse_date(request.form.get("start_date") or "")
    notes = (request.form.get("notes") or "").strip()

    if not name or not house or category not in ("Broiler", "Layer", "Breeder") or not start_date:
        flash("Missing required fields for flock creation.", "danger")
        return redirect(url_for("main.dashboard"))
    if db.session.query(Flock).filter(func.lower(Flock.name) == name.lower()).first():
        flash("A flock with that name already exists.", "danger")
        return redirect(url_for("main.dashboard"))

    f = Flock(name=name, house_location=house, category=category, start_date=start_date, notes=notes or None)
    db.session.add(f)
    db.session.commit()
    flash("Flock created successfully.", "success")
    return redirect(url_for("main.flocks"))


@bp.post("/health/record")
@login_required
@can_edit_data
def record_health_event():
    leg = (request.form.get("leg_band_number") or "").strip()
    event_type = (request.form.get("event_type") or "").strip()
    event_date = parse_date(request.form.get("event_date") or "")
    desc = (request.form.get("description") or "").strip()
    medicine = (request.form.get("medicine_used") or "").strip()
    dose = (request.form.get("dose") or "").strip()
    severity = (request.form.get("severity") or "Low").strip()

    bird = db.session.query(Bird).filter_by(leg_band_number=leg).first()
    if not bird:
        flash("Bird not found for that leg band number.", "danger")
        return redirect(url_for("main.dashboard"))
    if event_type not in ("vaccination", "disease", "treatment", "checkup"):
        flash("Invalid event type.", "danger")
        return redirect(url_for("main.dashboard"))
    if not event_date or not desc:
        flash("Event date and description are required.", "danger")
        return redirect(url_for("main.dashboard"))

    if severity not in ("Low", "Medium", "High"):
        severity = "Low"

    e = HealthEvent(
        bird_id=bird.id,
        event_type=event_type,
        event_date=event_date,
        description=desc,
        medicine_used=medicine or None,
        dose=dose or None,
        recorded_by=current_user.username,
        severity=severity,
    )
    db.session.add(e)
    db.session.commit()
    flash("Health event recorded.", "success")
    return redirect(url_for("main.bird_profile", leg_band_number=bird.leg_band_number, tab="health"))


@bp.get("/birds")
@login_required
def birds():
    q = (request.args.get("q") or "").strip()
    flock_id = request.args.get("flock_id") or ""
    category = request.args.get("category") or ""
    status = request.args.get("status") or ""
    agegrp = request.args.get("agegrp") or ""
    page = int(request.args.get("page") or 1)
    per_page = 20

    query = db.session.query(Bird).outerjoin(Flock).order_by(Bird.leg_band_number.asc())
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(
            func.lower(Bird.leg_band_number).like(like)
            | func.lower(Bird.breed).like(like)
            | func.lower(Flock.name).like(like)
        )
    if flock_id:
        try:
            query = query.filter(Bird.flock_id == int(flock_id))
        except Exception:
            pass
    if category in ("Broiler", "Layer", "Breeder"):
        query = query.filter(Bird.category == category)
    if status in ("alive", "sold", "dead"):
        query = query.filter(Bird.status == status)

    birds_all = query.all()
    if agegrp:
        birds_all = [b for b in birds_all if age_group(age_days(b.hatch_date)) == agegrp]

    total = len(birds_all)
    pages = max(1, int(np.ceil(total / per_page)))
    page = max(1, min(page, pages))
    items = birds_all[(page - 1) * per_page : (page - 1) * per_page + per_page]

    rows = []
    for b in items:
        days = age_days(b.hatch_date)
        rows.append(
            {
                "bird": b,
                "age_label": f"{days} days" if days is not None else "—",
                "age_group": age_group(days),
                "health_score": calc_bird_health_score(b),
            }
        )

    flocks = db.session.query(Flock).order_by(Flock.name.asc()).all()
    age_groups = ["Chick (0-29d)", "Grower (30-89d)", "Juvenile (90-179d)", "Adult (180d+)"]
    return render_template(
        "birds.html",
        theme=THEME,
        rows=rows,
        total=total,
        q=q,
        flock_id=flock_id,
        category=category,
        status=status,
        agegrp=agegrp,
        page=page,
        pages=pages,
        flocks=flocks,
        age_groups=age_groups,
    )


@bp.get("/birds/export.csv")
@login_required
def birds_export_csv():
    q = (request.args.get("q") or "").strip()
    flock_id = request.args.get("flock_id") or ""
    category = request.args.get("category") or ""
    status = request.args.get("status") or ""
    agegrp = request.args.get("agegrp") or ""

    query = db.session.query(Bird).outerjoin(Flock).order_by(Bird.leg_band_number.asc())
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(
            func.lower(Bird.leg_band_number).like(like)
            | func.lower(Bird.breed).like(like)
            | func.lower(Flock.name).like(like)
        )
    if flock_id:
        try:
            query = query.filter(Bird.flock_id == int(flock_id))
        except Exception:
            pass
    if category in ("Broiler", "Layer", "Breeder"):
        query = query.filter(Bird.category == category)
    if status in ("alive", "sold", "dead"):
        query = query.filter(Bird.status == status)

    birds_all = query.all()
    if agegrp:
        birds_all = [b for b in birds_all if age_group(age_days(b.hatch_date)) == agegrp]

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["leg_band_number", "breed", "category", "hatch_date", "age_days", "flock", "status", "health_score", "registration_date", "weight_kg", "notes"])
    for b in birds_all:
        days = age_days(b.hatch_date) or ""
        w.writerow([
            b.leg_band_number,
            b.breed,
            b.category,
            b.hatch_date.strftime("%Y-%m-%d"),
            days,
            b.flock.name if b.flock else "",
            b.status,
            calc_bird_health_score(b),
            b.registration_date.strftime("%Y-%m-%d") if b.registration_date else "",
            b.weight_kg if b.weight_kg is not None else "",
            (b.notes or "").replace("\n", " ").strip(),
        ])
    out = buf.getvalue()
    buf.close()
    filename = f"birds_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(out, mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})


def _log_bird_change(bird: Bird, field: str, old: object, new: object) -> None:
    old_s = "" if old is None else str(old)
    new_s = "" if new is None else str(new)
    if old_s == new_s:
        return
    db.session.add(
        AuditLog(
            bird_id=bird.id,
            user_id=current_user.id,
            field_changed=field,
            old_value=old_s,
            new_value=new_s,
        )
    )


@bp.route("/birds/<leg_band_number>", methods=["GET", "POST"])
@login_required
def bird_profile(leg_band_number: str):
    bird = db.session.query(Bird).filter_by(leg_band_number=leg_band_number).first_or_404()
    tab = request.args.get("tab") or "overview"
    if tab not in ("overview", "health", "growth", "ai", "audit"):
        tab = "overview"

    if request.method == "POST":
        action = request.form.get("action") or ""
        if action == "update_bird" and Config.is_editing_enabled(current_user.role):
            before = {
                "breed": bird.breed,
                "category": bird.category,
                "hatch_date": bird.hatch_date,
                "flock_id": bird.flock_id,
                "status": bird.status,
                "weight_kg": bird.weight_kg,
                "notes": bird.notes,
            }
            bird.breed = (request.form.get("breed") or bird.breed).strip()
            bird.category = (request.form.get("category") or bird.category).strip()
            hd = parse_date(request.form.get("hatch_date") or "")
            if hd:
                bird.hatch_date = hd
            fid = request.form.get("flock_id") or ""
            if fid:
                try:
                    bird.flock_id = int(fid)
                except Exception:
                    pass
            st = (request.form.get("status") or bird.status).strip()
            if st in ("alive", "sold", "dead"):
                bird.status = st
            w = request.form.get("weight_kg")
            bird.weight_kg = safe_float(w, default=None) if w not in (None, "", " ") else None
            bird.notes = (request.form.get("notes") or "").strip() or None

            after = {
                "breed": bird.breed,
                "category": bird.category,
                "hatch_date": bird.hatch_date,
                "flock_id": bird.flock_id,
                "status": bird.status,
                "weight_kg": bird.weight_kg,
                "notes": bird.notes,
            }
            for k in before:
                if str(before[k]) != str(after[k]):
                    _log_bird_change(bird, k, before[k], after[k])
            db.session.commit()
            flash("Bird record updated.", "success")
            return redirect(url_for("main.bird_profile", leg_band_number=bird.leg_band_number, tab="overview"))

        if action == "add_health_event" and Config.is_editing_enabled(current_user.role):
            et = (request.form.get("event_type") or "").strip()
            ed = parse_date(request.form.get("event_date") or "")
            desc = (request.form.get("description") or "").strip()
            severity = (request.form.get("severity") or "Low").strip()
            med = (request.form.get("medicine_used") or "").strip()
            dose = (request.form.get("dose") or "").strip()
            if et not in ("vaccination", "disease", "treatment", "checkup") or not ed or not desc:
                flash("Health event requires type, date, and description.", "danger")
            else:
                if severity not in ("Low", "Medium", "High"):
                    severity = "Low"
                db.session.add(
                    HealthEvent(
                        bird_id=bird.id,
                        event_type=et,
                        event_date=ed,
                        description=desc,
                        medicine_used=med or None,
                        dose=dose or None,
                        recorded_by=current_user.username,
                        severity=severity,
                    )
                )
                db.session.commit()
                flash("Health event added.", "success")
            return redirect(url_for("main.bird_profile", leg_band_number=bird.leg_band_number, tab="health"))

        if action == "add_weight" and Config.is_editing_enabled(current_user.role):
            wd = parse_date(request.form.get("recorded_date") or "")
            w = safe_float(request.form.get("weight_kg"), default=None)
            if not wd or w is None or w <= 0:
                flash("Weight record requires valid date and weight.", "danger")
            else:
                db.session.add(WeightRecord(bird_id=bird.id, recorded_date=wd, weight_kg=float(w)))
                bird.weight_kg = float(w)
                _log_bird_change(bird, "weight_kg", "updated", w)
                db.session.commit()
                flash("Weight record added.", "success")
            return redirect(url_for("main.bird_profile", leg_band_number=bird.leg_band_number, tab="growth"))

        if action == "add_eggs" and Config.is_editing_enabled(current_user.role):
            dd = parse_date(request.form.get("date") or "")
            cnt = request.form.get("count")
            try:
                cnt_i = int(cnt)
            except Exception:
                cnt_i = -1
            if not dd or cnt_i < 0:
                flash("Egg production requires a valid date and non-negative count.", "danger")
            else:
                db.session.add(EggProduction(bird_id=bird.id, flock_id=bird.flock_id or 0, date=dd, count=cnt_i))
                db.session.commit()
                flash("Egg production record added.", "success")
            return redirect(url_for("main.bird_profile", leg_band_number=bird.leg_band_number, tab="growth"))

    hs = calc_bird_health_score(bird)
    days = age_days(bird.hatch_date) or 0
    days_on_farm = max(0, (today() - bird.registration_date).days) if bird.registration_date else 0
    vax_cnt = bird_vaccination_count(bird.id)
    he_cnt = bird_health_event_count(bird.id)
    last_dis = bird_last_disease_date(bird.id)
    last_dis_s = last_dis.strftime("%Y-%m-%d") if last_dis else "None"
    m7 = flock_mortality_rate_7d(bird.flock_id)

    flock = bird.flock
    flock_avg = avg_health_score_for_flock(flock.id) if flock else 0.0
    flock_risk = flock_risk_classifier(flock) if flock else FlockRiskResult(label="Low Risk", anomaly_score=0.0)
    mort_pred = mortality_predictor(bird)
    prod_fc = productivity_forecast_layer(bird)

    events = db.session.query(HealthEvent).filter(HealthEvent.bird_id == bird.id).order_by(HealthEvent.event_date.desc(), HealthEvent.id.desc()).all()
    weights = db.session.query(WeightRecord).filter(WeightRecord.bird_id == bird.id).order_by(WeightRecord.recorded_date.asc()).all()
    eggs = db.session.query(EggProduction).filter(EggProduction.bird_id == bird.id).order_by(EggProduction.date.asc()).all()
    audits = db.session.query(AuditLog).filter(AuditLog.bird_id == bird.id).order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).all()
    flocks = db.session.query(Flock).order_by(Flock.name.asc()).all()

    # Merge measurements for table
    wmap = {wr.recorded_date: wr.weight_kg for wr in weights}
    emap = {ep.date: ep.count for ep in eggs}
    all_dates = sorted(set(list(wmap.keys()) + list(emap.keys())))
    meas_rows = [{"date": d.strftime("%Y-%m-%d"), "weight": wmap.get(d, "—"), "eggs": emap.get(d, "—")} for d in all_dates]

    # AI flags/actions
    flags = []
    if hs < 60:
        flags.append("Low health score")
    if bird.category == "Broiler" and weight_trend_slope_kg_per_day(bird.id) < 0:
        flags.append("Negative weight trend")
    if last_dis and (today() - last_dis).days <= 14:
        flags.append("Recent disease")
    if m7 > 0.03:
        flags.append("Flock mortality elevated")

    actions = []
    if hs < 60:
        actions.append("Schedule a checkup within 48 hours and isolate if symptoms appear.")
    if last_dis and (today() - last_dis).days <= 7:
        actions.append("Review treatment adherence and hydration; consider vet consult.")
    if bird.flock_id and vaccination_coverage_pct(bird.flock_id) < 55:
        actions.append("Increase vaccination coverage for the flock; verify cold-chain and dosing.")
    if bird.category == "Broiler" and len(weights) < 4:
        actions.append("Record weekly weights for more reliable growth anomaly detection.")
    if bird.category == "Layer" and len(eggs) < 10:
        actions.append("Record daily egg counts for at least 2 weeks to enable forecasting.")
    if not actions:
        actions = ["Maintain routine; keep sanitation and vaccination on schedule.", "Continue measurement sampling to keep models stable."]

    return render_template(
        "bird_profile.html",
        theme=THEME,
        bird=bird,
        tab=tab,
        hs=hs,
        age_days=days,
        age_group_label=age_group(days),
        days_on_farm=days_on_farm,
        vax_cnt=vax_cnt,
        he_cnt=he_cnt,
        last_disease=last_dis_s,
        m7=m7,
        flock_avg=flock_avg,
        flock_risk=flock_risk,
        mort_prob=mort_pred.get("prob_14d", 0.0),
        mort_explain=mort_pred.get("explain", ""),
        prod_fc=prod_fc,
        events=events,
        meas_rows=meas_rows,
        audits=audits,
        flocks=flocks,
        ai_actions=actions,
        anomaly_flags=flags,
    )


@bp.get("/flocks")
@login_required
def flocks():
    flocks = db.session.query(Flock).order_by(Flock.name.asc()).all()
    cards = []
    for f in flocks:
        count_alive = db.session.query(func.count(Bird.id)).filter(Bird.flock_id == f.id, Bird.status == "alive").scalar() or 0
        avg = avg_health_score_for_flock(f.id)
        last_upd = (
            db.session.query(func.max(HealthEvent.event_date))
            .join(Bird, Bird.id == HealthEvent.bird_id)
            .filter(Bird.flock_id == f.id)
            .scalar()
        )
        cards.append({"flock": f, "count": count_alive, "avg": avg, "last": last_upd.strftime("%Y-%m-%d") if last_upd else "—", "risk": flock_risk_classifier(f).label})
    return render_template("flocks.html", theme=THEME, cards=cards)


@bp.route("/flocks/<int:flock_id>", methods=["GET", "POST"])
@login_required
def flock_detail(flock_id: int):
    flock = db.session.get(Flock, flock_id)
    if not flock:
        flash("Flock not found.", "danger")
        return redirect(url_for("main.flocks"))

    if request.method == "POST" and Config.is_editing_enabled(current_user.role):
        name = (request.form.get("name") or flock.name).strip()
        house = (request.form.get("house_location") or flock.house_location).strip()
        category = (request.form.get("category") or flock.category).strip()
        start_date = parse_date(request.form.get("start_date") or "") or flock.start_date
        notes = (request.form.get("notes") or "").strip()
        if not name or not house or category not in ("Broiler", "Layer", "Breeder"):
            flash("Invalid flock values.", "danger")
        else:
            flock.name = name
            flock.house_location = house
            flock.category = category
            flock.start_date = start_date
            flock.notes = notes or None
            db.session.commit()
            flash("Flock updated.", "success")
        return redirect(url_for("main.flock_detail", flock_id=flock.id))

    birds = db.session.query(Bird).filter(Bird.flock_id == flock.id).order_by(Bird.leg_band_number.asc()).all()
    health_map = {b.id: calc_bird_health_score(b) for b in birds}
    avg = avg_health_score_for_flock(flock.id)
    cov = vaccination_coverage_pct(flock.id)
    risk = flock_risk_classifier(flock)
    m7 = flock_mortality_rate_7d(flock.id)

    since = today() - timedelta(days=7)
    outbreak = (
        db.session.query(HealthEvent.description, func.count(HealthEvent.id))
        .join(Bird, Bird.id == HealthEvent.bird_id)
        .filter(Bird.flock_id == flock.id, HealthEvent.event_type == "disease", HealthEvent.event_date >= since)
        .group_by(HealthEvent.description)
        .having(func.count(HealthEvent.id) >= 3)
        .all()
    )
    outbreak_items = [f"{cnt} cases of “{desc}” in last 7 days" for desc, cnt in outbreak]

    return render_template(
        "flock_detail.html",
        theme=THEME,
        flock=flock,
        birds=birds,
        health_map=health_map,
        avg=avg,
        cov=cov,
        risk=risk,
        m7=m7,
        outbreaks=outbreak_items,
    )


@bp.get("/health")
@login_required
def health():
    event_type = request.args.get("event_type") or ""
    flock_id = request.args.get("flock_id") or ""
    severity = request.args.get("severity") or ""
    start = parse_date(request.args.get("start") or "")
    end = parse_date(request.args.get("end") or "")

    query = db.session.query(HealthEvent).join(Bird).outerjoin(Flock).order_by(HealthEvent.event_date.desc(), HealthEvent.id.desc())
    if event_type in ("vaccination", "disease", "treatment", "checkup"):
        query = query.filter(HealthEvent.event_type == event_type)
    if severity in ("Low", "Medium", "High"):
        query = query.filter(HealthEvent.severity == severity)
    if flock_id:
        try:
            query = query.filter(Bird.flock_id == int(flock_id))
        except Exception:
            pass
    if start:
        query = query.filter(HealthEvent.event_date >= start)
    if end:
        query = query.filter(HealthEvent.event_date <= end)

    events = query.limit(200).all()
    mort = db.session.query(MortalityLog).order_by(MortalityLog.death_date.desc(), MortalityLog.id.desc()).limit(80).all()

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
            due.append(b)

    since7 = today() - timedelta(days=7)
    outbreaks = (
        db.session.query(Flock.name, HealthEvent.description, func.count(HealthEvent.id))
        .join(Bird, Bird.id == HealthEvent.bird_id)
        .join(Flock, Flock.id == Bird.flock_id)
        .filter(HealthEvent.event_type == "disease", HealthEvent.event_date >= since7)
        .group_by(Flock.name, HealthEvent.description)
        .having(func.count(HealthEvent.id) >= 3)
        .all()
    )

    flocks = db.session.query(Flock).order_by(Flock.name.asc()).all()
    birds = db.session.query(Bird).order_by(Bird.leg_band_number.asc()).all()

    return render_template(
        "health.html",
        theme=THEME,
        events=events,
        mort=mort,
        due=due,
        outbreaks=outbreaks,
        flocks=flocks,
        birds=birds,
        event_type=event_type,
        flock_id=flock_id,
        severity=severity,
        start=request.args.get("start") or "",
        end=request.args.get("end") or "",
    )


@bp.get("/reports")
@login_required
def reports():
    flocks = db.session.query(Flock).order_by(Flock.name.asc()).all()

    perf_rows = []
    for f in flocks:
        alive = db.session.query(func.count(Bird.id)).filter(Bird.flock_id == f.id, Bird.status == "alive").scalar() or 0
        sold = db.session.query(func.count(Bird.id)).filter(Bird.flock_id == f.id, Bird.status == "sold").scalar() or 0
        dead = db.session.query(func.count(Bird.id)).filter(Bird.flock_id == f.id, Bird.status == "dead").scalar() or 0
        perf_rows.append(
            {
                "name": f.name,
                "category": f.category,
                "alive": alive,
                "sold": sold,
                "dead": dead,
                "avg_health": round(avg_health_score_for_flock(f.id), 1),
                "vax_cov": round(vaccination_coverage_pct(f.id), 0),
                "risk": flock_risk_classifier(f).label,
            }
        )

    mort_causes = db.session.query(MortalityLog.cause, func.count(MortalityLog.id)).group_by(MortalityLog.cause).all()
    mort_labels = [c for c, _ in mort_causes] if mort_causes else ["None"]
    mort_values = [int(n) for _, n in mort_causes] if mort_causes else [0]

    vax_labels = [f.name for f in flocks]
    vax_values = [round(vaccination_coverage_pct(f.id), 1) for f in flocks]

    birds_alive = db.session.query(Bird).filter(Bird.status == "alive").all()
    risks = []
    for b in birds_alive:
        hs = calc_bird_health_score(b)
        prob = mortality_predictor(b).get("prob_14d", 0.0)
        risks.append({"leg": b.leg_band_number, "flock": b.flock.name if b.flock else "Unassigned", "hs": hs, "risk": round(prob * 100, 0)})
    risks.sort(key=lambda x: (-x["risk"], x["hs"]))

    return render_template(
        "reports.html",
        theme=THEME,
        perf_rows=perf_rows,
        mort_labels=mort_labels,
        mort_values=mort_values,
        vax_labels=vax_labels,
        vax_values=vax_values,
        risk_rows=risks[:8],
    )


@bp.get("/reports/export/performance.csv")
@login_required
def reports_export_performance():
    flocks = db.session.query(Flock).order_by(Flock.name.asc()).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["flock", "category", "alive", "sold", "dead", "avg_health", "vaccination_coverage_pct", "risk"])
    for f in flocks:
        alive = db.session.query(func.count(Bird.id)).filter(Bird.flock_id == f.id, Bird.status == "alive").scalar() or 0
        sold = db.session.query(func.count(Bird.id)).filter(Bird.flock_id == f.id, Bird.status == "sold").scalar() or 0
        dead = db.session.query(func.count(Bird.id)).filter(Bird.flock_id == f.id, Bird.status == "dead").scalar() or 0
        w.writerow([f.name, f.category, alive, sold, dead, round(avg_health_score_for_flock(f.id), 1), round(vaccination_coverage_pct(f.id), 1), flock_risk_classifier(f).label])
    out = buf.getvalue()
    buf.close()
    filename = f"flock_performance_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(out, mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})


@bp.get("/settings")
@login_required
def settings():
    return render_template("settings.html", theme=THEME)


@bp.post("/birds/<leg_band_number>/delete")
@login_required
@admin_required
def delete_bird(leg_band_number: str):
    bird = db.session.query(Bird).filter_by(leg_band_number=leg_band_number).first_or_404()
    db.session.delete(bird)
    db.session.commit()
    flash(f"Bird {leg_band_number} deleted successfully.", "success")
    return redirect(url_for("main.birds"))


@bp.post("/flocks/<int:flock_id>/delete")
@login_required
@admin_required
def delete_flock(flock_id: int):
    flock = db.session.get(Flock, flock_id)
    if not flock:
        flash("Flock not found.", "danger")
        return redirect(url_for("main.flocks"))
    
    # Check if flock has birds
    bird_count = db.session.query(func.count(Bird.id)).filter(Bird.flock_id == flock_id).scalar()
    if bird_count > 0:
        flash(f"Cannot delete flock with {bird_count} birds. Remove or reassign birds first.", "danger")
        return redirect(url_for("main.flock_detail", flock_id=flock_id))
    
    db.session.delete(flock)
    db.session.commit()
    flash(f"Flock {flock.name} deleted successfully.", "success")
    return redirect(url_for("main.flocks"))


@bp.post("/health/<int:event_id>/delete")
@login_required
@admin_required
def delete_health_event(event_id: int):
    from models import HealthEvent
    event = db.session.get(HealthEvent, event_id)
    if not event:
        flash("Health event not found.", "danger")
        return redirect(request.referrer or url_for("main.health"))
    
    db.session.delete(event)
    db.session.commit()
    flash("Health event deleted successfully.", "success")
    return redirect(request.referrer or url_for("main.health"))

