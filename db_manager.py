import sqlite3
import os
import sys # --- اضافه شد: برای تشخیص محیط PyInstaller ---

DATABASE_NAME = "easy_invoice.db"
DATABASE_SCHEMA_VERSION = 5

class DBManager:
    def __init__(self, db_path):
        # --- اصلاح مسیر برای محیط PyInstaller ---
        if getattr(sys, 'frozen', False):
            # اگر برنامه از یک فایل exe (PyInstaller) اجرا شده است
            # مسیر دیتابیس را کنار فایل exe قرار می‌دهیم.
            base_path = os.path.dirname(sys.executable)
        else:
            # اگر برنامه از کد پایتون معمولی اجرا شده است
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        self.db_path = os.path.join(base_path, DATABASE_NAME)
        # ----------------------------------------
        
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
                name TEXT NOT NULL,
                company_name TEXT,
                address TEXT,
                phone TEXT,
                email TEXT UNIQUE,
                tax_id TEXT,
                registration_date TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_code INTEGER UNIQUE,
                description TEXT NOT NULL, 
                settlement_type TEXT NOT NULL,
                UNIQUE(description, settlement_type)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS Contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                contract_number TEXT UNIQUE,
                start_date TEXT NOT NULL,
                end_date TEXT,
                total_amount REAL,
                description TEXT,
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

        if current_db_version < DATABASE_SCHEMA_VERSION:
            print(f"Performing database migration from {current_db_version} to {DATABASE_SCHEMA_VERSION}...")
            self.set_db_version(DATABASE_SCHEMA_VERSION)
            print(f"Database migrated to version {DATABASE_SCHEMA_VERSION}.")
        elif current_db_version > DATABASE_SCHEMA_VERSION:
            print("Warning: Database version is newer than application schema version. This might cause issues.")
        else:
            print("Database schema is up to date.")

if __name__ == "__main__":
    # در بلاک تست مستقل، مسیر دیتابیس را به صورت معمولی تنظیم می‌کنیم
    base_path_for_test = os.path.dirname(os.path.abspath(__file__))
    db_path_for_test = os.path.join(base_path_for_test, DATABASE_NAME)
    db_manager_test = DBManager(db_path_for_test)

    if db_manager_test.connect():
        db_manager_test.create_tables()
        db_manager_test.migrate_database()
        db_manager_test.close()
    else:
        print("Could not connect to database for test. Exiting.")