# service_manager.py
import os
import sqlite3
from db_manager import DBManager, DATABASE_NAME
from models import Service

class ServiceManager:
    def __init__(self):
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATABASE_NAME)
        self.db_manager = DBManager(db_path)

    def get_next_service_code(self):
        """ بازیابی آخرین کد خدمت ذخیره شده و بازگرداندن کد بعدی (شروع از 1001) """
        if not self.db_manager.connect():
            return 1001 # اگر اتصال برقرار نشد، از کد پیش‌فرض شروع کن
        
        # پیدا کردن بزرگترین service_code موجود
        cursor = self.db_manager.execute_query("SELECT MAX(service_code) FROM Services")
        next_code = 1001
        if cursor:
            row = cursor.fetchone()
            if row and row[0] is not None:
                next_code = int(row[0]) + 1
        self.db_manager.close()
        return next_code

    def add_service(self, service: Service):
        """ اضافه کردن یک خدمت جدید به دیتابیس """
        if not self.db_manager.connect():
            return False, "خطا در اتصال به دیتابیس."
        try:
            # اگر service_code خالی بود، تولید خودکار انجام شود
            final_service_code = service.service_code
            if final_service_code is None:
                final_service_code = self.get_next_service_code()
                # بعد از گرفتن کد، اتصال جدید باز می‌شود، پس اینجا دوباره connect نکن
                # بلکه مطمئن شو که کد به درستی تولید شده.
                # نکته: این منطق در UI هم باید مدیریت شود تا کد را قبل از ارسال بسازد.
                
            cursor = self.db_manager.execute_query(
                "INSERT INTO Services (service_code, description, settlement_type) VALUES (?, ?, ?)",
                (final_service_code, service.description, service.settlement_type)
            )
            self.db_manager.close()
            if cursor:
                return True, "خدمت با موفقیت اضافه شد."
            else:
                return False, "خطا در اضافه کردن خدمت."
        except sqlite3.IntegrityError as e:
            self.db_manager.close()
            if "UNIQUE constraint failed: Services.description, Services.settlement_type" in str(e):
                return False, "این شرح خدمت با این نوع تسویه قبلاً ثبت شده است."
            elif "UNIQUE constraint failed: Services.service_code" in str(e):
                return False, "کد خدمت وارد شده تکراری است."
            else:
                return False, f"خطای تکراری بودن داده: {e}"
        except Exception as e:
            self.db_manager.close()
            return False, f"خطای ناشناخته در اضافه کردن خدمت: {e}"

    def get_all_services(self):
        """ بازیابی تمام خدمات از دیتابیس """
        if not self.db_manager.connect():
            return [], "خطا در اتصال به دیتابیس."
        cursor = self.db_manager.execute_query("SELECT * FROM Services")
        services = []
        if cursor:
            for row in cursor.fetchall():
                services.append(Service.from_dict(dict(row)))
        self.db_manager.close()
        return services, "خدمات با موفقیت بازیابی شد."

    def get_service_by_id(self, service_id: int):
        """ بازیابی یک خدمت بر اساس شناسه """
        if not self.db_manager.connect():
            return None, "خطا در اتصال به دیتابیس."
        cursor = self.db_manager.execute_query("SELECT * FROM Services WHERE id = ?", (service_id,))
        service = None
        if cursor:
            row = cursor.fetchone()
            if row:
                service = Service.from_dict(dict(row))
        self.db_manager.close()
        return service, "خدمت با موفقیت بازیابی شد."

    def update_service(self, service: Service):
        """ بروزرسانی یک خدمت موجود در دیتابیس """
        if not self.db_manager.connect():
            return False, "خطا در اتصال به دیتابیس."
        try:
            cursor = self.db_manager.execute_query(
                "UPDATE Services SET service_code = ?, description = ?, settlement_type = ? WHERE id = ?",
                (service.service_code, service.description, service.settlement_type, service.id)
            )
            self.db_manager.close()
            if cursor and cursor.rowcount > 0:
                return True, "خدمت با موفقیت بروزرسانی شد."
            else:
                return False, "خدمت مورد نظر یافت نشد یا تغییری اعمال نشد."
        except sqlite3.IntegrityError as e:
            self.db_manager.close()
            if "UNIQUE constraint failed: Services.description, Services.settlement_type" in str(e):
                return False, "این شرح خدمت با این نوع تسویه قبلاً ثبت شده است."
            elif "UNIQUE constraint failed: Services.service_code" in str(e):
                return False, "کد خدمت وارد شده تکراری است."
            else:
                return False, f"خطای تکراری بودن داده: {e}"
        except Exception as e:
            self.db_manager.close()
            return False, f"خطای ناشناخته در بروزرسانی خدمت: {e}"

    def delete_service(self, service_id: int):
        """ حذف یک خدمت از دیتابیس """
        if not self.db_manager.connect():
            return False, "خطا در اتصال به دیتابیس."
        cursor = self.db_manager.execute_query("DELETE FROM Services WHERE id = ?", (service_id,))
        self.db_manager.close()
        if cursor and cursor.rowcount > 0:
            return True, "خدمت با موفقیت حذف شد."
        else:
            return False, "خدمت مورد نظر یافت نشد."

# --- بلاک تست مستقل ---
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_file_path = os.path.join(current_dir, DATABASE_NAME)

    db_test_manager = DBManager(db_file_path)
    if db_test_manager.connect():
        db_test_manager.create_tables()
        db_test_manager.migrate_database()
        db_test_manager.close()
    else:
        print("Failed to connect for test setup.")
        sys.exit(1)

    service_manager = ServiceManager()

    print("\n--- Testing ServiceManager ---")

    # تست get_next_service_code
    next_code = service_manager.get_next_service_code()
    print(f"Next available service code: {next_code}")

    # تست افزودن خدمت (با کد دستی و خودکار)
    print("Adding new service (manual code 1001)...")
    new_service_m1 = Service(service_code=1001, description="نصب و راه‌اندازی", settlement_type="پروژه ای")
    success, message = service_manager.add_service(new_service_m1)
    print(f"Add Service 1: {success} - {message}")

    print("Adding new service (auto code)...")
    new_service_auto = Service(description="پشتیبانی نرم‌افزار", settlement_type="ماهانه")
    success, message = service_manager.add_service(new_service_auto)
    print(f"Add Service 2: {success} - {message}")

    next_code = service_manager.get_next_service_code()
    print(f"Next available service code after auto-add: {next_code}")

    # تست افزودن خدمت تکراری (description, settlement_type)
    print("\nAdding duplicate service (description, type)...")
    duplicate_service = Service(service_code=1002, description="طراحی سایت شرکتی", settlement_type="پروژه ای") # فرض کنیم طراحی سایت قبلا اضافه شده
    success, message = service_manager.add_service(duplicate_service)
    print(f"Add Duplicate Service: {success} - {message}")

    # تست افزودن خدمت با کد تکراری
    print("\nAdding service with duplicate service code...")
    duplicate_code_service = Service(service_code=1001, description="آموزش حضوری", settlement_type="ساعت")
    success, message = service_manager.add_service(duplicate_code_service)
    print(f"Add Duplicate Code Service: {success} - {message}")


    # تست بازیابی همه خدمات
    print("\nGetting all services...")
    services, message = service_manager.get_all_services()
    for s in services:
        print(f"ID: {s.id}, Code: {s.service_code}, Description: {s.description}, Type: {s.settlement_type}")

    # تست بروزرسانی خدمت
    if services:
        service_to_update = services[0]
        service_to_update.description = "نصب و راه‌اندازی (آپدیت)"
        service_to_update.settlement_type = "ماهانه"
        service_to_update.service_code = 1005 # کد رو هم آپدیت کن
        print(f"\nUpdating service ID {service_to_update.id}...")
        success, message = service_manager.update_service(service_to_update)
        print(f"Update Service: {success} - {message}")

        updated_services, _ = service_manager.get_all_services()
        print("Services after update:")
        for s in updated_services:
            print(f"ID: {s.id}, Code: {s.service_code}, Description: {s.description}, Type: {s.settlement_type}")
    
    # تست حذف خدمت
    if len(services) > 1:
        service_id_to_delete = services[1].id
        print(f"\nDeleting service ID {service_id_to_delete}...")
        success, message = service_manager.delete_service(service_id_to_delete)
        print(f"Delete Service: {success} - {message}")

        final_services, _ = service_manager.get_all_services()
        print("Services after deletion:")
        for s in final_services:
            print(f"ID: {s.id}, Code: {s.service_code}, Description: {s.description}, Type: {s.settlement_type}")