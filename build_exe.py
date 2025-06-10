# build_exe.py
import os
import subprocess
import sys
import configparser # --- اضافه شد: برای خواندن/نوشتن فایل INI ---

# --- مسیر فایل تنظیمات ورژن ---
VERSION_CONFIG_FILE = "version.ini"

# --- مسیر اسکریپت اصلی برنامه شما ---
MAIN_APP_SCRIPT = "main_app.py"

# --- نام پوشه خروجی PyInstaller ---
DIST_FOLDER_NAME = "dist"

# --- نام فایل EXE نهایی (بدون ورژن) ---
BASE_EXE_NAME = "EasyInvoice"

def _read_version_data_for_build():
    """ مقادیر ورژن را از فایل version.ini می‌خواند. """
    config = configparser.ConfigParser()
    config_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), VERSION_CONFIG_FILE)
    
    major = 1
    compile_c = 0
    build_c = 0
    
    try:
        if os.path.exists(config_file_path):
            config.read(config_file_path)
            major = config.getint('Version', 'MAJOR_VERSION', fallback=1)
            compile_c = config.getint('Version', 'COMPILE_COUNT', fallback=0)
            build_c = config.getint('Version', 'BUILD_COUNT', fallback=0)
        else:
            # اگر فایل وجود نداشت، با مقادیر پیش‌فرض ایجادش کن
            _write_version_data_for_build(major, compile_c, build_c)
            config.read(config_file_path) # دوباره بخوان تا مطمئن شویم فایل لود شده
    except Exception as e:
        print(f"Warning: Error reading version from {config_file_path} for build: {e}. Using default version (1.00(0)).")
        _write_version_data_for_build(1, 0, 0)
        return 1, 0, 0
    return major, compile_c, build_c

def _write_version_data_for_build(major, compile_c, build_c):
    """ مقادیر ورژن جدید را در فایل version.ini می‌نویسد. """
    config = configparser.ConfigParser()
    config['Version'] = {
        'MAJOR_VERSION': str(major),
        'COMPILE_COUNT': str(compile_c),
        'BUILD_COUNT': str(build_c)
    }
    config_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), VERSION_CONFIG_FILE)
    try:
        with open(config_file_path, "w") as f:
            config.write(f)
    except Exception as e:
        print(f"Error writing new version data to {config_file_path}: {e}")

def run_pyinstaller():
    """
    تابع اصلی برای اجرای PyInstaller.
    شماره Compile را افزایش داده و سپس فایل EXE را می‌سازد.
    """
    
    # --- مرحله 1: افزایش Compile Count در version.ini ---
    print("Incrementing compile version...")
    try:
        # برای افزایش COMPILE_COUNT، باید ورژن قبلی رو بخونیم و افزایش بدیم.
        current_major, current_compile_c, current_build_c = _read_version_data_for_build()
        
        current_compile_c += 1
        # فرض می‌کنیم VERSION_MINOR_LIMIT_APP هم 99 هست.
        if current_compile_c > 99: 
            current_major += 1
            current_compile_c = 0
        
        # بیلد کانت را در اینجا تغییر نمی‌دهیم، چون مربوط به اجرای برنامه است، نه کامپایل.
        _write_version_data_for_build(current_major, current_compile_c, current_build_c)
        
        # ورژن کامل برای نام فایل EXE
        full_version_string = f"v{current_major}.{current_compile_c:02d}({current_build_c})"
        print(f"Compile version updated to: {full_version_string}")
    except Exception as e:
        print(f"Error incrementing compile version: {e}")
        sys.exit(1)

    # --- مرحله 2: پاک کردن پوشه‌های قبلی (اختیاری اما توصیه می‌شود) ---
    print(f"Cleaning up previous build folders ({DIST_FOLDER_NAME}/ and build/)...")
    if os.path.exists(DIST_FOLDER_NAME):
        import shutil
        shutil.rmtree(DIST_FOLDER_NAME)
    if os.path.exists("build"):
        import shutil
        shutil.rmtree("build")
    
    # --- مرحله 3: ساخت فایل EXE با PyInstaller ---
    # --- تنظیم نام فایل EXE نهایی با ورژن ---
    final_exe_name = f"{BASE_EXE_NAME}_{full_version_string}"
    print(f"Running PyInstaller for {MAIN_APP_SCRIPT} to create {final_exe_name}.exe...")
    try:
        # مسیر فایل version.ini را به عنوان داده اضافی به پکیج اضافه می‌کنیم
        # تا برنامه در زمان اجرا بتواند آن را بخواند.
        command = [
            sys.executable, "-m", "PyInstaller", 
            "--onefile",
            "--windowed", 
            f"--name={final_exe_name}", # --- نام EXE با ورژن ---
            f"--add-data={os.path.join(os.path.dirname(os.path.abspath(__file__)), VERSION_CONFIG_FILE)};.", # اضافه کردن version.ini به root برنامه
            f"--add-data=assets;assets", # اگر پوشه assets دارید (آیکون‌ها، تمپلیت‌ها و...)
            # f"--icon=app_icon.ico", # اگر فایل آیکون دارید (نیاز به یک فایل .ico در روت پروژه)
            MAIN_APP_SCRIPT
        ]
        
        result = subprocess.run(command, capture_output=True, text=True, check=True) 
        
        print("PyInstaller output:")
        print(result.stdout)
        if result.stderr:
            print("PyInstaller errors:")
            print(result.stderr)
        
        print(f"\nSuccessfully created {final_exe_name}.exe in the {DIST_FOLDER_NAME}/ folder.")
        print("Final build process finished.")

    except subprocess.CalledProcessError as e:
        print(f"Error during PyInstaller execution: {e}")
        print("PyInstaller stdout:")
        print(e.stdout)
        print("PyInstaller stderr:")
        print(e.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: PyInstaller not found. Make sure it's installed and in your PATH.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_pyinstaller()