from flask import Flask, render_template, request
import os
from collections import defaultdict

from models import db, Class, Room, Subject, TimetableEntry
from input_processor import process_inputs

app = Flask(__name__)

# ---------------- CONFIG ----------------
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db.init_app(app)


# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/admin_upload", methods=["GET", "POST"])
def admin_upload():
    if request.method == "POST":
        files = {
            "class_strength": "class_strength.xlsx",
            "room_mapping": "room_mapping.xlsx",
            "class_type": "class_type.xlsx",
            "teacher_subject": "teacher_subject_mapping.xlsx",
            "parallel_classes": "parallel_classes.xlsx",
            "timetables": "timetables.xlsx",
        }

        for key, filename in files.items():
            if key not in request.files:
                return f"Missing file: {key}", 400

            request.files[key].save(
                os.path.join(app.config["UPLOAD_FOLDER"], filename)
            )

        process_inputs()
        return "✅ Files uploaded and data stored successfully"

    return render_template("admin_upload.html")


@app.route("/view/classes")
def view_classes():
    return render_template(
        "view_class.html",
        classes=Class.query.all()
    )


@app.route("/view/rooms")
def view_rooms():
    return render_template(
        "view_rooms.html",
        rooms=Room.query.all()
    )


@app.route("/view/subjects")
def view_subjects():
    return render_template(
        "view_subjects.html",
        subjects=Subject.query.all()
    )


@app.route("/view/timetable")
def view_timetable():
    entries = (
        TimetableEntry.query
        .order_by(
            TimetableEntry.class_id,
            TimetableEntry.day,
            TimetableEntry.slot
        )
        .all()
    )

    grouped_entries = defaultdict(list)
    for e in entries:
        grouped_entries[e.class_obj.name].append(e)

    return render_template(
        "view_timetable.html",
        grouped_entries=grouped_entries
    )


# ---------------- MAIN ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True, use_reloader=False)
