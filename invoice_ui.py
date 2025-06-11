# invoice_ui.py
import customtkinter as ctk
from tkinter import messagebox, filedialog, ttk
import os
import jdatetime
import sys
import subprocess

from db_manager import DBManager, DATABASE_NAME # برای تست مستقل
from customer_manager import CustomerManager
from service_manager import ServiceManager # اصلاح شد: services_manager به service_manager
from models import Invoice, InvoiceItem, Customer, Service
from settings_manager import SettingsManager # برای پاس دادن به InvoiceGenerator
from invoice_generator import InvoiceGenerator

class InvoiceUI(ctk.CTkFrame):
    def __init__(self, parent, db_manager, ui_colors, base_font, heading_font, button_font, nav_button_font):
        super().__init__(parent, fg_color="transparent")
        self.parent = parent
        self.db_manager = db_manager
        self.customer_manager = CustomerManager()
        self.service_manager = ServiceManager() # Instantiate ServiceManager
        self.settings_manager = SettingsManager() # Instantiate SettingsManager
        self.invoice_generator = InvoiceGenerator(self.settings_manager)

        self.ui_colors = ui_colors
        self.base_font = base_font
        self.heading_font = heading_font
        self.button_font = button_font
        self.nav_button_font = nav_button_font

        self.selected_invoice_id = None
        self.customer_data_map = {} # {customer_name: customer_id}
        self.service_data_map = {} # {service_description: service_id}

        # Invoice Variables
        self.invoice_number_var = ctk.StringVar()
        self.issue_date_var = ctk.StringVar(value=jdatetime.date.today().strftime("%Y/%m/%d"))
        self.due_date_var = ctk.StringVar(value="----/--/--") # Optional due date
        self.customer_dropdown_var = ctk.StringVar()
        self.description_textbox = None
        self.discount_percentage_var = ctk.StringVar(value="0")
        self.tax_percentage_var = ctk.StringVar(value="9") # Default VAT
        self.total_amount_var = ctk.StringVar(value="0") # Sum of items
        self.final_amount_var = ctk.StringVar(value="0") # total - discount + tax

        # Invoice Items
        self.invoice_items_tree = None
        self.invoice_items_list = [] # List of InvoiceItem objects in UI
        self.current_item_service_var = ctk.StringVar()
        self.current_item_quantity_var = ctk.StringVar()
        self.current_item_unit_price_var = ctk.StringVar()
        self.current_item_total_price_var = ctk.StringVar(value="0")


        self.create_widgets()
        self.load_customer_and_service_data()
        self.clear_invoice_form()


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

        # Customer Dropdown
        ctk.CTkLabel(info_frame, text="مشتری:", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_idx, column=3, padx=5, pady=5, sticky="e")
        self.customer_dropdown = ctk.CTkComboBox(info_frame, values=[], variable=self.customer_dropdown_var, font=self.base_font, justify="right", width=200, command=self.on_customer_selected)
        self.customer_dropdown.grid(row=row_idx, column=2, padx=5, pady=5, sticky="ew")

        # Due Date
        ctk.CTkLabel(info_frame, text="تاریخ سررسید:", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_idx, column=1, padx=5, pady=5, sticky="e")
        ctk.CTkEntry(info_frame, textvariable=self.due_date_var, font=self.base_font, justify="right", width=200).grid(row=row_idx, column=0, padx=5, pady=5, sticky="ew")

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
        self.unit_price_entry.bind("<KeyRelease>", self.calculate_item_total)

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
        discount_entry = ctk.CTkEntry(totals_frame, textvariable=self.discount_percentage_var, font=self.base_font, justify="right", width=150)
        discount_entry.grid(row=1, column=2, padx=5, sticky="ew")
        discount_entry.bind("<KeyRelease>", self.calculate_final_amount)

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

    def load_customer_and_service_data(self):
        # Load Customers
        customers, _ = self.customer_manager.get_all_customers()
        customers.sort(key=lambda c: c.name)
        customer_names = []
        self.customer_data_map = {}
        for cust in customers:
            customer_names.append(cust.name)
            self.customer_data_map[cust.name] = cust
        self.customer_dropdown.configure(values=customer_names)
        if customer_names:
            self.customer_dropdown_var.set(customer_names[0])
            self.on_customer_selected(customer_names[0])

        # Load Services
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

    def on_customer_selected(self, choice):
        # You can add logic here to load customer-specific info if needed
        pass

    def on_service_selected(self, choice):
        # Populate unit price if a service has a default price (not implemented yet)
        # For now, just ensure current_item_total_price_var is updated on quantity/price changes
        self.calculate_item_total()

    def calculate_item_total(self, event=None):
        try:
            quantity = float(self.quantity_entry.get().replace(",", "") or 0)
            unit_price = float(self.unit_price_entry.get().replace(",", "") or 0)
            total = quantity * unit_price
            self.current_item_total_price_var.set(f"{int(total):,}")
            self.calculate_final_amount() # Recalculate invoice totals when item changes
        except ValueError:
            self.current_item_total_price_var.set("0")

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
            existing_item_id = None
            selected_item_iid = self.invoice_items_tree.focus()
            if selected_item_iid: # If an item is selected, assume update
                # Find the actual InvoiceItem object
                for idx, item in enumerate(self.invoice_items_list):
                    if str(item.id) == selected_item_iid: # item.id is set when loaded from DB, for new items it's None
                        existing_item_id = idx
                        break
                
                # If it's a new item added to tree, its iid is its index
                if existing_item_id is None:
                     try: existing_item_id = int(selected_item_iid)
                     except ValueError: pass

            new_item = InvoiceItem(
                service_id=service_obj.id,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price
            )

            if existing_item_id is not None and existing_item_id < len(self.invoice_items_list):
                self.invoice_items_list[existing_item_id] = new_item
                self.invoice_items_tree.item(selected_item_iid, values=(
                    service_description,
                    f"{quantity:g}",
                    f"{int(unit_price):,}",
                    f"{int(total_price):,}"
                ))
            else:
                # Assign a temporary unique ID for treeview management for new items
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
        self.current_item_quantity_var.set("")
        self.current_item_unit_price_var.set("")
        self.current_item_total_price_var.set("0")
        self.invoice_items_tree.selection_remove(self.invoice_items_tree.focus()) # Deselect current item

    def on_item_select(self, event):
        selected_item = self.invoice_items_tree.focus()
        if selected_item:
            item_values = self.invoice_items_tree.item(selected_item, "values")
            self.current_item_service_var.set(item_values[0])
            self.current_item_quantity_var.set(item_values[1])
            self.current_item_unit_price_var.set(item_values[2])
            self.current_item_total_price_var.set(item_values[3])

    def calculate_final_amount(self, event=None):
        total_items_amount = sum(item.total_price for item in self.invoice_items_list)
        self.total_amount_var.set(f"{int(total_items_amount):,}")

        try:
            discount_percent = float(self.discount_percentage_var.get().replace(",", "") or 0)
            tax_percent = float(self.tax_percentage_var.get().replace(",", "") or 0)
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
        self.selected_invoice_id = None
        self.invoice_number_var.set("")
        self.issue_date_var.set(jdatetime.date.today().strftime("%Y/%m/%d"))
        self.due_date_var.set("----/--/--")
        self.customer_dropdown_var.set(self.customer_dropdown.cget("values")[0] if self.customer_dropdown.cget("values") else "")
        self.description_textbox.delete("1.0", "end")
        self.discount_percentage_var.set("0")
        self.tax_percentage_var.set("9")
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
        customer_name = self.customer_dropdown_var.get()
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

        selected_customer = self.customer_data_map.get(customer_name)
        if not selected_customer:
            messagebox.showwarning("خطای ورودی", "لطفاً یک مشتری را انتخاب کنید.", master=self)
            return None, None
        
        if not self.invoice_items_list:
            messagebox.showwarning("خطای ورودی", "لطفاً حداقل یک آیتم به صورتحساب اضافه کنید.", master=self)
            return None, None

        try:
            discount_percentage = float(discount_percent_str)
            tax_percentage = float(tax_percent_str)
            total_amount = float(total_amount_str)
            final_amount = float(final_amount_str)
        except ValueError:
            messagebox.showwarning("خطای ورودی", "مبالغ و درصدها باید اعداد معتبر باشند.", master=self)
            return None, None

        invoice = Invoice(
            id=self.selected_invoice_id,
            invoice_number=invoice_number,
            customer_id=selected_customer.id,
            issue_date=issue_date,
            due_date=due_date,
            total_amount=total_amount,
            discount_percentage=discount_percentage,
            tax_percentage=tax_percentage,
            final_amount=final_amount,
            description=description
        )

        return invoice, selected_customer


    def preview_invoice(self):
        invoice, customer = self._get_invoice_data_from_ui()
        if not invoice or not customer:
            return

        # Generate PDF
        temp_pdf_path = os.path.join(os.getcwd(), "temp_invoice_preview.pdf")
        success, message = self.invoice_generator.create_invoice_pdf(invoice, customer, self.invoice_items_list, temp_pdf_path)

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
            messagebox.showerror("خطا در تولید پیش‌نمایش", message, master=self)


    def save_and_print_invoice(self):
        # This part requires saving the invoice to the DB first
        # For simplicity, we'll just generate and print the PDF here
        # A full implementation would involve:
        # 1. Saving Invoice to Invoices table
        # 2. Saving InvoiceItems to InvoiceItems table (linking to new invoice ID)
        # 3. Generating and printing PDF

        invoice, customer = self._get_invoice_data_from_ui()
        if not invoice or not customer:
            return
        
        # Here you would typically save the invoice and items to the database
        # For this example, we'll skip DB save and just generate PDF
        # In a real app, you'd insert the invoice, get its ID, then insert items.

        output_dir = os.path.join(os.path.expanduser("~"), "Documents", "EasyInvoice_Invoices")
        os.makedirs(output_dir, exist_ok=True)
        pdf_filename = f"Invoice_{invoice.invoice_number}_{invoice.issue_date.replace('/', '-')}.pdf"
        full_pdf_path = os.path.join(output_dir, pdf_filename)

        success, message = self.invoice_generator.create_invoice_pdf(invoice, customer, self.invoice_items_list, full_pdf_path)

        if success:
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
            self.clear_invoice_form()
        else:
            messagebox.showerror("خطا در ذخیره و پرینت", message, master=self)


# --- بلاک تست مستقل UI ---
if __name__ == "__main__":
    root = ctk.CTk()
    root.title("صدور صورتحساب EasyInvoice (تست مستقل)")
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


    temp_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATABASE_NAME)
    temp_db_manager = DBManager(temp_db_path)
    
    if temp_db_manager.connect():
        temp_db_manager.create_tables()
        temp_db_manager.migrate_database()
        temp_db_manager.close()
    
    # Ensure there are some customers and services for testing
    from customer_manager import CustomerManager
    from service_manager import ServiceManager # اصلاح شد: services_manager به service_manager
    from models import Customer, Service, AppSettings

    cust_man = CustomerManager()
    svc_man = ServiceManager()
    
    # Add dummy customer if not exists
    if not cust_man.get_all_customers()[0]:
        cust_man.add_customer(Customer(customer_code=1001, name="شرکت تست فاکتور", customer_type="حقوقی", tax_id="11223344556", email="invoice_test@example.com", address="خیابان نمونه، پلاک 10"))
        cust_man.add_customer(Customer(customer_code=1002, name="آقای تستی فاکتور", customer_type="حقیقی", tax_id="0001112223", mobile="09121234567"))
    
    # Add dummy services if not exists
    if not svc_man.get_all_services()[0]:
        svc_man.add_service(Service(service_code=201, description="طراحی UI/UX"))
        svc_man.add_service(Service(service_code=202, description="توسعه بک‌اند"))
        svc_man.add_service(Service(service_code=203, description="مشاوره فناوری اطلاعات"))
    
    # Add dummy settings if not exists (for seller info and logo)
    settings_man = SettingsManager()
    current_settings = settings_man.get_settings()
    if not current_settings.seller_name:
        dummy_settings = AppSettings(
            seller_name="شرکت آسان‌فاکتور",
            seller_address="تهران، میدان آزادی، دفتر 5",
            seller_phone="021-88888888",
            seller_tax_id="1234567890",
            seller_economic_code="9876543",
            seller_logo_path="" # Or provide a real path for testing logo
        )
        settings_man.save_settings(dummy_settings)


    invoice_ui_frame = InvoiceUI(root, temp_db_manager, test_ui_colors, base_font_tuple, heading_font_tuple, button_font_tuple, nav_button_font_tuple)
    invoice_ui_frame.pack(fill="both", expand=True)

    root.mainloop()