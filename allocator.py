from models import db, Room, Class, TimetableEntry


def allocate_rooms():
    # 1️⃣ Floating theory entries that need rooms
    floating_entries = TimetableEntry.query.filter(
        TimetableEntry.is_floating == True,
        TimetableEntry.is_lab_hour == False,
        TimetableEntry.room_id == None
    ).all()

    # 2️⃣ Permanent rooms
    permanent_rooms = Room.query.filter_by(is_permanent=True).all()

    for entry in floating_entries:
        cls = Class.query.get(entry.class_id)

        for room in permanent_rooms:
            # ----------------------------
            # Capacity check
            # ----------------------------
            if room.capacity < cls.strength:
                continue

            # ----------------------------
            # Owner class must be in LAB
            # at SAME day & SAME slot
            # ----------------------------
            lab_slot = TimetableEntry.query.filter_by(
                class_id=room.owner_class_id,
                day=entry.day,
                slot=entry.slot,
                is_lab_hour=True
            ).first()

            if not lab_slot:
                continue

            # ----------------------------
            # Room must not already be used
            # ----------------------------
            clash = TimetableEntry.query.filter_by(
                room_id=room.id,
                day=entry.day,
                slot=entry.slot
            ).first()

            if clash:
                continue

            # ✅ Allocate
            entry.room_id = room.id
            break

    db.session.commit()
