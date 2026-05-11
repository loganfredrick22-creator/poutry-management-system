from __future__ import annotations

import random
from datetime import datetime, timedelta

from sqlalchemy import func

from models import AuditLog, Bird, EggProduction, Flock, HealthEvent, MortalityLog, User, WeightRecord, db
from utils import today


def seed_admin_user(bcrypt) -> None:
    admin = db.session.query(User).filter_by(username="admin").first()
    if admin:
        return
    admin = User(
        username="admin",
        role="admin",
        password_hash=bcrypt.generate_password_hash("admin123").decode("utf-8"),
    )
    db.session.add(admin)
    db.session.commit()


def seed_sample_data_if_empty() -> None:
    has_any = (db.session.query(func.count(Flock.id)).scalar() or 0) > 0 or (db.session.query(func.count(Bird.id)).scalar() or 0) > 0
    if has_any:
        return

    r = random.Random(7)
    t = today()

    flocks = [
        Flock(
            name="Batch A - Broilers",
            house_location="House 1",
            category="Broiler",
            start_date=t - timedelta(days=70),
            notes="Fast-growth broilers batch.",
        ),
        Flock(
            name="Flock B - Layers",
            house_location="House 2",
            category="Layer",
            start_date=t - timedelta(days=210),
            notes="Primary egg-laying flock.",
        ),
        Flock(
            name="Breeders Unit C",
            house_location="House 3",
            category="Breeder",
            start_date=t - timedelta(days=330),
            notes="Breeding stock unit.",
        ),
    ]
    db.session.add_all(flocks)
    db.session.commit()

    breeds = {
        "Broiler": ["Cobb 500", "Ross 308"],
        "Layer": ["Hy-Line Brown", "Lohmann Brown"],
        "Breeder": ["Sasso", "Kuroiler"],
    }

    statuses = ["alive"] * 12 + ["sold"] * 2 + ["dead"] * 1
    r.shuffle(statuses)

    birds = []
    for i in range(15):
        flock = flocks[i % len(flocks)]
        hatch = t - timedelta(days=r.randint(25, 260))
        reg = max(hatch + timedelta(days=1), t - timedelta(days=r.randint(10, 240)))
        b = Bird(
            leg_band_number=f"FL-{1001+i}",
            breed=r.choice(breeds[flock.category]),
            category=flock.category,
            hatch_date=hatch,
            flock_id=flock.id,
            status=statuses[i],
            registration_date=reg,
            weight_kg=round(r.uniform(1.2, 3.6), 2) if flock.category == "Broiler" else round(r.uniform(1.3, 2.3), 2),
            notes="Seeded sample bird.",
        )
        birds.append(b)
    db.session.add_all(birds)
    db.session.commit()

    # Weight records (broilers)
    for b in birds:
        if b.category != "Broiler":
            continue
        start = b.hatch_date + timedelta(days=10)
        for k in range(10):
            d = start + timedelta(days=k * 6)
            if d > t:
                break
            w = max(0.4, float(b.weight_kg or 2.0) - 0.8 + 0.22 * k + r.uniform(-0.12, 0.12))
            db.session.add(WeightRecord(bird_id=b.id, recorded_date=d, weight_kg=round(w, 2)))

    # Egg production (layers)
    layer_birds = [b for b in birds if b.category == "Layer"]
    for b in layer_birds:
        start = t - timedelta(days=45)
        for k in range(46):
            d = start + timedelta(days=k)
            base = 1 + (k / 60.0)
            noise = r.uniform(-0.4, 0.4)
            cnt = int(max(0, round(base + noise)))
            db.session.add(EggProduction(bird_id=b.id, flock_id=b.flock_id, date=d, count=cnt))

    db.session.commit()

    # Health events (30+)
    recorder = "admin"
    disease_names = ["Coccidiosis", "Respiratory infection", "Newcastle suspicion"]
    treatments = ["Electrolytes", "Amprolium", "Oxytetracycline"]
    vaccines = ["Newcastle", "Gumboro", "Fowl Pox"]

    for _ in range(34):
        b = r.choice(birds)
        et = r.choices(["vaccination", "disease", "treatment", "checkup"], weights=[0.38, 0.22, 0.22, 0.18])[0]
        d = t - timedelta(days=r.randint(1, 120))
        severity = r.choices(["Low", "Medium", "High"], weights=[0.55, 0.30, 0.15])[0]
        if et == "vaccination":
            desc = f"{r.choice(vaccines)} vaccine administered"
            med = r.choice(vaccines)
            dose = "0.2ml"
        elif et == "disease":
            desc = r.choice(disease_names)
            med = None
            dose = None
        elif et == "treatment":
            desc = "Treatment given"
            med = r.choice(treatments)
            dose = r.choice(["5ml/L", "10mg/kg", "1 tab"])
        else:
            desc = "Routine health check"
            med = None
            dose = None
            severity = "Low"

        db.session.add(
            HealthEvent(
                bird_id=b.id,
                event_type=et,
                event_date=d,
                description=desc,
                medicine_used=med,
                dose=dose,
                recorded_by=recorder,
                severity=severity,
            )
        )
    db.session.commit()

    # Mortality logs for 2-3 birds
    dead_birds = [b for b in birds if b.status == "dead"]
    if dead_birds:
        b = dead_birds[0]
        db.session.add(
            MortalityLog(
                bird_id=b.id,
                death_date=t - timedelta(days=r.randint(1, 24)),
                cause=r.choice(["Heat stress", "Respiratory illness", "Unknown"]),
                notes="Seeded mortality record.",
                recorded_by=recorder,
            )
        )
    else:
        for b in r.sample(birds, k=2):
            db.session.add(
                MortalityLog(
                    bird_id=b.id,
                    death_date=t - timedelta(days=r.randint(1, 24)),
                    cause=r.choice(["Heat stress", "Predation", "Unknown"]),
                    notes="Seeded mortality record.",
                    recorded_by=recorder,
                )
            )
            b.status = "dead"

    db.session.commit()

    # Audit logs (seed)
    admin = db.session.query(User).filter_by(username="admin").first()
    if admin:
        for b in r.sample(birds, k=min(8, len(birds))):
            db.session.add(
                AuditLog(
                    bird_id=b.id,
                    user_id=admin.id,
                    field_changed="notes",
                    old_value="",
                    new_value="Seeded sample bird.",
                    timestamp=datetime.utcnow() - timedelta(days=r.randint(1, 20)),
                )
            )
    db.session.commit()

