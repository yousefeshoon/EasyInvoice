import customtkinter as ctk
from tkinter import messagebox, filedialog, ttk # ttk برای Treeview
import os
from datetime import datetime
from PIL import Image, ImageTk

# Import کردن managerها و مدل‌ها از روت پروژه
from settings_manager import SettingsManager
from service_manager import ServiceManager 
from models import AppSettings, Service 
from db_manager import DBManager, DATABASE_NAME 

class SettingsUI(ctk.CTkFrame):
    def __init__(self, parent, db_manager, ui_colors, base_font, heading_font, button_font, nav_button_font):
        super().__init__(parent, fg_color="transparent") 
        self.parent = parent
        self.db_manager = db_manager
        self.settings_manager = SettingsManager()
        self.service_manager = ServiceManager() 
        self.ui_colors = ui_colors 
        self.base_font = base_font 
        self.heading_font = heading_font
        self.button_font = button_font
        self.nav_button_font = nav_button_font 
        self.current_settings = AppSettings()

        self.frames = {} 
        self.current_logo_image = None 
        
        self.selected_service_id = None 
        self.delete_service_button = None 
        self.service_description_var = None 
        self.service_settlement_type_combobox = None 
        self.service_code_var = None # --- جدید: برای کد خدمت ---
        self.service_table = None 

        self.create_widgets()
        
        self.current_active_sub_button = None 
        self.current_active_sub_page_name = None 
        
        self.after(100, lambda: self.on_sub_nav_button_click("seller_info", self.seller_info_btn))


    def create_widgets(self):
        """ ویجت‌های مربوط به تنظیمات برنامه را ایجاد می‌کند. """
        settings_card_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=10, 
                                           border_width=1, border_color=self.ui_colors["border_gray"])
        settings_card_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew") 
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        settings_card_frame.grid_rowconfigure(0, weight=0) 
        settings_card_frame.grid_rowconfigure(1, weight=1) 
        settings_card_frame.grid_columnconfigure(0, weight=1) 

        self.sub_navbar_frame = ctk.CTkFrame(settings_card_frame, fg_color="white", corner_radius=0) 
        self.sub_navbar_frame.grid(row=0, column=0, padx=0, pady=0, sticky="ew") 
        # --- اضافه کردن پدینگ بیشتر بین نوبار داخلی و محتوا ---
        self.sub_navbar_frame.grid_rowconfigure(0, weight=1) # برای کشیدن سطر دکمه‌ها
        self.sub_navbar_frame.grid_columnconfigure(0, weight=1) 
        self.sub_navbar_frame.grid_columnconfigure(1, weight=0) 
        self.sub_navbar_frame.grid_columnconfigure(2, weight=1) 
        # --------------------------------------------------------
        
        sub_buttons_container = ctk.CTkFrame(self.sub_navbar_frame, fg_color="transparent")
        sub_buttons_container.grid(row=0, column=1, sticky="nsew") 
        
        sub_buttons_container.grid_columnconfigure(0, weight=0) 
        sub_buttons_container.grid_columnconfigure(1, weight=0) 
        sub_buttons_container.grid_rowconfigure(0, weight=1) 
        
        # --- ترتیب دکمه‌های منوی سبز معکوس شد ---
        # دکمه "اطلاعات فروشنده" (جدیداً راست‌ترین)
        self.seller_info_btn = ctk.CTkButton(sub_buttons_container, text="اطلاعات فروشنده", 
                                              font=self.nav_button_font,
                                              fg_color=self.ui_colors["white"], 
                                              text_color=self.ui_colors["text_medium_gray"],
                                              hover_color=self.ui_colors["hover_light_blue"],
                                              corner_radius=8,
                                              command=lambda: self.on_sub_nav_button_click("seller_info", self.seller_info_btn))
        self.seller_info_btn.grid(row=0, column=1, padx=5, pady=10) 

        # دکمه "انواع خدمات" (جدیداً چپ‌ترین)
        self.service_types_btn = ctk.CTkButton(sub_buttons_container, text="انواع خدمات", 
                                                font=self.nav_button_font, 
                                                fg_color=self.ui_colors["white"], 
                                                text_color=self.ui_colors["text_medium_gray"],
                                                hover_color=self.ui_colors["hover_light_blue"],
                                                corner_radius=8,
                                                command=lambda: self.on_sub_nav_button_click("service_types", self.service_types_btn))
        self.service_types_btn.grid(row=0, column=0, padx=5, pady=10) 
        # -------------------------------------------------------------

        self.settings_content_frame = ctk.CTkFrame(settings_card_frame, fg_color="white") 
        # --- اضافه کردن پدینگ بیشتر بین نوبار داخلی و محتوا (پدینگ بالا 20) ---
        self.settings_content_frame.grid(row=1, column=0, padx=20, pady=(20, 20), sticky="nsew") 
        self.settings_content_frame.grid_rowconfigure(0, weight=1)
        self.settings_content_frame.grid_columnconfigure(0, weight=1)

        self.seller_info_form = self.create_seller_info_form(self.settings_content_frame)
        self.frames["seller_info"] = self.seller_info_form
        self.seller_info_form.grid(row=0, column=0, sticky="nsew") 

        self.service_types_page = self.create_service_types_form(self.settings_content_frame) 
        self.frames["service_types"] = self.service_types_page
        self.service_types_page.grid(row=0, column=0, sticky="nsew") 

        self.show_sub_frame("seller_info")


    def create_seller_info_form(self, parent_frame):
        """ ایجاد فرم اطلاعات فروشنده """
        seller_frame = ctk.CTkFrame(parent_frame, fg_color="white")
        seller_frame.grid(row=0, column=0, sticky="nsew") 
        parent_frame.grid_rowconfigure(0, weight=1)
        parent_frame.grid_columnconfigure(0, weight=1)

        form_inner_frame = ctk.CTkFrame(seller_frame, fg_color="transparent")
        form_inner_frame.grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="nsew") 
        seller_frame.grid_rowconfigure(0, weight=1)
        seller_frame.grid_columnconfigure(0, weight=1)

        form_inner_frame.grid_columnconfigure(0, weight=1) 
        form_inner_frame.grid_columnconfigure(1, weight=0) 

        labels_info = [
            ("نام فروشنده:", "seller_name", "entry"), 
            ("آدرس:", "seller_address", "entry"),     
            ("تلفن:", "seller_phone", "entry"),       
            ("شناسه ملی:", "seller_tax_id", "entry"),    
            ("کد اقتصادی:", "seller_economic_code", "entry"), 
            ("لوگو:", "seller_logo_path", "logo")     
        ]

        self.entries = {} 
        self.logo_path_var = ctk.StringVar() 
        self.logo_preview_label = None 

        for i, (label_text, var_name, field_type) in enumerate(labels_info):
            ctk.CTkLabel(form_inner_frame, text=label_text, 
                         font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=i, column=1, padx=10, pady=10, sticky="e")
            
            if field_type == "entry":
                entry_var = ctk.StringVar()
                entry = ctk.CTkEntry(form_inner_frame, textvariable=entry_var, width=300, justify="right", 
                                     font=self.base_font, fg_color="#f8f8f8", border_color=self.ui_colors["border_gray"], corner_radius=5)
                entry.grid(row=i, column=0, padx=10, pady=10, sticky="ew") 
                self.entries[var_name] = entry_var 
            elif field_type == "logo":
                logo_frame = ctk.CTkFrame(form_inner_frame, fg_color="transparent")
                logo_frame.grid(row=i, column=0, padx=10, pady=10, sticky="ew")
                logo_frame.grid_columnconfigure(0, weight=1) 
                logo_frame.grid_columnconfigure(1, weight=0) 
                logo_frame.grid_columnconfigure(2, weight=0) 

                logo_entry = ctk.CTkEntry(logo_frame, textvariable=self.logo_path_var, width=200, justify="left", 
                                          font=self.base_font, fg_color="#f8f8f8", border_color=self.ui_colors["border_gray"], corner_radius=5, state="readonly") 
                logo_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))

                select_logo_btn = ctk.CTkButton(logo_frame, text="انتخاب لوگو", 
                                                font=(self.base_font[0], self.base_font[1]-1), 
                                                fg_color=self.ui_colors["accent_blue"], 
                                                hover_color=self.ui_colors["accent_blue_hover"],
                                                text_color="white",
                                                corner_radius=5,
                                                command=self.select_logo_file) 
                select_logo_btn.grid(row=0, column=1, sticky="e")
                
                logo_preview_size = 50 
                self.logo_preview_label = ctk.CTkLabel(logo_frame, text="", width=logo_preview_size, height=logo_preview_size)
                self.logo_preview_label.grid(row=0, column=2, padx=5, sticky="e")

        save_button = ctk.CTkButton(form_inner_frame, text="ذخیره تنظیمات", 
                                   font=self.button_font, 
                                   fg_color=self.ui_colors["accent_blue"], 
                                   hover_color=self.ui_colors["accent_blue_hover"],
                                   text_color="white",
                                   corner_radius=8,
                                   command=self.save_settings_from_ui)
        save_button.grid(row=len(labels_info), column=0, columnspan=2, pady=20) 
        
        self.load_settings_into_ui() 

        return seller_frame 

    def create_service_types_form(self, parent_frame):
        """ ایجاد فرم و جدول برای مدیریت انواع خدمات """
        service_types_frame = ctk.CTkFrame(parent_frame, fg_color="white")
        service_types_frame.grid(row=0, column=0, sticky="nsew") 
        parent_frame.grid_rowconfigure(0, weight=1)
        parent_frame.grid_columnconfigure(0, weight=1)

        service_types_frame.grid_columnconfigure(0, weight=1) # ستون چپ (جدول)
        service_types_frame.grid_columnconfigure(1, weight=0) # ستون راست (فرم)
        service_types_frame.grid_rowconfigure(0, weight=1) 

        # --- ستون سمت راست: فرم افزودن/ویرایش خدمت ---
        form_frame = ctk.CTkFrame(service_types_frame, fg_color="white", corner_radius=10, 
                                  border_width=1, border_color=self.ui_colors["border_gray"])
        form_frame.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="nsew") 
        
        form_frame.grid_columnconfigure(0, weight=1) # فیلدها
        form_frame.grid_columnconfigure(1, weight=0) # لیبل‌ها
        
        form_title_label = ctk.CTkLabel(form_frame, text="خدمت جدید / ویرایش خدمت", 
                                        font=self.heading_font, text_color=self.ui_colors["text_dark_gray"])
        form_title_label.grid(row=0, column=0, columnspan=2, padx=20, pady=15, sticky="e")

        # --- فیلد کد خدمت (جدید) ---
        ctk.CTkLabel(form_frame, text="کد خدمت:", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=1, column=1, padx=10, pady=10, sticky="e")
        self.service_code_var = ctk.StringVar()
        service_code_entry = ctk.CTkEntry(form_frame, textvariable=self.service_code_var, width=250, justify="right",
                                          font=self.base_font, fg_color="#f8f8f8", border_color=self.ui_colors["border_gray"], corner_radius=5)
        service_code_entry.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        # ---------------------------

        ctk.CTkLabel(form_frame, text="شرح خدمت:", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=2, column=1, padx=10, pady=10, sticky="e")
        self.service_description_var = ctk.StringVar() 
        description_entry = ctk.CTkEntry(form_frame, textvariable=self.service_description_var, width=250, justify="right",
                                         font=self.base_font, fg_color="#f8f8f8", border_color=self.ui_colors["border_gray"], corner_radius=5)
        description_entry.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(form_frame, text="نوع تسویه:", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=3, column=1, padx=10, pady=10, sticky="e")
        self.service_settlement_type_var = ctk.StringVar() 
        self.service_settlement_type_combobox = ctk.CTkComboBox(form_frame, variable=self.service_settlement_type_var,
                                                         values=["ماهانه", "سالانه", "پروژه ای"],
                                                         width=250, justify="right", font=self.base_font,
                                                         dropdown_font=self.base_font,
                                                         command=self.combobox_selected_callback) 
        self.service_settlement_type_combobox.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        self.service_settlement_type_combobox.set("ماهانه") 
        
        buttons_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        buttons_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        save_button = ctk.CTkButton(buttons_frame, text="ذخیره", 
                                    font=self.button_font, fg_color=self.ui_colors["accent_blue"], 
                                    hover_color=self.ui_colors["accent_blue_hover"], text_color="white", corner_radius=8,
                                    command=self.save_service)
        save_button.pack(side="right", padx=5) 
        
        clear_button = ctk.CTkButton(buttons_frame, text="جدید", 
                                     font=self.button_font, fg_color="#999999", 
                                     hover_color="#777777", text_color="white", corner_radius=8,
                                     width=60, # --- نصف اندازه ---
                                     height=30, # --- نصف اندازه ---
                                     command=self.clear_service_form) 
        clear_button.pack(side="right", padx=5) 

        self.delete_service_button = ctk.CTkButton(buttons_frame, text="حذف", 
                                           font=self.button_font, fg_color="#dc3545", 
                                           hover_color="#c82333", text_color="white", corner_radius=8,
                                           width=60, # --- نصف اندازه ---
                                           height=30, # --- نصف اندازه ---
                                           command=self.delete_service_from_db, state="disabled") 
        self.delete_service_button.pack(side="left", padx=5) 

        # --- ستون سمت چپ: جدول نمایش خدمات ---
        table_frame = ctk.CTkFrame(service_types_frame, fg_color="white", corner_radius=10, 
                                   border_width=1, border_color=self.ui_colors["border_gray"])
        table_frame.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew") 
        
        table_frame.grid_rowconfigure(0, weight=1) 
        table_frame.grid_columnconfigure(0, weight=1)

        self.tree_scrollbar = ctk.CTkScrollbar(table_frame)
        self.tree_scrollbar.pack(side="right", fill="y")
        
        self.service_table = ttk.Treeview(table_frame, columns=("ID", "Code", "Description", "SettlementType"), show="headings", # --- ستون Code اضافه شد ---
                                           yscrollcommand=self.tree_scrollbar.set)
        self.service_table.pack(fill="both", expand=True)

        self.tree_scrollbar.configure(command=self.service_table.yview)

        # --- تنظیمات ستون‌ها (ID حذف شد، Code اضافه شد) ---
        self.service_table.heading("ID", text="شناسه", anchor="e") 
        self.service_table.heading("Code", text="کد خدمت", anchor="e") # --- جدید ---
        self.service_table.heading("Description", text="شرح خدمت", anchor="e")
        self.service_table.heading("SettlementType", text="نوع تسویه", anchor="e")

        self.service_table.column("ID", width=0, stretch=False) # --- ID مخفی شد ---
        self.service_table.column("Code", width=80, anchor="e", stretch=False) # --- جدید ---
        self.service_table.column("Description", width=200, anchor="e", stretch=True) # عرض تنظیم شد
        self.service_table.column("SettlementType", width=100, anchor="e", stretch=False)
        # ----------------------------------------------------------------------------------

        self.service_table.bind("<<TreeviewSelect>>", self.on_service_select) 
        self.service_table.bind("<Double-1>", self.on_service_double_click) 

        tree_style = ttk.Style()
        tree_style.configure("Treeview", font=self.base_font, rowheight=25) 
        tree_style.configure("Treeview.Heading", font=self.button_font) 
        tree_style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nsew'})]) 

        self.load_services_to_table() 
        
        return service_types_frame 

    def select_logo_file(self):
        """ باز کردن دیالوگ انتخاب فایل برای لوگو """
        file_path = filedialog.askopenfilename(
            title="انتخاب فایل لوگو",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")],
            master=self 
        )
        if file_path:
            self.logo_path_var.set(file_path)
            self.display_logo_preview(file_path)

    def display_logo_preview(self, file_path):
        """ نمایش پیش‌نمایش لوگو در UI """
        try:
            image_pil = Image.open(file_path)
            image_pil = image_pil.resize((50, 50), Image.LANCZOS)
            
            ctk_image = ctk.CTkImage(light_image=image_pil, dark_image=image_pil, size=(50, 50))
            self.logo_preview_label.configure(image=ctk_image, text="")
        except Exception as e:
            messagebox.showwarning("خطا در بارگذاری تصویر", f"امکان بارگذاری فایل تصویر وجود ندارد: {e}", master=self)
            self.logo_preview_label.configure(image=None, text="خطا")
            self.logo_path_var.set("") 

    def load_settings_into_ui(self):
        """ تنظیمات موجود را از دیتابیس بارگذاری کرده و در فیلدهای UI قرار می‌دهد. """
        self.current_settings = self.settings_manager.get_settings()
        if self.current_settings:
            self.entries["seller_name"].set(self.current_settings.seller_name or "")
            self.entries["seller_address"].set(self.current_settings.seller_address or "")
            self.entries["seller_phone"].set(self.current_settings.seller_phone or "")
            self.entries["seller_tax_id"].set(self.current_settings.seller_tax_id or "")
            self.entries["seller_economic_code"].set(self.current_settings.seller_economic_code or "") 
            
            logo_path = self.current_settings.seller_logo_path or ""
            self.logo_path_var.set(logo_path) 
            if logo_path: 
                self.display_logo_preview(logo_path)
        else:
            messagebox.showerror("خطا در بارگذاری تنظیمات", "خطا در بارگذاری تنظیمات از دیتابیس. ممکن است دیتابیس مقداردهی اولیه نشده باشد.", master=self)

    def save_settings_from_ui(self):
        """ اطلاعات وارد شده در UI را دریافت کرده و اعتبارسنجی کرده و در دیتابیس ذخیره می‌کند. """
        seller_name = self.entries["seller_name"].get()
        seller_tax_id = self.entries["seller_tax_id"].get()
        seller_economic_code = self.entries["seller_economic_code"].get()
        seller_logo_path = self.logo_path_var.get() 

        if not seller_name.strip():
            messagebox.showwarning("خطای ورودی", "نام فروشنده نمی‌تواند خالی باشد.", master=self)
            return

        if seller_tax_id: 
            if not seller_tax_id.isdigit() or len(seller_tax_id) != 11:
                messagebox.showwarning("خطای ورودی", "شناسه ملی باید یک عدد ۱۱ رقمی باشد.", master=self)
                return
        
        if seller_economic_code: 
            if not seller_economic_code.isdigit():
                messagebox.showwarning("خطای ورودی", "کد اقتصادی باید فقط شامل اعداد باشد.", master=self)
                return
            if not (len(seller_economic_code) == 11 or len(seller_economic_code) == 12):
                messagebox.showwarning("خطای ورودی", "کد اقتصادی باید ۱۱ یا ۱۲ رقمی باشد.", master=self)
                return

        updated_settings = AppSettings(
            id=self.current_settings.id,
            seller_name=seller_name,
            seller_address=self.entries["seller_address"].get(),
            seller_phone=self.entries["seller_phone"].get(),
            seller_tax_id=seller_tax_id,
            seller_economic_code=seller_economic_code,
            seller_logo_path=seller_logo_path,         
            db_version=self.current_settings.db_version
        )

        if self.settings_manager.save_settings(updated_settings):
            messagebox.showinfo("موفقیت", "تنظیمات با موفقیت ذخیره شد!", master=self)
            self.current_settings = self.settings_manager.get_settings() 
        else:
            messagebox.showerror("خطا در ذخیره تنظیمات", "خطا در ذخیره تنظیمات.", master=self)

    def combobox_selected_callback(self, choice):
        """ callback برای انتخاب از Combobox (در فرم خدمات) """
        print("Combobox selected:", choice)

    def load_services_to_table(self):
        """ بارگذاری خدمات از دیتابیس به جدول (در فرم خدمات) """
        for item in self.service_table.get_children():
            self.service_table.delete(item) 

        services, message = self.service_manager.get_all_services()
        if not services:
            pass 

        for service in services:
            # --- نمایش service_code در جدول ---
            self.service_table.insert("", "end", iid=service.id, 
                                     values=(service.id, service.service_code, service.description, service.settlement_type))

    def clear_service_form(self):
        """ پاک کردن فیلدهای فرم خدمات و غیرفعال کردن دکمه حذف """
        self.service_description_var.set("")
        self.service_settlement_type_combobox.set("ماهانه") 
        self.service_code_var.set(str(self.service_manager.get_next_service_code())) # --- کد بعدی رو خودکار پر کن ---
        self.selected_service_id = None
        self.delete_service_button.configure(state="disabled") 

    def save_service(self):
        """ ذخیره (افزودن/ویرایش) خدمت در دیتابیس """
        description = self.service_description_var.get().strip()
        settlement_type = self.service_settlement_type_combobox.get()
        service_code_str = self.service_code_var.get().strip()
        service_code = None

        if service_code_str:
            try:
                service_code = int(service_code_str)
            except ValueError:
                messagebox.showwarning("خطای ورودی", "کد خدمت باید یک عدد باشد.", master=self)
                return

        if not description:
            messagebox.showwarning("خطای ورودی", "شرح خدمت نمی‌تواند خالی باشد.", master=self)
            return
        if not settlement_type:
            messagebox.showwarning("خطای ورودی", "نوع تسویه نمی‌تواند خالی باشد.", master=self)
            return
        
        if self.selected_service_id: # حالت ویرایش
            service_obj = Service(id=self.selected_service_id, service_code=service_code, description=description, settlement_type=settlement_type)
            success, message = self.service_manager.update_service(service_obj)
        else: # حالت افزودن جدید
            service_obj = Service(service_code=service_code, description=description, settlement_type=settlement_type)
            success, message = self.service_manager.add_service(service_obj)

        if success:
            messagebox.showinfo("موفقیت", message, master=self)
            self.clear_service_form()
            self.load_services_to_table() 
        else:
            messagebox.showerror("خطا", message, master=self)

    def delete_service_from_db(self):
        """ حذف خدمت از دیتابیس """
        if self.selected_service_id:
            confirm = messagebox.askyesno("تایید حذف", f"آیا مطمئنید می‌خواهید خدمت با شناسه {self.selected_service_id} را حذف کنید؟", master=self)
            if confirm:
                success, message = self.service_manager.delete_service(self.selected_service_id)
                if success:
                    messagebox.showinfo("موفقیت", message, master=self)
                    self.clear_service_form()
                    self.load_services_to_table()
                else:
                    messagebox.showerror("خطا", message, master=self)
        else:
            messagebox.showwarning("هشدار", "هیچ خدمتی برای حذف انتخاب نشده است.", master=self)

    def on_service_select(self, event):
        """ رویداد انتخاب سطر در جدول (تک کلیک) """
        selected_items = self.service_table.selection()
        if selected_items:
            selected_item_id = selected_items[0]
            values = self.service_table.item(selected_item_id, "values")
            
            self.selected_service_id = int(values[0]) 
            self.service_code_var.set(str(values[1])) # --- کد خدمت را هم پر کن ---
            self.service_description_var.set(values[2])
            self.service_settlement_type_combobox.set(values[3])
            self.delete_service_button.configure(state="normal") 
        else:
            self.clear_service_form() 

    def on_service_double_click(self, event):
        """ رویداد دابل کلیک روی سطر در جدول """
        self.on_service_select(event)

    def show_sub_frame(self, page_name):
        """ نمایش یک فریم خاص در منوی تنظیمات """
        frame = self.frames.get(page_name)
        if frame:
            frame.tkraise()
            self.current_active_sub_page_name = page_name
        else:
            messagebox.showwarning("زیرصفحه هنوز پیاده‌سازی نشده", f"زیرصفحه '{page_name}' هنوز در دست ساخت است.", master=self)

    def on_sub_nav_button_click(self, page_name, clicked_button):
        """
        هندل کردن کلیک روی دکمه‌های منوی داخلی تنظیمات.
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
                if self.current_active_sub_page_name == "seller_info":
                    self.seller_info_btn.configure(
                        fg_color=self.ui_colors["active_sub_button_bg"], 
                        text_color=self.ui_colors["active_sub_button_text"],
                        border_width=2, 
                        border_color=self.ui_colors["active_sub_button_border"] 
                    )
                    self.current_active_sub_button = self.seller_info_btn
                elif self.current_active_sub_page_name == "service_types":
                    self.service_types_btn.configure(
                        fg_color=self.ui_colors["active_sub_button_bg"], 
                        text_color=self.ui_colors["active_sub_button_text"],
                        border_width=2, 
                        border_color=self.ui_colors["active_sub_button_border"] 
                    )
                    self.current_active_sub_button = self.service_types_btn


# --- بلاک تست مستقل UI ---
if __name__ == "__main__":
    root = ctk.CTk()
    root.title("تنظیمات easy_invoice (تست مستقل)")
    root.geometry("600x400")
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

    settings_frame = SettingsUI(root, temp_db_manager, test_ui_colors, base_font_tuple, heading_font_tuple, button_font_tuple, nav_button_font_tuple)
    settings_frame.pack(fill="both", expand=True)

    root.mainloop()