from models import db, Room, Class, TimetableEntry

def allocate_rooms():
    floating_entries = TimetableEntry.query.filter_by(is_floating=True).all()

    for entry in floating_entries:
        cls = Class.query.get(entry.class_id)

        for room in Room.query.filter_by(is_permanent=True).all():

            # Owner class must be in LAB at same slot
            lab = TimetableEntry.query.filter_by(
                class_id=room.owner_class_id,
                day=entry.day,
                slot=entry.slot,
                is_lab_hour=True
            ).first()

            if not lab:
                continue

            # Room must not already be used
            clash = TimetableEntry.query.filter_by(
                room_id=room.id,
                day=entry.day,
                slot=entry.slot
            ).first()

            if clash:
                continue

            # Capacity check
            if room.capacity >= cls.strength:
                entry.room_id = room.id
                break

    db.session.commit()
