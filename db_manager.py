# db_manager.py
import sqlite3
import os
import sys

DATABASE_NAME = "easy_invoice.db"
DATABASE_SCHEMA_VERSION = 15 # افزایش یافت به 15

class DBManager:
    def __init__(self, db_path):
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        self.db_path = os.path.join(base_path, DATABASE_NAME)
        
        self.conn = None

    def connect(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            print(f"Connected to database: {self.db_path}")
            return True
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            return False

    def close(self):
        if self.conn:
            self.conn.close()
            print("Database connection closed.")

    def execute_query(self, query, params=()):
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            return cursor
        except sqlite3.Error as e:
            print(f"Error executing query: {query} with params {params} - {e}")
            return None

    def create_tables(self):
        queries = [
            """
            CREATE TABLE IF NOT EXISTS AppSettings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_name TEXT,
                seller_address TEXT,
                seller_phone TEXT,
                seller_tax_id TEXT,
                seller_economic_code TEXT,
                seller_logo_path TEXT,
                db_version INTEGER DEFAULT 0
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_code INTEGER UNIQUE,
                name TEXT NOT NULL,
                customer_type TEXT NOT NULL,
                address TEXT,
                phone TEXT,
                phone2 TEXT,
                mobile TEXT,
                email TEXT UNIQUE,
                tax_id TEXT UNIQUE,
                postal_code TEXT,
                notes TEXT,
                registration_date TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_code INTEGER UNIQUE,
                description TEXT NOT NULL UNIQUE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                contract_number TEXT UNIQUE NOT NULL,
                contract_date TEXT,               -- تاریخ قرارداد
                total_amount REAL,
                description TEXT,
                title TEXT,               -- عنوان قرارداد (باقی ماند)
                payment_method TEXT,      -- نحوه پرداخت (باقی ماند)
                scanned_pages TEXT,       -- مسیر اسکن‌ها (JSON)
                FOREIGN KEY (customer_id) REFERENCES Customers(id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL UNIQUE,
                customer_id INTEGER NOT NULL,
                contract_id INTEGER,
                issue_date TEXT NOT NULL,
                due_date TEXT,
                total_amount REAL NOT NULL,
                discount_percentage REAL DEFAULT 0,
                tax_percentage REAL DEFAULT 0,
                final_amount REAL NOT NULL,
                description TEXT,
                FOREIGN KEY (customer_id) REFERENCES Customers(id),
                FOREIGN KEY (contract_id) REFERENCES Contracts(id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS InvoiceItems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                total_price REAL NOT NULL,
                FOREIGN KEY (invoice_id) REFERENCES Invoices(id) ON DELETE CASCADE,
                FOREIGN KEY (service_id) REFERENCES Services(id)
            );
            """,
            # اضافه شد: جدول InvoiceTemplates
            """
            CREATE TABLE IF NOT EXISTS InvoiceTemplates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_name TEXT UNIQUE NOT NULL,
                template_type TEXT NOT NULL,
                required_fields TEXT,       -- JSON array of required field names
                template_settings TEXT,      -- تغییر از default_settings به template_settings (JSON object of default values/rules)
                is_active INTEGER DEFAULT 1, -- 1 for active, 0 for inactive
                header_image_path TEXT,     -- مسیر عکس هدر
                footer_image_path TEXT,     -- مسیر عکس فوتر
                background_image_path TEXT, -- مسیر عکس بک‌گراند
                background_opacity REAL     -- شفافیت بک‌گراند (0.0 تا 1.0)
            );
            """
        ]
        for query in queries:
            if not self.execute_query(query):
                print(f"Failed to create table with query: {query}")
                return False
        print("All tables created or already exist.")
        return True

    def get_db_version(self):
        cursor = self.execute_query("SELECT db_version FROM AppSettings WHERE id = 1")
        if cursor:
            row = cursor.fetchone()
            if row:
                return row['db_version']
        return 0

    def set_db_version(self, version):
        self.execute_query("INSERT OR IGNORE INTO AppSettings (id) VALUES (?)", (1,))
        self.execute_query("UPDATE AppSettings SET db_version = ? WHERE id = 1", (version,))

    def migrate_database(self):
        current_db_version = self.get_db_version()
        print(f"Current database version: {current_db_version}")

        if current_db_version < 2:
            print("Migrating to version 2: Adding seller_economic_code and seller_logo_path to AppSettings...")
            try:
                self.execute_query("ALTER TABLE AppSettings ADD COLUMN seller_economic_code TEXT;")
                self.execute_query("ALTER TABLE AppSettings ADD COLUMN seller_logo_path TEXT;")
                print("Migration to version 2 successful.")
                self.set_db_version(2)
            except sqlite3.Error as e:
                print(f"Error migrating to version 2: {e}")
        
        if current_db_version < 3:
            print("Migrating to version 3: Removing invoice_number_format and last_invoice_number from AppSettings...")
            try:
                self.execute_query("""
                    CREATE TABLE AppSettings_temp (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        seller_name TEXT,
                        seller_address TEXT,
                        seller_phone TEXT,
                        seller_tax_id TEXT,
                        seller_economic_code TEXT,
                        seller_logo_path TEXT,
                        db_version INTEGER DEFAULT 0
                    );
                """)
                self.execute_query("""
                    INSERT INTO AppSettings_temp (id, seller_name, seller_address, seller_phone, seller_tax_id, seller_economic_code, seller_logo_path, db_version)
                    SELECT id, seller_name, seller_address, seller_phone, seller_tax_id, seller_economic_code, seller_logo_path, db_version
                    FROM AppSettings;
                """)
                self.execute_query("DROP TABLE AppSettings;")
                self.execute_query("ALTER TABLE AppSettings_temp RENAME TO AppSettings;")
                print("Migration to version 3 successful.")
                self.set_db_version(3)
            except sqlite3.Error as e:
                print(f"Error migrating to version 3 (AppSettings schema change): {e}")

        if current_db_version < 4:
            print("Migrating to version 4: Modifying Services table schema (description and settlement_type)...")
            try:
                self.execute_query("""
                    CREATE TABLE Services_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        description TEXT NOT NULL UNIQUE,
                        settlement_type TEXT NOT NULL
                    );
                """)
                self.execute_query("""
                    INSERT INTO Services_new (id, description, settlement_type)
                    SELECT id, name, unit
                    FROM Services;
                """)
                self.execute_query("DROP TABLE Services;")
                self.execute_query("ALTER TABLE Services_new RENAME TO Services;")
                print("Migration to version 4 successful.")
                self.set_db_version(4)
            except sqlite3.Error as e:
                print(f"Error migrating to version 4 (Services schema change): {e}")

        if current_db_version < 5:
            print("Migrating to version 5: Adding service_code and UNIQUE constraint to Services table...")
            try:
                self.execute_query("""
                    CREATE TABLE Services_temp (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service_code INTEGER UNIQUE,
                        description TEXT NOT NULL,
                        settlement_type TEXT NOT NULL,
                        UNIQUE(description, settlement_type)
                    );
                """)
                self.execute_query("""
                    INSERT INTO Services_temp (id, description, settlement_type)
                    SELECT id, description, settlement_type
                    FROM Services;
                """)
                self.execute_query("DROP TABLE Services;")
                self.execute_query("ALTER TABLE Services_temp RENAME TO Services;")
                print("Migration to version 5 successful.")
                self.set_db_version(5)
            except sqlite3.Error as e:
                print(f"Error migrating to version 5 (Services schema change): {e}")
        
        if current_db_version < 6:
            print("Migrating to version 6: Removing settlement_type from Services table and setting UNIQUE on description...")
            try:
                self.execute_query("""
                    CREATE TABLE Services_temp (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service_code INTEGER UNIQUE,
                        description TEXT NOT NULL UNIQUE
                    );
                """)
                self.execute_query("""
                    INSERT INTO Services_temp (id, service_code, description)
                    SELECT id, service_code, description
                    FROM Services;
                """)
                self.execute_query("DROP TABLE Services;")
                self.execute_query("ALTER TABLE Services_temp RENAME TO Services;")
                print("Migration to version 6 successful.")
                self.set_db_version(6)
            except sqlite3.Error as e:
                print(f"Error migrating to version 6 (Services schema change): {e}")

        if current_db_version < 7:
            print("Migrating to version 7: Adding customer_code, customer_type, phone2, mobile, postal_code, notes to Customers table and setting UNIQUE on customer_code and tax_id...")
            try:
                self.execute_query("""
                    CREATE TABLE Customers_temp (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_code INTEGER UNIQUE,
                        name TEXT NOT NULL,
                        customer_type TEXT NOT NULL,
                        company_name TEXT,
                        address TEXT,
                        phone TEXT,
                        phone2 TEXT,
                        mobile TEXT,
                        email TEXT UNIQUE,
                        tax_id TEXT UNIQUE,
                        postal_code TEXT,
                        notes TEXT,
                        registration_date TEXT DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                self.execute_query("""
                    INSERT INTO Customers_temp (id, name, company_name, address, phone, email, tax_id, registration_date)
                    SELECT id, name, company_name, address, phone, email, tax_id, registration_date
                    FROM Customers;
                """)
                self.execute_query("DROP TABLE Customers;")
                self.execute_query("ALTER TABLE Customers_temp RENAME TO Customers;")
                print("Migration to version 7 successful.")
                self.set_db_version(7)
            except sqlite3.Error as e:
                print(f"Error migrating to version 7 (Customers schema change): {e}")

        # بلاک مهاجرت برای حذف company_name از Customers
        if current_db_version < 8:
            print("Migrating to version 8: Removing company_name from Customers table...")
            try:
                self.execute_query("""
                    CREATE TABLE Customers_temp (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_code INTEGER UNIQUE,
                        name TEXT NOT NULL,
                        customer_type TEXT NOT NULL,
                        address TEXT,
                        phone TEXT,
                        phone2 TEXT,
                        mobile TEXT,
                        email TEXT UNIQUE,
                        tax_id TEXT UNIQUE,
                        postal_code TEXT,
                        notes TEXT,
                        registration_date TEXT DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                self.execute_query("""
                    INSERT INTO Customers_temp (id, customer_code, name, customer_type, address, phone, phone2, mobile, email, tax_id, postal_code, notes, registration_date)
                    SELECT id, customer_code, name, customer_type, address, phone, phone2, mobile, email, tax_id, postal_code, notes, registration_date
                    FROM Customers;
                """)
                self.execute_query("DROP TABLE Customers;")
                self.execute_query("ALTER TABLE Customers_temp RENAME TO Customers;")
                print("Migration to version 8 successful.")
                self.set_db_version(8)
            except sqlite3.Error as e:
                print(f"Error migrating to version 8 (Customers schema change): {e}")

        # بلاک مهاجرت برای جدول Contracts (حذف ستون‌های اضافی و اضافه کردن contract_date)
        if current_db_version < 9:
            print("Migrating to version 9: Adding new columns to Contracts table...")
            try:
                self.execute_query("""
                    CREATE TABLE Contracts_temp (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_id INTEGER NOT NULL,
                        contract_number TEXT UNIQUE NOT NULL,
                        start_date TEXT NOT NULL,
                        end_date TEXT,
                        total_amount REAL,
                        description TEXT,
                        title TEXT,
                        services_provided TEXT,
                        fiscal_year TEXT,
                        scanned_pages TEXT,
                        payment_method TEXT,
                        FOREIGN KEY (customer_id) REFERENCES Customers(id)
                    );
                """)
                self.execute_query("""
                    INSERT INTO Contracts_temp (id, customer_id, contract_number, start_date, end_date, total_amount, description, title, services_provided, fiscal_year, scanned_pages, payment_method)
                    SELECT id, customer_id, contract_number, start_date, end_date, total_amount, description, title, services_provided, fiscal_year, scanned_pages, payment_method
                    FROM Contracts;
                """)
                self.execute_query("DROP TABLE Contracts;")
                self.execute_query("ALTER TABLE Contracts_temp RENAME TO Contracts;")
                print("Migration to version 9 successful.")
                self.set_db_version(9)
            except sqlite3.Error as e:
                print(f"Error migrating to version 9 (Contracts schema change): {e}")

        # بلاک مهاجرت برای حذف ستون‌های اضافی از Contracts و اضافه کردن contract_date
        if current_db_version < 10:
            print("Migrating to version 10: Removing redundant columns from Contracts and adding contract_date...")
            try:
                self.execute_query("""
                    CREATE TABLE Contracts_temp (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_id INTEGER NOT NULL,
                        contract_number TEXT UNIQUE NOT NULL,
                        contract_date TEXT,
                        total_amount REAL,
                        description TEXT,
                        scanned_pages TEXT,
                        FOREIGN KEY (customer_id) REFERENCES Customers(id)
                    );
                """)
                self.execute_query("""
                    INSERT INTO Contracts_temp (id, customer_id, contract_number, total_amount, description, scanned_pages)
                    SELECT id, customer_id, contract_number, total_amount, description, scanned_pages
                    FROM Contracts;
                """)
                self.execute_query("DROP TABLE Contracts;")
                self.execute_query("ALTER TABLE Contracts_temp RENAME TO Contracts;")
                print("Migration to version 10 successful.")
                self.set_db_version(10)
            except sqlite3.Error as e:
                print(f"Error migrating to version 10 (Contracts schema change): {e}")
        
        # بلاک مهاجرت جدید برای حذف start_date, end_date, services_provided و حفظ title, payment_method
        if current_db_version < 11:
            print("Migrating to version 11: Removing start_date, end_date, services_provided from Contracts, keeping title and payment_method...")
            try:
                self.execute_query("""
                    CREATE TABLE Contracts_temp (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_id INTEGER NOT NULL,
                        contract_number TEXT UNIQUE NOT NULL,
                        contract_date TEXT,
                        total_amount REAL,
                        description TEXT,
                        title TEXT,               -- عنوان قرارداد (باقی ماند)
                        payment_method TEXT,      -- نحوه پرداخت (باقی ماند)
                        scanned_pages TEXT,
                        FOREIGN KEY (customer_id) REFERENCES Customers(id)
                    );
                """)
                # کپی کردن داده‌های موجود به جز فیلدهای حذف شده
                self.execute_query("""
                    INSERT INTO Contracts_temp (id, customer_id, contract_number, contract_date, total_amount, description, title, payment_method, scanned_pages)
                    SELECT id, customer_id, contract_number, contract_date, total_amount, description, title, payment_method, scanned_pages
                    FROM Contracts;
                """)
                self.execute_query("DROP TABLE Contracts;")
                self.execute_query("ALTER TABLE Contracts_temp RENAME TO Contracts;")
                print("Migration to version 11 successful.")
                self.set_db_version(11)
            except sqlite3.Error as e:
                print(f"Error migrating to version 11 (Contracts schema change): {e}")

        # بلاک مهاجرت جدید برای جداول Invoices و InvoiceItems
        if current_db_version < 12:
            print("Migrating to version 12: Adding Invoices and InvoiceItems tables...")
            try:
                self.execute_query("""
                    CREATE TABLE IF NOT EXISTS Invoices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        invoice_number TEXT NOT NULL UNIQUE,
                        customer_id INTEGER NOT NULL,
                        contract_id INTEGER,
                        issue_date TEXT NOT NULL,
                        due_date TEXT,
                        total_amount REAL NOT NULL,
                        discount_percentage REAL DEFAULT 0,
                        tax_percentage REAL DEFAULT 0,
                        final_amount REAL NOT NULL,
                        description TEXT,
                        FOREIGN KEY (customer_id) REFERENCES Customers(id),
                        FOREIGN KEY (contract_id) REFERENCES Contracts(id)
                    );
                """)
                self.execute_query("""
                    CREATE TABLE IF NOT EXISTS InvoiceItems (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        invoice_id INTEGER NOT NULL,
                        service_id INTEGER NOT NULL,
                        quantity REAL NOT NULL,
                        unit_price REAL NOT NULL,
                        total_price REAL NOT NULL,
                        FOREIGN KEY (invoice_id) REFERENCES Invoices(id) ON DELETE CASCADE,
                        FOREIGN KEY (service_id) REFERENCES Services(id)
                    );
                """)
                print("Migration to version 12 successful: Invoices and InvoiceItems tables created.")
                self.set_db_version(12)
            except sqlite3.Error as e:
                print(f"Error migrating to version 12 (Invoices/InvoiceItems tables): {e}")

        # بلاک مهاجرت جدید برای جدول InvoiceTemplates
        if current_db_version < 13:
            print("Migrating to version 13: Adding InvoiceTemplates table...")
            try:
                self.execute_query("""
                    CREATE TABLE IF NOT EXISTS InvoiceTemplates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        template_name TEXT UNIQUE NOT NULL,
                        template_type TEXT NOT NULL,
                        required_fields TEXT,       -- JSON array of required field names
                        default_settings TEXT,      -- JSON object of default values/rules
                        is_active INTEGER DEFAULT 1, -- 1 for active, 0 for inactive
                        notes TEXT                  -- notes فیلد قبلی (حذف خواهد شد در 14)
                    );
                """)
                print("Migration to version 13 successful: InvoiceTemplates table created.")
                self.set_db_version(13)
            except sqlite3.Error as e:
                print(f"Error migrating to version 13 (InvoiceTemplates table): {e}")

        # بلاک مهاجرت جدید برای اضافه کردن فیلدهای عکس به InvoiceTemplates و حذف notes
        if current_db_version < 14:
            print("Migrating to version 14: Adding image paths and opacity to InvoiceTemplates, removing notes...")
            try:
                self.execute_query("""
                    CREATE TABLE InvoiceTemplates_temp (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        template_name TEXT UNIQUE NOT NULL,
                        template_type TEXT NOT NULL,
                        required_fields TEXT,
                        default_settings TEXT,
                        is_active INTEGER DEFAULT 1,
                        header_image_path TEXT,
                        footer_image_path TEXT,
                        background_image_path TEXT,
                        background_opacity REAL
                    );
                """)
                self.execute_query("""
                    INSERT INTO InvoiceTemplates_temp (id, template_name, template_type, required_fields, default_settings, is_active, header_image_path, footer_image_path, background_image_path, background_opacity)
                    SELECT id, template_name, template_type, required_fields, default_settings, is_active, '', '', '', 1.0
                    FROM InvoiceTemplates;
                """) # با مقادیر پیش فرض برای مسیرهای عکس و شفافیت
                self.execute_query("DROP TABLE InvoiceTemplates;")
                self.execute_query("ALTER TABLE InvoiceTemplates_temp RENAME TO InvoiceTemplates;")
                print("Migration to version 14 successful.")
                self.set_db_version(14)
            except sqlite3.Error as e:
                print(f"Error migrating to version 14 (InvoiceTemplates schema change for images): {e}")
        
        # بلاک مهاجرت جدید برای تغییر نام default_settings به template_settings
        if current_db_version < 15:
            print("Migrating to version 15: Renaming 'default_settings' to 'template_settings' in InvoiceTemplates table...")
            try:
                # مرحله 1: ایجاد جدول موقت با شمای جدید
                self.execute_query("""
                    CREATE TABLE InvoiceTemplates_temp (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        template_name TEXT UNIQUE NOT NULL,
                        template_type TEXT NOT NULL,
                        required_fields TEXT,
                        template_settings TEXT, -- فیلد جدید
                        is_active INTEGER DEFAULT 1,
                        header_image_path TEXT,
                        footer_image_path TEXT,
                        background_image_path TEXT,
                        background_opacity REAL
                    );
                """)
                # مرحله 2: کپی داده‌ها از جدول قدیمی به جدول موقت
                # توجه: اگر default_settings قبلاً NULL یا خالی بوده، اینجا به صورت '{}' کپی می‌شود.
                self.execute_query("""
                    INSERT INTO InvoiceTemplates_temp (
                        id, template_name, template_type, required_fields, 
                        template_settings, is_active, header_image_path, 
                        footer_image_path, background_image_path, background_opacity
                    )
                    SELECT 
                        id, template_name, template_type, required_fields, 
                        COALESCE(default_settings, '{}'), -- اگر default_settings خالی بود، '{}' را بگذار
                        is_active, header_image_path, 
                        footer_image_path, background_image_path, background_opacity
                    FROM InvoiceTemplates;
                """)
                # مرحله 3: حذف جدول قدیمی
                self.execute_query("DROP TABLE InvoiceTemplates;")
                # مرحله 4: تغییر نام جدول موقت به نام اصلی
                self.execute_query("ALTER TABLE InvoiceTemplates_temp RENAME TO InvoiceTemplates;")
                
                print("Migration to version 15 successful.")
                self.set_db_version(15)
            except sqlite3.Error as e:
                print(f"Error migrating to version 15 (InvoiceTemplates schema change for template_settings): {e}")


        if current_db_version < DATABASE_SCHEMA_VERSION:
            print(f"Performing database migration from {current_db_version} to {DATABASE_SCHEMA_VERSION}...")
            self.set_db_version(DATABASE_SCHEMA_VERSION)
            print(f"Database migrated to version {DATABASE_SCHEMA_VERSION}.")
        elif current_db_version > DATABASE_SCHEMA_VERSION:
            print("Warning: Database version is newer than application schema version. This might cause issues.")
        else:
            print("Database schema is up to date.")

if __name__ == "__main__":
    base_path_for_test = os.path.dirname(os.path.abspath(__file__))
    db_file_path_for_test = os.path.join(base_path_for_test, DATABASE_NAME)
    db_manager_test = DBManager(db_file_path_for_test)

    if db_manager_test.connect():
        db_manager_test.create_tables()
        db_manager_test.migrate_database()
        db_manager_test.close()
    else:
        print("Could not connect to database for test. Exiting.")