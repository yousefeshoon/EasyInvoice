# contract_manager.py
import os
import sqlite3
import random 
import json # برای serializing/deserializing لیست scanned_pages
from db_manager import DBManager, DATABASE_NAME
from models import Contract
import sys 


class ContractManager:
    def __init__(self):
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATABASE_NAME)
        self.db_manager = DBManager(db_path)
        # self.persian_alphabet_parts = ["الف", "ب", "ت", "ج", "ح", "د", "ر", "ز", "س", "ش", "ص", "ط"] # دیگر نیازی نیست

    # get_next_contract_number حذف شد

    def add_contract(self, contract: Contract):
        """ اضافه کردن یک قرارداد جدید به دیتابیس. """
        if not self.db_manager.connect():
            return False, "خطا در اتصال به دیتابیس." 
        try:
            # شماره قرارداد باید حتماً توسط کاربر وارد شده باشد
            if not contract.contract_number:
                return False, "شماره قرارداد نمی‌تواند خالی باشد." 

            # تبدیل لیست scanned_pages به رشته JSON برای ذخیره در دیتابیس
            scanned_pages_json = json.dumps(contract.scanned_pages)

            query = """
            INSERT INTO Contracts (
                customer_id, contract_number, contract_date, total_amount, description, title, payment_method, scanned_pages
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """ 
            params = (
                contract.customer_id, contract.contract_number, contract.contract_date,
                contract.total_amount, contract.description, contract.title, contract.payment_method, scanned_pages_json # استفاده از رشته JSON
            )
            
            cursor = self.db_manager.execute_query(query, params) 
            self.db_manager.close()
            if cursor:
                return True, "قرارداد با موفقیت اضافه شد." 
            else:
                return False, "خطا در اضافه کردن قرارداد." 
        except sqlite3.IntegrityError as e:
            self.db_manager.close()
            if "UNIQUE constraint failed: Contracts.contract_number" in str(e): 
                return False, "شماره قرارداد تکراری است. لطفاً شماره دیگری را وارد کنید." 
            else:
                return False, f"خطای تکراری بودن داده: {e}" 
        except Exception as e:
            self.db_manager.close()
            return False, f"خطای ناشناخته در اضافه کردن قرارداد: {e}" 

    def get_all_contracts(self):
        """ بازیابی تمام قراردادها از دیتابیس (با اطلاعات مشتری) """
        if not self.db_manager.connect():
            return [], "خطا در اتصال به دیتابیس." 
        
        # JOIN با جدول Customers برای نمایش نام مشتری
        query = """
        SELECT
            c.id, c.customer_id, c.contract_number, c.contract_date,
            c.total_amount, c.description, c.title, c.payment_method, c.scanned_pages,
            cust.name as customer_name
        FROM Contracts c
        JOIN Customers cust ON c.customer_id = cust.id
        ORDER BY c.contract_date DESC
        """ 
        cursor = self.db_manager.execute_query(query) 
        contracts = []
        if cursor:
            for row in cursor.fetchall():
                contract_data = dict(row)
                # در مدل از from_dict استفاده می‌کنیم که خودش json.loads را هندل می‌کند
                contract_obj = Contract.from_dict(contract_data)
                contract_obj.customer_name = contract_data['customer_name'] 
                contracts.append(contract_obj) 
        self.db_manager.close()
        return contracts, "قراردادها با موفقیت بازیابی شدند." 

    def get_contract_by_id(self, contract_id: int):
        """ بازیابی یک قرارداد بر اساس شناسه """
        if not self.db_manager.connect():
            return None, "خطا در اتصال به دیتابیس." 
        
        # JOIN با جدول Customers برای اطلاعات مشتری
        query = """
        SELECT
            c.id, c.customer_id, c.contract_number, c.contract_date,
            c.total_amount, c.description, c.title, c.payment_method, c.scanned_pages,
            cust.name as customer_name
        FROM Contracts c
        JOIN Customers cust ON c.customer_id = cust.id
        WHERE c.id = ?
        """ 
        cursor = self.db_manager.execute_query(query, (contract_id,)) 
        contract = None
        if cursor:
            row = cursor.fetchone()
            if row:
                contract_data = dict(row)
                # در مدل از from_dict استفاده می‌کنیم که خودش json.loads را هندل می‌کند
                contract = Contract.from_dict(contract_data)
                contract.customer_name = contract_data['customer_name'] 
        self.db_manager.close()
        return contract, "قرارداد با موفقیت بازیابی شد." 

    def update_contract(self, contract: Contract):
        """ بروزرسانی یک قرارداد موجود در دیتابیس """
        if not self.db_manager.connect():
            return False, "خطا در اتصال به دیتابیس." 
        try:
            # تبدیل لیست scanned_pages به رشته JSON برای ذخیره در دیتابیس
            scanned_pages_json = json.dumps(contract.scanned_pages)

            query = """
            UPDATE Contracts SET
                customer_id = ?, contract_number = ?, contract_date = ?,
                total_amount = ?, description = ?, title = ?, payment_method = ?, scanned_pages = ?
            WHERE id = ?
            """ 
            params = (
                contract.customer_id, contract.contract_number, contract.contract_date,
                contract.total_amount, contract.description, contract.title, contract.payment_method, scanned_pages_json, # استفاده از رشته JSON
                contract.id 
            )
            cursor = self.db_manager.execute_query(query, params) 
            self.db_manager.close()
            if cursor and cursor.rowcount > 0:
                return True, "قرارداد با موفقیت بروزرسانی شد." 
            else:
                return False, "قرارداد مورد نظر یافت نشد یا تغییری اعمال نشد." 
        except sqlite3.IntegrityError as e:
            self.db_manager.close()
            if "UNIQUE constraint failed: Contracts.contract_number" in str(e): 
                return False, "شماره قرارداد تکراری است. لطفاً شماره دیگری را وارد کنید." 
            else:
                return False, f"خطای تکراری بودن داده: {e}" 
        except Exception as e:
            self.db_manager.close()
            return False, f"خطای ناشناخته در بروزرسانی قرارداد: {e}" 

    def delete_contract(self, contract_id: int):
        """ حذف یک قرارداد از دیتابیس """
        if not self.db_manager.connect():
            return False, "خطا در اتصال به دیتابیس." 
        cursor = self.db_manager.execute_query("DELETE FROM Contracts WHERE id = ?", (contract_id,)) 
        self.db_manager.close()
        if cursor and cursor.rowcount > 0:
            return True, "قرارداد با موفقیت حذف شد." 
        else:
            return False, "قرارداد مورد نظر یافت نشد." 

# --- بلاک تست مستقل ---
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_file_path = os.path.join(current_dir, DATABASE_NAME)

    # اطمینان از وجود دیتابیس و جداول
    db_test_manager = DBManager(db_file_path)
    if db_test_manager.connect():
        db_test_manager.create_tables()
        db_test_manager.migrate_database()
        db_test_manager.close()
    else:
        print("Failed to connect for test setup.")
        sys.exit(1)

    contract_manager = ContractManager() 

    print("\n--- Testing ContractManager ---") 

    # اضافه کردن یک مشتری برای تست قرارداد
    from customer_manager import CustomerManager 
    temp_cust_manager = CustomerManager() 
    
    # اطمینان از وجود حداقل یک مشتری
    customers_in_db, _ = temp_cust_manager.get_all_customers() 
    if not customers_in_db:
        print("Adding a temporary customer for contract testing...") 
        from models import Customer 
        temp_customer = Customer(name="مشتری آزمایشی قرارداد", customer_type="حقوقی", tax_id="12345678901", email="test@example.com") 
        temp_cust_manager.add_customer(temp_customer) 
        customers_in_db, _ = temp_cust_manager.get_all_customers() 
    
    if customers_in_db:
        customer_id_for_test = customers_in_db[0].id 
        print(f"Using customer ID: {customer_id_for_test} for contract tests.") 
    else:
        print("No customers found or added. Cannot proceed with contract tests.") 
        sys.exit(1)

    # تست افزودن قرارداد جدید
    print("\nAdding new contract...") 
    new_contract = Contract(
        customer_id=customer_id_for_test, 
        contract_number="C-001", # دستی وارد می‌شود
        contract_date="1402/01/01", 
        total_amount=12000000, 
        description="قرارداد ساده برای تست", 
        title="قرارداد خدمات نرم افزاری", # باقی ماند
        payment_method="ماهانه", # باقی ماند
        scanned_pages=['path/to/scan1.jpg', 'path/to/scan2.pdf'] # اینجا هنوز لیست هست
    )
    success, message = contract_manager.add_contract(new_contract) 
    print(f"Add Contract: {success} - {message}") 
    if success:
        print(f"New contract number: {new_contract.contract_number}")

    # تست افزودن قرارداد دیگر
    print("\nAdding another contract...") 
    new_contract_auto = Contract(
        customer_id=customer_id_for_test, 
        contract_number="C-002", # دستی وارد می‌شود
        contract_date="1403/01/01", 
        total_amount=6000000, 
        description="قرارداد دوم برای تست", 
        title="قرارداد پشتیبانی", # باقی ماند
        payment_method="سالانه", # باقی ماند
        scanned_pages=[] # اینجا هنوز لیست هست
    )
    success, message = contract_manager.add_contract(new_contract_auto) 
    print(f"Add Contract 2: {success} - {message}") 


    # تست بازیابی همه قراردادها
    print("\nGetting all contracts...") 
    contracts, message = contract_manager.get_all_contracts() 
    for c in contracts:
        print(f"ID: {c.id}, Number: {c.contract_number}, Customer: {c.customer_name}, Date: {c.contract_date}, Amount: {c.total_amount}, Title: {c.title}, Payment: {c.payment_method}") 

    # تست بروزرسانی قرارداد
    if contracts:
        contract_to_update = contracts[0]
        contract_to_update.total_amount = 15000000 
        contract_to_update.description = "قرارداد ساده (بروزرسانی شده)" 
        contract_to_update.title = "قرارداد خدمات نرم افزاری (آپدیت)"
        contract_to_update.payment_method = "پروژه‌ای"
        contract_to_update.scanned_pages = ['updated_scan.pdf'] # اینجا هنوز لیست هست
        print(f"\nUpdating contract ID {contract_to_update.id} (Number: {contract_to_update.contract_number})...") 
        success, message = contract_manager.update_contract(contract_to_update) 
        print(f"Update Contract: {success} - {message}") 

        updated_contracts, _ = contract_manager.get_all_contracts() 
        print("Contracts after update:") 
        for c in updated_contracts:
            print(f"ID: {c.id}, Number: {c.contract_number}, Customer: {c.customer_name}, Amount: {c.total_amount}, Desc: {c.description}, Title: {c.title}, Payment: {c.payment_method}") 
    
    # تست حذف قرارداد
    if len(contracts) > 1:
        contract_id_to_delete = contracts[1].id 
        print(f"\nDeleting contract ID {contract_id_to_delete}...") 
        success, message = contract_manager.delete_contract(contract_id_to_delete) 
        print(f"Delete Contract: {success} - {message}") 

        final_contracts, _ = contract_manager.get_all_contracts() 
        print("Contracts after deletion:") 
        for c in final_contracts:
            print(f"ID: {c.id}, Number: {c.contract_number}, Customer: {c.customer_name}")