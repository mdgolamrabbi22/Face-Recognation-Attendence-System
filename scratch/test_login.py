import os
import sys

# ✅ Path adjustment MUST come before importing local packages
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

import customtkinter as ctk
from views.admin_login import AdminLogin

def test_admin_login():
    app = ctk.CTk()
    app.withdraw()
    
    try:
        print("Testing AdminLogin instantiation...")
        login = AdminLogin(on_close=app.destroy, master=app)
        print("AdminLogin instantiated successfully.")
        # We won't run mainloop, just check if it builds without error
        login.destroy()
        app.destroy()
        print("Test passed.")
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_admin_login()
