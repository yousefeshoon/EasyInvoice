# settings_manager.py
import os
import sys

from db_manager import DBManager, DATABASE_NAME, DATABASE_SCHEMA_VERSION 
from models import AppSettings, Service # Service اضافه شد تا بتونیم در متد جدید ازش استفاده کنیم

class SettingsManager:
    def __init__(self):
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATABASE_NAME)
        self.db_manager = DBManager(db_path)

    def get_settings(self):
        if not self.db_manager.connect():
            return AppSettings()

        cursor = self.db_manager.execute_query("SELECT * FROM AppSettings WHERE id = 1")
        if cursor:
            row = cursor.fetchone()
            self.db_manager.close()
            if row:
                return AppSettings.from_dict(dict(row))
        self.db_manager.close()
        return AppSettings() 

    def save_settings(self, settings: AppSettings):
        if not self.db_manager.connect():
            return False
        
        settings.db_version = DATABASE_SCHEMA_VERSION 

        query = """
        INSERT OR REPLACE INTO AppSettings 
        (id, seller_name, seller_address, seller_phone, seller_tax_id, 
         seller_economic_code, seller_logo_path, db_version) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?) 
        """
        params = (
            1, 
            settings.seller_name,
            settings.seller_address,
            settings.seller_phone,
            settings.seller_tax_id,
            settings.seller_economic_code, 
            settings.seller_logo_path,     
            settings.db_version
        )
        success = self.db_manager.execute_query(query, params) is not None
        self.db_manager.close()
        return success

    # این متد برای حل مشکل ModuleNotFoundError اضافه شده بود
    # تا invoice_generator و invoice_ui بتوانند توضیحات سرویس را بخوانند
    # اگرچه از نظر معماری ایده آل نیست، اما در حال حاضر مشکل را حل می‌کند.
    def get_service_description_by_id(self, service_id: int):
        """ بازیابی توضیحات سرویس بر اساس شناسه سرویس. """
        if not self.db_manager.connect():
            return None
        
        query = "SELECT description FROM Services WHERE id = ?"
        cursor = self.db_manager.execute_query(query, (service_id,))
        description = None
        if cursor:
            row = cursor.fetchone()
            if row:
                description = row['description']
        self.db_manager.close()
        return description


# --- بلاک تست مستقل ---
if __name__ == "__main__":
    db_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATABASE_NAME)
    
    if not os.path.exists(db_file_path):
        print("Database not found. Initializing database...")
        db_temp_manager = DBManager(db_file_path)
        if db_temp_manager.connect():
            db_temp_manager.create_tables()
            db_temp_manager.migrate_database()
            db_temp_manager.close()
        else:
            print("Failed to initialize database.")
            sys.exit(1)
    
    settings_manager = SettingsManager()

    print("\n--- Testing SettingsManager ---")

    settings = settings_manager.get_settings()
    if settings:
        print("Initial Settings:", settings.to_dict())
    else:
        print("Could not retrieve initial settings.")
        settings = AppSettings() 

    settings.seller_name = "شرکت خدمات آسان‌فاکتور جدید"
    settings.seller_address = "تهران، خیابان آزادی، پلاک ۲۰۰"
    settings.seller_phone = "021-98765432"
    settings.seller_tax_id = "12345678901"
    settings.seller_economic_code = "987654321098" 
    settings.seller_logo_path = "C:/path/to/my_logo.png" 
    
    if settings_manager.save_settings(settings):
        print("Settings saved successfully.")
    else:
        print("Failed to save settings.")

    updated_settings = settings_manager.get_settings()
    if updated_settings:
        print("Updated Settings:", updated_settings.to_dict())
    else:
        print("Could not retrieve updated settings.")
    
    final_settings = settings_manager.get_settings()
    if final_settings:
        print("Final Settings after update:", final_settings.to_dict())
    else:
        print("Could not retrieve final settings.")

    # تست get_service_description_by_id
    # این بلاک نیاز به وجود services_manager و مدل Service دارد تا بتواند تست شود
    try:
        from service_manager import ServiceManager # از services_manager موجود شما استفاده می‌شود
        from models import Service

        svc_man = ServiceManager()
        # اضافه کردن یک سرویس موقت برای تست
        svc_man.add_service(Service(service_code=999, description="خدمت تست توضیحات"))
        all_services, _ = svc_man.get_all_services()
        if all_services:
            test_service_id = all_services[0].id
            service_desc = settings_manager.get_service_description_by_id(test_service_id)
            print(f"\nDescription for service ID {test_service_id}: {service_desc}")
        else:
            print("\nNo services to test get_service_description_by_id.")
    except ImportError:
        print("\nCould not import ServiceManager for testing get_service_description_by_id (ignore if not running this test block).")