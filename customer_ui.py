# customer_ui.py
import customtkinter as ctk
from tkinter import messagebox, ttk
import os
from datetime import datetime

from customer_manager import CustomerManager
from models import Customer
from db_manager import DBManager, DATABASE_NAME

class CustomerUI(ctk.CTkFrame):
    def __init__(self, parent, db_manager, ui_colors, base_font, heading_font, button_font, nav_button_font):
        super().__init__(parent, fg_color="transparent")
        self.parent = parent
        self.db_manager = db_manager
        self.customer_manager = CustomerManager()
        self.ui_colors = ui_colors
        self.base_font = base_font
        self.heading_font = heading_font
        self.button_font = button_font
        self.nav_button_font = nav_button_font

        self.frames = {}
        self.selected_customer_id = None
        self.delete_customer_button = None

        # متغیرهای مربوط به فرم مشتری
        self.customer_code_var = ctk.StringVar()
        self.customer_name_var = ctk.StringVar()
        self.customer_type_var = ctk.StringVar(value="حقوقی") # پیش‌فرض: حقوقی
        self.address_var = ctk.StringVar()
        self.phone_var = ctk.StringVar()
        self.phone2_var = ctk.StringVar()
        self.mobile_var = ctk.StringVar()
        self.email_var = ctk.StringVar()
        self.tax_id_var = ctk.StringVar()
        self.postal_code_var = ctk.StringVar()
        self.notes_var = ctk.StringVar()

        self.tax_id_label = None # برای تغییر متن لیبل
        
        # متغیرها و ویجت‌های مربوط به جستجو/فیلتر
        self.filter_entries = {} # دیکشنری برای نگهداری Entry های فیلتر
        self.filter_vars = {} # دیکشنری برای نگهداری StringVar های فیلتر
        self.filter_row_frame = None # فریم نگهداری کننده Entry های فیلتر
        self.is_filter_row_visible = False


        self.create_widgets()
        
        self.current_active_sub_button = None
        self.current_active_sub_page_name = None
        
        self.after(100, lambda: self.on_sub_nav_button_click("new_customer", self.new_customer_btn))


    def create_widgets(self):
        """ ویجت‌های اصلی مربوط به مشتریان را ایجاد می‌کند. """
        customer_card_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=10, 
                                           border_width=1, border_color=self.ui_colors["border_gray"])
        customer_card_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        customer_card_frame.grid_rowconfigure(0, weight=0)
        customer_card_frame.grid_rowconfigure(1, weight=1)
        customer_card_frame.grid_columnconfigure(0, weight=1)

        self.sub_navbar_frame = ctk.CTkFrame(customer_card_frame, fg_color="white", corner_radius=0)
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
        
        self.new_customer_btn = ctk.CTkButton(sub_buttons_container, text="تعریف مشتری جدید",
                                               font=self.nav_button_font,
                                               fg_color=self.ui_colors["white"],
                                               text_color=self.ui_colors["text_medium_gray"],
                                               hover_color=self.ui_colors["hover_light_blue"],
                                               corner_radius=8,
                                               command=lambda: self.on_sub_nav_button_click("new_customer", self.new_customer_btn))
        self.new_customer_btn.grid(row=0, column=1, padx=5, pady=10)

        self.list_customers_btn = ctk.CTkButton(sub_buttons_container, text="لیست مشتریان",
                                                 font=self.nav_button_font,
                                                 fg_color=self.ui_colors["white"],
                                                 text_color=self.ui_colors["text_medium_gray"],
                                                 hover_color=self.ui_colors["hover_light_blue"],
                                                 corner_radius=8,
                                                 command=lambda: self.on_sub_nav_button_click("list_customers", self.list_customers_btn))
        self.list_customers_btn.grid(row=0, column=0, padx=5, pady=10)

        self.customer_content_frame = ctk.CTkFrame(customer_card_frame, fg_color="white")
        self.customer_content_frame.grid(row=1, column=0, padx=20, pady=(20, 20), sticky="nsew")
        self.customer_content_frame.grid_rowconfigure(0, weight=1)
        self.customer_content_frame.grid_columnconfigure(0, weight=1)

        self.new_customer_form = self.create_new_customer_form(self.customer_content_frame)
        self.frames["new_customer"] = self.new_customer_form
        self.new_customer_form.grid(row=0, column=0, sticky="nsew")

        self.list_customers_page = self.create_customers_list_table(self.customer_content_frame)
        self.frames["list_customers"] = self.list_customers_page
        self.list_customers_page.grid(row=0, column=0, sticky="nsew")

        self.show_sub_frame("new_customer")


    def create_new_customer_form(self, parent_frame):
        """ ایجاد فرم تعریف مشتری جدید """
        form_frame = ctk.CTkFrame(parent_frame, fg_color="white")
        form_frame.grid(row=0, column=0, sticky="nsew")
        parent_frame.grid_rowconfigure(0, weight=1)
        parent_frame.grid_columnconfigure(0, weight=1)

        form_inner_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        form_inner_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # دو ستون برای فیلدها
        form_inner_frame.grid_columnconfigure(0, weight=1) # ستون چپ (فیلد)
        form_inner_frame.grid_columnconfigure(1, weight=0) # ستون چپ (لیبل)
        form_inner_frame.grid_columnconfigure(2, weight=1) # ستون راست (فیلد)
        form_inner_frame.grid_columnconfigure(3, weight=0) # ستون راست (لیبل)

        # فیلدهای ستون راست
        labels_right_column = [
            ("کد مشتری", self.customer_code_var, "entry_readonly"),
            ("نام مشتری", self.customer_name_var, "entry"),
            ("نوع مشتری", self.customer_type_var, "radio"),
            ("شناسه ملی/شماره ملی", self.tax_id_var, "entry"), # لیبل این فیلد در on_customer_type_select تغییر می‌کند
            ("آدرس", self.address_var, "entry_singleline")
        ]

        # فیلدهای ستون چپ
        labels_left_column = [
            ("تلفن", self.phone_var, "entry"),
            ("تلفن2", self.phone2_var, "entry"),
            ("شماره همراه", self.mobile_var, "entry"),
            ("ایمیل", self.email_var, "entry"),
            ("کد پستی", self.postal_code_var, "entry"),
            ("سایر توضیحات", self.notes_var, "textbox")
        ]
        
        # ایجاد فیلدها در ستون راست
        # max_rows = max(len(labels_right_column), len(labels_left_column)) # این خط دیگه نیاز نیست، از row_index استفاده می کنیم

        for i, (label_text, var, field_type) in enumerate(labels_right_column):
            if label_text == "شناسه ملی/شماره ملی": # این لیبل نیاز به ارجاع مستقیم دارد
                self.tax_id_label = ctk.CTkLabel(form_inner_frame, text=label_text, font=self.base_font, text_color=self.ui_colors["text_dark_gray"])
                self.tax_id_label.grid(row=i, column=3, padx=10, pady=5, sticky="e")
            else:
                # حذف ":"
                ctk.CTkLabel(form_inner_frame, text=label_text.replace(":", ""),
                             font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=i, column=3, padx=10, pady=5, sticky="e")
            
            if field_type == "entry":
                entry = ctk.CTkEntry(form_inner_frame, textvariable=var, width=250, justify="right", 
                                     font=self.base_font, fg_color="#f8f8f8", border_color=self.ui_colors["border_gray"], corner_radius=5)
                entry.grid(row=i, column=2, padx=10, pady=5, sticky="ew")
            elif field_type == "entry_readonly":
                entry = ctk.CTkEntry(form_inner_frame, textvariable=var, width=250, justify="right", 
                                     font=self.base_font, fg_color="#f8f8f8", border_color=self.ui_colors["border_gray"], corner_radius=5, state="readonly")
                entry.grid(row=i, column=2, padx=10, pady=5, sticky="ew")
            elif field_type == "radio":
                type_frame = ctk.CTkFrame(form_inner_frame, fg_color="transparent")
                type_frame.grid(row=i, column=2, padx=10, pady=5, sticky="w")
                
                radio_corp = ctk.CTkRadioButton(type_frame, text="حقوقی", variable=self.customer_type_var, value="حقوقی", 
                                                font=self.base_font, text_color=self.ui_colors["text_dark_gray"],
                                                command=self.on_customer_type_select)
                radio_corp.pack(side="right", padx=10)
                
                radio_ind = ctk.CTkRadioButton(type_frame, text="حقیقی", variable=self.customer_type_var, value="حقیقی",
                                               font=self.base_font, text_color=self.ui_colors["text_dark_gray"],
                                               command=self.on_customer_type_select)
                radio_ind.pack(side="right", padx=10)
            elif field_type == "entry_singleline":
                 entry = ctk.CTkEntry(form_inner_frame, textvariable=var, width=250, justify="right", 
                                     font=self.base_font, fg_color="#f8f8f8", border_color=self.ui_colors["border_gray"], corner_radius=5)
                 entry.grid(row=i, column=2, padx=10, pady=5, sticky="ew")

        # ایجاد فیلدها در ستون چپ
        for i, (label_text, var, field_type) in enumerate(labels_left_column):
            # حذف ":"
            ctk.CTkLabel(form_inner_frame, text=label_text.replace(":", ""),
                         font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=i, column=1, padx=10, pady=5, sticky="e")
            
            if field_type == "entry":
                entry = ctk.CTkEntry(form_inner_frame, textvariable=var, width=250, justify="right", 
                                     font=self.base_font, fg_color="#f8f8f8", border_color=self.ui_colors["border_gray"], corner_radius=5)
                entry.grid(row=i, column=0, padx=10, pady=5, sticky="ew")
            elif field_type == "textbox":
                textbox = ctk.CTkTextbox(form_inner_frame, width=250, height=70, font=self.base_font, fg_color="#f8f8f8", 
                                         border_color=self.ui_colors["border_gray"], corner_radius=5, wrap="word")
                textbox.grid(row=i, column=0, padx=10, pady=5, sticky="ew")
                self.notes_textbox = textbox

        # دکمه‌ها
        buttons_frame = ctk.CTkFrame(form_inner_frame, fg_color="transparent")
        # محاسبه سطر برای دکمه ها
        row_for_buttons = max(len(labels_right_column), len(labels_left_column))
        buttons_frame.grid(row=row_for_buttons, column=0, columnspan=4, pady=20) # در سطر جدید و وسط دو ستون
        buttons_frame.grid_columnconfigure(0, weight=1) # برای فضای خالی سمت چپ دکمه‌ها
        buttons_frame.grid_columnconfigure(1, weight=0) # دکمه حذف (اولین از راست)
        buttons_frame.grid_columnconfigure(2, weight=0) # دکمه جدید
        buttons_frame.grid_columnconfigure(3, weight=0) # دکمه ذخیره (آخرین از چپ)
        buttons_frame.grid_columnconfigure(4, weight=1) # برای فضای خالی سمت راست دکمه‌ها
        
        # ترتیب دکمه‌ها: ذخیره، جدید، حذف (راست به چپ)
        save_button = ctk.CTkButton(buttons_frame, text="ذخیره", 
                                    font=self.button_font, fg_color=self.ui_colors["accent_blue"], 
                                    hover_color=self.ui_colors["accent_blue_hover"], text_color="white", corner_radius=8,
                                    command=self.save_customer_from_ui)
        save_button.grid(row=0, column=1, padx=5) # ستون ۱

        clear_button = ctk.CTkButton(buttons_frame, text="جدید", 
                                     font=self.button_font, fg_color="#999999", 
                                     hover_color="#777777", text_color="white", corner_radius=8,
                                     width=60, height=30, 
                                     command=self.clear_customer_form)
        clear_button.grid(row=0, column=2, padx=5) # ستون ۲

        self.delete_customer_button = ctk.CTkButton(buttons_frame, text="حذف", 
                                                    font=self.button_font, fg_color="#dc3545", 
                                                    hover_color="#c82333", text_color="white", corner_radius=8,
                                                    width=60, height=30, 
                                                    command=self.delete_customer_from_db, state="disabled")
        self.delete_customer_button.grid(row=0, column=3, padx=5) # ستون ۳


        # بارگذاری اولیه کد مشتری و تنظیم اولیه لیبل شناسه ملی/شماره ملی
        self.clear_customer_form()
        # فراخوانی on_customer_type_select بعد از اطمینان از ایجاد tax_id_label
        self.after(10, self.on_customer_type_select) # کمی تاخیر برای اطمینان از رندر شدن

        return form_frame

    def create_customers_list_table(self, parent_frame):
        """ ایجاد جدول نمایش لیست مشتریان """
        table_frame = ctk.CTkFrame(parent_frame, fg_color="white", corner_radius=10, 
                                   border_width=1, border_color=self.ui_colors["border_gray"])
        table_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0) 
        
        # یک فریم برای دکمه جستجو/فیلتر
        search_button_frame = ctk.CTkFrame(table_frame, fg_color="transparent")
        search_button_frame.pack(side="top", fill="x", padx=10, pady=(10, 0))
        search_button_frame.grid_columnconfigure(0, weight=1) # برای فضای خالی سمت راست دکمه
        search_button_frame.grid_columnconfigure(1, weight=0) # ستون برای دکمه

        # دکمه "جستجوی مشتریان"
        self.search_customers_btn = ctk.CTkButton(search_button_frame, text="جستجوی مشتریان",
                                                  font=self.button_font, 
                                                  fg_color=self.ui_colors["accent_blue"],
                                                  hover_color=self.ui_colors["accent_blue_hover"],
                                                  text_color="white",
                                                  corner_radius=8,
                                                  command=self.toggle_filter_row)
        self.search_customers_btn.grid(row=0, column=0, padx=5, pady=5, sticky="w") # به ستون 0 و سمت چپ تغییر یافت


        self.filter_row_frame = ctk.CTkFrame(table_frame, fg_color="#e0e0e0", height=40, corner_radius=0)
        # این فریم ابتدا مخفی می‌شود و با toggle_filter_row() ظاهر می‌شود
        # self.filter_row_frame.pack(side="top", fill="x", padx=0, pady=0) # فعلا پک نمی‌شود

        # Treeview و اسکرول‌بار
        self.tree_scrollbar = ctk.CTkScrollbar(table_frame)
        self.tree_scrollbar.pack(side="right", fill="y")
        
        # تعریف ستون‌ها به ترتیب معکوس نمایش (آخرین ستون در لیست، اولین ستون در نمایش)
        # ID همیشه آخرین ستون در این لیست داخلی Treeview باشد
        column_identifiers = ("Notes", "PostalCode", "TaxID", "Email", "Mobile", 
                              "Phone2", "Phone", "Address", "Type", "Name", "Code", "ID")
        self.customer_table = ttk.Treeview(table_frame, 
                                           columns=column_identifiers, 
                                           show="headings", 
                                           yscrollcommand=self.tree_scrollbar.set)
        self.customer_table.pack(fill="both", expand=True)

        self.tree_scrollbar.configure(command=self.customer_table.yview)

        # تنظیمات سربرگ ستون‌ها (برعکس شدن ترتیب)
        self.customer_table.heading("Notes", text="سایر توضیحات", anchor="e")
        self.customer_table.heading("PostalCode", text="کد پستی", anchor="e")
        self.customer_table.heading("TaxID", text="شناسه ملی/شماره ملی", anchor="e")
        self.customer_table.heading("Email", text="ایمیل", anchor="e")
        self.customer_table.heading("Mobile", text="موبایل", anchor="e")
        self.customer_table.heading("Phone2", text="تلفن2", anchor="e")
        self.customer_table.heading("Phone", text="تلفن", anchor="e")
        self.customer_table.heading("Address", text="آدرس", anchor="e")
        self.customer_table.heading("Type", text="نوع", anchor="e")
        self.customer_table.heading("Name", text="نام مشتری", anchor="e")
        self.customer_table.heading("Code", text="کد مشتری", anchor="e")
        self.customer_table.heading("ID", text="شناسه", anchor="e") # این ستون مخفی باقی می ماند

        # تنظیمات پهنای ستون‌ها (برعکس شدن ترتیب)
        self.customer_table.column("Notes", width=150, anchor="e", stretch=True) # سایر توضیحات
        self.customer_table.column("PostalCode", width=80, anchor="e", stretch=False) # کد پستی
        self.customer_table.column("TaxID", width=100, anchor="e", stretch=False) # شناسه ملی/شماره ملی
        self.customer_table.column("Email", width=120, anchor="e", stretch=True) # ایمیل
        self.customer_table.column("Mobile", width=90, anchor="e", stretch=False) # موبایل
        self.customer_table.column("Phone2", width=90, anchor="e", stretch=False) # تلفن2
        self.customer_table.column("Phone", width=90, anchor="e", stretch=False) # تلفن
        self.customer_table.column("Address", width=150, anchor="e", stretch=True) # آدرس
        self.customer_table.column("Type", width=60, anchor="e", stretch=False) # نوع
        self.customer_table.column("Name", width=120, anchor="e", stretch=True) # نام مشتری - پهنای پویا
        self.customer_table.column("Code", width=80, anchor="e", stretch=False) # کد مشتری
        self.customer_table.column("ID", width=0, stretch=False) # شناسه - مخفی

        # ایجاد فیلدهای جستجو برای هر ستون
        for col_id in column_identifiers:
            if col_id == "ID": # برای ID فیلتر نمی‌خواهیم
                self.filter_vars[col_id] = ctk.StringVar(value="")
                self.filter_entries[col_id] = None # placeholder
                continue

            self.filter_vars[col_id] = ctk.StringVar(value="")
            entry = ctk.CTkEntry(self.filter_row_frame, textvariable=self.filter_vars[col_id],
                                 font=self.base_font, fg_color="#f8f8f8",
                                 border_color=self.ui_colors["border_gray"], corner_radius=0)
            entry.grid(row=0, column=len(self.filter_entries), sticky="nsew", padx=0, pady=0)
            entry.bind("<KeyRelease>", self.apply_live_filter)
            self.filter_entries[col_id] = entry
            self.filter_row_frame.grid_columnconfigure(len(self.filter_entries)-1, weight=1) # برای گسترش ستون‌ها

        #绑定 configure event to Treeview
        self.customer_table.bind("<Configure>", self.on_treeview_configure)


        self.customer_table.bind("<<TreeviewSelect>>", self.on_customer_select)
        self.customer_table.bind("<Double-1>", self.on_customer_double_click)

        tree_style = ttk.Style()
        tree_style.configure("Treeview", font=self.base_font, rowheight=25)
        tree_style.configure("Treeview.Heading", font=self.button_font)
        tree_style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nsew'})])

        self.load_customers_to_table()
        
        return table_frame

    def on_treeview_configure(self, event):
        """
        این تابع موقعیت و پهنای فیلدهای جستجو را با تغییر اندازه ستون‌های Treeview هماهنگ می‌کند.
        """
        if not self.is_filter_row_visible:
            return

        # یک بعد از Treeview برای گرفتن ابعاد ستون‌ها
        for col_id in self.customer_table["columns"]:
            if col_id == "ID": # ID مخفی است، نیازی به فیلد جستجو ندارد
                continue
            
            column_width = self.customer_table.column(col_id, "width")
            
            # پیدا کردن Entry متناظر با col_id
            if self.filter_entries[col_id]:
                self.filter_entries[col_id].configure(width=column_width)
                # برای تنظیم دقیق موقعیت با grid
                # این بخش پیچیده‌تر است و نیاز به محاسبه X offset هر ستون دارد
                # با pack یا grid در یک فریم خودش، مدیریت اندازه ساده‌تر است
                # برای سادگی، فعلا فقط عرض را تنظیم می‌کنیم.
                # جایگذاری دقیق با .place() نیاز به مختصات دقیق پیکسل دارد که تغییر پذیر است.
                # استفاده از grid در filter_row_frame و weight مناسب بهترین راهکار است.

    def toggle_filter_row(self):
        """ نمایش یا مخفی کردن ردیف فیلتر و مدیریت وضعیت دکمه """
        if self.is_filter_row_visible:
            self.filter_row_frame.pack_forget()
            self.is_filter_row_visible = False
            self.search_customers_btn.configure(fg_color=self.ui_colors["accent_blue"], text_color="white")
            # پاک کردن فیلترها و بارگذاری مجدد لیست کامل
            for var in self.filter_vars.values():
                var.set("")
            self.load_customers_to_table()
        else:
            self.filter_row_frame.pack(side="top", fill="x", padx=0, pady=0)
            self.is_filter_row_visible = True
            self.search_customers_btn.configure(fg_color=self.ui_colors["active_button_bg"], text_color=self.ui_colors["active_button_text"])
            # بعد از نمایش ردیف، ابعاد فیلدها را هماهنگ کن
            self.on_treeview_configure(None) # فراخوانی دستی برای تنظیم اولیه ابعاد

    def apply_live_filter(self, event=None):
        """ اعمال فیلتر زنده بر اساس ورودی کاربر در فیلدهای جستجو """
        search_terms = {col_id: self.filter_vars[col_id].get().strip().lower() 
                        for col_id in self.filter_vars if self.filter_vars[col_id].get().strip()}
        
        all_customers, _ = self.customer_manager.get_all_customers()
        
        # پاک کردن آیتم‌های فعلی جدول
        for item in self.customer_table.get_children():
            self.customer_table.delete(item)

        filtered_customers = []
        for customer in all_customers:
            match = True
            # باید مطمئن شویم که داده‌های customer به ترتیب و نام صحیح ستون‌ها در Treeview مپ می‌شوند
            # به ترتیب: Notes, PostalCode, TaxID, Email, Mobile, Phone2, Phone, Address, Type, Name, Code, ID
            customer_values_for_filter = {
                "Notes": str(customer.notes).lower(),
                "PostalCode": str(customer.postal_code).lower(),
                "TaxID": str(customer.tax_id).lower(),
                "Email": str(customer.email).lower(),
                "Mobile": str(customer.mobile).lower(),
                "Phone2": str(customer.phone2).lower(),
                "Phone": str(customer.phone).lower(),
                "Address": str(customer.address).lower(),
                "Type": str(customer.customer_type).lower(),
                "Name": str(customer.name).lower(),
                "Code": str(customer.customer_code).lower(),
                # "ID": str(customer.id).lower() # ID فیلتر نمی‌شود
            }

            for col_id, term in search_terms.items():
                if col_id in customer_values_for_filter:
                    if term not in customer_values_for_filter[col_id]:
                        match = False
                        break
                else: # اگر ستون مورد جستجو در customer_values_for_filter نبود
                    match = False
                    break # یا می‌توانید اینجا یک پیام هشدار بدهید که ستون نامعتبر است

            if match:
                filtered_customers.append(customer)
        
        for customer in filtered_customers:
            self.customer_table.insert("", "end", iid=customer.id,
                                     values=(str(customer.notes) if customer.notes else '',
                                             str(customer.postal_code) if customer.postal_code else '',
                                             str(customer.tax_id) if customer.tax_id else '',
                                             str(customer.email) if customer.email else '',
                                             str(customer.mobile) if customer.mobile else '',
                                             str(customer.phone2) if customer.phone2 else '',
                                             str(customer.phone) if customer.phone else '',
                                             str(customer.address) if customer.address else '',
                                             str(customer.customer_type) if customer.customer_type else '',
                                             str(customer.name) if customer.name else '',
                                             str(customer.customer_code) if customer.customer_code else '',
                                             customer.id))


    def on_customer_type_select(self):
        """ تغییر لیبل شناسه ملی/شماره ملی بر اساس نوع مشتری """
        if self.tax_id_label: 
            selected_type = self.customer_type_var.get()
            if selected_type == "حقوقی":
                self.tax_id_label.configure(text="شناسه ملی")
            else: # حقیقی
                self.tax_id_label.configure(text="شماره ملی")

    def load_customers_to_table(self):
        """ بارگذاری مشتریان از دیتابیس به جدول """
        for item in self.customer_table.get_children():
            self.customer_table.delete(item)

        customers, message = self.customer_manager.get_all_customers()
        if not customers:
            pass

        for customer in customers:
            # هنگام درج، مقادیر را به ترتیب ستون‌های تعریف شده در Treeview بدهید
            self.customer_table.insert("", "end", iid=customer.id,
                                     values=(str(customer.notes) if customer.notes else '',
                                             str(customer.postal_code) if customer.postal_code else '',
                                             str(customer.tax_id) if customer.tax_id else '',
                                             str(customer.email) if customer.email else '',
                                             str(customer.mobile) if customer.mobile else '',
                                             str(customer.phone2) if customer.phone2 else '',
                                             str(customer.phone) if customer.phone else '',
                                             str(customer.address) if customer.address else '',
                                             str(customer.customer_type) if customer.customer_type else '',
                                             str(customer.name) if customer.name else '',
                                             str(customer.customer_code) if customer.customer_code else '',
                                             customer.id))

    def clear_customer_form(self):
        """ پاک کردن فیلدهای فرم مشتری و غیرفعال کردن دکمه حذف """
        self.selected_customer_id = None
        self.customer_code_var.set(str(self.customer_manager.get_next_customer_code()))
        self.customer_name_var.set("")
        self.customer_type_var.set("حقوقی") # پیش‌فرض به حقوقی برگردانده شود
        self.address_var.set("")
        self.phone_var.set("")
        self.phone2_var.set("")
        self.mobile_var.set("")
        self.email_var.set("")
        self.tax_id_var.set("")
        self.postal_code_var.set("")
        self.notes_textbox.delete("1.0", "end") # پاک کردن محتوای تکست‌باکس
        self.delete_customer_button.configure(state="disabled")
        self.after(10, self.on_customer_type_select) # برای اطمینان از مقداردهی tax_id_label

    def save_customer_from_ui(self):
        """ اطلاعات وارد شده در UI را دریافت کرده و اعتبارسنجی کرده و در دیتابیس ذخیره می‌کند. """
        customer_code_str = self.customer_code_var.get().strip()
        customer_code = None
        if customer_code_str:
            try:
                customer_code = int(customer_code_str)
            except ValueError:
                messagebox.showwarning("خطای ورودی", "کد مشتری باید یک عدد باشد.", master=self)
                return

        name = self.customer_name_var.get().strip()
        customer_type = self.customer_type_var.get()
        address = self.address_var.get().strip()
        phone = self.phone_var.get().strip()
        phone2 = self.phone2_var.get().strip()
        mobile = self.mobile_var.get().strip()
        email = self.email_var.get().strip()
        tax_id = self.tax_id_var.get().strip()
        postal_code = self.postal_code_var.get().strip()
        notes = self.notes_textbox.get("1.0", "end").strip() # گرفتن محتوای تکست‌باکس

        if not name:
            messagebox.showwarning("خطای ورودی", "نام مشتری نمی‌تواند خالی باشد.", master=self)
            return

        if customer_type == "حقوقی":
            if not tax_id:
                messagebox.showwarning("خطای ورودی", "برای مشتری حقوقی، شناسه ملی اجباری است.", master=self)
                return
            if not tax_id.isdigit() or len(tax_id) != 11:
                messagebox.showwarning("خطای ورودی", "شناسه ملی باید یک عدد ۱۱ رقمی باشد.", master=self)
                return
        elif customer_type == "حقیقی":
            if not tax_id:
                messagebox.showwarning("خطای ورودی", "برای مشتری حقیقی، شماره ملی اجباری است.", master=self)
                return
            if not tax_id.isdigit() or len(tax_id) != 10:
                messagebox.showwarning("خطای ورودی", "شماره ملی باید یک عدد ۱۰ رقمی باشد.", master=self)
                return
        
        # اعتبارسنجی کد پستی (اختیاری ولی اگر وارد شد 10 رقم)
        if postal_code and (not postal_code.isdigit() or len(postal_code) != 10):
            messagebox.showwarning("خطای ورودی", "کد پستی (در صورت وارد شدن) باید یک عدد ۱۰ رقمی باشد.", master=self)
            return

        updated_customer = Customer(
            id=self.selected_customer_id, # اگر در حال ویرایش باشد
            customer_code=customer_code,
            name=name,
            customer_type=customer_type,
            address=address,
            phone=phone,
            phone2=phone2,
            mobile=mobile,
            email=email,
            tax_id=tax_id,
            postal_code=postal_code,
            notes=notes
        )

        if self.selected_customer_id: # حالت ویرایش
            success, message = self.customer_manager.update_customer(updated_customer)
        else: # حالت افزودن جدید
            success, message = self.customer_manager.add_customer(updated_customer)

        if success:
            messagebox.showinfo("موفقیت", message, master=self)
            self.clear_customer_form()
            self.load_customers_to_table()
        else:
            messagebox.showerror("خطا", message, master=self)

    def delete_customer_from_db(self):
        """ حذف مشتری از دیتابیس """
        if self.selected_customer_id:
            confirm = messagebox.askyesno("تایید حذف", f"آیا مطمئنید می‌خواهید مشتری '{self.customer_name_var.get()}' را حذف کنید؟", master=self)
            if confirm:
                success, message = self.customer_manager.delete_customer(self.selected_customer_id)
                if success:
                    messagebox.showinfo("موفقیت", message, master=self)
                    self.clear_customer_form()
                    self.load_customers_to_table()
                else:
                    messagebox.showerror("خطا", message, master=self)
        else:
            messagebox.showwarning("هشدار", "هیچ مشتری برای حذف انتخاب نشده است.", master=self)

    def on_customer_select(self, event):
        """ رویداد انتخاب سطر در جدول (تک کلیک) """
        selected_items = self.customer_table.selection()
        if selected_items:
            selected_item_id = selected_items[0]
            values = self.customer_table.item(selected_item_id, "values")
            
            # مقادیر را بر اساس ترتیب جدید ستون‌ها استخراج کنید
            # ترتیب ستون‌ها در Treeview: Notes, PostalCode, TaxID, Email, Mobile, Phone2, Phone, Address, Type, Name, Code, ID
            
            # مقادیر customer از دیتابیس به ترتیب مدل: id, customer_code, name, customer_type, address, phone, phone2, mobile, email, tax_id, postal_code, notes
            # باید مقادیر values را به ترتیب اصلی مدل برگردانیم تا در StringVar ها درست ست شوند
            customer_id = values[11] # ID در ایندکس 11 (آخرین ستون)
            customer_code = values[10] # Code در ایندکس 10
            name = values[9] # Name در ایندکس 9
            customer_type = values[8] # Type در ایندکس 8
            address = values[7] # Address در ایندکس 7
            phone = values[6] # Phone در ایندکس 6
            phone2 = values[5] # Phone2 در ایندکس 5
            mobile = values[4] # Mobile در ایندکس 4
            email = values[3] # Email در ایندکس 3
            tax_id = values[2] # TaxID در ایندکس 2
            postal_code = values[1] # PostalCode در ایندکس 1
            notes = values[0] # Notes در ایندکس 0

            self.selected_customer_id = int(customer_id)
            self.customer_code_var.set(str(customer_code) if customer_code != 'None' else '')
            self.customer_name_var.set(name if name != 'None' else '')
            self.customer_type_var.set(customer_type if customer_type != 'None' else 'حقوقی') # اطمینان از مقداردهی پیش‌فرض
            self.address_var.set(address if address != 'None' else '')
            self.phone_var.set(phone if phone != 'None' else '')
            self.phone2_var.set(phone2 if phone2 != 'None' else '')
            self.mobile_var.set(mobile if mobile != 'None' else '')
            self.email_var.set(email if email != 'None' else '')
            self.tax_id_var.set(tax_id if tax_id != 'None' else '')
            self.postal_code_var.set(postal_code if postal_code != 'None' else '')
            
            self.notes_textbox.delete("1.0", "end")
            self.notes_textbox.insert("1.0", notes if notes != 'None' else '')

            self.delete_customer_button.configure(state="normal")
            self.on_customer_type_select() # برای به‌روزرسانی لیبل بر اساس نوع مشتری

        else:
            self.clear_customer_form()

    def on_customer_double_click(self, event):
        """ رویداد دابل کلیک روی سطر در جدول """
        self.on_customer_select(event)
        # بعد از انتخاب، به تب "تعریف مشتری جدید" برو
        self.on_sub_nav_button_click("new_customer", self.new_customer_btn)

    def show_sub_frame(self, page_name):
        """ نمایش یک فریم خاص در منوی مشتریان """
        frame = self.frames.get(page_name)
        if frame:
            frame.tkraise()
            self.current_active_sub_page_name = page_name
            if page_name == "list_customers":
                self.load_customers_to_table()
                # اطمینان حاصل کن که ردیف فیلتر با تغییر تب مخفی شود
                if self.is_filter_row_visible:
                    self.toggle_filter_row() # اگر باز بود ببندش
            elif page_name == "new_customer":
                if not self.selected_customer_id:
                    self.clear_customer_form()
        else:
            messagebox.showwarning("زیرصفحه هنوز پیاده‌سازی نشده", f"زیرصفحه '{page_name}' هنوز در دست ساخت است.", master=self)

    def on_sub_nav_button_click(self, page_name, clicked_button):
        """
        هندل کردن کلیک روی دکمه‌های منوی داخلی مشتریان.
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
            
            if self.current_active_sub_page_name:
                if self.current_active_sub_page_name == "new_customer":
                    self.new_customer_btn.configure(
                        fg_color=self.ui_colors["active_sub_button_bg"], 
                        text_color=self.ui_colors["active_sub_button_text"],
                        border_width=2, 
                        border_color=self.ui_colors["active_sub_button_border"] 
                    )
                    self.current_active_sub_button = self.new_customer_btn
                elif self.current_active_sub_page_name == "list_customers":
                    self.list_customers_btn.configure(
                        fg_color=self.ui_colors["active_sub_button_bg"], 
                        text_color=self.ui_colors["active_sub_button_text"],
                        border_width=2, 
                        border_color=self.ui_colors["active_sub_button_border"] 
                    )
                    self.current_active_sub_button = self.list_customers_btn


# --- بلاک تست مستقل UI ---
if __name__ == "__main__":
    root = ctk.CTk()
    root.title("مشتریان easy_invoice (تست مستقل)")
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


    temp_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATABASE_NAME)
    temp_db_manager = DBManager(temp_db_path)
    
    if temp_db_manager.connect():
        temp_db_manager.create_tables()
        temp_db_manager.migrate_database()
        temp_db_manager.close()

    customer_frame = CustomerUI(root, temp_db_manager, test_ui_colors, base_font_tuple, heading_font_tuple, button_font_tuple, nav_button_font_tuple)
    customer_frame.pack(fill="both", expand=True)

    root.mainloop()