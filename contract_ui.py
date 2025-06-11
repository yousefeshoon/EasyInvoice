# contract_ui.py
import customtkinter as ctk
from tkinter import messagebox, filedialog, ttk
import os
import json
import jdatetime
from PIL import Image, ImageTk 
import fitz # (PyMuPDF) برای کار با PDF
import subprocess # برای باز کردن فایل‌ها

from contract_manager import ContractManager
from customer_manager import CustomerManager
from models import Contract 


class CalendarWidget(ctk.CTkToplevel):
    """ یک ویجت تقویم شمسی ساده برای انتخاب تاریخ """
    def __init__(self, master, date_var, ui_colors, base_font, button_font): 
        super().__init__(master)
        self.date_var = date_var
        self.ui_colors = ui_colors
        self.base_font = base_font
        self.button_font = button_font 
        self.title("انتخاب تاریخ")
        self.transient(master) 
        self.grab_set() 

        self.current_jdate = jdatetime.date.today()
        self.selected_jdate = None

        self.create_widgets()
        self.update_calendar()

        self.update_idletasks()
        master_x = master.winfo_x()
        master_y = master.winfo_y()
        master_width = master.winfo_width()
        master_height = master.winfo_height()

        self_width = self.winfo_width()
        self_height = self.winfo_height()

        x = master_x + (master_width // 2) - (self_width // 2)
        y = master_y + (master_height // 2) - (self_height // 2)

        self.geometry(f"+{x}+{y}")


    def create_widgets(self):
        header_frame = ctk.CTkFrame(self, fg_color=self.ui_colors["accent_blue"])
        header_frame.pack(fill="x", pady=0)

        ctk.CTkButton(header_frame, text="<<", command=lambda: self.change_month(-1),
                      font=self.base_font, text_color="white", fg_color="transparent", hover_color=self.ui_colors["accent_blue_hover"]).pack(side="right", padx=5, pady=5)
        
        self.month_year_label = ctk.CTkLabel(header_frame, text="", font=self.base_font, text_color="white")
        self.month_year_label.pack(side="right", padx=10, pady=5)

        ctk.CTkButton(header_frame, text=">>", command=lambda: self.change_month(1),
                      font=self.base_font, text_color="white", fg_color="transparent", hover_color=self.ui_colors["accent_blue_hover"]).pack(side="right", padx=5, pady=5)

        days_of_week = ["ش", "ی", "د", "س", "چ", "پ", "ج"] 
        days_frame = ctk.CTkFrame(self, fg_color="transparent")
        days_frame.pack(fill="x", pady=5)
        for i, day in enumerate(days_of_week):
            ctk.CTkLabel(days_frame, text=day, font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=0, column=i, padx=5, pady=2)

        self.calendar_grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.calendar_grid_frame.pack(fill="both", expand=True, padx=5, pady=5)

        select_button = ctk.CTkButton(self, text="انتخاب", command=self.select_date,
                                      font=self.button_font, fg_color=self.ui_colors["accent_blue"], 
                                      text_color="white", hover_color=self.ui_colors["accent_blue_hover"])
        select_button.pack(pady=10)

    def update_calendar(self):
        for widget in self.calendar_grid_frame.winfo_children():
            widget.destroy()

        self.month_year_label.configure(text=f"{self.current_jdate.j_month_name} {self.current_jdate.jyear}")

        first_day_of_month = self.current_jdate.replace(day=1)
        first_weekday = first_day_of_month.weekday() 
        start_column = (first_weekday + 2) % 7 

        row = 0
        col = start_column

        for day in range(1, self.current_jdate.j_days_in_month + 1):
            day_label = ctk.CTkButton(self.calendar_grid_frame, text=str(day),
                                      font=self.base_font,
                                      fg_color=self.ui_colors["white"],
                                      text_color=self.ui_colors["text_dark_gray"],
                                      hover_color=self.ui_colors["hover_light_blue"],
                                      command=lambda d=day: self.on_day_click(d))
            
            current_day_jdate = self.current_jdate.replace(day=day)
            if current_day_jdate == jdatetime.date.today():
                day_label.configure(border_color=self.ui_colors["accent_blue"], border_width=2)
            if self.selected_jdate == current_day_jdate:
                day_label.configure(fg_color=self.ui_colors["active_sub_button_bg"], text_color=self.ui_colors["active_sub_button_text"])


            day_label.grid(row=row, column=col, padx=2, pady=2)
            col += 1
            if col > 6:
                col = 0
                row += 1

    def change_month(self, delta):
        new_month = self.current_jdate.jmonth + delta
        new_year = self.current_jdate.jyear

        if new_month > 12:
            new_month = 1
            new_year += 1
        elif new_month < 1:
            new_month = 12
            new_year -= 1
        
        try:
            self.current_jdate = jdatetime.date(new_year, new_month, 1)
        except ValueError: 
            last_day_of_prev_month = jdatetime.date(new_year, new_month, 1).j_days_in_month
            self.current_jdate = jdatetime.date(new_year, new_month, last_day_of_prev_month)


        self.update_calendar()

    def on_day_click(self, day):
        self.selected_jdate = self.current_jdate.replace(day=day)
        self.update_calendar() 

    def select_date(self):
        if self.selected_jdate:
            self.date_var.set(self.selected_jdate.strftime("%Y/%m/%d"))
        self.destroy() 


class ImageViewer(ctk.CTkToplevel):
    """ پنجره‌ای برای نمایش پیش‌نمایش بزرگ‌تر عکس و دکمه پرینت """
    def __init__(self, master_geometry_str, image_path, ui_colors, base_font, button_font):
        super().__init__() 
        self.image_path = image_path
        self.ui_colors = ui_colors
        self.base_font = base_font
        self.button_font = button_font
        self.title(f"پیش‌نمایش: {os.path.basename(image_path)}")
        self.transient(self.master) 

        self.geometry(master_geometry_str) 
        self.update_idletasks()

        self.create_widgets()

    def create_widgets(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # فریم برای نمایش عکس
        image_frame = ctk.CTkFrame(self, fg_color="black")
        image_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        image_frame.grid_rowconfigure(0, weight=1)
        image_frame.grid_columnconfigure(0, weight=1)

        # نمایش عکس
        try:
            image_pil = None
            if self.image_path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
                image_pil = Image.open(self.image_path)
            elif self.image_path.lower().endswith(".pdf"):
                doc = fitz.open(self.image_path)
                page = doc.load_page(0)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) 
                image_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                doc.close()

            if image_pil:
                img_width, img_height = image_pil.size
                
                image_frame.update_idletasks() 
                frame_width = image_frame.winfo_width() 
                frame_height = image_frame.winfo_height() 

                if frame_width == 0 or frame_height == 0: 
                    ratio = 1 
                else:
                    ratio = min(frame_width / img_width, frame_height / img_height)
                
                new_width = int(img_width * ratio)
                new_height = int(img_height * ratio)

                image_pil = image_pil.resize((new_width, new_height), Image.LANCZOS)
                ctk_image = ctk.CTkImage(light_image=image_pil, dark_image=image_pil, size=(new_width, new_height))
                
                self.image_label = ctk.CTkLabel(image_frame, image=ctk_image, text="")
                self.image_label.image = ctk_image 
                self.image_label.pack(expand=True)
            else:
                ctk.CTkLabel(image_frame, text="قالب فایل پشتیبانی نمی‌شود.", font=self.base_font, text_color="red").pack(expand=True)

        except Exception as e:
            ctk.CTkLabel(image_frame, text=f"خطا در بارگذاری تصویر: {e}", font=self.base_font, text_color="red").pack(expand=True)


        # فریم برای دکمه‌ها
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=1, column=0, pady=10)

        print_btn = ctk.CTkButton(button_frame, text="پرینت", command=self.print_image,
                                  font=self.button_font, fg_color=self.ui_colors["accent_blue"],
                                  hover_color=self.ui_colors["accent_blue_hover"], text_color="white", corner_radius=8)
        print_btn.pack(side="left", padx=10)

        close_btn = ctk.CTkButton(button_frame, text="بستن", command=self.destroy,
                                  font=self.button_font, fg_color="#999999",
                                  hover_color="#777777", text_color="white", corner_radius=8)
        close_btn.pack(side="left", padx=10)

    def print_image(self):
        """ ارسال فایل برای پرینت """
        try:
            if sys.platform == "win32":
                os.startfile(self.image_path, "print")
            elif sys.platform == "darwin": 
                subprocess.run(["lp", self.image_path])
            else: 
                subprocess.run(["lpr", self.image_path])
            messagebox.showinfo("دستور پرینت ارسال شد", f"دستور پرینت برای فایل '{os.path.basename(self.image_path)}' ارسال شد.", master=self)
        except Exception as e:
            messagebox.showerror("خطا در پرینت", f"خطا در ارسال دستور پرینت برای '{os.path.basename(self.image_path)}': {e}", master=self)


class ContractUI(ctk.CTkFrame):
    def __init__(self, parent, db_manager, ui_colors, base_font, heading_font, button_font, nav_button_font):
        super().__init__(parent, fg_color="transparent")
        self.parent = parent
        self.db_manager = db_manager
        self.contract_manager = ContractManager()
        self.customer_manager = CustomerManager()
        self.ui_colors = ui_colors
        self.base_font = base_font
        self.heading_font = heading_font
        self.button_font = button_font
        self.nav_button_font = nav_button_font

        self.frames = {}
        self.selected_contract_id = None
        self.delete_contract_button = None

        # متغیرهای مربوط به فرم قرارداد
        self.contract_number_var = ctk.StringVar()
        self.contract_date_var = ctk.StringVar(value="----/--/--") 
        self.contract_title_var = ctk.StringVar() 
        self.total_amount_var = ctk.StringVar()
        self.payment_method_var = ctk.StringVar(value="ماهانه") 
        self.customer_dropdown_var = ctk.StringVar()
        self.description_textbox = None 
        self.scanned_pages_paths = []
        self.scanned_pages_frame = None
        self.scanned_page_widgets = []
        self.scanned_image_references = [] 

        self.customer_data_map = {}

        self.is_filter_row_visible = False

        self.create_widgets()
        
        self.current_active_sub_button = None
        self.current_active_sub_page_name = None
        
        self.after(100, lambda: self.on_sub_nav_button_click("new_contract", self.new_contract_btn))


    def create_widgets(self):
        """ ایجاد ویجت‌های اصلی مربوط به قراردادها. """
        contract_card_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=10, 
                                           border_width=1, border_color=self.ui_colors["border_gray"])
        contract_card_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        contract_card_frame.grid_rowconfigure(0, weight=0)
        contract_card_frame.grid_rowconfigure(1, weight=1)
        contract_card_frame.grid_columnconfigure(0, weight=1)

        self.sub_navbar_frame = ctk.CTkFrame(contract_card_frame, fg_color="white", corner_radius=0)
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
        
        self.list_contracts_btn = ctk.CTkButton(sub_buttons_container, text="لیست قراردادها",
                                                font=self.nav_button_font,
                                                fg_color=self.ui_colors["white"],
                                                text_color=self.ui_colors["text_medium_gray"],
                                                hover_color=self.ui_colors["hover_light_blue"],
                                                corner_radius=8,
                                                command=lambda: self.on_sub_nav_button_click("list_contracts", self.list_contracts_btn))
        self.list_contracts_btn.grid(row=0, column=0, padx=5, pady=10)

        self.new_contract_btn = ctk.CTkButton(sub_buttons_container, text="ثبت قرارداد",
                                                font=self.nav_button_font,
                                                fg_color=self.ui_colors["white"],
                                                text_color=self.ui_colors["text_medium_gray"],
                                                hover_color=self.ui_colors["hover_light_blue"],
                                                corner_radius=8,
                                                command=lambda: self.on_sub_nav_button_click("new_contract", self.new_contract_btn))
        self.new_contract_btn.grid(row=0, column=1, padx=5, pady=10)

        self.contract_content_frame = ctk.CTkFrame(contract_card_frame, fg_color="white")
        self.contract_content_frame.grid(row=1, column=0, padx=20, pady=(20, 20), sticky="nsew")
        self.contract_content_frame.grid_rowconfigure(0, weight=1)
        self.contract_content_frame.grid_columnconfigure(0, weight=1)

        self.new_contract_form = self.create_new_contract_form(self.contract_content_frame)
        self.frames["new_contract"] = self.new_contract_form
        self.new_contract_form.grid(row=0, column=0, sticky="nsew")

        self.list_contracts_page = self.create_contracts_list_table(self.contract_content_frame)
        self.frames["list_contracts"] = self.list_contracts_page
        self.list_contracts_page.grid(row=0, column=0, sticky="nsew")


    def create_new_contract_form(self, parent_frame):
        """ ایجاد فرم ثبت قرارداد جدید """
        form_frame = ctk.CTkFrame(parent_frame, fg_color="white")
        form_frame.grid(row=0, column=0, sticky="nsew")
        parent_frame.grid_rowconfigure(0, weight=1)
        parent_frame.grid_columnconfigure(0, weight=1)

        # اسکرول‌فریم برای محتوای فرم
        scroll_frame = ctk.CTkScrollableFrame(form_frame, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)

        form_inner_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        form_inner_frame.pack(fill="both", expand=True)

        # دو ستون برای فیلدها
        form_inner_frame.grid_columnconfigure(0, weight=1) # ستون چپ (فیلد)
        form_inner_frame.grid_columnconfigure(1, weight=0) # ستون چپ (لیبل)
        form_inner_frame.grid_columnconfigure(2, weight=1) # ستون راست (فیلد)
        form_inner_frame.grid_columnconfigure(3, weight=0) # ستون راست (لیبل)

        row_index = 0

        # فیلد شماره قرارداد
        ctk.CTkLabel(form_inner_frame, text="شماره قرارداد", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_index, column=3, padx=10, pady=5, sticky="e")
        contract_num_entry = ctk.CTkEntry(form_inner_frame, textvariable=self.contract_number_var, width=250, justify="right",
                                          font=self.base_font, fg_color="#f8f8f8", border_color=self.ui_colors["border_gray"], corner_radius=5)
        contract_num_entry.grid(row=row_index, column=2, padx=10, pady=5, sticky="ew")
        row_index += 1

        # فیلد تاریخ قرارداد (بدون دکمه تقویم)
        ctk.CTkLabel(form_inner_frame, text="تاریخ قرارداد", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_index, column=3, padx=10, pady=5, sticky="e")
        ctk.CTkEntry(form_inner_frame, textvariable=self.contract_date_var, width=250, justify="right",
                                        font=self.base_font, fg_color="#f8f8f8", border_color=self.ui_colors["border_gray"], corner_radius=5).grid(row=row_index, column=2, padx=10, pady=5, sticky="ew")
        row_index += 1

        # فیلد نام مشتری
        ctk.CTkLabel(form_inner_frame, text="نام مشتری", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_index, column=3, padx=10, pady=5, sticky="e")
        self.customer_dropdown = ctk.CTkComboBox(form_inner_frame, values=[], 
                                              variable=self.customer_dropdown_var, width=250, justify="right",
                                              font=self.base_font, fg_color="#f8f8f8", border_color=self.ui_colors["border_gray"], corner_radius=5,
                                              command=self.on_customer_selected)
        self.customer_dropdown.grid(row=row_index, column=2, padx=10, pady=5, sticky="ew")
        row_index += 1
        
        # فیلد عنوان قرارداد (باقی ماند)
        ctk.CTkLabel(form_inner_frame, text="عنوان قرارداد", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_index, column=3, padx=10, pady=5, sticky="e")
        ctk.CTkEntry(form_inner_frame, textvariable=self.contract_title_var, width=250, justify="right",
                     font=self.base_font, fg_color="#f8f8f8", border_color=self.ui_colors["border_gray"], corner_radius=5).grid(row=row_index, column=2, padx=10, pady=5, sticky="ew")
        row_index += 1

        # فیلد مبلغ قرارداد (ستون راست)
        ctk.CTkLabel(form_inner_frame, text="مبلغ قرارداد (ریال)", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_index, column=3, padx=10, pady=5, sticky="e")
        amount_entry = ctk.CTkEntry(form_inner_frame, textvariable=self.total_amount_var, width=250, justify="right",
                                    font=self.base_font, fg_color="#f2f2f2", border_color=self.ui_colors["border_gray"], corner_radius=5)
        amount_entry.grid(row=row_index, column=2, padx=10, pady=5, sticky="ew")
        amount_entry.bind("<KeyRelease>", self.format_amount_input)
        row_index += 1
        
        # فیلد نحوه پرداخت (باقی ماند)
        ctk.CTkLabel(form_inner_frame, text="نحوه پرداخت", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_index, column=3, padx=10, pady=5, sticky="e")
        payment_method_frame = ctk.CTkFrame(form_inner_frame, fg_color="transparent")
        payment_method_frame.grid(row=row_index, column=2, padx=10, pady=5, sticky="w")

        radio_monthly = ctk.CTkRadioButton(payment_method_frame, text="ماهانه", variable=self.payment_method_var, value="ماهانه",
                                           font=self.base_font, text_color=self.ui_colors["text_dark_gray"])
        radio_monthly.pack(side="right", padx=10)
        radio_yearly = ctk.CTkRadioButton(payment_method_frame, text="سالانه", variable=self.payment_method_var, value="سالانه",
                                          font=self.base_font, text_color=self.ui_colors["text_dark_gray"])
        radio_yearly.pack(side="right", padx=10)
        radio_project = ctk.CTkRadioButton(payment_method_frame, text="پروژه‌ای", variable=self.payment_method_var, value="پروژه‌ای",
                                           font=self.base_font, text_color=self.ui_colors["text_dark_gray"])
        radio_project.pack(side="right", padx=10)
        row_index += 1


        # فیلد توضیحات (textbox)
        ctk.CTkLabel(form_inner_frame, text="توضیحات", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_index, column=3, padx=10, pady=5, sticky="ne")
        self.description_textbox = ctk.CTkTextbox(form_inner_frame, width=250, height=70, font=self.base_font, fg_color="#f8f8f8",
                                                  border_color=self.ui_colors["border_gray"], corner_radius=5, wrap="word")
        self.description_textbox.grid(row=row_index, column=2, padx=10, pady=5, sticky="ew")
        row_index += 1


        # فیلد اسکن قرارداد (ستون چپ)
        left_column_start_row = 0
        ctk.CTkLabel(form_inner_frame, text="اسکن قرارداد (حداکثر 10 صفحه)", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=left_column_start_row, column=1, padx=10, pady=5, sticky="ne")
        
        scan_wrapper_frame = ctk.CTkFrame(form_inner_frame, fg_color="transparent")
        scan_wrapper_frame.grid(row=left_column_start_row, column=0, rowspan=row_index+1, padx=10, pady=5, sticky="nsew") # rowspan تنظیم شد
        scan_wrapper_frame.grid_columnconfigure(0, weight=1) 
        scan_wrapper_frame.grid_columnconfigure(1, weight=1) 
        scan_wrapper_frame.grid_rowconfigure(1, weight=1) # برای فریم اسکرول‌شونده

        # دکمه آپلود اسکن
        upload_scan_btn = ctk.CTkButton(scan_wrapper_frame, text="آپلود اسکن", 
                                        font=self.button_font, 
                                        fg_color=self.ui_colors["accent_blue"], 
                                        hover_color=self.ui_colors["accent_blue_hover"],
                                        text_color="white", corner_radius=5,
                                        command=self.upload_scanned_page)
        upload_scan_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=5)

        # دکمه پرینت اسکن‌ها
        print_scan_btn = ctk.CTkButton(scan_wrapper_frame, text="پرینت اسکن‌ها", 
                                       font=self.button_font, 
                                       fg_color="#28a745", # سبز
                                       hover_color="#218838", # سبز تیره
                                       text_color="white", corner_radius=5,
                                       command=self.print_scanned_pages)
        print_scan_btn.grid(row=0, column=1, sticky="ew", padx=(5, 0), pady=5)

        # فریم جدید برای نگه داشتن scrolled frame جهت جلوگیری از بهم ریختگی
        self.scanned_pages_container = ctk.CTkFrame(scan_wrapper_frame, fg_color="transparent", height=120) # ارتفاع ثابت
        self.scanned_pages_container.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(10,0))
        self.scanned_pages_container.grid_columnconfigure(0, weight=1) 
        self.scanned_pages_container.grid_rowconfigure(0, weight=1)

        self.scanned_pages_frame = ctk.CTkScrollableFrame(self.scanned_pages_container, 
                                                           fg_color="transparent", 
                                                           orientation="horizontal") 
        self.scanned_pages_frame.grid(row=0, column=0, sticky="nsew") # استفاده از grid
        self.scanned_pages_frame.grid_rowconfigure(0, weight=1) # برای نمایشگرهای پیش‌نمایش
        
        self.scanned_pages_frame.grid_remove() # ابتدا مخفی باشد

        left_column_start_row += 1


        # دکمه‌ها
        buttons_frame = ctk.CTkFrame(form_inner_frame, fg_color="transparent")
        row_for_buttons = max(row_index, left_column_start_row) 
        buttons_frame.grid(row=row_for_buttons, column=0, columnspan=4, pady=20)
        buttons_frame.grid_columnconfigure(0, weight=1) 
        buttons_frame.grid_columnconfigure(1, weight=0) 
        buttons_frame.grid_columnconfigure(2, weight=0) 
        buttons_frame.grid_columnconfigure(3, weight=0) 
        buttons_frame.grid_columnconfigure(4, weight=1) 
        
        # ترتیب دکمه‌ها: حذف، جدید، ذخیره (از چپ به راست)
        self.delete_contract_button = ctk.CTkButton(buttons_frame, text="حذف",
                                                    font=self.button_font, fg_color="#dc3545",
                                                    hover_color="#c82333", text_color="white", corner_radius=8,
                                                    width=60, height=30,
                                                    command=self.delete_contract_from_db, state="disabled")
        self.delete_contract_button.grid(row=0, column=1, padx=5)

        clear_button = ctk.CTkButton(buttons_frame, text="جدید",
                                     font=self.button_font, fg_color="#999999",
                                     hover_color="#777777", text_color="white", corner_radius=8,
                                     width=60, height=30,
                                     command=lambda: self.clear_contract_form()) 
        clear_button.grid(row=0, column=2, padx=5)

        save_button = ctk.CTkButton(buttons_frame, text="ذخیره",
                                    font=self.button_font, fg_color=self.ui_colors["accent_blue"],
                                    hover_color=self.ui_colors["accent_blue_hover"], text_color="white", corner_radius=8,
                                    command=self.save_contract_from_ui)
        save_button.grid(row=0, column=3, padx=5)


        self.load_customers_to_dropdown()
        self.clear_contract_form() 
        return form_frame

    def create_contracts_list_table(self, parent_frame):
        """ ایجاد جدول نمایش لیست قراردادها (مشابه لیست مشتریان) """
        table_frame = ctk.CTkFrame(parent_frame, fg_color="white", corner_radius=10, 
                                   border_width=1, border_color=self.ui_colors["border_gray"])
        table_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0) 
        
        # یک فریم برای دکمه جستجو/فیلتر
        search_button_frame = ctk.CTkFrame(table_frame, fg_color="transparent")
        search_button_frame.pack(side="top", fill="x", padx=10, pady=(10, 0))
        search_button_frame.grid_columnconfigure(0, weight=1) 
        search_button_frame.grid_columnconfigure(1, weight=0) 

        # دکمه "جستجوی قراردادها"
        self.search_contracts_btn = ctk.CTkButton(search_button_frame, text="جستجوی قراردادها",
                                                  font=self.button_font, 
                                                  fg_color=self.ui_colors["accent_blue"],
                                                  hover_color=self.ui_colors["accent_blue_hover"],
                                                  text_color="white",
                                                  corner_radius=8,
                                                  command=self.toggle_filter_row)
        self.search_contracts_btn.grid(row=0, column=0, padx=5, pady=5, sticky="w") 


        self.filter_row_frame = ctk.CTkFrame(table_frame, fg_color="#e0e0e0", height=40, corner_radius=0)

        # Treeview و اسکرول‌بار
        self.tree_scrollbar = ctk.CTkScrollbar(table_frame)
        self.tree_scrollbar.pack(side="right", fill="y")
        
        # تعریف ستون‌ها (فیلدهای حذف شده برداشته شدند)
        column_identifiers = ("ScannedPagesCount", "PaymentMethod", "Title", "Description", "TotalAmount", "ContractDate", "CustomerName", "ContractNumber", "ID") 
        self.contract_table = ttk.Treeview(table_frame, 
                                           columns=column_identifiers, 
                                           show="headings", 
                                           yscrollcommand=self.tree_scrollbar.set)
        self.contract_table.pack(fill="both", expand=True)

        self.tree_scrollbar.configure(command=self.contract_table.yview)

        # تنظیمات سربرگ ستون‌ها
        self.contract_table.heading("ScannedPagesCount", text="تعداد اسکن", anchor="e")
        self.contract_table.heading("PaymentMethod", text="نحوه پرداخت", anchor="e")
        self.contract_table.heading("Title", text="عنوان قرارداد", anchor="e")
        self.contract_table.heading("Description", text="توضیحات", anchor="e")
        self.contract_table.heading("TotalAmount", text="مبلغ", anchor="e")
        self.contract_table.heading("ContractDate", text="تاریخ قرارداد", anchor="e") 
        self.contract_table.heading("CustomerName", text="نام مشتری", anchor="e")
        self.contract_table.heading("ContractNumber", text="شماره قرارداد", anchor="e")
        self.contract_table.heading("ID", text="شناسه", anchor="e")

        # تنظیمات پهنای ستون‌ها
        self.contract_table.column("ScannedPagesCount", width=70, anchor="center", stretch=False)
        self.contract_table.column("PaymentMethod", width=80, anchor="e", stretch=False)
        self.contract_table.column("Title", width=150, anchor="e", stretch=True)
        self.contract_table.column("Description", width=200, anchor="e", stretch=True)
        self.contract_table.column("TotalAmount", width=100, anchor="e", stretch=False)
        self.contract_table.column("ContractDate", width=80, anchor="e", stretch=False) 
        self.contract_table.column("CustomerName", width=120, anchor="e", stretch=True)
        self.contract_table.column("ContractNumber", width=100, anchor="e", stretch=False)
        self.contract_table.column("ID", width=0, stretch=False)

        # ایجاد فیلدهای جستجو برای هر ستون
        self.filter_entries = {}
        self.filter_vars = {}
        for col_id in column_identifiers:
            if col_id == "ID" or col_id == "ScannedPagesCount": 
                self.filter_vars[col_id] = ctk.StringVar(value="")
                self.filter_entries[col_id] = None
                continue

            self.filter_vars[col_id] = ctk.StringVar(value="")
            entry = ctk.CTkEntry(self.filter_row_frame, textvariable=self.filter_vars[col_id],
                                 font=self.base_font, fg_color="#f8f8f8",
                                 border_color=self.ui_colors["border_gray"], corner_radius=0)
            entry.grid(row=0, column=len(self.filter_entries), sticky="nsew", padx=0, pady=0)
            entry.bind("<KeyRelease>", self.apply_live_filter)
            self.filter_entries[col_id] = entry
            self.filter_row_frame.grid_columnconfigure(len(self.filter_entries)-1, weight=1)

        #绑定 configure event to Treeview
        self.contract_table.bind("<Configure>", self.on_treeview_configure)


        self.contract_table.bind("<<TreeviewSelect>>", self.on_contract_select)
        self.contract_table.bind("<Double-1>", self.on_contract_double_click)

        # تنظیمات استایل Treeview اصلی برای قراردادها
        tree_style = ttk.Style()
        tree_style.configure("Treeview", font=self.base_font, rowheight=25)
        tree_style.configure("Treeview.Heading", font=self.button_font)
        tree_style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nsew'})])

        self.load_contracts_to_table()
        
        return table_frame
    
    def on_treeview_configure(self, event):
        """
        این تابع موقعیت و پهنای فیلدهای جستجو را با تغییر اندازه ستون‌های Treeview هماهنگ می‌کند.
        """
        if not self.is_filter_row_visible:
            return

        for col_id in self.contract_table["columns"]:
            if col_id == "ID" or col_id == "ScannedPagesCount":
                continue
            
            column_width = self.contract_table.column(col_id, "width")
            
            if self.filter_entries.get(col_id): 
                self.filter_entries[col_id].configure(width=column_width)

    def toggle_filter_row(self):
        """ نمایش یا مخفی کردن ردیف فیلتر و مدیریت وضعیت دکمه """
        if self.is_filter_row_visible:
            self.filter_row_frame.pack_forget()
            self.is_filter_row_visible = False
            self.search_contracts_btn.configure(fg_color=self.ui_colors["accent_blue"], text_color="white")
            for var in self.filter_vars.values():
                var.set("")
            self.load_contracts_to_table()
        else:
            self.filter_row_frame.pack(side="top", fill="x", padx=0, pady=0)
            self.is_filter_row_visible = True
            self.search_contracts_btn.configure(fg_color=self.ui_colors["active_button_bg"], text_color=self.ui_colors["active_button_text"])
            self.on_treeview_configure(None)

    def apply_live_filter(self, event=None):
        """ اعمال فیلتر زنده بر اساس ورودی کاربر در فیلدهای جستجو """
        search_terms = {col_id: self.filter_vars[col_id].get().strip().lower() 
                        for col_id in self.filter_vars if self.filter_vars[col_id].get().strip()}
        
        all_contracts, _ = self.contract_manager.get_all_contracts()
        
        for item in self.contract_table.get_children():
            self.contract_table.delete(item)

        filtered_contracts = []
        for contract in all_contracts:
            match = True
            contract_values_for_filter = {
                "Description": str(contract.description).lower(),
                "TotalAmount": str(contract.total_amount).lower(),
                "ContractDate": str(contract.contract_date).lower() if contract.contract_date else '',
                "CustomerName": str(contract.customer_name).lower(),
                "ContractNumber": str(contract.contract_number).lower(),
                "Title": str(contract.title).lower(),
                "PaymentMethod": str(contract.payment_method).lower(),
            }

            for col_id, term in search_terms.items():
                if col_id in contract_values_for_filter:
                    if term not in contract_values_for_filter[col_id]:
                        match = False
                        break
                else:
                    match = False
                    break

            if match:
                filtered_contracts.append(contract)
        
        self.insert_contracts_into_table(filtered_contracts)

    def load_customers_to_dropdown(self):
        """ بارگذاری مشتریان در دراپ‌داون انتخاب مشتری """
        customers, _ = self.customer_manager.get_all_customers()
        customers.sort(key=lambda c: c.name)
        customer_names = []
        self.customer_data_map = {}
        for cust in customers:
            customer_names.append(cust.name)
            self.customer_data_map[cust.name] = cust.id
        self.customer_dropdown.configure(values=customer_names)
        self.customer_dropdown.configure(font=self.base_font)
        if customer_names:
            self.customer_dropdown_var.set(customer_names[0])
            self.on_customer_selected(customer_names[0]) 

    def on_customer_selected(self, choice):
        """ تابعی که هنگام انتخاب مشتری از دراپ‌داون فراخوانی می‌شود. """
        pass

    def load_contracts_to_table(self):
        """ بارگذاری قراردادها از دیتابیس به جدول """
        for item in self.contract_table.get_children():
            self.contract_table.delete(item)

        contracts, message = self.contract_manager.get_all_contracts()
        if not contracts:
            pass

        self.insert_contracts_into_table(contracts)

    def insert_contracts_into_table(self, contracts):
        """ توابع کمکی برای درج قراردادها در جدول (برای فیلتر و بارگذاری اولیه) """
        for contract in contracts:
            formatted_amount = f"{int(contract.total_amount):,}" if contract.total_amount is not None else ""
            scanned_pages_count = len(contract.scanned_pages) if contract.scanned_pages else 0

            self.contract_table.insert("", "end", iid=contract.id,
                                     values=(scanned_pages_count,
                                             str(contract.payment_method) if contract.payment_method else '',
                                             str(contract.title) if contract.title else '',
                                             str(contract.description) if contract.description else '',
                                             formatted_amount,
                                             str(contract.contract_date) if contract.contract_date else '',
                                             str(contract.customer_name) if hasattr(contract, 'customer_name') and contract.customer_name else '',
                                             str(contract.contract_number) if contract.contract_number else '',
                                             contract.id))


    def clear_contract_form(self):
        """ پاک کردن فیلدهای فرم قرارداد و غیرفعال کردن دکمه حذف. """
        self.selected_contract_id = None
        self.contract_number_var.set("") 
        self.contract_date_var.set("----/--/--") 
        self.contract_title_var.set("")
        self.total_amount_var.set("")
        self.payment_method_var.set("ماهانه")
        self.customer_dropdown_var.set("")
        self.description_textbox.delete("1.0", "end")

        self.scanned_pages_paths = []
        self.clear_scanned_page_previews()

        self.delete_contract_button.configure(state="disabled")
        self.load_customers_to_dropdown()

    def save_contract_from_ui(self):
        """ اطلاعات وارد شده در UI را دریافت کرده و اعتبارسنجی کرده و در دیتابیس ذخیره می‌کند. """
        contract_number = self.contract_number_var.get().strip()
        contract_date = self.contract_date_var.get().strip()
        title = self.contract_title_var.get().strip()
        total_amount_str = self.total_amount_var.get().strip().replace(",", "")
        payment_method = self.payment_method_var.get()
        description = self.description_textbox.get("1.0", "end").strip()
        
        selected_customer_name = self.customer_dropdown_var.get()
        customer_id = self.customer_data_map.get(selected_customer_name)
        
        # اعتبارسنجی
        if not contract_number:
            messagebox.showwarning("خطای ورودی", "شماره قرارداد نمی‌تواند خالی باشد.", master=self)
            return
        if not contract_date or contract_date == "----/--/--":
            messagebox.showwarning("خطای ورودی", "تاریخ قرارداد نمی‌تواند خالی باشد.", master=self)
            return
        # اعتبارسنجی فرمت تاریخ (سال/ماه/روز)
        try:
            jdatetime.datetime.strptime(contract_date, "%Y/%m/%d")
        except ValueError:
            messagebox.showwarning("خطای ورودی", "فرمت تاریخ قرارداد باید سال/ماه/روز (مثال: 1402/01/01) باشد.", master=self)
            return

        if not customer_id:
            messagebox.showwarning("خطای ورودی", "انتخاب مشتری الزامی است.", master=self)
            return
        if not title:
            messagebox.showwarning("خطای ورودی", "عنوان قرارداد نمی‌تواند خالی باشد.", master=self)
            return
        
        total_amount = None
        if total_amount_str:
            try:
                total_amount = float(total_amount_str)
            except ValueError:
                messagebox.showwarning("خطای ورودی", "مبلغ قرارداد باید عدد باشد.", master=self)
                return

        # scanned_pages_json = json.dumps(self.scanned_pages_paths) # این خط دیگر نیاز نیست، مدل خودش هندل می‌کند

        updated_contract = Contract(
            id=self.selected_contract_id,
            customer_id=customer_id,
            contract_number=contract_number,
            contract_date=contract_date,
            total_amount=total_amount,
            description=description,
            title=title,
            payment_method=payment_method,
            scanned_pages=self.scanned_pages_paths # لیست رو مستقیم پاس میدیم
        )

        if self.selected_contract_id:
            success, message = self.contract_manager.update_contract(updated_contract)
        else:
            success, message = self.contract_manager.add_contract(updated_contract)

        if success:
            messagebox.showinfo("موفقیت", message, master=self)
            self.clear_contract_form()
            self.load_contracts_to_table()
        else:
            messagebox.showerror("خطا", message, master=self)

    def delete_contract_from_db(self):
        """ حذف قرارداد از دیتابیس """
        if self.selected_contract_id:
            confirm = messagebox.askyesno("تایید حذف", f"آیا مطمئنید می‌خواهید قرارداد با شماره '{self.contract_number_var.get()}' را حذف کنید؟", master=self)
            if confirm:
                success, message = self.contract_manager.delete_contract(self.selected_contract_id)
                if success:
                    messagebox.showinfo("موفقیت", message, master=self)
                    self.clear_contract_form()
                    self.load_contracts_to_table()
                else:
                    messagebox.showerror("خطا", message, master=self)
        else:
            messagebox.showwarning("هشدار", "هیچ قراردادی برای حذف انتخاب نشده است.", master=self)

    def on_contract_select(self, event):
        """ رویداد انتخاب سطر در جدول (تک کلیک) """
        selected_items = self.contract_table.selection()
        if selected_items:
            selected_item_id = selected_items[0]
            
            contract_obj, _ = self.contract_manager.get_contract_by_id(int(selected_item_id)) 
            if contract_obj:
                self.selected_contract_id = contract_obj.id
                self.contract_number_var.set(contract_obj.contract_number if contract_obj.contract_number else '')
                self.contract_date_var.set(contract_obj.contract_date if contract_obj.contract_date else '----/--/--')
                self.contract_title_var.set(contract_obj.title if contract_obj.title else '')
                
                self.total_amount_var.set(f"{int(contract_obj.total_amount)}" if contract_obj.total_amount is not None else '')
                self.payment_method_var.set(contract_obj.payment_method if contract_obj.payment_method else 'ماهانه')
                
                self.description_textbox.delete("1.0", "end")
                self.description_textbox.insert("1.0", contract_obj.description if contract_obj.description else '')
                
                customer_name_from_db = next((c_name for c_name, c_id in self.customer_data_map.items() if c_id == contract_obj.customer_id), '')
                self.customer_dropdown_var.set(customer_name_from_db)
                
                self.scanned_pages_paths = list(contract_obj.scanned_pages)
                self.display_scanned_page_previews()

                self.delete_contract_button.configure(state="normal")
            else:
                self.clear_contract_form()
        else:
            self.clear_contract_form()

    def on_contract_double_click(self, event):
        """ رویداد دابل کلیک روی سطر در جدول """
        self.on_contract_select(event)
        self.on_sub_nav_button_click("new_contract", self.new_contract_btn)

    def show_sub_frame(self, page_name):
        """ نمایش یک فریم خاص در منوی قراردادها """
        frame = self.frames.get(page_name)
        if frame:
            frame.tkraise()
            self.current_active_sub_page_name = page_name
            if page_name == "list_contracts":
                self.load_contracts_to_table()
                if self.is_filter_row_visible:
                    self.toggle_filter_row()
            elif page_name == "new_contract":
                if self.selected_contract_id is None:
                    self.clear_contract_form()
        else:
            messagebox.showwarning("زیرصفحه هنوز پیاده‌سازی نشده", f"زیرصفحه '{page_name}' هنوز در دست ساخت است.", master=self)

    def on_sub_nav_button_click(self, page_name, clicked_button):
        """
        هندل کردن کلیک روی دکمه‌های منوی داخلی قراردادها.
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
                if self.current_active_sub_page_name == "new_contract":
                    self.new_contract_btn.configure(
                        fg_color=self.ui_colors["active_sub_button_bg"],
                        text_color=self.ui_colors["active_sub_button_text"],
                        border_width=2,
                        border_color=self.ui_colors["active_sub_button_border"]
                    )
                    self.current_active_sub_button = self.new_contract_btn
                elif self.current_active_sub_page_name == "list_contracts":
                    self.list_contracts_btn.configure(
                        fg_color=self.ui_colors["active_sub_button_bg"],
                        text_color=self.ui_colors["active_sub_button_text"],
                        border_width=2,
                        border_color=self.ui_colors["active_sub_button_border"]
                    )
                    self.current_active_sub_button = self.list_contracts_btn

    def format_amount_input(self, event=None):
        """ فرمت کردن ورودی مبلغ به صورت سه رقم سه رقم جدا شده """
        current_text = self.total_amount_var.get().replace(",", "")
        if not current_text:
            return
        
        try:
            numeric_value = int("".join(filter(str.isdigit, current_text)))
            formatted_value = f"{numeric_value:,}"
            self.total_amount_var.set(formatted_value)
        except ValueError:
            pass

    def upload_scanned_page(self):
        """ باز کردن دیالوگ انتخاب فایل برای اسکن قرارداد (تصویر یا PDF) با قابلیت انتخاب چند فایل """
        if len(self.scanned_pages_paths) >= 10:
            messagebox.showwarning("محدودیت تعداد", "حداکثر ۱۰ صفحه اسکن قابل آپلود است.", master=self)
            return

        file_paths = filedialog.askopenfilenames(
            title="انتخاب فایل‌های اسکن (تصویر یا PDF)",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
                       ("PDF files", "*.pdf"),
                       ("All files", "*.*")],
            master=self
        )
        if file_paths:
            for file_path in file_paths:
                if len(self.scanned_pages_paths) < 10:
                    self.scanned_pages_paths.append(file_path)
                else:
                    messagebox.showwarning("محدودیت تعداد", "فایل‌های بیشتر از ۱۰ صفحه نادیده گرفته شدند.", master=self)
                    break
            self.display_scanned_page_previews()

    def display_scanned_page_previews(self):
        """ نمایش پیش‌نمایش فایل‌های اسکن شده (تصویر یا صفحه اول PDF) """
        for widget in self.scanned_pages_frame.winfo_children():
            widget.destroy()
        self.scanned_page_widgets = []
        self.scanned_image_references = [] 

        if not self.scanned_pages_paths: 
            self.scanned_pages_frame.grid_remove()
            self.scanned_pages_container.grid_remove() # فریم کانتینر هم مخفی شود
            return
        else:
            self.scanned_pages_container.grid() # فریم کانتینر نمایش داده شود
            self.scanned_pages_frame.grid()

        for i, file_path in enumerate(self.scanned_pages_paths):
            # هر پیش‌نمایش در یک ستون جداگانه در scrolled_pages_frame قرار می‌گیرد
            preview_container = ctk.CTkFrame(self.scanned_pages_frame, fg_color="transparent", width=100, height=110) # اندازه ثابت
            preview_container.grid(row=0, column=i, padx=5, pady=5, sticky="n") 
            preview_container.grid_propagate(False) # جلوگیری از تغییر اندازه بر اساس محتوا
            preview_container.grid_rowconfigure(0, weight=0)
            preview_container.grid_rowconfigure(1, weight=1)
            preview_container.grid_rowconfigure(2, weight=0)
            preview_container.grid_columnconfigure(0, weight=1)
            
            ctk.CTkLabel(preview_container, text=f"عکس {i+1}", font=(self.base_font[0], 10, "bold"), text_color=self.ui_colors["text_dark_gray"]).grid(row=0, column=0, pady=(0, 2))

            preview_frame = ctk.CTkFrame(preview_container, fg_color="#e0e0e0", corner_radius=5, width=80, height=80)
            preview_frame.grid(row=1, column=0, padx=0, pady=0)
            preview_frame.grid_propagate(False) 
            preview_frame.grid_rowconfigure(0, weight=1)
            preview_frame.grid_columnconfigure(0, weight=1)
            
            img_to_display = None
            try:
                image_pil = None
                if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
                    image_pil = Image.open(file_path)
                elif file_path.lower().endswith(".pdf"):
                    doc = fitz.open(file_path)
                    page = doc.load_page(0)
                    pix = page.get_pixmap()
                    image_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    doc.close()
                else:
                    img_to_display = ctk.CTkLabel(preview_frame, text="خطا/ناشناخته", font=(self.base_font[0], 8), text_color="red")
                    img_to_display.grid(row=0, column=0, sticky="nsew")

                if img_to_display is None:
                    image_pil = image_pil.resize((70, 70), Image.LANCZOS)
                    ctk_image = ctk.CTkImage(light_image=image_pil, dark_image=image_pil, size=(70, 70))
                    
                    self.scanned_image_references.append(ctk_image) 
                    
                    img_to_display = ctk.CTkLabel(preview_frame, image=ctk_image, text="")
                    img_to_display.image = ctk_image
                    img_to_display.grid(row=0, column=0, sticky="nsew") # استفاده از grid

                    img_to_display.bind("<Button-1>", lambda event, fp=file_path: self.open_image_preview(fp))

            except Exception as e:
                print(f"Error loading preview for {file_path}: {e}")
                img_to_display = ctk.CTkLabel(preview_frame, text="بارگذاری نشد", font=(self.base_font[0], 8), text_color="red")
                img_to_display.grid(row=0, column=0, sticky="nsew")
            
            delete_btn = ctk.CTkButton(preview_container, text="حذف", width=60, height=25,
                                       font=(self.base_font[0], 10),
                                       fg_color="red", hover_color="#c82333", text_color="white",
                                       command=lambda fp=file_path: self.remove_scanned_page(fp))
            delete_btn.grid(row=2, column=0, pady=(5,0))

            self.scanned_page_widgets.append(preview_container)

    def remove_scanned_page(self, file_path_to_remove):
        """ حذف یک فایل اسکن از لیست و به‌روزرسانی پیش‌نمایش‌ها """
        if file_path_to_remove in self.scanned_pages_paths:
            self.scanned_pages_paths.remove(file_path_to_remove)
            self.display_scanned_page_previews()

    def clear_scanned_page_previews(self):
        """ پاک کردن تمام پیش‌نمایش‌های اسکن شده و مخفی کردن فریم """
        for widget in self.scanned_pages_frame.winfo_children():
            widget.destroy()
        self.scanned_page_widgets = []
        self.scanned_image_references = [] 
        self.scanned_pages_frame.grid_remove() 
        self.scanned_pages_container.grid_remove()


    def open_image_preview(self, image_path):
        """ باز کردن پنجره ImageViewer برای نمایش عکس بزرگتر """
        master_geometry_string = self.winfo_toplevel().geometry()
        ImageViewer(master_geometry_string, image_path, self.ui_colors, self.base_font, self.button_font)


    def print_scanned_pages(self):
        """ باز کردن فایل‌های اسکن شده با نرم‌افزار پیش‌فرض سیستم برای پرینت. """
        if not self.scanned_pages_paths:
            messagebox.showwarning("هیچ فایلی برای پرینت نیست", "هیچ اسکن قراردادی برای پرینت آپلود نشده است.", master=self)
            return

        for file_path in self.scanned_pages_paths:
            if not os.path.exists(file_path):
                messagebox.showerror("فایل یافت نشد", f"فایل اسکن شده در مسیر '{file_path}' یافت نشد.", master=self)
                continue

            try:
                if sys.platform == "win32":
                    os.startfile(file_path, "print")
                elif sys.platform == "darwin": 
                    subprocess.run(["lp", file_path])
                else: 
                    subprocess.run(["lpr", file_path])
                messagebox.showinfo("دستور پرینت ارسال شد", f"دستور پرینت برای فایل '{os.path.basename(file_path)}' ارسال شد.", master=self)
            except Exception as e:
                messagebox.showerror("خطا در پرینت", f"خطا در ارسال دستور پرینت برای '{os.path.basename(file_path)}': {e}", master=self)

# --- بلاک تست مستقل UI ---
if __name__ == "__main__":
    root = ctk.CTk()
    root.title("مدیریت قراردادها EasyInvoice (تست مستقل)")
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
    
    from customer_manager import CustomerManager
    from models import Customer 

    cust_man = CustomerManager()
    if not cust_man.get_all_customers()[0]:
        cust_man.add_customer(Customer(name="شرکت الفا", customer_type="حقوقی", tax_id="11111111111", email="alpha@example.com"))
        cust_man.add_customer(Customer(name="آقای بتایی", customer_type="حقیقی", tax_id="0000000001", mobile="09123456789"))


    contract_frame = ContractUI(root, temp_db_manager, test_ui_colors, base_font_tuple, heading_font_tuple, button_font_tuple, nav_button_font_tuple)
    contract_frame.pack(fill="both", expand=True)

    root.mainloop()