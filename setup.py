# ============================================================
# Comment translated to English.
# ============================================================
# Run: python setup.py
# Comment translated to English.
# Comment translated to English.
# Comment translated to English.
# Comment translated to English.
# ============================================================

import os
import sys
import bcrypt

# Comment translated to English.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def create_env_file():
    """ .env     ."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        print("[SETUP] .env file   , skip  .")
        return

    print("\n[SETUP] .env file   ...")
    db_password = input(
        "MySQL password  (blank =  password ): ").strip()
    db_user = input("MySQL username  (default=root): ").strip() or "root"
    db_name = input("Database name  (default=face_attendance_db): ").strip(
    ) or "face_attendance_db"

    content = f"""# Face Attendance System — Environment Variables
DB_HOST=localhost
DB_PORT=3306
DB_USER={db_user}
DB_PASSWORD={db_password}
DB_NAME={db_name}
"""
    with open(env_path, "w") as f:
        f.write(content)
    print(f"[SETUP] ✓ .env file  : {env_path}")


def setup_admin_password():
    """Admin  default password hash  DB  save ."""
    from database.db_connection import test_connection, execute_query

    if not test_connection():
        print("[SETUP] ✗ DB connect  . MySQL    .")
        return

    print("\n[SETUP] Admin account setup  ...")
    username = input("Admin username  (default=admin): ").strip() or "admin"
    password = input(
        "Admin password  (default=admin123): ").strip() or "admin123"

    hashed = bcrypt.hashpw(password.encode(
        "utf-8"), bcrypt.gensalt()).decode("utf-8")

# Comment translated to English.
    existing = execute_query(
        "SELECT id FROM admins WHERE username=%s",
        (username,),
        fetch="one"
    )
    if existing:
        execute_query(
            "UPDATE admins SET password_hash=%s WHERE username=%s",
            (hashed, username)
        )
        print(f"[SETUP] ✓ Admin '{username}'  password update .")
    else:
        execute_query(
            "INSERT INTO admins (username, password_hash) VALUES (%s, %s)",
            (username, hashed)
        )
        print(f"[SETUP] ✓ Admin '{username}'  .")


def create_directories():
    """ directory   ."""
    dirs = [
        "assets",
        "assets/unknown_faces",
        "database",
        "models",
        "views",
        "services",
    ]
    for d in dirs:
        path = os.path.join(os.path.dirname(__file__), d)
        os.makedirs(path, exist_ok=True)
    print("[SETUP] ✓  directory  .")


if __name__ == "__main__":
    print("=" * 50)
    print("  Face Attendance System — First Time Setup")
    print("=" * 50)

    create_env_file()
    create_directories()

    try:
        setup_admin_password()
    except Exception as e:
        print(f"[SETUP] Admin setup skip : {e}")
        print("  → schema.sql  run ,  setup.py  .")

    print("\n[SETUP] ✓ Setup !  main.py .")