# invoice_list_ui.py
import customtkinter as ctk
from tkinter import messagebox, ttk
import os
import sys
import subprocess

from invoice_manager import InvoiceManager # برای بازیابی لیست صورتحساب‌ها
from models import Invoice # برای Type Hinting
from invoice_generator import InvoiceGenerator # برای تولید مجدد PDF در مشاهده/پرینت مجدد
from settings_manager import SettingsManager # برای پاس دادن به InvoiceGenerator

class InvoiceListUI(ctk.CTkFrame):
    def __init__(self, parent, db_manager, ui_colors, base_font, heading_font, button_font, nav_button_font):
        super().__init__(parent, fg_color="transparent")
        self.parent = parent
        self.db_manager = db_manager
        self.ui_colors = ui_colors
        self.base_font = base_font
        self.heading_font = heading_font
        self.button_font = button_font
        self.nav_button_font = nav_button_font

        self.invoice_manager = InvoiceManager()
        self.settings_manager = SettingsManager() # Instantiate SettingsManager for invoice_generator
        self.invoice_generator = InvoiceGenerator(self.settings_manager) # Pass settings_manager

        self.create_widgets()
        self.load_invoices_to_table()

    def create_widgets(self):
        main_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=10,
                                  border_width=1, border_color=self.ui_colors["border_gray"])
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(main_frame, text="لیست صورتحساب‌های صادر شده", font=self.heading_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # Treeview for invoices
        self.invoice_table = ttk.Treeview(main_frame, columns=("InvoiceNumber", "CustomerName", "IssueDate", "FinalAmount"), show="headings")
        
        self.invoice_table.heading("InvoiceNumber", text="شماره صورتحساب", anchor="e")
        self.invoice_table.heading("CustomerName", text="نام مشتری", anchor="e")
        self.invoice_table.heading("IssueDate", text="تاریخ صدور", anchor="e")
        self.invoice_table.heading("FinalAmount", text="مبلغ نهایی", anchor="e")

        self.invoice_table.column("InvoiceNumber", width=120, anchor="e", stretch=False)
        self.invoice_table.column("CustomerName", width=200, anchor="e", stretch=True)
        self.invoice_table.column("IssueDate", width=100, anchor="e", stretch=False)
        self.invoice_table.column("FinalAmount", width=120, anchor="e", stretch=False)
        
        self.invoice_table.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # Scrollbar
        tree_scrollbar = ctk.CTkScrollbar(main_frame, command=self.invoice_table.yview)
        tree_scrollbar.grid(row=1, column=1, sticky="ns", padx=(0,10), pady=10)
        self.invoice_table.configure(yscrollcommand=tree_scrollbar.set)

        # Buttons (مثلاً مشاهده جزئیات، پرینت مجدد، حذف)
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="e")

        ctk.CTkButton(button_frame, text="مشاهده/پرینت مجدد", font=self.button_font, fg_color=self.ui_colors["accent_blue"], command=self.view_selected_invoice).pack(side="right", padx=5)
        ctk.CTkButton(button_frame, text="حذف", font=self.button_font, fg_color="#dc3545", command=self.delete_selected_invoice).pack(side="right", padx=5)

    def load_invoices_to_table(self):
        for item in self.invoice_table.get_children():
            self.invoice_table.delete(item)
        
        invoices, msg = self.invoice_manager.get_all_invoices()
        if not invoices:
            print(msg) # Log message if no invoices
            return

        for invoice in invoices:
            formatted_amount = f"{int(invoice.final_amount):,}" if invoice.final_amount is not None else "0"
            self.invoice_table.insert("", "end", iid=invoice.id, values=(
                invoice.invoice_number,
                invoice.customer_name, # فرض می‌کنیم invoice_manager نام مشتری را هم برمی‌گرداند
                invoice.issue_date,
                formatted_amount
            ))

    def view_selected_invoice(self):
        selected_item_id = self.invoice_table.focus()
        if not selected_item_id:
            messagebox.showwarning("هشدار", "لطفاً یک صورتحساب را از لیست انتخاب کنید.", master=self)
            return
        
        invoice_id = int(selected_item_id)
        invoice, msg = self.invoice_manager.get_invoice_by_id(invoice_id)
        if not invoice:
            messagebox.showerror("خطا", f"صورتحساب با شناسه {invoice_id} یافت نشد: {msg}", master=self)
            return
        
        customer, msg_cust = self.invoice_manager.customer_manager.get_customer_by_id(invoice.customer_id)
        if not customer:
            messagebox.showerror("خطا", f"مشتری صورتحساب یافت نشد: {msg_cust}", master=self)
            return

        invoice_items, msg_items = self.invoice_manager.get_invoice_items_by_invoice_id(invoice_id)
        if not invoice_items:
            messagebox.showwarning("هشدار", f"آیتم‌های صورتحساب یافت نشدند: {msg_items}", master=self)
            # می‌توانیم ادامه دهیم یا خطا دهیم
            invoice_items = []

        # تولید مجدد PDF و نمایش آن
        # از invoice_generator که در __init__ این کلاس تعریف شده استفاده می‌کنیم
        # نیازی به ایمپورت InvoiceDetailsWindow اینجا نیست چون فقط برای نمایش استفاده میشه
        
        temp_pdf_path = os.path.join(os.path.expanduser("~"), "Documents", "EasyInvoice_Invoices", f"Preview_{invoice.invoice_number}.pdf")
        success, _ = self.invoice_generator.create_invoice_pdf(invoice, customer, invoice_items, temp_pdf_path)

        if success:
            try:
                if sys.platform == "win32":
                    os.startfile(temp_pdf_path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", temp_pdf_path])
                else:
                    subprocess.run(["xdg-open", temp_pdf_path])
            except Exception as e:
                messagebox.showerror("خطا در باز کردن PDF", f"فایل PDF تولید شد اما در باز کردن آن خطا رخ داد: {e}", master=self)
        else:
            messagebox.showerror("خطا در تولید PDF", "خطا در تولید فایل PDF برای مشاهده.", master=self)


    def delete_selected_invoice(self):
        selected_item_id = self.invoice_table.focus()
        if not selected_item_id:
            messagebox.showwarning("هشدار", "لطفاً یک صورتحساب را برای حذف انتخاب کنید.", master=self)
            return

        confirm = messagebox.askyesno("تایید حذف", "آیا مطمئنید می‌خواهید این صورتحساب را حذف کنید؟", master=self)
        if confirm:
            invoice_id = int(selected_item_id)
            success, msg = self.invoice_manager.delete_invoice(invoice_id)
            if success:
                messagebox.showinfo("موفقیت", "صورتحساب با موفقیت حذف شد.", master=self)
                self.load_invoices_to_table() # رفرش جدول
            else:
                messagebox.showerror("خطا", f"خطا در حذف صورتحساب: {msg}", master=self)

# --- بلاک تست مستقل ---
# این بلاک دیگر برای تست مستقیم این UI استفاده نمی‌شود و در InvoiceManagerUI تست خواهد شد.
# if __name__ == "__main__":
#     root = ctk.CTk()
#     root.title("لیست صورتحساب‌ها (تست مستقل)")
#     root.geometry("800x600")
#     ctk.set_appearance_mode("light") 
    
#     default_font_family = "Vazirmatn"
#     default_font_size = 14
#     base_font_tuple = (default_font_family, default_font_size)
#     heading_font_tuple = (default_font_family, default_font_size + 2, "bold")
#     button_font_tuple = (default_font_family, default_font_size + 1)
#     nav_button_font_tuple = (default_font_family, default_font_size + 1, "bold") 
    
#     test_ui_colors = {
#         "background_light_gray": "#F0F2F5", 
#         "text_dark_gray": "#333333", 
#         "text_medium_gray": "#555555", 
#         "hover_light_blue": "#e0f2f7", 
#         "accent_blue": "#007bff", 
#         "accent_blue_hover": "#0056b3",
#         "active_button_bg": "#E8F0FE", 
#         "active_button_text": "#1A73E8", 
#         "active_button_border": "#1A73E8", 
#         "active_sub_button_bg": "#E6FFE6", 
#         "active_sub_button_text": "#28A745", 
#         "active_sub_button_border": "#28A745", 
#         "white": "white",
#         "border_gray": "#cccccc",
#     }
    
#     try:
#         test_label = ctk.CTkLabel(master=root, text="بررسی فونت", font=base_font_tuple)
#         test_label.pack()
#         test_label.destroy() 
#     except Exception:
#         print("Vazirmatn font might not be installed. Using default CTk font.")

#     from db_manager import DBManager, DATABASE_NAME
#     from customer_manager import CustomerManager
#     from service_manager import ServiceManager
#     from contract_manager import ContractManager
#     from models import Customer, Service, Contract, Invoice, InvoiceItem
    
#     temp_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATABASE_NAME)
#     temp_db_manager = DBManager(temp_db_path)
    
#     if temp_db_manager.connect():
#         temp_db_manager.create_tables()
#         temp_db_manager.migrate_database()
#         temp_db_manager.close()
    
#     # اطمینان از وجود داده‌های تست
#     cust_man = CustomerManager()
#     svc_man = ServiceManager()
#     cont_man = ContractManager()

#     if not cust_man.get_all_customers()[0]:
#         cust_man.add_customer(Customer(customer_code=1001, name="مشتری تست لیست فاکتور", customer_type="حقوقی", tax_id="22222222222", email="list@example.com", address="آدرس لیست"))
#     if not svc_man.get_all_services()[0]:
#         svc_man.add_service(Service(service_code=201, description="طراحی UX"))

#     customers_in_db, _ = cust_man.get_all_customers()
#     services_in_db, _ = svc_man.get_all_services()
#     contracts_in_db, _ = cont_man.get_all_contracts()

#     if customers_in_db and services_in_db and contracts_in_db:
#         # ایجاد چند فاکتور تست برای نمایش در لیست
#         invoice_man = InvoiceManager()
        
#         # Invoice 1
#         test_invoice1 = Invoice(
#             invoice_number="INV-001",
#             customer_id=customers_in_db[0].id,
#             contract_id=contracts_in_db[0].id,
#             issue_date="1403/03/01",
#             total_amount=10000000,
#             discount_percentage=0,
#             tax_percentage=9,
#             final_amount=10900000,
#             description="صورتحساب تست 1"
#         )
#         test_items1 = [
#             InvoiceItem(service_id=services_in_db[0].id, quantity=1, unit_price=10000000, total_price=10000000)
#         ]
#         invoice_man.add_invoice(test_invoice1, test_items1)

#         # Invoice 2
#         test_invoice2 = Invoice(
#             invoice_number="INV-002",
#             customer_id=customers_in_db[0].id,
#             contract_id=contracts_in_db[0].id,
#             issue_date="1403/03/15",
#             total_amount=5000000,
#             discount_percentage=5,
#             tax_percentage=9,
#             final_amount=5177500,
#             description="صورتحساب تست 2"
#         )
#         test_items2 = [
#             InvoiceItem(service_id=services_in_db[0].id, quantity=0.5, unit_price=10000000, total_price=5000000)
#         ]
#         invoice_man.add_invoice(test_invoice2, test_items2)


#     invoice_list_frame = InvoiceListUI(root, temp_db_manager, test_ui_colors, base_font_tuple, heading_font_tuple, button_font_tuple, nav_button_font_tuple)
#     invoice_list_frame.pack(fill="both", expand=True)

#     root.mainloop()