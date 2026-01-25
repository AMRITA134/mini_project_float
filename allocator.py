from models import db, Room, Class, TimetableEntry


def allocate_rooms():
    print("\n========== ALLOCATOR START ==========")

    # ----------------------------------
    # 1️⃣ Floating entries needing rooms
    # ----------------------------------
    # NOTE: We ONLY select entries that are floating AND not yet allocated
    floating_entries = TimetableEntry.query.filter(
        TimetableEntry.is_floating == True,
        TimetableEntry.room_id == None,
        TimetableEntry.is_lab_hour == False
    ).all()

    print(f"Floating entries to allocate: {len(floating_entries)}")

    # ----------------------------------
    # 2️⃣ Permanent rooms
    # ----------------------------------
    permanent_rooms = Room.query.filter_by(is_permanent=True).all()
    print(f"Permanent rooms available: {len(permanent_rooms)}")

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
    allocated_count = 0
    unresolved_count = 0

    for entry in floating_entries:
        cls = Class.query.get(entry.class_id)
        allocated = False

        for room in permanent_rooms:

            # Capacity check
            if room.capacity < cls.strength:
                continue

            # ✅ KEEP THIS LOGIC UNCHANGED (as requested)
            # Permanent room is usable ONLY if owner class has LAB now
            lab_free = TimetableEntry.query.filter_by(
                class_id=room.owner_class_id,
                day=entry.day,
                slot=entry.slot,
                is_lab_hour=True
            ).first()

            if not lab_free:
                continue

            key = (entry.day, entry.slot, room.id)

            # Room clash check
            if key in occupied:
                continue

            # ✅ ALLOCATE (DO NOT TOUCH is_floating)
            entry.room_id = room.id
            occupied.add(key)
            allocated = True
            allocated_count += 1

            print(
                f"✔ Allocated | Class={cls.name} | "
                f"{entry.day} {entry.slot} | "
                f"Room={room.name}"
            )
            break

        if not allocated:
            unresolved_count += 1
            print(
                f"❌ Unresolved | Class={cls.name} | "
                f"{entry.day} {entry.slot} | "
                f"Subject={entry.subject.name if entry.subject else '-'}"
            )

    db.session.commit()

    print("\n========== ALLOCATOR SUMMARY ==========")
    print(f"Allocated entries  : {allocated_count}")
    print(f"Unresolved entries : {unresolved_count}")
    print("======================================\n")
