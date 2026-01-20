import pandas as pd
from models import db, Class, Room, Teacher, Subject, TimetableEntry


# ---------------- HELPERS ----------------

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
    raise ValueError(f"No class column found. Columns: {list(df.columns)}")


# ---------------- MAIN PROCESS ----------------

def process_inputs():
    # -------- CLEAR DATABASE --------
    TimetableEntry.query.delete()
    Subject.query.delete()
    Teacher.query.delete()
    Room.query.delete()
    Class.query.delete()
    db.session.commit()

    # =====================================================
    # 1️⃣ CLASS STRENGTH
    # =====================================================
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

    # =====================================================
    # 2️⃣ ROOM MAPPING (PERMANENT ROOMS)
    # =====================================================
    room_df = normalize(pd.read_excel("uploads/room_mapping.xlsx"))
    room_class_col = get_class_column(room_df)

    for _, r in room_df.iterrows():
        class_name = str(r[room_class_col]).strip()
        if class_name not in class_map:
            continue

        db.session.add(Room(
            name=str(r["room"]).strip(),
            capacity=int(r["capacity"]),
            is_permanent=True,
            owner_class_id=class_map[class_name]
        ))

    # =====================================================
    # 3️⃣ SUBJECT TYPE (LAB / THEORY)
    # =====================================================
    type_df = normalize(pd.read_excel("uploads/class_type.xlsx"))
    subject_type = {
        str(r["subject"]).strip(): str(r["type"]).lower()
        for _, r in type_df.iterrows()
    }

    # =====================================================
    # 4️⃣ TEACHERS & SUBJECTS (DEDUPLICATED)
    # =====================================================
    ts_df = normalize(pd.read_excel("uploads/teacher_subject_mapping.xlsx"))

    teacher_map = {}   # faculty_name -> Teacher
    subject_map = {}   # subject_name -> Subject

    for _, r in ts_df.iterrows():
        faculty = str(r["faculty"]).strip()
        subject_name = str(r["subject"]).strip()

        if faculty in teacher_map:
            teacher = teacher_map[faculty]
        else:
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

    # =====================================================
    # 5️⃣ CLASS TIMETABLES (EACH SHEET = ONE CLASS)
    # =====================================================
    xls = pd.ExcelFile("uploads/timetables.xlsx")

    for sheet_name in xls.sheet_names:
        class_name = sheet_name.strip()
        if class_name not in class_map:
            continue

        cls_id = class_map[class_name]
        cls = Class.query.get(cls_id)

        df = pd.read_excel(xls, sheet_name=sheet_name)
        df = normalize(df)

        day_col = df.columns[0]
        period_cols = df.columns[1:]

        for _, row in df.iterrows():
            day = str(row[day_col]).strip()

            for period in period_cols:
                subject_name = row[period]

                if pd.isna(subject_name):
                    continue

                subject_name = str(subject_name).strip()

                # Skip non-teaching slots
                if subject_name.lower() in ["activity hour", "activity"]:
                    continue

                # ---------------- LAB HOURS ----------------
                if subject_type.get(subject_name) == "lab":
                    db.session.add(TimetableEntry(
                        class_id=cls_id,
                        day=day,
                        slot=period,
                        batch=None,
                        is_lab_hour=True,
                        is_floating=False
                    ))
                    continue

                # ---------------- THEORY HOURS ----------------
                # Always ensure subject exists
                if subject_name in subject_map:
                    subject = subject_map[subject_name]
                else:
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

    # =====================================================
    # 6️⃣ PARALLEL CLASSES
    # =====================================================
    pc_df = normalize(pd.read_excel("uploads/parallel_classes.xlsx"))
    pc_class_col = get_class_column(pc_df)

    for _, r in pc_df.iterrows():
        class_name = str(r[pc_class_col]).strip()
        subject_name = str(r["subject"]).strip()

        if class_name not in class_map:
            continue

        if subject_name in subject_map:
            subject = subject_map[subject_name]
        else:
            subject = Subject(
                name=subject_name,
                is_lab=False,
                teacher_id=None
            )
            db.session.add(subject)
            db.session.flush()
            subject_map[subject_name] = subject

        db.session.add(TimetableEntry(
            class_id=class_map[class_name],
            subject_id=subject.id,
            teacher_id=subject.teacher_id,
            room_id=None,
            day=str(r["day"]).strip(),
            slot=str(r["period"]).strip(),
            batch=str(r["batch"]).strip(),
            is_lab_hour=False,
            is_floating=True
        ))

    db.session.commit()
