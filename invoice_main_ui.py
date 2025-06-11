# invoice_main_ui.py
import customtkinter as ctk
from tkinter import messagebox
import os
import jdatetime
import json # اضافه شد برای خواندن JSON از قالب

from contract_manager import ContractManager
from invoice_details_window import InvoiceDetailsWindow # پنجره جزئیات
from models import Contract, InvoiceTemplate # InvoiceTemplate اضافه شد
from invoice_template_manager import InvoiceTemplateManager # اضافه شد

class InvoiceMainUI(ctk.CTkFrame):
    def __init__(self, parent, db_manager, ui_colors, base_font, heading_font, button_font, nav_button_font):
        super().__init__(parent, fg_color="transparent")
        self.parent = parent
        self.db_manager = db_manager
        self.ui_colors = ui_colors
        self.base_font = base_font
        self.heading_font = heading_font
        self.button_font = button_font
        self.nav_button_font = nav_button_font

        self.contract_manager = ContractManager()
        self.invoice_template_manager = InvoiceTemplateManager() # اضافه شد

        self.selected_contract_var = ctk.StringVar()
        self.selected_template_var = ctk.StringVar() # تغییر: از selected_format_var به selected_template_var
        self.contract_data_map = {} # Map contract_number to Contract object
        self.template_data_map = {} # Map template_name to InvoiceTemplate object
        self.current_selected_template = None # برای نگهداری آبجکت قالب انتخاب شده

        self.create_widgets()
        self.load_contracts_to_dropdown()
        self.load_templates_to_dropdown() # اضافه شد

    def create_widgets(self):
        main_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=10,
                                  border_width=1, border_color=self.ui_colors["border_gray"])
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(2, weight=1) # برای فضا

        # --- Section 1: Contract Selection ---
        contract_selection_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        contract_selection_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        contract_selection_frame.grid_columnconfigure(0, weight=1)
        contract_selection_frame.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(contract_selection_frame, text="انتخاب قرارداد:", font=self.heading_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=0, column=1, padx=10, pady=5, sticky="e")
        self.contract_dropdown = ctk.CTkComboBox(contract_selection_frame, values=[], variable=self.selected_contract_var,
                                                 font=self.base_font, justify="right", width=300,
                                                 command=self.on_contract_selected)
        self.contract_dropdown.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        # --- Section 2: Invoice Template Selection ---
        template_selection_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        template_selection_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        template_selection_frame.grid_columnconfigure(0, weight=1)
        template_selection_frame.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(template_selection_frame, text="انتخاب قالب صورتحساب:", font=self.heading_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=0, column=1, padx=10, pady=5, sticky="e")
        self.template_dropdown = ctk.CTkComboBox(template_selection_frame, values=[], # مقادیر داینامیک از دیتابیس
                                               variable=self.selected_template_var,
                                               font=self.base_font, justify="right", width=300,
                                               command=self.on_template_selected) # اضافه شد
        self.template_dropdown.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        
        # --- Create Invoice Button ---
        create_invoice_btn = ctk.CTkButton(main_frame, text="ساخت صورتحساب",
                                           font=self.button_font, fg_color=self.ui_colors["accent_blue"],
                                           hover_color=self.ui_colors["accent_blue_hover"], text_color="white",
                                           corner_radius=8, command=self.open_invoice_details_window)
        create_invoice_btn.grid(row=3, column=0, columnspan=2, padx=10, pady=20)


    def load_contracts_to_dropdown(self):
        contracts, _ = self.contract_manager.get_all_contracts()
        contracts.sort(key=lambda c: c.contract_number, reverse=True) # Sort by number descending
        
        contract_numbers = []
        self.contract_data_map = {}
        for contract in contracts:
            display_text = f"{contract.contract_number} ({contract.customer_name} - {contract.contract_date})"
            contract_numbers.append(display_text)
            self.contract_data_map[display_text] = contract
        
        self.contract_dropdown.configure(values=contract_numbers)
        if contract_numbers:
            self.selected_contract_var.set(contract_numbers[0])
            self.on_contract_selected(contract_numbers[0])
        else:
            self.selected_contract_var.set("قراردادی یافت نشد")
            self.contract_dropdown.configure(state="disabled")

    def load_templates_to_dropdown(self):
        """ بارگذاری قالب‌های صورتحساب فعال از دیتابیس به دراپ‌داون """
        templates, _ = self.invoice_template_manager.get_all_templates(active_only=True)
        templates.sort(key=lambda t: t.template_name)
        
        template_names = []
        self.template_data_map = {}
        for template in templates:
            template_names.append(template.template_name)
            self.template_data_map[template.template_name] = template
        
        self.template_dropdown.configure(values=template_names)
        if template_names:
            self.selected_template_var.set(template_names[0])
            self.on_template_selected(template_names[0]) # فراخوانی برای بارگذاری تنظیمات اولیه
        else:
            self.selected_template_var.set("قالبی یافت نشد")
            self.template_dropdown.configure(state="disabled")
            self.current_selected_template = None


    def on_contract_selected(self, choice):
        # این تابع وقتی یک قرارداد از دراپ‌داون انتخاب میشه، فراخوانی میشه
        pass

    def on_template_selected(self, choice):
        """ وقتی یک قالب از دراپ‌داون انتخاب می‌شود، آبجکت آن را ذخیره می‌کند. """
        self.current_selected_template = self.template_data_map.get(choice)
        if not self.current_selected_template:
            messagebox.showwarning("خطا", "قالب انتخاب شده نامعتبر است.", master=self)
            self.selected_template_var.set("قالبی یافت نشد") # ریست کردن دراپ‌داون
            self.current_selected_template = None


    def open_invoice_details_window(self):
        selected_contract_display_text = self.selected_contract_var.get()
        selected_contract: Contract = self.contract_data_map.get(selected_contract_display_text)
        
        if not selected_contract:
            messagebox.showwarning("خطا", "لطفاً یک قرارداد را انتخاب کنید.", master=self)
            return
        
        if not self.current_selected_template:
            messagebox.showwarning("خطا", "لطفاً یک قالب صورتحساب را انتخاب کنید.", master=self)
            return

        # باز کردن پنجره جدید
        # master for Toplevel should be the main app instance (self.master.master)
        invoice_details_win = InvoiceDetailsWindow(
            master=self.master.master, 
            db_manager=self.db_manager,
            ui_colors=self.ui_colors,
            base_font=self.base_font,
            heading_font=self.heading_font,
            button_font=self.button_font,
            selected_contract=selected_contract,
            selected_invoice_template=self.current_selected_template # تغییر: ارسال آبجکت قالب
        )
        invoice_details_win.grab_set() 
        self.master.master.wait_window(invoice_details_win) 

# --- بلاک تست مستقل ---
# این بلاک دیگر برای تست مستقیم این UI استفاده نمی‌شود و در InvoiceManagerUI تست خواهد شد.
# if __name__ == "__main__":
#     root = ctk.CTk()
#     root.title("تب صدور صورتحساب (تست مستقل)")
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
#     from models import Customer, Service, Contract
    
#     temp_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATABASE_NAME)
#     temp_db_manager = DBManager(temp_db_path)
    
#     if temp_db_manager.connect():
#         temp_db_manager.create_tables()
#         temp_db_manager.migrate_database()
#         temp_db_manager.close()
    
#     cust_man = CustomerManager()
#     svc_man = ServiceManager()
#     cont_man = ContractManager()

#     # ایجاد مشتری و سرویس تست اگر وجود ندارند
#     if not cust_man.get_all_customers()[0]:
#         cust_man.add_customer(Customer(customer_code=1001, name="مشتری قرارداد تست", customer_type="حقوقی", tax_id="11111111111", email="contract@example.com", address="آدرس تست"))
    
#     if not svc_man.get_all_services()[0]:
#         svc_man.add_service(Service(service_code=101, description="مشاوره پروژه"))
#         svc_man.add_service(Service(service_code=102, description="نصب نرم افزار"))

#     # ایجاد قرارداد تست اگر وجود ندارد
#     if not cont_man.get_all_contracts()[0]:
#         customers_in_db, _ = cust_man.get_all_customers()
#         if customers_in_db:
#             test_customer_id = customers_in_db[0].id
#             cont_man.add_contract(Contract(
#                 customer_id=test_customer_id,
#                 contract_number="C-TEST-001",
#                 contract_date=jdatetime.date.today().strftime("%Y/%m/%d"),
#                 total_amount=50000000,
#                 description="قرارداد تست برای صدور صورتحساب",
#                 title="قرارداد خدمات نرم افزاری",
#                 payment_method="یکجا",
#                 scanned_pages=[]
#             ))


#     invoice_main_frame = InvoiceMainUI(root, temp_db_manager, test_ui_colors, base_font_tuple, heading_font_tuple, button_font_tuple, nav_button_font_tuple)
#     invoice_main_frame.pack(fill="both", expand=True)

#     root.mainloop()