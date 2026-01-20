import pandas as pd
from models import db, Class, Room, Teacher, Subject, TimetableEntry


# ---------------- HELPER FUNCTIONS ----------------

def normalize(df):
    """
    Normalize column names: lowercase, no spaces
    """
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )
    return df


def get_class_column(df):
    """
    Safely detect class column
    """
    if "class" in df.columns:
        return "class"
    if "class_name" in df.columns:
        return "class_name"
    raise ValueError(f"No class column found. Columns: {list(df.columns)}")


# ---------------- MAIN PROCESSOR ----------------

def process_inputs():
    # -------- CLEAR OLD DATA --------
    TimetableEntry.query.delete()
    Subject.query.delete()
    Teacher.query.delete()
    Room.query.delete()
    Class.query.delete()
    db.session.commit()

    # =====================================================
    # 1️⃣ CLASS STRENGTH (class, strength, class_category)
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
    # 2️⃣ ROOM MAPPING (class → permanent room)
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
    # 3️⃣ SUBJECT TYPE (lab / theory)
    # =====================================================
    type_df = normalize(pd.read_excel("uploads/class_type.xlsx"))
    subject_type = {
        str(r["subject"]).strip(): str(r["type"]).lower()
        for _, r in type_df.iterrows()
    }

    # =====================================================
    # 4️⃣ TEACHER – SUBJECT (faculty, subject)
    # =====================================================
    ts_df = normalize(pd.read_excel("uploads/teacher_subject_mapping.xlsx"))

    subject_teacher_map = {}

    for _, r in ts_df.iterrows():
        teacher = Teacher(name=str(r["faculty"]).strip())
        db.session.add(teacher)
        db.session.flush()

        subject_name = str(r["subject"]).strip()

        subject = Subject(
            name=subject_name,
            is_lab=(subject_type.get(subject_name) == "lab"),
            teacher_id=teacher.id
        )
        db.session.add(subject)
        db.session.flush()

        subject_teacher_map[subject_name] = subject

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

        # First column = day
        day_col = df.columns[0]

        # Remaining columns = periods (8.00-8.45 etc.)
        period_cols = df.columns[1:]

        for _, row in df.iterrows():
            day = str(row[day_col]).strip()

            for period in period_cols:
                subject_name = row[period]

                if pd.isna(subject_name):
                    continue

                subject_name = str(subject_name).strip()

                # Skip non-academic slots
                if subject_name.lower() in ["activity hour", "activity"]:
                    continue

                subj_type = subject_type.get(subject_name, "theory")

                # LAB → room becomes free
                if subj_type == "lab":
                    db.session.add(TimetableEntry(
                        class_id=cls_id,
                        day=day,
                        slot=period,
                        batch=None,
                        is_lab_hour=True,
                        is_floating=False
                    ))
                else:
                    subject = subject_teacher_map.get(subject_name)
                    if not subject:
                        continue

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
    # 6️⃣ PARALLEL CLASSES (class, day, period, batch, subject)
    # =====================================================
    pc_df = normalize(pd.read_excel("uploads/parallel_classes.xlsx"))
    pc_class_col = get_class_column(pc_df)

    for _, r in pc_df.iterrows():
        class_name = str(r[pc_class_col]).strip()
        subject_name = str(r["subject"]).strip()

        if class_name not in class_map:
            continue

        subject = subject_teacher_map.get(subject_name)
        if not subject:
            continue

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
