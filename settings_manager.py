import os
import sys

from db_manager import DBManager, DATABASE_NAME, DATABASE_SCHEMA_VERSION 
from models import AppSettings, Service 

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