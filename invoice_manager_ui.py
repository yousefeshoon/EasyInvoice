# invoice_manager_ui.py
import customtkinter as ctk
from tkinter import messagebox
import os

# Import the individual UI components for invoices
from invoice_main_ui import InvoiceMainUI
from invoice_list_ui import InvoiceListUI

class InvoiceManagerUI(ctk.CTkFrame):
    def __init__(self, parent, db_manager, ui_colors, base_font, heading_font, button_font, nav_button_font):
        super().__init__(parent, fg_color="transparent")
        self.parent = parent
        self.db_manager = db_manager
        self.ui_colors = ui_colors
        self.base_font = base_font
        self.heading_font = heading_font
        self.button_font = button_font
        self.nav_button_font = nav_button_font

        self.frames = {}
        self.current_active_sub_button = None
        self.current_active_sub_page_name = None

        self.create_widgets()
        self.init_sub_frames()
        
        # Default to showing the "Create Invoice" page
        self.after(100, lambda: self.on_sub_nav_button_click("create_invoice", self.create_invoice_btn))

    def create_widgets(self):
        """ ایجاد ویجت‌های اصلی مربوط به مدیریت صورتحساب‌ها. """
        invoice_card_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=10, 
                                           border_width=1, border_color=self.ui_colors["border_gray"])
        invoice_card_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        invoice_card_frame.grid_rowconfigure(0, weight=0)
        invoice_card_frame.grid_rowconfigure(1, weight=1)
        invoice_card_frame.grid_columnconfigure(0, weight=1)

        self.sub_navbar_frame = ctk.CTkFrame(invoice_card_frame, fg_color="white", corner_radius=0)
        self.sub_navbar_frame.grid(row=0, column=0, padx=0, pady=0, sticky="ew")
        self.sub_navbar_frame.grid_rowconfigure(0, weight=1)
        self.sub_navbar_frame.grid_columnconfigure(0, weight=1)
        self.sub_navbar_frame.grid_columnconfigure(1, weight=0)
        self.sub_navbar_frame.grid_columnconfigure(2, weight=1)
        
        sub_buttons_container = ctk.CTkFrame(self.sub_navbar_frame, fg_color="transparent")
        sub_buttons_container.grid(row=0, column=1, sticky="nsew")
        
        sub_buttons_container.grid_columnconfigure(0, weight=0)
        sub_buttons_container.grid_columnconfigure(1, weight=0)
        sub_buttons_container.grid_rowconfigure(0, weight=1)
        
        self.create_invoice_btn = ctk.CTkButton(sub_buttons_container, text="صدور صورتحساب",
                                                font=self.nav_button_font,
                                                fg_color=self.ui_colors["white"],
                                                text_color=self.ui_colors["text_medium_gray"],
                                                hover_color=self.ui_colors["hover_light_blue"],
                                                corner_radius=8,
                                                command=lambda: self.on_sub_nav_button_click("create_invoice", self.create_invoice_btn))
        self.create_invoice_btn.grid(row=0, column=1, padx=5, pady=10)

        self.list_invoices_btn = ctk.CTkButton(sub_buttons_container, text="لیست صورتحساب‌ها",
                                                font=self.nav_button_font,
                                                fg_color=self.ui_colors["white"],
                                                text_color=self.ui_colors["text_medium_gray"],
                                                hover_color=self.ui_colors["hover_light_blue"],
                                                corner_radius=8,
                                                command=lambda: self.on_sub_nav_button_click("list_invoices", self.list_invoices_btn))
        self.list_invoices_btn.grid(row=0, column=0, padx=5, pady=10)

        self.invoice_content_frame = ctk.CTkFrame(invoice_card_frame, fg_color="white")
        self.invoice_content_frame.grid(row=1, column=0, padx=20, pady=(20, 20), sticky="nsew")
        self.invoice_content_frame.grid_rowconfigure(0, weight=1)
        self.invoice_content_frame.grid_columnconfigure(0, weight=1)

    def init_sub_frames(self):
        """ مقداردهی اولیه فریم‌های زیرمجموعه مدیریت صورتحساب. """
        # Instance of InvoiceMainUI (for creating invoices, now using 'contract-based' main UI)
        create_invoice_page = InvoiceMainUI(self.invoice_content_frame, self.db_manager, self.ui_colors,
                                            self.base_font, self.heading_font, self.button_font, self.nav_button_font)
        self.frames["create_invoice"] = create_invoice_page
        create_invoice_page.grid(row=0, column=0, sticky="nsew")

        # Instance of InvoiceListUI
        list_invoices_page = InvoiceListUI(self.invoice_content_frame, self.db_manager, self.ui_colors,
                                          self.base_font, self.heading_font, self.button_font, self.nav_button_font)
        self.frames["list_invoices"] = list_invoices_page
        list_invoices_page.grid(row=0, column=0, sticky="nsew")

    def show_sub_frame(self, page_name):
        """ نمایش یک فریم زیرمجموعه خاص در مدیریت صورتحساب‌ها """
        frame = self.frames.get(page_name)
        if frame:
            frame.tkraise()
            self.current_active_sub_page_name = page_name
            # Optionally call a refresh method on the frame if it needs to update its data
            if page_name == "list_invoices":
                frame.load_invoices_to_table() # Ensure list is refreshed when tab is opened
            elif page_name == "create_invoice":
                frame.clear_contract_selection() # Reset contract selection on page load
                frame.load_templates_to_dropdown() # Refresh templates if needed

        else:
            messagebox.showwarning("زیرصفحه هنوز پیاده‌سازی نشده", f"زیرصفحه '{page_name}' هنوز در دست ساخت است.", master=self)

    def on_sub_nav_button_click(self, page_name, clicked_button):
        """
        هندل کردن کلیک روی دکمه‌های منوی داخلی مدیریت صورتحساب‌ها.
        صفحه مورد نظر را نمایش داده و استایل دکمه فعال را تغییر می‌دهد.
        """
        target_frame = self.frames.get(page_name)

        if target_frame:
            if self.current_active_sub_button:
                self.current_active_sub_button.configure(
                    fg_color=self.ui_colors["white"],
                    text_color=self.ui_colors["text_medium_gray"],
                    border_width=0
                )
            
            clicked_button.configure(
                fg_color=self.ui_colors["active_sub_button_bg"],
                text_color=self.ui_colors["active_sub_button_text"],
                border_width=2,
                border_color=self.ui_colors["active_sub_button_border"]
            )
            self.current_active_sub_button = clicked_button
            self.show_sub_frame(page_name)
        else:
            messagebox.showwarning("زیرصفحه هنوز پیاده‌سازی نشده", f"زیرصفحه '{page_name}' هنوز در دست ساخت است.", master=self)
            
            # Revert to previous active button if the new page is not implemented
            if self.current_active_sub_page_name:
                if self.current_active_sub_page_name == "create_invoice":
                    self.create_invoice_btn.configure(
                        fg_color=self.ui_colors["active_sub_button_bg"],
                        text_color=self.ui_colors["active_sub_button_text"],
                        border_width=2,
                        border_color=self.ui_colors["active_sub_button_border"]
                    )
                    self.current_active_sub_button = self.create_invoice_btn
                elif self.current_active_sub_page_name == "list_invoices":
                    self.list_invoices_btn.configure(
                        fg_color=self.ui_colors["active_sub_button_bg"],
                        text_color=self.ui_colors["active_sub_button_text"],
                        border_width=2,
                        border_color=self.ui_colors["active_sub_button_border"]
                    )
                    self.current_active_sub_button = self.list_invoices_btn

# --- بلاک تست مستقل UI ---
if __name__ == "__main__":
    root = ctk.CTk()
    root.title("مدیریت صورتحساب EasyInvoice (تست مستقل)")
    root.geometry("1000x700")
    ctk.set_appearance_mode("light") 
    
    default_font_family = "Vazirmatn"
    default_font_size = 14
    base_font_tuple = (default_font_family, default_font_size)
    heading_font_tuple = (default_font_family, default_font_size + 2, "bold")
    button_font_tuple = (default_font_family, default_font_size + 1)
    nav_button_font_tuple = (default_font_family, default_font_size + 1, "bold")
    
    test_ui_colors = {
        "background_light_gray": "#F0F2F5", 
        "text_dark_gray": "#333333", 
        "text_medium_gray": "#555555", 
        "hover_light_blue": "#e0f2f7", 
        "accent_blue": "#007bff", 
        "accent_blue_hover": "#0056b3",
        "active_button_bg": "#E8F0FE", 
        "active_button_text": "#1A73E8", 
        "active_button_border": "#1A73E8", 
        "active_sub_button_bg": "#E6FFE6", 
        "active_sub_button_text": "#28A745", 
        "active_sub_button_border": "#28A745", 
        "white": "white",
        "border_gray": "#cccccc",
    }
    
    try:
        test_label = ctk.CTkLabel(master=root, text="بررسی فونت", font=base_font_tuple)
        test_label.pack()
        test_label.destroy() 
    except Exception:
        print("Vazirmatn font might not be installed. Using default CTk font.")

    from db_manager import DBManager, DATABASE_NAME
    from customer_manager import CustomerManager
    from service_manager import ServiceManager
    from contract_manager import ContractManager
    from models import Customer, Service, Contract, AppSettings
    from settings_manager import SettingsManager # Added for test setup
    from invoice_template_manager import InvoiceTemplateManager


    temp_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATABASE_NAME)
    temp_db_manager = DBManager(temp_db_path)
    
    if temp_db_manager.connect():
        temp_db_manager.create_tables()
        temp_db_manager.migrate_database()
        temp_db_manager.close()
    
    # Ensure there are some customers, services, and contracts for testing
    cust_man = CustomerManager()
    svc_man = ServiceManager()
    cont_man = ContractManager()
    settings_man = SettingsManager()
    tmpl_man = InvoiceTemplateManager()

    if not cust_man.get_all_customers()[0]:
        cust_man.add_customer(Customer(customer_code=1001, name="مشتری تست صورتحساب", customer_type="حقوقی", tax_id="11111111111", email="invoice_test@example.com", address="آدرس تست"))
    
    if not svc_man.get_all_services()[0]:
        svc_man.add_service(Service(service_code=101, description="مشاوره پروژه"))
        svc_man.add_service(Service(service_code=102, description="نصب نرم افزار"))

    if not cont_man.get_all_contracts()[0]:
        customers_in_db, _ = cust_man.get_all_customers()
        if customers_in_db:
            test_customer_id = customers_in_db[0].id
            cont_man.add_contract(Contract(
                customer_id=test_customer_id,
                contract_number="C-TEST-001",
                contract_date=jdatetime.date.today().strftime("%Y/%m/%d"),
                total_amount=50000000,
                description="قرارداد تست برای صدور صورتحساب",
                title="قرارداد خدمات نرم افزاری",
                payment_method="یکجا",
                scanned_pages=[]
            ))
    
    # Add dummy settings if not exists (for seller info and logo)
    current_settings = settings_man.get_settings()
    if not current_settings.seller_name:
        dummy_settings = AppSettings(
            seller_name="شرکت آسان‌فاکتور (تست)",
            seller_address="تهران، میدان آزادی، دفتر 5",
            seller_phone="021-88888888",
            seller_tax_id="1234567890",
            seller_economic_code="9876543",
            seller_logo_path="" # Or provide a real path for testing logo
        )
        settings_man.save_settings(dummy_settings)

    # ایجاد قالب صورتحساب تست اگر وجود ندارد
    if not tmpl_man.get_all_templates()[0]:
        tmpl_man.add_template(InvoiceTemplate(
            template_name="قالب پیش‌فرض",
            template_type="PDF_Standard",
            required_fields=["invoice_number", "customer_name", "total_amount", "item_service_description"],
            default_settings={"tax_percentage": 9, "discount_editable": True},
            is_active=1
        ))

    invoice_manager_frame = InvoiceManagerUI(root, temp_db_manager, test_ui_colors, base_font_tuple, heading_font_tuple, button_font_tuple, nav_button_font_tuple)
    invoice_manager_frame.pack(fill="both", expand=True)

    root.mainloop()