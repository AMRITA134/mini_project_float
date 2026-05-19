from models import db, Room, Class, TimetableEntry, CancelledClass
from utils.normalize import normalize_slot
from datetime import date


def allocate_rooms():

    print("\n========== ALLOCATOR START ==========")

    today = date.today()
    cancelled = CancelledClass.query.filter(
    CancelledClass.date >= today
).all()

    for c in cancelled:

        cancel_day = c.date.strftime("%A").upper()

        entries = TimetableEntry.query.filter_by(
            class_id=c.class_id
        ).all()

        for e in entries:

            slot = normalize_slot(e.slot)

            if slot == normalize_slot(c.slot) and e.day == cancel_day:

                if e.room_id is not None:
                    print(
                        f"❌ Cancelled | {e.class_obj.name} | {cancel_day} {slot} | freeing room {e.room.name}"
                    )

                e.room_id = None

    db.session.commit()
    floating_allocated = TimetableEntry.query.filter(
        TimetableEntry.is_floating == True,
        TimetableEntry.room_id != None
    ).all()

    for e in floating_allocated:
        e.room_id = None

    db.session.commit()

    floating_entries = TimetableEntry.query.filter(
        TimetableEntry.is_floating == True,
        TimetableEntry.is_lab_hour == False
    ).all()

    available_rooms = Room.query.order_by(Room.capacity).all()
    occupied = set()

    for e in TimetableEntry.query.filter(
        TimetableEntry.room_id != None,
        TimetableEntry.is_floating == False
    ):

        slot = normalize_slot(e.slot)

        occupied.add((e.day, slot, e.room_id))

    for entry in floating_entries:

        slot = normalize_slot(entry.slot)

        cls = Class.query.get(entry.class_id)

        for room in available_rooms:
            
            if room.capacity < cls.strength:
                continue

            key = (entry.day, slot, room.id)

            if key in occupied:
                continue

            entry.room_id = room.id
            occupied.add(key)

            print(
                f"✔ Allocated | {cls.name} | {entry.day} {slot} | {room.name}"
            )
        

            break

    db.session.commit()
    print("\n===== FREE ROOMS =====")

    printed = set()

    day_order = {
        "MONDAY": 0,
        "TUESDAY": 1,
        "WEDNESDAY": 2,
        "THURSDAY": 3,
        "FRIDAY": 4,
        "SATURDAY": 5
    }

    sorted_entries = sorted(
        floating_entries,
        key=lambda e: (
            day_order.get(e.day, 99),
            normalize_slot(e.slot)
        )
    )

    for entry in sorted_entries:

        slot = normalize_slot(entry.slot)

        slot_key = (entry.day, slot)

        if slot_key in printed:
            continue

        printed.add(slot_key)

        free_rooms = []

        for room in available_rooms:

            key = (entry.day, slot, room.id)

            if key not in occupied:
                free_rooms.append(room.name)

        print(f"\n{entry.day} {slot}")

        if free_rooms:
            for r in free_rooms:
                print(f"   {r}")
        else:
            print("   No free rooms")
    print("\n========== ALLOCATOR END ==========")