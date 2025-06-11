# invoice_manager.py
import sqlite3
import os
import json # برای serializing/deserializing
from db_manager import DBManager, DATABASE_NAME
from models import Invoice, InvoiceItem, Customer, Service # Customer و Service هم ایمپورت شدند برای JOIN
from customer_manager import CustomerManager # برای دسترسی به اطلاعات مشتری
from settings_manager import SettingsManager # برای دسترسی به تنظیمات (مثلاً توضیحات سرویس)

class InvoiceManager:
    def __init__(self):
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATABASE_NAME)
        self.db_manager = DBManager(db_path)
        self.customer_manager = CustomerManager() # برای بازیابی اطلاعات مشتری
        self.settings_manager = SettingsManager() # برای بازیابی توضیحات سرویس از طریق SettingsManager

    def add_invoice(self, invoice: Invoice, invoice_items: list[InvoiceItem]):
        """ اضافه کردن یک صورتحساب جدید و آیتم‌های آن به دیتابیس. """
        if not self.db_manager.connect():
            return False, "خطا در اتصال به دیتابیس."
        
        try:
            # شروع تراکنش
            self.db_manager.conn.execute("BEGIN TRANSACTION;")

            # 1. اضافه کردن صورتحساب اصلی
            invoice_query = """
            INSERT INTO Invoices (
                invoice_number, customer_id, contract_id, issue_date, due_date,
                total_amount, discount_percentage, tax_percentage, final_amount, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            invoice_params = (
                invoice.invoice_number, invoice.customer_id, invoice.contract_id,
                invoice.issue_date, invoice.due_date, invoice.total_amount,
                invoice.discount_percentage, invoice.tax_percentage, invoice.final_amount,
                invoice.description
            )
            invoice_cursor = self.db_manager.execute_query(invoice_query, invoice_params)
            
            if not invoice_cursor:
                raise sqlite3.Error("Failed to insert invoice.")
            
            invoice_id = invoice_cursor.lastrowid

            # 2. اضافه کردن آیتم‌های صورتحساب
            item_query = """
            INSERT INTO InvoiceItems (
                invoice_id, service_id, quantity, unit_price, total_price
            ) VALUES (?, ?, ?, ?, ?)
            """
            for item in invoice_items:
                item_params = (
                    invoice_id, item.service_id, item.quantity,
                    item.unit_price, item.total_price
                )
                item_cursor = self.db_manager.execute_query(item_query, item_params)
                if not item_cursor:
                    raise sqlite3.Error(f"Failed to insert invoice item for service ID {item.service_id}.")
            
            # کامیت تراکنش
            self.db_manager.conn.commit()
            self.db_manager.close()
            return True, "صورتحساب با موفقیت ذخیره شد."

        except sqlite3.IntegrityError as e:
            self.db_manager.conn.rollback() # برگشت تراکنش در صورت خطا
            self.db_manager.close()
            if "UNIQUE constraint failed: Invoices.invoice_number" in str(e):
                return False, "شماره صورتحساب تکراری است. لطفاً شماره دیگری را وارد کنید."
            else:
                return False, f"خطای تکراری بودن داده: {e}"
        except Exception as e:
            self.db_manager.conn.rollback() # برگشت تراکنش در صورت خطا
            self.db_manager.close()
            return False, f"خطای ناشناخته در ذخیره صورتحساب: {e}"

    def get_all_invoices(self):
        """ بازیابی تمام صورتحساب‌ها از دیتابیس (با نام مشتری) """
        if not self.db_manager.connect():
            return [], "خطا در اتصال به دیتابیس."
        
        query = """
        SELECT 
            i.id, i.invoice_number, i.customer_id, i.contract_id, i.issue_date, i.due_date,
            i.total_amount, i.discount_percentage, i.tax_percentage, i.final_amount, i.description,
            c.name as customer_name
        FROM Invoices i
        JOIN Customers c ON i.customer_id = c.id
        ORDER BY i.issue_date DESC, i.id DESC
        """
        cursor = self.db_manager.execute_query(query)
        invoices = []
        if cursor:
            for row in cursor.fetchall():
                invoice_data = dict(row)
                customer_name = invoice_data.pop('customer_name') # تغییر: customer_name را حذف کرده و ذخیره کن
                invoice_obj = Invoice.from_dict(invoice_data)
                invoice_obj.customer_name = customer_name # تغییر: customer_name را به آبجکت اضافه کن
                invoices.append(invoice_obj)
        self.db_manager.close()
        return invoices, "صورتحساب‌ها با موفقیت بازیابی شدند."

    def get_invoice_by_id(self, invoice_id: int):
        """ بازیابی یک صورتحساب بر اساس شناسه. """
        if not self.db_manager.connect():
            return None, "خطا در اتصال به دیتابیس."
        
        query = """
        SELECT 
            i.id, i.invoice_number, i.customer_id, i.contract_id, i.issue_date, i.due_date,
            i.total_amount, i.discount_percentage, i.tax_percentage, i.final_amount, i.description,
            c.name as customer_name
        FROM Invoices i
        JOIN Customers c ON i.customer_id = c.id
        WHERE i.id = ?
        """
        cursor = self.db_manager.execute_query(query, (invoice_id,))
        invoice = None
        if cursor:
            row = cursor.fetchone()
            if row:
                invoice_data = dict(row)
                customer_name = invoice_data.pop('customer_name') # تغییر: customer_name را حذف کرده و ذخیره کن
                invoice = Invoice.from_dict(invoice_data)
                invoice.customer_name = customer_name # تغییر: customer_name را به آبجکت اضافه کن
        self.db_manager.close()
        return invoice, "صورتحساب با موفقیت بازیابی شد."

    def get_invoice_items_by_invoice_id(self, invoice_id: int):
        """ بازیابی آیتم‌های یک صورتحساب بر اساس شناسه صورتحساب. """
        if not self.db_manager.connect():
            return [], "خطا در اتصال به دیتابیس."
        
        query = """
        SELECT 
            id, invoice_id, service_id, quantity, unit_price, total_price
        FROM InvoiceItems
        WHERE invoice_id = ?
        """
        cursor = self.db_manager.execute_query(query, (invoice_id,))
        items = []
        if cursor:
            for row in cursor.fetchall():
                items.append(InvoiceItem.from_dict(dict(row)))
        self.db_manager.close()
        return items, "آیتم‌های صورتحساب با موفقیت بازیابی شدند."

    def delete_invoice(self, invoice_id: int):
        """ حذف یک صورتحساب و تمام آیتم‌های مربوط به آن. """
        if not self.db_manager.connect():
            return False, "خطا در اتصال به دیتابیس."
        
        try:
            self.db_manager.conn.execute("BEGIN TRANSACTION;")
            
            # حذف آیتم‌های صورتحساب (CASCADE ON DELETE در تعریف جدول)
            # cursor_items = self.db_manager.execute_query("DELETE FROM InvoiceItems WHERE invoice_id = ?", (invoice_id,))
            
            # حذف صورتحساب اصلی
            cursor_invoice = self.db_manager.execute_query("DELETE FROM Invoices WHERE id = ?", (invoice_id,))
            
            if not cursor_invoice or cursor_invoice.rowcount == 0:
                raise sqlite3.Error("Invoice not found or failed to delete.")
            
            self.db_manager.conn.commit()
            self.db_manager.close()
            return True, "صورتحساب با موفقیت حذف شد."
        except Exception as e:
            self.db_manager.conn.rollback()
            self.db_manager.close()
            return False, f"خطا در حذف صورتحساب: {e}"

    # متد update_invoice فعلاً پیاده‌سازی نشده است، اما می‌توانید آن را اضافه کنید.
    # def update_invoice(self, invoice: Invoice, invoice_items: list[InvoiceItem]):
    #    ...

# --- بلاک تست مستقل ---
if __name__ == "__main__":
    import sys
    import jdatetime
    from models import AppSettings, Customer, Contract, Service # اضافه شده برای تست

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

    invoice_manager = InvoiceManager()

    # ایجاد داده‌های پیش‌فرض برای تست
    customer_manager_temp = CustomerManager()
    service_manager_temp = ServiceManager()
    contract_manager_temp = ContractManager()
    settings_manager_temp = SettingsManager()

    # اطمینان از وجود مشتری
    customer_temp = Customer(customer_code=1000, name="مشتری آزمایشی فاکتور", customer_type="حقوقی", tax_id="1234567890", email="invtest@example.com")
    customer_manager_temp.add_customer(customer_temp)
    customers, _ = customer_manager_temp.get_all_customers()
    if not customers:
        print("No customers available for testing. Exiting.")
        sys.exit(1)
    test_customer = customers[0]

    # اطمینان از وجود سرویس
    service_temp = Service(service_code=1000, description="خدمت آزمایشی فاکتور")
    service_manager_temp.add_service(service_temp)
    services, _ = service_manager_temp.get_all_services()
    if not services:
        print("No services available for testing. Exiting.")
        sys.exit(1)
    test_service = services[0]

    # اطمینان از وجود قرارداد
    contract_temp = Contract(customer_id=test_customer.id, contract_number="CONT-TEST-001", contract_date=jdatetime.date.today().strftime("%Y/%m/%d"), total_amount=1000000, description="قرارداد تست فاکتور", title="قرارداد آزمایشی", payment_method="نقدی", scanned_pages="[]")
    contract_manager_temp.add_contract(contract_temp)
    contracts, _ = contract_manager_temp.get_all_contracts()
    if not contracts:
        print("No contracts available for testing. Exiting.")
        sys.exit(1)
    test_contract = contracts[0]


    print("\n--- Testing InvoiceManager ---")

    # تست افزودن صورتحساب جدید
    print("\nAdding new invoice...")
    new_invoice = Invoice(
        invoice_number="INV-2024-001",
        customer_id=test_customer.id,
        contract_id=test_contract.id,
        issue_date=jdatetime.date.today().strftime("%Y/%m/%d"),
        due_date=jdatetime.date.today().strftime("%Y/%m/%d"),
        total_amount=10000000,
        discount_percentage=5,
        tax_percentage=9,
        final_amount=10450000,
        description="صورتحساب تست شماره یک"
    )
    new_invoice_items = [
        InvoiceItem(service_id=test_service.id, quantity=1, unit_price=10000000, total_price=10000000)
    ]
    success, message = invoice_manager.add_invoice(new_invoice, new_invoice_items)
    print(f"Add Invoice 1: {success} - {message}")

    # تست افزودن صورتحساب دیگر
    print("\nAdding another invoice...")
    new_invoice2 = Invoice(
        invoice_number="INV-2024-002",
        customer_id=test_customer.id,
        contract_id=test_contract.id,
        issue_date=jdatetime.date.today().strftime("%Y/%m/%d"),
        due_date=jdatetime.date.today().strftime("%Y/%m/%d"),
        total_amount=5000000,
        discount_percentage=0,
        tax_percentage=9,
        final_amount=5450000,
        description="صورتحساب تست شماره دو"
    )
    new_invoice_items2 = [
        InvoiceItem(service_id=test_service.id, quantity=0.5, unit_price=10000000, total_price=5000000)
    ]
    success, message = invoice_manager.add_invoice(new_invoice2, new_invoice_items2)
    print(f"Add Invoice 2: {success} - {message}")

    # تست بازیابی همه صورتحساب‌ها
    print("\nGetting all invoices...")
    invoices, message = invoice_manager.get_all_invoices()
    for inv in invoices:
        print(f"ID: {inv.id}, Number: {inv.invoice_number}, Customer: {inv.customer_name}, Amount: {inv.final_amount}")

    # تست بازیابی آیتم‌های صورتحساب
    if invoices:
        test_invoice_id = invoices[0].id
        items, message = invoice_manager.get_invoice_items_by_invoice_id(test_invoice_id)
        print(f"\nItems for Invoice ID {test_invoice_id}:")
        for item in items:
            print(f"  Service ID: {item.service_id}, Quantity: {item.quantity}, Total Price: {item.total_price}")

    # تست حذف صورتحساب
    if len(invoices) > 1:
        invoice_to_delete_id = invoices[1].id
        print(f"\nDeleting Invoice ID {invoice_to_delete_id}...")
        success, message = invoice_manager.delete_invoice(invoice_to_delete_id)
        print(f"Delete Invoice: {success} - {message}")

        final_invoices, _ = invoice_manager.get_all_invoices()
        print("Invoices after deletion:")
        for inv in final_invoices:
            print(f"ID: {inv.id}, Number: {inv.invoice_number}")