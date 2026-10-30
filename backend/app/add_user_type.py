from sqlalchemy import inspect, text

from .database import engine


def run():
    cols = [c["name"] for c in inspect(engine).get_columns("users")]
    with engine.begin() as conn:
        if "user_type" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN user_type VARCHAR(20) DEFAULT 'student'"))
        conn.execute(text("UPDATE users SET user_type='student' WHERE role='student_faculty'"))
        conn.execute(text("UPDATE users SET user_type='faculty' WHERE email='faculty@campus.edu'"))
        conn.execute(text("UPDATE users SET user_type='staff' WHERE role!='student_faculty'"))
    print("user_type is ready.")


if __name__ == "__main__":
    run()