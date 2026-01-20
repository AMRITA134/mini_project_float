import pandas as pd
from models import db, Class, Room, Teacher, Subject, TimetableEntry

def process_inputs():
    TimetableEntry.query.delete()
    Subject.query.delete()
    Teacher.query.delete()
    Room.query.delete()
    Class.query.delete()
    db.session.commit()

    # Classes
    class_df = pd.read_excel("uploads/class_strength.xlsx")
    class_map = {}

    for _, r in class_df.iterrows():
        cls = Class(
            name=r["class_name"],
            strength=r["strength"],
            class_category=r["class_category"].lower()
        )
        db.session.add(cls)
        db.session.flush()
        class_map[r["class_name"]] = cls.id

    # Rooms
    room_df = pd.read_excel("uploads/room_mapping.xlsx")
    for _, r in room_df.iterrows():
        db.session.add(Room(
            name=r["room_name"],
            capacity=r["capacity"],
            is_lab=r["is_lab"] == "yes",
            is_permanent=r["is_permanent"] == "yes",
            owner_class_id=class_map.get(r["owner_class"])
        ))

    # Subject type
    type_df = pd.read_excel("uploads/class_type.xlsx")
    subject_type = {r["subject"]: r["type"].lower() for _, r in type_df.iterrows()}

    # Teachers + subjects
    ts_df = pd.read_excel("uploads/teacher_subject_mapping.xlsx")
    for _, r in ts_df.iterrows():
        teacher = Teacher(name=r["teacher"])
        db.session.add(teacher)
        db.session.flush()

        db.session.add(Subject(
            name=r["subject"],
            is_lab=(subject_type.get(r["subject"]) == "lab"),
            teacher_id=teacher.id
        ))

    # Timetable
    tt_df = pd.read_excel("uploads/timetables.xlsx")
    for _, r in tt_df.iterrows():
        cls_id = class_map[r["class_name"]]
        subj_type = subject_type.get(r["subject"], "theory")

        if subj_type == "lab":
            db.session.add(TimetableEntry(
                class_id=cls_id,
                day=r["day"],
                slot=r["slot"],
                is_lab_hour=True
            ))
        else:
            subject = Subject.query.filter_by(name=r["subject"]).first()
            cls = Class.query.get(cls_id)

            room_id = None
            if cls.class_category == "permanent":
                room = Room.query.filter_by(owner_class_id=cls_id).first()
                room_id = room.id if room else None

            db.session.add(TimetableEntry(
                class_id=cls_id,
                subject_id=subject.id,
                teacher_id=subject.teacher_id,
                room_id=room_id,
                day=r["day"],
                slot=r["slot"],
                is_floating=(cls.class_category == "floating")
            ))

    db.session.commit()
