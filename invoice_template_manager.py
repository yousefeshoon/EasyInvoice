# invoice_template_manager.py
import sqlite3
import os
import json
from db_manager import DBManager, DATABASE_NAME
from models import InvoiceTemplate

class InvoiceTemplateManager:
    def __init__(self):
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATABASE_NAME)
        self.db_manager = DBManager(db_path)

    def add_template(self, template: InvoiceTemplate):
        if not self.db_manager.connect():
            return False, "خطا در اتصال به دیتابیس."
        try:
            query = """
            INSERT INTO InvoiceTemplates (
                template_name, template_type, required_fields, default_settings, is_active, notes
            ) VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (
                template.template_name, template.template_type, 
                json.dumps(template.required_fields), json.dumps(template.default_settings),
                template.is_active, template.notes
            )
            cursor = self.db_manager.execute_query(query, params)
            self.db_manager.close()
            if cursor:
                return True, "قالب صورتحساب با موفقیت اضافه شد."
            else:
                return False, "خطا در اضافه کردن قالب صورتحساب."
        except sqlite3.IntegrityError as e:
            self.db_manager.close()
            if "UNIQUE constraint failed: InvoiceTemplates.template_name" in str(e):
                return False, "نام قالب صورتحساب تکراری است. لطفاً نام دیگری را وارد کنید."
            else:
                return False, f"خطای تکراری بودن داده: {e}"
        except Exception as e:
            self.db_manager.close()
            return False, f"خطای ناشناخته در اضافه کردن قالب صورتحساب: {e}"

    def get_all_templates(self, active_only=True):
        if not self.db_manager.connect():
            return [], "خطا در اتصال به دیتابیس."
        query = "SELECT * FROM InvoiceTemplates"
        params = ()
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY template_name ASC"
        
        cursor = self.db_manager.execute_query(query, params)
        templates = []
        if cursor:
            for row in cursor.fetchall():
                templates.append(InvoiceTemplate.from_dict(dict(row)))
        self.db_manager.close()
        return templates, "قالب‌های صورتحساب با موفقیت بازیابی شدند."

    def get_template_by_name(self, template_name: str):
        if not self.db_manager.connect():
            return None, "خطا در اتصال به دیتابیس."
        query = "SELECT * FROM InvoiceTemplates WHERE template_name = ?"
        cursor = self.db_manager.execute_query(query, (template_name,))
        template = None
        if cursor:
            row = cursor.fetchone()
            if row:
                template = InvoiceTemplate.from_dict(dict(row))
        self.db_manager.close()
        return template, "قالب صورتحساب با موفقیت بازیابی شد."

    def update_template(self, template: InvoiceTemplate):
        if not self.db_manager.connect():
            return False, "خطا در اتصال به دیتابیس."
        try:
            query = """
            UPDATE InvoiceTemplates SET
                template_name = ?, template_type = ?, required_fields = ?, 
                default_settings = ?, is_active = ?, notes = ?
            WHERE id = ?
            """
            params = (
                template.template_name, template.template_type, 
                json.dumps(template.required_fields), json.dumps(template.default_settings),
                template.is_active, template.notes, template.id
            )
            cursor = self.db_manager.execute_query(query, params)
            self.db_manager.close()
            if cursor and cursor.rowcount > 0:
                return True, "قالب صورتحساب با موفقیت بروزرسانی شد."
            else:
                return False, "قالب صورتحساب مورد نظر یافت نشد یا تغییری اعمال نشد."
        except sqlite3.IntegrityError as e:
            self.db_manager.close()
            if "UNIQUE constraint failed: InvoiceTemplates.template_name" in str(e):
                return False, "نام قالب صورتحساب تکراری است. لطفاً نام دیگری را وارد کنید."
            else:
                return False, f"خطای تکراری بودن داده: {e}"
        except Exception as e:
            self.db_manager.close()
            return False, f"خطای ناشناخته در بروزرسانی قالب صورتحساب: {e}"

    def delete_template(self, template_id: int):
        if not self.db_manager.connect():
            return False, "خطا در اتصال به دیتابیس."
        cursor = self.db_manager.execute_query("DELETE FROM InvoiceTemplates WHERE id = ?", (template_id,))
        self.db_manager.close()
        if cursor and cursor.rowcount > 0:
            return True, "قالب صورتحساب با موفقیت حذف شد."
        else:
            return False, "قالب صورتحساب مورد نظر یافت نشد."