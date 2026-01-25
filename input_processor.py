import pandas as pd
from models import db, Class, Room, Teacher, Subject, TimetableEntry


def normalize(df):
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )
    return df


def get_class_column(df):
    if "class" in df.columns:
        return "class"
    if "class_name" in df.columns:
        return "class_name"
    raise ValueError("No class column found")


def process_inputs():
    # -------- CLEAR DATABASE --------
    TimetableEntry.query.delete()
    Subject.query.delete()
    Teacher.query.delete()
    Room.query.delete()
    Class.query.delete()
    db.session.commit()

    # -------- CLASS STRENGTH --------
    class_df = normalize(pd.read_excel("uploads/class_strength.xlsx"))
    class_col = get_class_column(class_df)

    class_map = {}
    for _, r in class_df.iterrows():
        cls = Class(
            name=str(r[class_col]).strip(),
            strength=int(r["strength"]),
            class_category=str(r["class_category"]).lower()
        )
        db.session.add(cls)
        db.session.flush()
        class_map[cls.name] = cls.id

    # -------- ROOM MAPPING --------
    room_df = normalize(pd.read_excel("uploads/room_mapping.xlsx"))
    room_class_col = get_class_column(room_df)

    for _, r in room_df.iterrows():
        cname = str(r[room_class_col]).strip()
        if cname not in class_map:
            continue

        db.session.add(Room(
            name=str(r["room"]).strip(),
            capacity=int(r["capacity"]),
            is_permanent=True,
            owner_class_id=class_map[cname]
        ))

    # -------- SUBJECT TYPE --------
    type_df = normalize(pd.read_excel("uploads/class_type.xlsx"))
    subject_type = {
        str(r["subject"]).strip(): str(r["type"]).lower()
        for _, r in type_df.iterrows()
    }

    # -------- TEACHER–SUBJECT --------
    ts_df = normalize(pd.read_excel("uploads/teacher_subject_mapping.xlsx"))
    teacher_map = {}
    subject_map = {}

    for _, r in ts_df.iterrows():
        faculty = str(r["faculty"]).strip()
        subject_name = str(r["subject"]).strip()

        teacher = teacher_map.get(faculty)
        if not teacher:
            teacher = Teacher(name=faculty)
            db.session.add(teacher)
            db.session.flush()
            teacher_map[faculty] = teacher

        subject = Subject(
            name=subject_name,
            is_lab=(subject_type.get(subject_name) == "lab"),
            teacher_id=teacher.id
        )
        db.session.add(subject)
        db.session.flush()
        subject_map[subject_name] = subject

    # -------- TIMETABLES --------
    xls = pd.ExcelFile("uploads/timetables.xlsx")

    for sheet_name in xls.sheet_names:
        class_name = sheet_name.strip()
        if class_name not in class_map:
            continue

        cls_id = class_map[class_name]
        cls = Class.query.get(cls_id)

        df = normalize(pd.read_excel(xls, sheet_name=sheet_name))
        day_col = df.columns[0]
        period_cols = df.columns[1:]

        for _, row in df.iterrows():
            day = str(row[day_col]).strip()

            for period in period_cols:
                cell = row[period]
                if pd.isna(cell):
                    continue

                subject_name = str(cell).strip()

                # ===== ACTIVITY HOUR (STORE EXACTLY WHERE IT APPEARS) =====
                if subject_name.lower() in ["activity hour", "activity"]:
                    db.session.add(TimetableEntry(
                        class_id=cls_id,
                        subject_id=None,
                        teacher_id=None,
                        room_id=None,
                        day=day,
                        slot=period,
                        batch=None,
                        is_lab_hour=False,
                        is_floating=False
                    ))
                    continue

                # ===== LAB =====
                if subject_type.get(subject_name) == "lab":
                    db.session.add(TimetableEntry(
                        class_id=cls_id,
                        subject_id=None,
                        teacher_id=None,
                        room_id=None,
                        day=day,
                        slot=period,
                        batch=None,
                        is_lab_hour=True,
                        is_floating=False
                    ))
                    continue

                # ===== THEORY =====
                subject = subject_map.get(subject_name)
                if not subject:
                    subject = Subject(
                        name=subject_name,
                        is_lab=False,
                        teacher_id=None
                    )
                    db.session.add(subject)
                    db.session.flush()
                    subject_map[subject_name] = subject

                room_id = None
                if cls.class_category == "permanent":
                    room = Room.query.filter_by(owner_class_id=cls_id).first()
                    if room:
                        room_id = room.id

                db.session.add(TimetableEntry(
                    class_id=cls_id,
                    subject_id=subject.id,
                    teacher_id=subject.teacher_id,
                    room_id=room_id,
                    day=day,
                    slot=period,
                    batch=None,
                    is_lab_hour=False,
                    is_floating=(cls.class_category == "floating")
                ))

    db.session.commit()
