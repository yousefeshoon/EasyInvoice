# main_app.py
import customtkinter as ctk
from tkinter import messagebox
import os
import sys
import configparser
from PIL import Image, ImageTk 

from db_manager import DBManager, DATABASE_NAME
from settings_ui import SettingsUI 
from customer_ui import CustomerUI
from contract_ui import ContractUI 
from invoice_manager_ui import InvoiceManagerUI # تغییر: Import InvoiceManagerUI بجای دوتا فایل جداگانه
from settings_manager import SettingsManager 
from invoice_template_manager import InvoiceTemplateManager # اضافه شد

class MainApplication(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.version_config_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version.ini")
        
        self.settings_manager = SettingsManager() 
        self.app_version_string = self._get_and_increment_build_version()
        self.title(f"سیستم آسان‌فاکتور (Easy Invoice) - {self.app_version_string}")

        self.update_idletasks() 
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        window_width = 1024
        window_height = 680 

        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2) 

        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.minsize(window_width, window_height)
        
        ctk.set_appearance_mode("light") 

        ctk.set_widget_scaling(1.0)
        default_font_family = "Vazirmatn"
        default_font_size = 14 

        self.base_font = (default_font_family, default_font_size)
        self.heading_font = (default_font_family, default_font_size + 2, "bold")
        self.button_font = (default_font_family, default_font_size + 1)
        self.nav_button_font = (default_font_family, default_font_size + 1, "bold")
        
        if getattr(sys, 'frozen', False):
            db_base_path = os.path.dirname(sys.executable)
        else:
            db_base_path = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(db_base_path, DATABASE_NAME)
        
        self.db_manager = DBManager(self.db_path)
        
        self.ui_colors = {
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
        
        self.app_logo_label = None 
        self.create_widgets()
        self.frames = {}
        self.init_frames()
        self.current_active_top_button = None 
        self.current_active_top_page_name = None 
        
        self.show_reports_page_on_start()
        self.load_and_display_logo() 

    def _read_version_data(self):
        """ مقادیر ورژن را از فایل version.ini می‌خواند. """
        config = configparser.ConfigParser()
        
        major = 1
        compile_c = 0
        build_c = 0
        try:
            if not os.path.exists(self.version_config_file_path):
                self._write_version_data(major, compile_c, build_c)
                config.read(self.version_config_file_path)
            else:
                config.read(self.version_config_file_path)

            major = config.getint('Version', 'MAJOR_VERSION', fallback=1)
            compile_c = config.getint('Version', 'COMPILE_COUNT', fallback=0)
            build_c = config.getint('Version', 'BUILD_COUNT', fallback=0)
        except Exception as e:
            print(f"Warning: Error reading version from {self.version_config_file_path}: {e}. Using default version (1.00(0)).")
            self._write_version_data(1, 0, 0)
            return 1, 0, 0
        return major, compile_c, build_c

    def _write_version_data(self, major, compile_c, build_c):
        """ مقادیر ورژن جدید را در فایل version.ini می‌نویسد. """
        config = configparser.ConfigParser()
        config['Version'] = {
            'MAJOR_VERSION': str(major),
            'COMPILE_COUNT': str(compile_c),
            'BUILD_COUNT': str(build_c)
        }
        try:
            with open(self.version_config_file_path, "w") as f:
                config.write(f)
        except Exception as e:
            print(f"Error writing new version data to {self.version_config_file_path}: {e}")

    def _get_and_increment_build_version(self):
        """
        ورژن را از فایل می‌خواند، BUILD_COUNT (BB) را افزایش می‌دهد، در فایل ذخیره می‌کند
        و ورژن کامل را به فرمت vX.YY(BB) باز می‌گرداند.
        این تابع هر بار که برنامه اصلی اجرا می‌شود (Run Count) فراخوانی می‌شود.
        """
        current_major, current_compile_c, current_build_c = self._read_version_data()
        
        current_build_c += 1
        
        self._write_version_data(current_major, current_compile_c, current_build_c)
        
        return f"v{current_major}.{current_compile_c:02d}({current_build_c})"

    def increment_compile_version(self):
        """
        COMPILE_COUNT (YY) را یک واحد افزایش داده (با مدیریت سرریز به Major)،
        در فایل ذخیره می‌کند و ورژن کامل را به فرمت vX.YY(BB) باز می‌گرداند.
        این تابع باید هنگام "کامپایل نهایی" برنامه (مثلاً با PyInstaller) فراخوانی شود.
        """
        current_major, current_compile_c, current_build_c = self._read_version_data()
        
        current_compile_c += 1
        if current_compile_c > 99: 
            current_major += 1
            current_compile_c = 0
            
        self._write_version_data(current_major, current_compile_c, current_build_c)
        
        return f"v{current_major}.{current_compile_c:02d}({current_build_c})"

    def load_and_display_logo(self):
        """ لوگوی فروشنده را بارگذاری کرده و در نوبار نمایش می‌دهد. """
        settings = self.settings_manager.get_settings()
        logo_path = settings.seller_logo_path
        
        if self.app_logo_label: 
            self.app_logo_label.destroy()
            self.app_logo_label = None

        if logo_path and os.path.exists(logo_path):
            try:
                image_pil = Image.open(logo_path)
                image_pil = image_pil.resize((50, 50), Image.LANCZOS) 
                ctk_image = ctk.CTkImage(light_image=image_pil, dark_image=image_pil, size=(50, 50))
                
                self.app_logo_label = ctk.CTkLabel(self.navbar_frame, image=ctk_image, text="")
                self.app_logo_label.grid(row=0, column=2, padx=20, pady=5, sticky="e") 
                self.app_logo_label.image = ctk_image 
                
            except Exception as e:
                print(f"Error loading logo for main app: {e}")
                self.app_logo_label = ctk.CTkLabel(self.navbar_frame, text="سیستم آسان‌فاکتور", font=self.heading_font, text_color=self.ui_colors["text_dark_gray"])
                self.app_logo_label.grid(row=0, column=2, padx=20, pady=10, sticky="e")
        else:
            self.app_logo_label = ctk.CTkLabel(self.navbar_frame, text="سیستم آسان‌فاکتور", font=self.heading_font, text_color=self.ui_colors["text_dark_gray"])
            self.app_logo_label.grid(row=0, column=2, padx=20, pady=10, sticky="e")


    def show_reports_page_on_start(self):
        """ نمایش صفحه گزارش اولیه هنگام شروع برنامه (صفحه سفید) """
        reports_placeholder_page = ctk.CTkFrame(self.content_frame, fg_color=self.ui_colors["white"], corner_radius=10)
        ctk.CTkLabel(reports_placeholder_page, text="گزارش اصلی برنامه (در دست ساخت)", font=self.heading_font, text_color=self.ui_colors["text_dark_gray"]).pack(pady=50)
        
        self.frames["reports"] = reports_placeholder_page
        self.show_frame("reports") # نمایش صفحه گزارشات به عنوان صفحه پیش فرض

    def create_widgets(self):
        """ ایجاد ویجت‌های اصلی برنامه (نوبار بالا و فریم کانتنت) """
        self.navbar_frame = ctk.CTkFrame(self, fg_color=self.ui_colors["background_light_gray"], corner_radius=0)
        self.navbar_frame.pack(side="top", fill="x", pady=0, padx=0) 

        self.navbar_frame.grid_columnconfigure(0, weight=1) 
        self.navbar_frame.grid_columnconfigure(1, weight=1) 
        self.navbar_frame.grid_columnconfigure(2, weight=1) 
        
        nav_buttons_container = ctk.CTkFrame(self.navbar_frame, fg_color="transparent") 
        nav_buttons_container.grid(row=0, column=1)
        
        nav_buttons_container.grid_columnconfigure(0, weight=1) 
        nav_buttons_container.grid_columnconfigure(1, weight=0) 
        nav_buttons_container.grid_columnconfigure(2, weight=0) 
        nav_buttons_container.grid_columnconfigure(3, weight=0) 
        nav_buttons_container.grid_columnconfigure(4, weight=0) 
        nav_buttons_container.grid_columnconfigure(5, weight=0) # این دیگه نیاز نیست، ولی برای حفظ گرید می‌تونیم نگهش داریم یا حذفش کنیم
        nav_buttons_container.grid_columnconfigure(6, weight=1) 

        self.settings_btn = ctk.CTkButton(nav_buttons_container, text="تنظیمات", 
                                          font=self.nav_button_font,
                                          fg_color=self.ui_colors["background_light_gray"], 
                                          text_color=self.ui_colors["text_medium_gray"],
                                          hover_color=self.ui_colors["hover_light_blue"], 
                                          corner_radius=8, 
                                          command=lambda: self.on_top_nav_button_click("settings", self.settings_btn))
        self.settings_btn.grid(row=0, column=1, padx=5, pady=0) 

        self.customers_btn = ctk.CTkButton(nav_buttons_container, text="مشتریان", 
                                           font=self.nav_button_font,
                                           fg_color=self.ui_colors["background_light_gray"], 
                                           text_color=self.ui_colors["text_medium_gray"],
                                           hover_color=self.ui_colors["hover_light_blue"],
                                           corner_radius=8,
                                           command=lambda: self.on_top_nav_button_click("customers", self.customers_btn))
        self.customers_btn.grid(row=0, column=2, padx=5, pady=0)
        self.contracts_btn = ctk.CTkButton(nav_buttons_container, text="مدیریت قراردادها", 
                                           font=self.nav_button_font,
                                           fg_color=self.ui_colors["background_light_gray"], 
                                           text_color=self.ui_colors["text_medium_gray"],
                                           hover_color=self.ui_colors["hover_light_blue"],
                                           corner_radius=8,
                                           command=lambda: self.on_top_nav_button_click("contracts", self.contracts_btn)) 
        self.contracts_btn.grid(row=0, column=3, padx=5, pady=0) 

        # دکمه جدید برای "مدیریت صورتحساب ها"
        self.invoice_manager_btn = ctk.CTkButton(nav_buttons_container, text="مدیریت صورتحساب‌ها", 
                                         font=self.nav_button_font,
                                         fg_color=self.ui_colors["background_light_gray"], 
                                         text_color=self.ui_colors["text_medium_gray"],
                                         hover_color=self.ui_colors["hover_light_blue"],
                                         corner_radius=8,
                                         command=lambda: self.on_top_nav_button_click("invoice_manager", self.invoice_manager_btn))
        self.invoice_manager_btn.grid(row=0, column=4, padx=5, pady=0) 
        
        # دکمه های "صدور صورتحساب" و "لیست صورتحساب‌ها" حذف شدند
        # self.invoice_main_btn و self.invoice_list_btn دیگر اینجا نیستند

        empty_placeholder_btn = ctk.CTkButton(self.navbar_frame, text="", 
                                         font=self.nav_button_font, 
                                         fg_color=self.ui_colors["background_light_gray"], 
                                         text_color=self.ui_colors["background_light_gray"], 
                                         hover_color=self.ui_colors["background_light_gray"], 
                                         corner_radius=8,
                                         width=150, 
                                         height=40, 
                                         state="disabled" 
                                         )
        empty_placeholder_btn.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        self.content_frame = ctk.CTkFrame(self, fg_color=self.ui_colors["background_light_gray"], corner_radius=0) 
        self.content_frame.pack(fill="both", expand=True, padx=0, pady=0)

        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

    def init_frames(self):
        """ مقداردهی اولیه فریم‌های UI مختلف و ذخیره آن‌ها در دیکشنری frames """
        settings_page = SettingsUI(self.content_frame, self.db_manager, self.ui_colors, 
                                   self.base_font, self.heading_font, self.button_font, self.nav_button_font)
        self.frames["settings"] = settings_page
        settings_page.grid(row=0, column=0, sticky="nsew")

        customer_page = CustomerUI(self.content_frame, self.db_manager, self.ui_colors,
                                   self.base_font, self.heading_font, self.button_font, self.nav_button_font)
        self.frames["customers"] = customer_page
        customer_page.grid(row=0, column=0, sticky="nsew")

        contract_page = ContractUI(self.content_frame, self.db_manager, self.ui_colors,
                                   self.base_font, self.heading_font, self.button_font, self.nav_button_font)
        self.frames["contracts"] = contract_page
        contract_page.grid(row=0, column=0, sticky="nsew")

        # اضافه شده: فریم UI مدیریت صورتحساب (که شامل زیرتب‌ها می‌شود)
        invoice_manager_page = InvoiceManagerUI(self.content_frame, self.db_manager, self.ui_colors,
                                   self.base_font, self.heading_font, self.button_font, self.nav_button_font)
        self.frames["invoice_manager"] = invoice_manager_page
        invoice_manager_page.grid(row=0, column=0, sticky="nsew")
        
        # فریم‌های invoice_main_ui و invoice_list_ui دیگر اینجا به صورت مستقیم مقداردهی اولیه نمی‌شوند


    def show_frame(self, page_name):
        """ نمایش یک فریم خاص بر اساس نام آن """
        frame = self.frames.get(page_name)
        if frame:
            frame.tkraise()
            self.current_active_top_page_name = page_name 

    def on_top_nav_button_click(self, page_name, clicked_button):
        """
        هندل کردن کلیک روی دکمه‌های نویگیشن اصلی.
        صفحه مورد نظر را نمایش داده و استایل دکمه فعال را تغییر می‌دهد.
        """
        target_frame = self.frames.get(page_name)

        if target_frame:
            if self.current_active_top_button:
                self.current_active_top_button.configure(
                    fg_color=self.ui_colors["background_light_gray"], 
                    text_color=self.ui_colors["text_medium_gray"],
                    border_width=0 
                )
            
            clicked_button.configure(
                fg_color=self.ui_colors["active_button_bg"], 
                text_color=self.ui_colors["active_button_text"],
                border_width=2, 
                border_color=self.ui_colors["active_button_border"] 
            )
            self.current_active_top_button = clicked_button 
            self.show_frame(page_name)
        else:
            messagebox.showwarning("صفحه هنوز پیاده‌سازی نشده", f"صفحه '{page_name}' هنوز در دست ساخت است.", master=self)
            
            if self.current_active_top_page_name:
                # این قسمت باید با توجه به ساختار جدید دکمه‌ها به‌روزرسانی شود
                # مطمئن شویم که دکمه فعال قبلی استایل خود را حفظ می‌کند
                active_button_ref = None
                if self.current_active_top_page_name == "settings":
                    active_button_ref = self.settings_btn
                elif self.current_active_top_page_name == "reports": 
                    pass # Reports has no dedicated button yet
                elif self.current_active_top_page_name == "customers":
                    active_button_ref = self.customers_btn
                elif self.current_active_top_page_name == "contracts":
                    active_button_ref = self.contracts_btn
                elif self.current_active_top_page_name == "invoice_manager":
                    active_button_ref = self.invoice_manager_btn
                
                if active_button_ref:
                    active_button_ref.configure(
                        fg_color=self.ui_colors["active_button_bg"], 
                        text_color=self.ui_colors["active_button_text"],
                        border_width=2, 
                        border_color=self.ui_colors["active_button_border"] 
                    )
                    self.current_active_top_button = active_button_ref
            

    def on_closing(self):
        """ تابعی که هنگام بسته شدن برنامه فراخالی می‌شود """
        if messagebox.askokcancel("خروج از برنامه", "آیا مطمئنید می‌خواهید خارج شوید؟", master=self):
            self.db_manager.close() 
            self.destroy()

    def _initialize_database(self):
        """
        این متد مسئول اتصال و راه‌اندازی دیتابیس است.
        در صورت بروز خطا، True را برمی‌گرداند تا برنامه ادامه یابد، در غیر این صورت False.
        """
        try:
            if not self.db_manager.connect():
                messagebox.showerror("خطا در اتصال به دیتابیس", "امکان اتصال به دیتابیس وجود ندارد! برنامه بسته خواهد شد.", master=self)
                return False
            
            self.db_manager.create_tables()
            self.db_manager.migrate_database()
            self.db_manager.close() 
            return True
        except Exception as e:
            messagebox.showerror("خطای راه‌اندازی دیتابیس", f"خطا در راه‌اندازی دیتابیس: {e}\nبرنامه بسته خواهد شد.", master=self)
            return False

if __name__ == "__main__":
    app = MainApplication()
    
    # قبل از تنظیم پروتکل یا شروع mainloop، دیتابیس را راه‌اندازی کن
    if not app._initialize_database():
        # اگر راه‌اندازی دیتابیس موفقیت آمیز نبود، برنامه را بدون خطا بستن
        sys.exit(1) # یا app.quit() اگر نیاز به مدیریت خاص‌تر بود

    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()