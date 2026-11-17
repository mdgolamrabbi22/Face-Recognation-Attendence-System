# Comment translated to English.
import bcrypt
from database.db_connection import execute_query

username = "admin"           #  admin username
plain_password = "1234"      #  actual plain password

new_hash = bcrypt.hashpw(plain_password.encode(
    "utf-8"), bcrypt.gensalt()).decode("utf-8")

execute_query(
    "UPDATE admins SET password_hash=%s WHERE username=%s",
    (new_hash, username)
)

print("✅ Password hash  update !")