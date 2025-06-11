# customer_manager.py
import os
import sqlite3
from db_manager import DBManager, DATABASE_NAME
from models import Customer

class CustomerManager:
    def __init__(self):
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATABASE_NAME)
        self.db_manager = DBManager(db_path)

    def get_next_customer_code(self):
        """ بازیابی بزرگترین کد مشتری ذخیره شده و بازگرداندن کد بعدی (شروع از 2001) """
        if not self.db_manager.connect():
            return 2001 # اگر اتصال برقرار نشد، از کد پیش‌فرض شروع کن
        
        # پیدا کردن بزرگترین customer_code موجود
        cursor = self.db_manager.execute_query("SELECT MAX(customer_code) FROM Customers")
        next_code = 2001
        if cursor:
            row = cursor.fetchone()
            if row and row[0] is not None:
                next_code = int(row[0]) + 1
        self.db_manager.close()
        return next_code

    def add_customer(self, customer: Customer):
        """ اضافه کردن یک مشتری جدید به دیتابیس """
        if not self.db_manager.connect():
            return False, "خطا در اتصال به دیتابیس."
        try:
            # اگر customer_code خالی بود، تولید خودکار انجام شود
            final_customer_code = customer.customer_code
            if final_customer_code is None:
                self.db_manager.close() # بستن اتصال قبلی برای get_next_customer_code
                final_customer_code = self.get_next_customer_code()
                if not self.db_manager.connect(): # اتصال مجدد
                     return False, "خطا در اتصال مجدد به دیتابیس برای تولید کد مشتری."
            
            query = """
            INSERT INTO Customers (
                customer_code, name, customer_type, address, 
                phone, phone2, mobile, email, tax_id, postal_code, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                final_customer_code, customer.name, customer.customer_type,  
                customer.address, customer.phone, customer.phone2, customer.mobile, 
                customer.email, customer.tax_id, customer.postal_code, customer.notes
            )
            
            cursor = self.db_manager.execute_query(query, params)
            self.db_manager.close()
            if cursor:
                return True, "مشتری با موفقیت اضافه شد."
            else:
                return False, "خطا در اضافه کردن مشتری."
        except sqlite3.IntegrityError as e:
            self.db_manager.close()
            if "UNIQUE constraint failed: Customers.name" in str(e):
                return False, "نام مشتری تکراری است. لطفاً نام دیگری را وارد کنید."
            elif "UNIQUE constraint failed: Customers.customer_code" in str(e):
                return False, "کد مشتری تکراری است. لطفاً کد دیگری را وارد کنید یا آن را خالی بگذارید."
            elif "UNIQUE constraint failed: Customers.tax_id" in str(e):
                return False, "شناسه ملی/شماره ملی وارد شده تکراری است."
            elif "UNIQUE constraint failed: Customers.email" in str(e):
                return False, "ایمیل وارد شده تکراری است."
            else:
                return False, f"خطای تکراری بودن داده: {e}"
        except Exception as e:
            self.db_manager.close()
            return False, f"خطای ناشناخته در اضافه کردن مشتری: {e}"

    def get_all_customers(self):
        """ بازیابی تمام مشتریان از دیتابیس """
        if not self.db_manager.connect():
            return [], "خطا در اتصال به دیتابیس."
        cursor = self.db_manager.execute_query("SELECT * FROM Customers ORDER BY name COLLATE NOCASE ASC")
        customers = []
        if cursor:
            for row in cursor.fetchall():
                customers.append(Customer.from_dict(dict(row)))
        self.db_manager.close()
        return customers, "مشتریان با موفقیت بازیابی شدند."

    def get_customer_by_id(self, customer_id: int):
        """ بازیابی یک مشتری بر اساس شناسه """
        if not self.db_manager.connect():
            return None, "خطا در اتصال به دیتابیس."
        cursor = self.db_manager.execute_query("SELECT * FROM Customers WHERE id = ?", (customer_id,))
        customer = None
        if cursor:
            row = cursor.fetchone()
            if row:
                customer = Customer.from_dict(dict(row))
        self.db_manager.close()
        return customer, "مشتری با موفقیت بازیابی شد."

    def update_customer(self, customer: Customer):
        """ بروزرسانی یک مشتری موجود در دیتابیس """
        if not self.db_manager.connect():
            return False, "خطا در اتصال به دیتابیس."
        try:
            query = """
            UPDATE Customers SET 
                customer_code = ?, name = ?, customer_type = ?, 
                address = ?, phone = ?, phone2 = ?, mobile = ?, email = ?, 
                tax_id = ?, postal_code = ?, notes = ?
            WHERE id = ?
            """
            params = (
                customer.customer_code, customer.name, customer.customer_type,  
                customer.address, customer.phone, customer.phone2, customer.mobile, 
                customer.email, customer.tax_id, customer.postal_code, customer.notes,
                customer.id
            )
            cursor = self.db_manager.execute_query(query, params)
            self.db_manager.close()
            if cursor and cursor.rowcount > 0:
                return True, "مشتری با موفقیت بروزرسانی شد."
            else:
                return False, "مشتری مورد نظر یافت نشد یا تغییری اعمال نشد."
        except sqlite3.IntegrityError as e:
            self.db_manager.close()
            if "UNIQUE constraint failed: Customers.name" in str(e):
                return False, "نام مشتری تکراری است. لطفاً نام دیگری را وارد کنید."
            elif "UNIQUE constraint failed: Customers.customer_code" in str(e):
                return False, "کد مشتری تکراری است. لطفاً کد دیگری را وارد کنید."
            elif "UNIQUE constraint failed: Customers.tax_id" in str(e):
                return False, "شناسه ملی/شماره ملی وارد شده تکراری است."
            elif "UNIQUE constraint failed: Customers.email" in str(e):
                return False, "ایمیل وارد شده تکراری است."
            else:
                return False, f"خطای تکراری بودن داده: {e}"
        except Exception as e:
            self.db_manager.close()
            return False, f"خطای ناشناخته در بروزرسانی مشتری: {e}"

    def delete_customer(self, customer_id: int):
        """ حذف یک مشتری از دیتابیس """
        if not self.db_manager.connect():
            return False, "خطا در اتصال به دیتابیس."
        cursor = self.db_manager.execute_query("DELETE FROM Customers WHERE id = ?", (customer_id,))
        self.db_manager.close()
        if cursor and cursor.rowcount > 0:
            return True, "مشتری با موفقیت حذف شد."
        else:
            return False, "مشتری مورد نظر یافت نشد."

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

    customer_manager = CustomerManager()

    print("\n--- Testing CustomerManager ---")

    # تست get_next_customer_code
    next_code = customer_manager.get_next_customer_code()
    print(f"Next available customer code: {next_code}")

    # تست افزودن مشتری جدید (حقوقی)
    print("\nAdding new corporate customer (manual code)...")
    new_customer_corp = Customer(
        customer_code=2001,
        name="شرکت توسعه داده نوین",
        customer_type="حقوقی",
        address="تهران، خیابان ولیعصر، پلاک ۱",
        phone="021-11111111",
        phone2="021-22222222",
        mobile="09121111111",
        email="info@tdn.com",
        tax_id="12345678901",
        postal_code="1111111111",
        notes="مشتری استراتژیک"
    )
    success, message = customer_manager.add_customer(new_customer_corp)
    print(f"Add Corporate Customer: {success} - {message}")

    # تست افزودن مشتری جدید (حقیقی با کد خودکار)
    print("\nAdding new individual customer (auto code)...")
    new_customer_ind = Customer(
        name="علی احمدی",
        customer_type="حقیقی",
        address="اصفهان، خیابان چهارباغ",
        phone="031-33333333",
        mobile="09132222222",
        email="ali.ahmadi@example.com",
        tax_id="0012345678", # 10 رقمی
        postal_code="2222222222",
        notes="مشتری خوش‌حساب"
    )
    success, message = customer_manager.add_customer(new_customer_ind)
    print(f"Add Individual Customer: {success} - {message}")

    next_code = customer_manager.get_next_customer_code()
    print(f"Next available customer code after auto-add: {next_code}")

    # تست افزودن مشتری با نام تکراری
    print("\nAdding customer with duplicate name...")
    duplicate_name_customer = Customer(
        name="علی احمدی", # نام تکراری
        customer_type="حقیقی",
        mobile="09133333333",
        tax_id="0012345679"
    )
    success, message = customer_manager.add_customer(duplicate_name_customer)
    print(f"Add Duplicate Name Customer: {success} - {message}")

    # تست افزودن مشتری با tax_id تکراری
    print("\nAdding customer with duplicate tax_id...")
    duplicate_tax_id_customer = Customer(
        name="رضا رضایی",
        customer_type="حقیقی",
        mobile="09134444444",
        tax_id="0012345678" # tax_id تکراری
    )
    success, message = customer_manager.add_customer(duplicate_tax_id_customer)
    print(f"Add Duplicate Tax ID Customer: {success} - {message}")

    # تست افزودن مشتری با customer_code تکراری
    print("\nAdding customer with duplicate customer_code...")
    duplicate_code_customer = Customer(
        customer_code=2001, # کد تکراری
        name="سعید سعیدی",
        customer_type="حقیقی",
        mobile="09135555555",
        tax_id="0012345680"
    )
    success, message = customer_manager.add_customer(duplicate_code_customer)
    print(f"Add Duplicate Code Customer: {success} - {message}")

    # تست بازیابی همه مشتریان
    print("\nGetting all customers...")
    customers, message = customer_manager.get_all_customers()
    for c in customers:
        print(f"ID: {c.id}, Code: {c.customer_code}, Name: {c.name}, Type: {c.customer_type}, TaxID: {c.tax_id}, Mobile: {c.mobile}")

    # تست بروزرسانی مشتری
    if customers:
        customer_to_update = customers[0]
        customer_to_update.address = "تهران، خیابان آزادی، پلاک ۱۰ (بروزرسانی شده)"
        customer_to_update.phone2 = "021-99999999"
        customer_to_update.tax_id = "12345678999" # تغییر tax_id
        print(f"\nUpdating customer ID {customer_to_update.id} (Name: {customer_to_update.name})...")
        success, message = customer_manager.update_customer(customer_to_update)
        print(f"Update Customer: {success} - {message}")

        updated_customers, _ = customer_manager.get_all_customers()
        print("Customers after update:")
        for c in updated_customers:
            print(f"ID: {c.id}, Code: {c.customer_code}, Name: {c.name}, Type: {c.customer_type}, TaxID: {c.tax_id}, Mobile: {c.mobile}, Address: {c.address}")
    
    # تست حذف مشتری
    if len(customers) > 1:
        customer_id_to_delete = customers[1].id
        print(f"\nDeleting customer ID {customer_id_to_delete}...")
        success, message = customer_manager.delete_customer(customer_id_to_delete)
        print(f"Delete Customer: {success} - {message}")

        final_customers, _ = customer_manager.get_all_customers()
        print("Customers after deletion:")
        for c in final_customers:
            print(f"ID: {c.id}, Code: {c.customer_code}, Name: {c.name}, Type: {c.customer_type}, TaxID: {c.tax_id}, Mobile: {c.mobile}")