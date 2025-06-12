# invoice_details_window.py
import customtkinter as ctk
from tkinter import messagebox, filedialog, ttk
import os
import json # برای serializing/deserializing لیست scanned_pages
import jdatetime
from PIL import Image, ImageTk 
import fitz # (PyMuPDF) برای کار با PDF
import subprocess # برای باز کردن فایل‌ها

from db_manager import DBManager # فقط برای تست مستقل لازم است
from customer_manager import CustomerManager # برای خواندن اطلاعات مشتری
from service_manager import ServiceManager # برای خواندن اطلاعات سرویس
from settings_manager import SettingsManager # برای خواندن تنظیمات فروشنده
from contract_manager import ContractManager # برای خواندن اطلاعات قرارداد
from models import Invoice, InvoiceItem, Customer, Service, Contract, InvoiceTemplate # InvoiceTemplate اضافه شد
from invoice_generator import InvoiceGenerator
from invoice_manager import InvoiceManager # اضافه شده: برای ذخیره در دیتابیس

class InvoiceDetailsWindow(ctk.CTkToplevel):
    def __init__(self, master, db_manager, ui_colors, base_font, heading_font, button_font,
                 selected_contract: Contract, selected_invoice_template: InvoiceTemplate):
        super().__init__(master)
        self.title("جزئیات صورتحساب")
        self.db_manager = db_manager
        self.ui_colors = ui_colors
        self.base_font = base_font
        self.heading_font = heading_font
        self.button_font = button_font
        
        self.customer_manager = CustomerManager()
        self.service_manager = ServiceManager()
        self.settings_manager = SettingsManager()
        self.contract_manager = ContractManager()
        self.invoice_generator = InvoiceGenerator(self.settings_manager)
        self.invoice_manager = InvoiceManager() # اضافه شده: برای ذخیره در دیتابیس

        self.selected_contract = selected_contract
        self.selected_invoice_template = selected_invoice_template 

        self.transient(master) # پنجره روی پنجره اصلی باشد
        self.grab_set() # تا وقتی باز است، کاربر نتواند با پنجره اصلی کار کند

        # Set window size and center it based on master
        self.update_idletasks()
        master_x = master.winfo_x()
        master_y = master.winfo_y()
        master_width = master.winfo_width()
        master_height = master.winfo_height()

        window_width = 900
        window_height = 650 

        x = master_x + (master_width // 2) - (window_width // 2)
        y = master_y + (master_height // 2) - (window_height // 2) 

        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.minsize(window_width, window_height)


        # Invoice Variables
        self.invoice_number_var = ctk.StringVar()
        self.issue_date_var = ctk.StringVar(value=jdatetime.date.today().strftime("%Y/%m/%d"))
        self.due_date_var = ctk.StringVar(value="----/--/--") # Optional due date
        self.customer_name_var = ctk.StringVar(value=self.selected_contract.customer_name if self.selected_contract.customer_name else "") # نام مشتری از قرارداد
        self.description_textbox = None
        self.discount_percentage_var = ctk.StringVar(value="0") # مقدار پیش‌فرض "0" نه ""
        self.tax_percentage_var = ctk.StringVar(value="9") # Default VAT (now from template)
        self.total_amount_var = ctk.StringVar(value="0") # Sum of items
        self.final_amount_var = ctk.StringVar(value="0") # total - discount + tax
        
        # Reference to discount entry for state change
        self.discount_entry = None 

        # Invoice Items
        self.invoice_items_tree = None
        self.invoice_items_list = [] # List of InvoiceItem objects in UI
        self.current_item_service_var = ctk.StringVar()
        self.current_item_quantity_var = ctk.StringVar(value="0") # مقدار پیش‌فرض "0"
        self.current_item_unit_price_var = ctk.StringVar(value="0") # مقدار پیش‌فرض "0"
        self.current_item_total_price_var = ctk.StringVar(value="0") # مقدار پیش‌فرض "0"

        self.customer_obj = None # برای نگهداری آبجکت مشتری

        self.create_widgets()
        self.load_initial_data()
        self.apply_template_settings() # اضافه شد: اعمال تنظیمات قالب
        self.clear_invoice_form() # برای مقداردهی اولیه فیلدها و اطمینان از پاک بودن

    def create_widgets(self):
        main_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=10,
                                  border_width=1, border_color=self.ui_colors["border_gray"])
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        main_frame.grid_rowconfigure(1, weight=1) # For invoice items table
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        # --- Invoice Header / Info Frame ---
        info_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        info_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        info_frame.grid_columnconfigure(0, weight=1)
        info_frame.grid_columnconfigure(1, weight=0) # Labels column
        info_frame.grid_columnconfigure(2, weight=1)
        info_frame.grid_columnconfigure(3, weight=0) # Labels column

        row_idx = 0
        
        # Invoice Number
        ctk.CTkLabel(info_frame, text="شماره صورتحساب:", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_idx, column=3, padx=5, pady=5, sticky="e")
        ctk.CTkEntry(info_frame, textvariable=self.invoice_number_var, font=self.base_font, justify="right", width=200).grid(row=row_idx, column=2, padx=5, pady=5, sticky="ew")
        
        # Issue Date
        ctk.CTkLabel(info_frame, text="تاریخ صدور:", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_idx, column=1, padx=5, pady=5, sticky="e")
        ctk.CTkEntry(info_frame, textvariable=self.issue_date_var, font=self.base_font, justify="right", width=200).grid(row=row_idx, column=0, padx=5, pady=5, sticky="ew")
        
        row_idx += 1

        # Customer Name (read-only from contract)
        ctk.CTkLabel(info_frame, text="مشتری:", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_idx, column=3, padx=5, pady=5, sticky="e")
        ctk.CTkEntry(info_frame, textvariable=self.customer_name_var, font=self.base_font, justify="right", width=200, state="readonly").grid(row=row_idx, column=2, padx=5, pady=5, sticky="ew")

        # Due Date
        ctk.CTkLabel(info_frame, text="تاریخ سررسید:", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_idx, column=1, padx=5, pady=5, sticky="e")
        ctk.CTkEntry(info_frame, textvariable=self.due_date_var, font=self.base_font, justify="right", width=200).grid(row=row_idx, column=0, padx=5, pady=5, sticky="ew")

        row_idx += 1

        # Contract Details (read-only)
        ctk.CTkLabel(info_frame, text="قرارداد مربوطه:", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_idx, column=3, padx=5, pady=5, sticky="e")
        ctk.CTkLabel(info_frame, text=f"{self.selected_contract.contract_number} - {self.selected_contract.title}", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_idx, column=2, padx=5, pady=5, sticky="ew")

        # Invoice Template (read-only)
        ctk.CTkLabel(info_frame, text="قالب صورتحساب:", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_idx, column=1, padx=5, pady=5, sticky="e")
        ctk.CTkLabel(info_frame, text=self.selected_invoice_template.template_name, font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_idx, column=0, padx=5, pady=5, sticky="ew")

        row_idx += 1

        # Description
        ctk.CTkLabel(info_frame, text="توضیحات کلی:", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_idx, column=3, padx=5, pady=5, sticky="ne")
        self.description_textbox = ctk.CTkTextbox(info_frame, height=60, font=self.base_font, wrap="word", width=400)
        self.description_textbox.grid(row=row_idx, column=0, columnspan=3, padx=5, pady=5, sticky="ew")

        # --- Invoice Items Frame ---
        items_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        items_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        items_frame.grid_rowconfigure(1, weight=1) # Treeview
        items_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(items_frame, text="آیتم‌های صورتحساب:", font=self.heading_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=0, column=0, columnspan=5, padx=5, pady=5, sticky="ew")

        # Item input fields
        item_input_frame = ctk.CTkFrame(items_frame, fg_color="transparent")
        item_input_frame.grid(row=0, column=0, columnspan=5, sticky="ew")
        item_input_frame.grid_columnconfigure((0,1,2,3,4), weight=1)

        ctk.CTkLabel(item_input_frame, text="خدمت/کالا:", font=self.base_font).grid(row=0, column=4, padx=5)
        self.service_dropdown = ctk.CTkComboBox(item_input_frame, values=[], variable=self.current_item_service_var, font=self.base_font, justify="right", command=self.on_service_selected)
        self.service_dropdown.grid(row=0, column=3, padx=5, sticky="ew")

        ctk.CTkLabel(item_input_frame, text="تعداد:", font=self.base_font).grid(row=0, column=2, padx=5)
        self.quantity_entry = ctk.CTkEntry(item_input_frame, textvariable=self.current_item_quantity_var, font=self.base_font, justify="right")
        self.quantity_entry.grid(row=0, column=1, padx=5, sticky="ew")
        self.quantity_entry.bind("<KeyRelease>", self.calculate_item_total)

        ctk.CTkLabel(item_input_frame, text="قیمت واحد:", font=self.base_font).grid(row=1, column=4, padx=5)
        self.unit_price_entry = ctk.CTkEntry(item_input_frame, textvariable=self.current_item_unit_price_var, font=self.base_font, justify="right")
        self.unit_price_entry.grid(row=1, column=3, padx=5, sticky="ew")
        self.unit_price_entry.bind("<KeyRelease>", self.format_amount_input)
        self.unit_price_entry.bind("<KeyRelease>", lambda e: self.calculate_item_total(e)) # Recalculate on price change

        ctk.CTkLabel(item_input_frame, text="مبلغ کل آیتم:", font=self.base_font).grid(row=1, column=2, padx=5)
        ctk.CTkEntry(item_input_frame, textvariable=self.current_item_total_price_var, font=self.base_font, justify="right", state="readonly").grid(row=1, column=1, padx=5, sticky="ew")

        add_item_btn = ctk.CTkButton(item_input_frame, text="اضافه/ویرایش آیتم", font=self.button_font, command=self.add_or_update_invoice_item)
        add_item_btn.grid(row=1, column=0, padx=5, pady=5, sticky="ew")


        # Treeview for invoice items
        self.invoice_items_tree = ttk.Treeview(items_frame, columns=("Service", "Quantity", "UnitPrice", "TotalPrice"), show="headings")
        self.invoice_items_tree.heading("Service", text="خدمت/کالا", anchor="e")
        self.invoice_items_tree.heading("Quantity", text="تعداد", anchor="e")
        self.invoice_items_tree.heading("UnitPrice", text="قیمت واحد", anchor="e")
        self.invoice_items_tree.heading("TotalPrice", text="مبلغ کل", anchor="e")

        self.invoice_items_tree.column("Service", width=250, anchor="e", stretch=True)
        self.invoice_items_tree.column("Quantity", width=80, anchor="e", stretch=False)
        self.invoice_items_tree.column("UnitPrice", width=120, anchor="e", stretch=False)
        self.invoice_items_tree.column("TotalPrice", width=120, anchor="e", stretch=False)
        self.invoice_items_tree.grid(row=2, column=0, columnspan=5, sticky="nsew", padx=5, pady=5)
        self.invoice_items_tree.bind("<<TreeviewSelect>>", self.on_item_select)

        # Treeview Scrollbar
        item_tree_scrollbar = ctk.CTkScrollbar(items_frame, command=self.invoice_items_tree.yview)
        item_tree_scrollbar.grid(row=2, column=5, sticky="ns", padx=(0,5), pady=5)
        self.invoice_items_tree.configure(yscrollcommand=item_tree_scrollbar.set)

        # --- Totals and Action Buttons ---
        totals_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        totals_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        totals_frame.grid_columnconfigure((0,1,2,3), weight=1) # Evenly distribute cols

        ctk.CTkLabel(totals_frame, text="جمع آیتم‌ها:", font=self.base_font).grid(row=0, column=3, padx=5, sticky="e")
        ctk.CTkEntry(totals_frame, textvariable=self.total_amount_var, font=self.base_font, justify="right", state="readonly", width=150).grid(row=0, column=2, padx=5, sticky="ew")

        ctk.CTkLabel(totals_frame, text="درصد تخفیف:", font=self.base_font).grid(row=1, column=3, padx=5, sticky="e")
        self.discount_entry = ctk.CTkEntry(totals_frame, textvariable=self.discount_percentage_var, font=self.base_font, justify="right", width=150) # Added reference
        self.discount_entry.grid(row=1, column=2, padx=5, sticky="ew")
        self.discount_entry.bind("<KeyRelease>", self.calculate_final_amount)

        ctk.CTkLabel(totals_frame, text="درصد مالیات:", font=self.base_font).grid(row=2, column=3, padx=5, sticky="e")
        tax_entry = ctk.CTkEntry(totals_frame, textvariable=self.tax_percentage_var, font=self.base_font, justify="right", width=150)
        tax_entry.grid(row=2, column=2, padx=5, sticky="ew")
        tax_entry.bind("<KeyRelease>", self.calculate_final_amount)

        ctk.CTkLabel(totals_frame, text="مبلغ نهایی:", font=self.heading_font, text_color=self.ui_colors["accent_blue"]).grid(row=3, column=3, padx=5, sticky="e")
        ctk.CTkEntry(totals_frame, textvariable=self.final_amount_var, font=self.heading_font, justify="right", state="readonly", width=150, text_color=self.ui_colors["accent_blue"]).grid(row=3, column=2, padx=5, sticky="ew")


        # Action Buttons
        button_frame = ctk.CTkFrame(totals_frame, fg_color="transparent")
        button_frame.grid(row=4, column=0, columnspan=4, pady=10, sticky="e")

        clear_btn = ctk.CTkButton(button_frame, text="جدید", font=self.button_font, command=self.clear_invoice_form, fg_color="#999999", hover_color="#777777")
        clear_btn.pack(side="right", padx=5)

        preview_btn = ctk.CTkButton(button_frame, text="پیش‌نمایش", font=self.button_font, command=self.preview_invoice, fg_color="#28a745", hover_color="#218838")
        preview_btn.pack(side="right", padx=5)
        
        save_print_btn = ctk.CTkButton(button_frame, text="ذخیره و پرینت", font=self.button_font, command=self.save_and_print_invoice, fg_color=self.ui_colors["accent_blue"], hover_color=self.ui_colors["accent_blue_hover"])
        save_print_btn.pack(side="right", padx=5)

    def load_initial_data(self):
        # Load Customer object from selected_contract.customer_id
        customer_obj, _ = self.customer_manager.get_customer_by_id(self.selected_contract.customer_id)
        if customer_obj:
            self.customer_obj = customer_obj
            self.customer_name_var.set(customer_obj.name)
        else:
            messagebox.showerror("خطا", "اطلاعات مشتری مربوط به قرارداد یافت نشد.", master=self)
            self.destroy() # بستن پنجره اگر مشتری پیدا نشد

        # Load Services for item dropdown
        services, _ = self.service_manager.get_all_services()
        services.sort(key=lambda s: s.description)
        service_descriptions = []
        self.service_data_map = {}
        for svc in services:
            service_descriptions.append(svc.description)
            self.service_data_map[svc.description] = svc
        self.service_dropdown.configure(values=service_descriptions)
        if service_descriptions:
            self.current_item_service_var.set(service_descriptions[0])
            self.on_service_selected(service_descriptions[0])
        else:
            messagebox.showwarning("هشدار", "هیچ خدمتی در دیتابیس ثبت نشده است. لطفاً خدمات را در بخش مربوطه ثبت کنید.", master=self)

        # Set contract description as initial invoice description
        if self.selected_contract.description:
            self.description_textbox.insert("1.0", self.selected_contract.description)
        
        # Set total amount from contract as initial suggestion
        if self.selected_contract.total_amount is not None: # بررسی برای None بودن
            self.total_amount_var.set(f"{int(self.selected_contract.total_amount):,}")
            self.calculate_final_amount()

    def apply_template_settings(self):
        """ اعمال تنظیمات پیش‌فرض و قوانین قالب انتخاب شده به فرم صورتحساب. """
        if self.selected_invoice_template and self.selected_invoice_template.template_settings: # تغییر نام default_settings به template_settings
            # تنظیمات پیش‌فرض (مثل tax_percentage, discount_editable) در یک کلید 'default_settings' در template_settings قرار دارند
            default_settings = self.selected_invoice_template.template_settings.get('default_settings', {}) # اضافه شد: get('default_settings', {})
            
            # اعمال درصد مالیات
            if "tax_percentage" in default_settings:
                try:
                    tax_percent_val = default_settings["tax_percentage"]
                    self.tax_percentage_var.set(str(tax_percent_val) if tax_percent_val is not None else "9") # اطمینان از رشته بودن
                except ValueError:
                    pass # Invalid tax percentage in template

            # اعمال درصد تخفیف (اگر قابل ویرایش نیست، غیرفعال شود)
            if "discount_percentage" in default_settings:
                try:
                    discount_percent_val = default_settings["discount_percentage"]
                    self.discount_percentage_var.set(str(discount_percent_val) if discount_percent_val is not None else "0") # اطمینان از رشته بودن
                except ValueError:
                    pass

            if "discount_editable" in default_settings:
                if not default_settings["discount_editable"]:
                    self.discount_entry.configure(state="readonly")
                    self.discount_percentage_var.set("0") # اگر قابل ویرایش نیست، صفر شود
                else:
                    self.discount_entry.configure(state="normal")
            
            self.calculate_final_amount() # محاسبه مجدد پس از اعمال تنظیمات قالب

        # TODO: پیاده‌سازی منطق نمایش/پنهان کردن فیلدها بر اساس self.selected_invoice_template.required_fields


    def on_service_selected(self, choice):
        # Populate unit price if a service has a default price (not implemented yet)
        self.calculate_item_total()

    def calculate_item_total(self, event=None):
        try:
            quantity_str = self.quantity_entry.get().replace(",", "")
            quantity = float(quantity_str) if quantity_str else 0.0 # اگر خالی بود، 0.0 در نظر بگیر

            unit_price_str = self.unit_price_entry.get().replace(",", "")
            unit_price = float(unit_price_str) if unit_price_str else 0.0 # اگر خالی بود، 0.0 در نظر بگیر
            
            total = quantity * unit_price
            self.current_item_total_price_var.set(f"{int(total):,}")
            self.calculate_final_amount() # Recalculate invoice totals when item changes
        except ValueError:
            self.current_item_total_price_var.set("0")
            # messagebox.showwarning("خطای ورودی", "تعداد و قیمت واحد باید اعداد معتبر باشند.", master=self) # Commented out to avoid repetitive popups


    def format_amount_input(self, event=None):
        """ فرمت کردن ورودی مبلغ به صورت سه رقم سه رقم جدا شده (برای قیمت واحد) """
        current_text = self.unit_price_entry.get().replace(",", "")
        if not current_text:
            return
        
        try:
            numeric_value = int("".join(filter(str.isdigit, current_text)))
            formatted_value = f"{numeric_value:,}"
            self.unit_price_entry.delete(0, ctk.END)
            self.unit_price_entry.insert(0, formatted_value)
            # cursor position might need adjustment for better UX
        except ValueError:
            pass


    def add_or_update_invoice_item(self):
        service_description = self.current_item_service_var.get()
        quantity_str = self.current_item_quantity_var.get().replace(",", "")
        unit_price_str = self.current_item_unit_price_var.get().replace(",", "")

        if not service_description or not quantity_str or not unit_price_str:
            messagebox.showwarning("خطای ورودی", "لطفاً خدمت/کالا، تعداد و قیمت واحد را پر کنید.", master=self)
            return

        try:
            service_obj = self.service_data_map.get(service_description)
            if not service_obj:
                messagebox.showerror("خطا", "خدمت/کالای انتخاب شده نامعتبر است.", master=self)
                return
            
            quantity = float(quantity_str)
            unit_price = float(unit_price_str)
            total_price = quantity * unit_price

            # Check if this item is already in the list (for update)
            existing_item_index = -1
            selected_item_iid = self.invoice_items_tree.focus()
            if selected_item_iid: # If an item is selected, assume update
                try:
                    existing_item_index = int(selected_item_iid)
                except ValueError:
                    pass # Not a valid index for update
            
            new_item = InvoiceItem(
                service_id=service_obj.id,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price
            )

            if 0 <= existing_item_index < len(self.invoice_items_list):
                self.invoice_items_list[existing_item_index] = new_item
                self.invoice_items_tree.item(selected_item_iid, values=(
                    service_description,
                    f"{quantity:g}",
                    f"{int(unit_price):,}",
                    f"{int(total_price):,}"
                ))
            else:
                # Assign a temporary unique ID (index in list) for treeview management for new items
                new_item.id = len(self.invoice_items_list) 
                self.invoice_items_list.append(new_item)
                self.invoice_items_tree.insert("", "end", iid=str(new_item.id), values=(
                    service_description,
                    f"{quantity:g}",
                    f"{int(unit_price):,}",
                    f"{int(total_price):,}"
                ))
            
            self.clear_item_fields()
            self.calculate_final_amount()

        except ValueError:
            messagebox.showerror("خطای ورودی", "تعداد و قیمت واحد باید اعداد معتبر باشند.", master=self)

    def clear_item_fields(self):
        self.current_item_service_var.set(self.service_dropdown.cget("values")[0] if self.service_dropdown.cget("values") else "")
        self.current_item_quantity_var.set("0") # مقدار پیش‌فرض "0"
        self.current_item_unit_price_var.set("0") # مقدار پیش‌فرض "0"
        self.current_item_total_price_var.set("0")
        self.invoice_items_tree.selection_remove(self.invoice_items_tree.focus()) # Deselect current item

    def on_item_select(self, event):
        selected_item = self.invoice_items_tree.focus()
        if selected_item:
            # item_values = self.invoice_items_tree.item(selected_item, "values")
            # For simplicity, we just select the item.
            # Populating fields for editing could be added here if needed.
            pass


    def calculate_final_amount(self, event=None):
        total_items_amount = sum(item.total_price for item in self.invoice_items_list)
        self.total_amount_var.set(f"{int(total_items_amount):,}")

        try:
            discount_percent_str = self.discount_percentage_var.get().replace(",", "")
            discount_percent = float(discount_percent_str) if discount_percent_str else 0.0 # اگر خالی بود، 0.0 در نظر بگیر
            
            tax_percent_str = self.tax_percentage_var.get().replace(",", "")
            tax_percent = float(tax_percent_str) if tax_percent_str else 0.0 # اگر خالی بود، 0.0 در نظر بگیر
        except ValueError:
            messagebox.showwarning("خطای ورودی", "درصد تخفیف و مالیات باید اعداد باشند.", master=self)
            self.final_amount_var.set("0")
            return

        discount_amount = total_items_amount * (discount_percent / 100)
        amount_after_discount = total_items_amount - discount_amount
        tax_amount = amount_after_discount * (tax_percent / 100)
        
        final_amount = amount_after_discount + tax_amount
        self.final_amount_var.set(f"{int(final_amount):,}")

    def clear_invoice_form(self):
        # self.selected_invoice_id = None # این برای ویرایش یک فاکتور موجود است
        self.invoice_number_var.set("")
        self.issue_date_var.set(jdatetime.date.today().strftime("%Y/%m/%d"))
        self.due_date_var.set("----/--/--")
        # self.customer_name_var.set(self.customer_obj.name) # از load_initial_data پر می‌شود
        self.description_textbox.delete("1.0", "end")
        # اگر در قرارداد توضیحات بود، اینجا دوباره پرش کن
        if self.selected_contract and self.selected_contract.description:
            self.description_textbox.insert("1.0", self.selected_contract.description)

        # از template_settings برای مقادیر پیش فرض استفاده کن
        self.apply_template_settings() 
        
        self.invoice_items_list = []
        self.update_invoice_items_treeview()
        self.clear_item_fields()
        self.calculate_final_amount() # Recalculate totals after clearing items

    def update_invoice_items_treeview(self):
        for item in self.invoice_items_tree.get_children():
            self.invoice_items_tree.delete(item)
        
        for idx, item in enumerate(self.invoice_items_list):
            service_description = self.settings_manager.get_service_description_by_id(item.service_id)
            if not service_description:
                service_description = "خدمت نامشخص" # Fallback if service not found
            self.invoice_items_tree.insert("", "end", iid=str(idx), values=(
                service_description,
                f"{item.quantity:g}",
                f"{int(item.unit_price):,}",
                f"{int(item.total_price):,}"
            ))

    def _get_invoice_data_from_ui(self):
        # Gather all data from UI and validate
        invoice_number = self.invoice_number_var.get().strip()
        issue_date = self.issue_date_var.get().strip()
        due_date = self.due_date_var.get().strip() if self.due_date_var.get().strip() != "----/--/--" else None
        description = self.description_textbox.get("1.0", "end").strip()
        
        discount_percent_str = self.discount_percentage_var.get().replace(",", "")
        tax_percent_str = self.tax_percentage_var.get().replace(",", "")
        final_amount_str = self.final_amount_var.get().replace(",", "")
        total_amount_str = self.total_amount_var.get().replace(",", "")

        if not invoice_number:
            messagebox.showwarning("خطای ورودی", "شماره صورتحساب نمی‌تواند خالی باشد.", master=self)
            return None, None

        if not issue_date or issue_date == "----/--/--":
            messagebox.showwarning("خطای ورودی", "تاریخ صدور نمی‌تواند خالی باشد.", master=self)
            return None, None
        try: jdatetime.datetime.strptime(issue_date, "%Y/%m/%d")
        except ValueError:
            messagebox.showwarning("خطای ورودی", "فرمت تاریخ صدور باید سال/ماه/روز (مثال: 1402/01/01) باشد.", master=self)
            return None, None

        if due_date:
            try: jdatetime.datetime.strptime(due_date, "%Y/%m/%d")
            except ValueError:
                messagebox.showwarning("خطای ورودی", "فرمت تاریخ سررسید باید سال/ماه/روز باشد.", master=self)
                return None, None

        if not self.customer_obj:
            messagebox.showwarning("خطا", "اطلاعات مشتری در دسترس نیست.", master=self)
            return None, None
        
        if not self.invoice_items_list:
            messagebox.showwarning("خطای ورودی", "لطفاً حداقل یک آیتم به صورتحساب اضافه کنید.", master=self)
            return None, None

        try:
            # اطمینان از تبدیل ایمن به float
            discount_percentage = float(discount_percent_str) if discount_percent_str else 0.0
            tax_percentage = float(tax_percent_str) if tax_percent_str else 0.0
            total_amount = float(total_amount_str) if total_amount_str else 0.0
            final_amount = float(final_amount_str) if final_amount_str else 0.0
        except ValueError:
            messagebox.showwarning("خطای ورودی", "مبالغ و درصدها باید اعداد معتبر باشند.", master=self)
            return None, None

        invoice = Invoice(
            invoice_number=invoice_number,
            customer_id=self.customer_obj.id,
            contract_id=self.selected_contract.id, # اضافه شده: لینک به قرارداد
            issue_date=issue_date,
            due_date=due_date,
            total_amount=total_amount,
            discount_percentage=discount_percentage,
            tax_percentage=tax_percentage,
            final_amount=final_amount,
            description=description
        )

        return invoice, self.customer_obj


    def preview_invoice(self):
        invoice, customer = self._get_invoice_data_from_ui()
        if not invoice or not customer:
            return

        # Generate PDF
        temp_pdf_path = os.path.join(os.getcwd(), "temp_invoice_preview.pdf")
        success, _ = self.invoice_generator.create_invoice_pdf(invoice, customer, self.invoice_items_list, temp_pdf_path, self.selected_invoice_template) # اضافه شد: ارسال قالب

        if success:
            try:
                if sys.platform == "win32":
                    os.startfile(temp_pdf_path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", temp_pdf_path])
                else:
                    subprocess.run(["xdg-open", temp_pdf_path])
            except Exception as e:
                messagebox.showerror("خطا در باز کردن پیش‌نمایش", f"فایل پیش‌نمایش تولید شد اما در باز کردن آن خطا رخ داد: {e}", master=self)
        else:
            messagebox.showerror("خطا در تولید پیش‌نمایش", "خطا در تولید فایل PDF پیش‌نمایش.", master=self)


    def save_and_print_invoice(self):
        invoice, customer = self._get_invoice_data_from_ui()
        if not invoice or not customer:
            return
        
        # Save invoice to database
        save_success, save_message = self.invoice_manager.add_invoice(invoice, self.invoice_items_list)
        if not save_success:
            messagebox.showerror("خطا در ذخیره صورتحساب", save_message, master=self)
            return

        output_dir = os.path.join(os.path.expanduser("~"), "Documents", "EasyInvoice_Invoices")
        os.makedirs(output_dir, exist_ok=True)
        pdf_filename = f"Invoice_{invoice.invoice_number}_{invoice.issue_date.replace('/', '-')}.pdf"
        full_pdf_path = os.path.join(output_dir, pdf_filename)

        generate_success, _ = self.invoice_generator.create_invoice_pdf(invoice, customer, self.invoice_items_list, full_pdf_path, self.selected_invoice_template) # اضافه شد: ارسال قالب

        if generate_success:
            messagebox.showinfo("موفقیت", f"صورتحساب با موفقیت در مسیر\n{full_pdf_path}\nذخیره و به پرینتر ارسال شد.", master=self)
            try:
                if sys.platform == "win32":
                    os.startfile(full_pdf_path, "print")
                elif sys.platform == "darwin":
                    subprocess.run(["lp", full_pdf_path])
                else:
                    subprocess.run(["lpr", full_pdf_path])
            except Exception as e:
                messagebox.showwarning("خطا در پرینت", f"صورتحساب ذخیره شد اما در ارسال به پرینتر خطا رخ داد: {e}", master=self)
            self.destroy() # بستن پنجره جزئیات بعد از ذخیره و پرینت
        else:
            messagebox.showerror("خطا در تولید PDF", "خطا در تولید فایل PDF صورتحساب.", master=self)