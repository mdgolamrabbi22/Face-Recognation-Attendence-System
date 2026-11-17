# ============================================================
# build.py — PyInstaller .exe Build Script
# ============================================================
# Run: python build.py
# Output: dist/FaceAttendance/FaceAttendance.exe (Windows)
#         dist/FaceAttendance/FaceAttendance     (Linux)
# ============================================================

import os
import sys
import subprocess
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "FaceAttendance"
ICON_PATH = os.path.join(BASE_DIR, "assets", "logo.ico")


def check_pyinstaller():
    try:
        import PyInstaller
        print(f"[BUILD] PyInstaller {PyInstaller.__version__} found.")
    except ImportError:
        print("[BUILD] PyInstaller . Install  ...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyinstaller"])


def clean_old_build():
    for folder in ["build", "dist", f"{APP_NAME}.spec"]:
        path = os.path.join(BASE_DIR, folder)
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
    print("[BUILD]  build files   .")


def build():
    check_pyinstaller()
    clean_old_build()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name",          APP_NAME,
        # single folder (faster startup than onefile)
        "--onedir",
        "--windowed",                    # console window 
        "--noconfirm",
        "--clean",

# Comment translated to English.
        "--hidden-import", "face_recognition",
        "--hidden-import", "face_recognition_models",
        "--hidden-import", "dlib",
        "--hidden-import", "cv2",
        "--hidden-import", "PIL",
        "--hidden-import", "customtkinter",
        "--hidden-import", "mysql.connector",
        "--hidden-import", "bcrypt",
        "--hidden-import", "dotenv",
        "--hidden-import", "pandas",
        "--hidden-import", "matplotlib",
        "--hidden-import", "matplotlib.backends.backend_tkagg",

# Comment translated to English.
        "--add-data", f"assets{os.pathsep}assets",
        "--add-data", f"database{os.pathsep}database",

        # .env file
        "--add-data", f".env{os.pathsep}.",
    ]

# Comment translated to English.
    if os.path.exists(ICON_PATH):
        cmd += ["--icon", ICON_PATH]

    # Entry point
    cmd.append(os.path.join(BASE_DIR, "main.py"))

    print("[BUILD] Build  ... (   )")
    print("[BUILD] Command:", " ".join(cmd))

    result = subprocess.run(cmd, cwd=BASE_DIR)

    if result.returncode == 0:
        dist_path = os.path.join(BASE_DIR, "dist", APP_NAME)
        print("\n" + "="*50)
        print(f"[BUILD] ✅ Build !")
        print(f"[BUILD] Output: {dist_path}")
        print("="*50)
        print("\nShare  :")
        print("  1. dist/FaceAttendance/ folder   .env file ")
        print("  2. MySQL install    target machine ")
        print("  3. schema.sql run  ")
    else:
        print("\n[BUILD] ❌ Build fail .")
        print("  dlib  install   .")


if __name__ == "__main__":
    build()