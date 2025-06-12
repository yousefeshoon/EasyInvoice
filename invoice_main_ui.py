# invoice_main_ui.py
import customtkinter as ctk
from tkinter import messagebox, ttk
import os
import jdatetime
import json

from contract_manager import ContractManager
from invoice_details_window import InvoiceDetailsWindow
from models import Contract, InvoiceTemplate
from invoice_template_manager import InvoiceTemplateManager

class ContractSelectionWindow(ctk.CTkToplevel):
    def __init__(self, master, opener_frame, db_manager, ui_colors, base_font, heading_font, button_font):
        super().__init__(master)
        self.master = master
        self.opener_frame = opener_frame # Store the InvoiceMainUI instance
        self.db_manager = db_manager
        self.ui_colors = ui_colors
        self.base_font = base_font
        self.heading_font = heading_font
        self.button_font = button_font
        self.contract_manager = ContractManager()
        
        self.title("انتخاب قرارداد")
        self.transient(master)
        self.grab_set() # کاربر نتواند با پنجره اصلی کار کند تا این پنجره باز است

        self.selected_contract = None
        self.filter_var = ctk.StringVar()

        self.create_widgets()
        self.load_contracts_to_table()
        
        # مرکز قرار دادن پنجره روی master
        self.update_idletasks()
        master_x = master.winfo_x()
        master_y = master.winfo_y()
        master_width = master.winfo_width()
        master_height = master.winfo_height()

        window_width = 700
        window_height = 500

        x = master_x + (master_width // 2) - (window_width // 2)
        y = master_y + (master_height // 2) - (window_height // 2)

        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.minsize(window_width, window_height)

    def create_widgets(self):
        main_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=10,
                                  border_width=1, border_color=self.ui_colors["border_gray"])
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        main_frame.grid_rowconfigure(2, weight=1) # برای جدول
        main_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(main_frame, text="جستجو در قراردادها:", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=0, column=0, padx=10, pady=5, sticky="e")
        
        filter_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        filter_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        filter_frame.grid_columnconfigure(0, weight=1)

        filter_entry = ctk.CTkEntry(filter_frame, textvariable=self.filter_var, font=self.base_font, justify="right",
                                    placeholder_text="جستجو بر اساس شماره قرارداد، مشتری، عنوان...",
                                    fg_color="#f8f8f8", border_color=self.ui_colors["border_gray"], corner_radius=5)
        filter_entry.pack(fill="x", expand=True)
        filter_entry.bind("<KeyRelease>", self.apply_filter)

        # Treeview برای نمایش قراردادها
        self.contract_table = ttk.Treeview(main_frame, columns=("ContractNumber", "CustomerName", "Title", "ContractDate"), show="headings")
        self.contract_table.heading("ContractNumber", text="شماره قرارداد", anchor="e")
        self.contract_table.heading("CustomerName", text="نام مشتری", anchor="e")
        self.contract_table.heading("Title", text="عنوان", anchor="e")
        self.contract_table.heading("ContractDate", text="تاریخ", anchor="e")

        self.contract_table.column("ContractNumber", width=100, anchor="e", stretch=False)
        self.contract_table.column("CustomerName", width=150, anchor="e", stretch=True)
        self.contract_table.column("Title", width=200, anchor="e", stretch=True)
        self.contract_table.column("ContractDate", width=80, anchor="e", stretch=False)
        
        self.contract_table.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        self.contract_table.bind("<<TreeviewSelect>>", self.on_contract_select)
        self.contract_table.bind("<Double-1>", self.on_double_click)

        # Scrollbar
        tree_scrollbar = ctk.CTkScrollbar(main_frame, command=self.contract_table.yview)
        tree_scrollbar.grid(row=2, column=1, sticky="ns", padx=(0,10), pady=10)
        self.contract_table.configure(yscrollcommand=tree_scrollbar.set)

        # Style for Treeview
        tree_style = ttk.Style()
        tree_style.configure("Treeview", font=self.base_font, rowheight=25)
        tree_style.configure("Treeview.Heading", font=self.button_font)
        tree_style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nsew'})])

        # Buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="e")

        select_btn = ctk.CTkButton(button_frame, text="انتخاب", font=self.button_font,
                                   fg_color=self.ui_colors["accent_blue"], hover_color=self.ui_colors["accent_blue_hover"],
                                   command=self.select_contract)
        select_btn.pack(side="right", padx=5)

        cancel_btn = ctk.CTkButton(button_frame, text="لغو", font=self.button_font,
                                   fg_color="#999999", hover_color="#777777",
                                   command=self.destroy)
        cancel_btn.pack(side="right", padx=5)

    def load_contracts_to_table(self, contracts_to_display=None):
        for item in self.contract_table.get_children():
            self.contract_table.delete(item)

        if contracts_to_display is None:
            contracts, _ = self.contract_manager.get_all_contracts()
        else:
            contracts = contracts_to_display
            
        contracts.sort(key=lambda c: c.contract_number, reverse=True) # Sort by number descending

        for contract in contracts:
            self.contract_table.insert("", "end", iid=contract.id, values=(
                contract.contract_number,
                contract.customer_name if contract.customer_name else "نامشخص",
                contract.title if contract.title else "بدون عنوان",
                contract.contract_date if contract.contract_date else ""
            ))

    def apply_filter(self, event=None):
        search_term = self.filter_var.get().strip().lower()
        all_contracts, _ = self.contract_manager.get_all_contracts()
        
        filtered_contracts = []
        if search_term:
            for contract in all_contracts:
                if (search_term in str(contract.contract_number).lower() or
                    search_term in str(contract.customer_name).lower() or
                    search_term in str(contract.title).lower() or
                    search_term in str(contract.contract_date).lower()):
                    filtered_contracts.append(contract)
        else:
            filtered_contracts = all_contracts
        
        self.load_contracts_to_table(filtered_contracts)

    def on_contract_select(self, event):
        selected_item_id = self.contract_table.focus()
        if selected_item_id:
            contract_id = int(selected_item_id)
            contract_obj, _ = self.contract_manager.get_contract_by_id(contract_id)
            self.selected_contract = contract_obj
        else:
            self.selected_contract = None

    def on_double_click(self, event):
        self.select_contract()

    def select_contract(self):
        if self.selected_contract:
            # Call the method on the opener_frame (InvoiceMainUI instance)
            self.opener_frame.after_contract_selected(self.selected_contract)
            self.destroy()
        else:
            messagebox.showwarning("هشدار", "لطفاً یک قرارداد را انتخاب کنید.", master=self)


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
        self.invoice_template_manager = InvoiceTemplateManager()

        self.selected_contract = None # برای نگهداری آبجکت قرارداد انتخاب شده
        self.selected_template_var = ctk.StringVar()
        self.template_data_map = {}
        self.current_selected_template = None

        self.contract_display_label = None # برای نمایش قرارداد انتخاب شده

        self.create_widgets()
        self.load_templates_to_dropdown()
        self.clear_contract_selection() # تنظیم اولیه نمایش قرارداد

    def create_widgets(self):
        main_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=10,
                                  border_width=1, border_color=self.ui_colors["border_gray"])
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(2, weight=1) # برای فضا

        # --- Section 1: Contract Selection Button and Display ---
        contract_selection_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        contract_selection_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        contract_selection_frame.grid_columnconfigure(0, weight=1) # برای لیبل نمایش
        contract_selection_frame.grid_columnconfigure(1, weight=0) # برای دکمه انتخاب
        contract_selection_frame.grid_columnconfigure(2, weight=0) # برای لیبل "انتخاب قرارداد"

        ctk.CTkLabel(contract_selection_frame, text="قرارداد انتخاب شده:", font=self.heading_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=0, column=2, padx=10, pady=5, sticky="e")
        
        self.contract_display_label = ctk.CTkLabel(contract_selection_frame, text="قراردادی انتخاب نشده است.", font=self.base_font, text_color=self.ui_colors["text_medium_gray"], wraplength=350, justify="right")
        self.contract_display_label.grid(row=0, column=0, padx=10, pady=5, sticky="e") # تراز راست

        select_contract_btn = ctk.CTkButton(contract_selection_frame, text="انتخاب قرارداد",
                                           font=self.button_font, fg_color=self.ui_colors["accent_blue"],
                                           hover_color=self.ui_colors["accent_blue_hover"], text_color="white",
                                           corner_radius=8, command=self.open_contract_selection_window)
        select_contract_btn.grid(row=0, column=1, padx=10, pady=5)


        # --- Section 2: Invoice Template Selection ---
        template_selection_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        template_selection_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        template_selection_frame.grid_columnconfigure(0, weight=1)
        template_selection_frame.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(template_selection_frame, text="انتخاب قالب صورتحساب:", font=self.heading_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=0, column=1, padx=10, pady=5, sticky="e")
        self.template_dropdown = ctk.CTkComboBox(template_selection_frame, values=[],
                                               variable=self.selected_template_var,
                                               font=self.base_font, justify="right", width=300,
                                               command=self.on_template_selected)
        self.template_dropdown.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        
        # --- Create Invoice Button ---
        create_invoice_btn = ctk.CTkButton(main_frame, text="ساخت صورتحساب",
                                           font=self.button_font, fg_color=self.ui_colors["accent_blue"],
                                           hover_color=self.ui_colors["accent_blue_hover"], text_color="white",
                                           corner_radius=8, command=self.open_invoice_details_window)
        create_invoice_btn.grid(row=3, column=0, columnspan=2, padx=10, pady=20)

    def open_contract_selection_window(self):
        # Master for Toplevel should be the main app instance
        contract_win = ContractSelectionWindow(
            master=self.master.master,
            opener_frame=self, # Pass the current InvoiceMainUI instance
            db_manager=self.db_manager,
            ui_colors=self.ui_colors,
            base_font=self.base_font,
            heading_font=self.heading_font,
            button_font=self.button_font
        )
        self.master.master.wait_window(contract_win) # منتظر می‌ماند تا پنجره بسته شود

    def after_contract_selected(self, contract: Contract):
        """ این تابع پس از انتخاب قرارداد در پنجره پاپ‌آپ فراخوانی می‌شود. """
        self.selected_contract = contract
        if contract:
            display_text = f"شماره: {contract.contract_number} - مشتری: {contract.customer_name} - عنوان: {contract.title}"
            self.contract_display_label.configure(text=display_text)
        else:
            self.clear_contract_selection()

    def clear_contract_selection(self):
        """ پاک کردن قرارداد انتخاب شده و نمایش متن پیش‌فرض. """
        self.selected_contract = None
        self.contract_display_label.configure(text="قراردادی انتخاب نشده است.")


    def load_templates_to_dropdown(self):
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
            self.on_template_selected(template_names[0])
        else:
            self.selected_template_var.set("قالبی یافت نشد")
            self.template_dropdown.configure(state="disabled")
            self.current_selected_template = None


    def on_template_selected(self, choice):
        self.current_selected_template = self.template_data_map.get(choice)
        if not self.current_selected_template:
            messagebox.showwarning("خطا", "قالب انتخاب شده نامعتبر است.", master=self)
            self.selected_template_var.set("قالبی یافت نشد")
            self.current_selected_template = None


    def open_invoice_details_window(self):
        if not self.selected_contract:
            messagebox.showwarning("خطا", "لطفاً یک قرارداد را انتخاب کنید.", master=self)
            return
        
        if not self.current_selected_template:
            messagebox.showwarning("خطا", "لطفاً یک قالب صورتحساب را انتخاب کنید.", master=self)
            return

        invoice_details_win = InvoiceDetailsWindow(
            master=self.master.master,
            db_manager=self.db_manager,
            ui_colors=self.ui_colors,
            base_font=self.base_font,
            heading_font=self.heading_font,
            button_font=self.button_font,
            selected_contract=self.selected_contract,
            selected_invoice_template=self.current_selected_template
        )
        invoice_details_win.grab_set()
        self.master.master.wait_window(invoice_details_win)

# --- بلاک تست مستقل ---
if __name__ == "__main__":
    root = ctk.CTk()
    root.title("تب صدور صورتحساب (تست مستقل)")
    root.geometry("800x600")
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
    from models import Customer, Service, Contract
    from invoice_template_manager import InvoiceTemplateManager
    
    temp_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATABASE_NAME)
    temp_db_manager = DBManager(temp_db_path)
    
    if temp_db_manager.connect():
        temp_db_manager.create_tables()
        temp_db_manager.migrate_database()
        temp_db_manager.close()
    
    cust_man = CustomerManager()
    svc_man = ServiceManager()
    cont_man = ContractManager()
    tmpl_man = InvoiceTemplateManager()

    # ایجاد مشتری و سرویس تست اگر وجود ندارند
    if not cust_man.get_all_customers()[0]:
        cust_man.add_customer(Customer(customer_code=1001, name="مشتری قرارداد تست", customer_type="حقوقی", tax_id="11111111111", email="contract@example.com", address="آدرس تست"))
        cust_man.add_customer(Customer(customer_code=1002, name="مشتری دو", customer_type="حقیقی", tax_id="2222222222", email="contract2@example.com", address="آدرس دو"))
    
    if not svc_man.get_all_services()[0]:
        svc_man.add_service(Service(service_code=101, description="مشاوره پروژه"))
        svc_man.add_service(Service(service_code=102, description="نصب نرم افزار"))

    # ایجاد قرارداد تست اگر وجود ندارد
    customers_in_db, _ = cust_man.get_all_customers()
    if customers_in_db and not cont_man.get_all_contracts()[0]:
        test_customer_id = customers_in_db[0].id
        test_customer_id_2 = customers_in_db[1].id
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
        cont_man.add_contract(Contract(
            customer_id=test_customer_id_2,
            contract_number="C-TEST-002",
            contract_date=jdatetime.date.today().strftime("%Y/%m/%d"),
            total_amount=25000000,
            description="قرارداد دوم برای تست",
            title="قرارداد پشتیبانی سالیانه",
            payment_method="ماهانه",
            scanned_pages=[]
        ))
        cont_man.add_contract(Contract(
            customer_id=test_customer_id,
            contract_number="C-SEARCH-003",
            contract_date=jdatetime.date.today().strftime("%Y/%m/%d"),
            total_amount=10000000,
            description="قراردادی برای جستجو",
            title="قرارداد مشاوره",
            payment_method="پروژه‌ای",
            scanned_pages=[]
        ))

    # ایجاد قالب صورتحساب تست اگر وجود ندارد
    if not tmpl_man.get_all_templates()[0]:
        tmpl_man.add_template(InvoiceTemplate(
            template_name="قالب پیش‌فرض",
            template_type="PDF_Standard",
            required_fields=["invoice_number", "customer_name", "total_amount", "item_service_description"],
            default_settings={"tax_percentage": 9, "discount_editable": True},
            is_active=1
        ))
        tmpl_man.add_template(InvoiceTemplate(
            template_name="قالب ساده",
            template_type="PDF_Standard",
            required_fields=["invoice_number", "customer_name", "final_amount"],
            default_settings={"tax_percentage": 0, "discount_editable": False},
            is_active=1
        ))

    invoice_main_frame = InvoiceMainUI(root, temp_db_manager, test_ui_colors, base_font_tuple, heading_font_tuple, button_font_tuple, nav_button_font_tuple)
    invoice_main_frame.pack(fill="both", expand=True)

    root.mainloop()