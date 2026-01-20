from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    strength = db.Column(db.Integer)
    class_category = db.Column(db.String(10))  # permanent / floating

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    capacity = db.Column(db.Integer)
    is_permanent = db.Column(db.Boolean)
    owner_class_id = db.Column(db.Integer)

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    is_lab = db.Column(db.Boolean)
    teacher_id = db.Column(db.Integer)

class TimetableEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer)
    subject_id = db.Column(db.Integer, nullable=True)
    teacher_id = db.Column(db.Integer, nullable=True)
    room_id = db.Column(db.Integer, nullable=True)
    day = db.Column(db.String(15))
    slot = db.Column(db.String(20))
    batch = db.Column(db.String(5), nullable=True)
    is_lab_hour = db.Column(db.Boolean)
    is_floating = db.Column(db.Boolean)
