from models import db, Room, Class, TimetableEntry


def allocate_rooms():
    # ----------------------------------
    # 1️⃣ Floating entries needing rooms
    # ----------------------------------
    floating_entries = TimetableEntry.query.filter(
        TimetableEntry.is_floating == True,
        TimetableEntry.room_id == None,
        TimetableEntry.is_lab_hour == False
    ).all()

    # ----------------------------------
    # 2️⃣ Permanent rooms
    # ----------------------------------
    permanent_rooms = Room.query.filter_by(is_permanent=True).all()

    # ----------------------------------
    # 3️⃣ Track occupied rooms (day, slot, room)
    # ----------------------------------
    occupied = set()

    existing = TimetableEntry.query.filter(
        TimetableEntry.room_id != None
    ).all()

    for e in existing:
        occupied.add((e.day, e.slot, e.room_id))

    # ----------------------------------
    # 4️⃣ Allocate
    # ----------------------------------
    for entry in floating_entries:
        cls = Class.query.get(entry.class_id)

        for room in permanent_rooms:
            # Capacity check
            if room.capacity < cls.strength:
                continue

            # Permanent class must be in LAB at same slot
            lab_free = TimetableEntry.query.filter_by(
                class_id=room.owner_class_id,
                day=entry.day,
                slot=entry.slot,
                is_lab_hour=True
            ).first()

            if not lab_free:
                continue

            key = (entry.day, entry.slot, room.id)

            # Clash check
            if key in occupied:
                continue

            # ✅ Allocate
            entry.room_id = room.id
            occupied.add(key)
            break

    db.session.commit()
