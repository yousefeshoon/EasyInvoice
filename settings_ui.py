# settings_ui.py
import customtkinter as ctk
from tkinter import messagebox, filedialog, ttk
import os
from PIL import Image, ImageTk 
import json
from bs4 import BeautifulSoup 
import re 
from collections import defaultdict 

from settings_manager import SettingsManager
from service_manager import ServiceManager
from models import AppSettings, Service, InvoiceTemplate 
from db_manager import DBManager, DATABASE_NAME
from invoice_template_manager import InvoiceTemplateManager 

class InvoiceTemplatePreviewWindow(ctk.CTkToplevel):
    def __init__(self, master, template: InvoiceTemplate, ui_colors, base_font, heading_font):
        super().__init__(master)
        self.template = template
        self.ui_colors = ui_colors
        self.base_font = base_font
        self.heading_font = heading_font
        self.title(f"پیش‌نمایش قالب: {template.template_name}")
        self.transient(master)
        self.grab_set()

        self.a4_width_pt = 595 # A4 width in points
        self.a4_height_pt = 842 # A4 height in points

        # Use A4 dimensions for window size, scaled down for preview
        window_width = int(self.a4_width_pt * 0.8) # Scale down for preview window
        window_height = int(self.a4_height_pt * 0.8)
        self.geometry(f"{window_width}x{window_height}")
        self.resizable(False, False)

        # فریم اصلی برای سازماندهی عناصر
        main_container_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=0)
        main_container_frame.pack(fill="both", expand=True)
        main_container_frame.grid_rowconfigure(0, weight=1) # Canvas for content
        main_container_frame.grid_columnconfigure(0, weight=1)

        # Canvas for drawing preview content
        self.canvas = ctk.CTkCanvas(main_container_frame, bg="white", highlightthickness=1, highlightbackground=self.ui_colors["border_gray"])
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Store references for images used on canvas
        self.canvas_image_refs = [] 

        self.after(50, self.draw_preview) # Small delay to ensure canvas dimensions are updated

        close_btn = ctk.CTkButton(self, text="بستن", command=self.destroy,
                                  font=self.base_font, fg_color="#999999", hover_color="#777777")
        close_btn.pack(pady=5)

    def draw_preview(self):
        self.canvas.delete("all")
        self.canvas_image_refs = [] # Clear image references

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1 or not self.winfo_exists():
            self.after(50, self.draw_preview)
            return
        
        # Scale factor from A4 points to canvas pixels
        scale_x = canvas_width / self.a4_width_pt
        scale_y = canvas_height / self.a4_height_pt
        
        # Draw background image if available
        if self.template.background_image_path and os.path.exists(self.template.background_image_path):
            try:
                bg_pil_image = Image.open(self.template.background_image_path) 
                bg_pil_image = bg_pil_image.resize((int(canvas_width), int(canvas_height)), Image.LANCZOS)
                
                if self.template.background_opacity < 1.0:
                    if bg_pil_image.mode != 'RGBA':
                        bg_pil_image = bg_pil_image.convert('RGBA')
                    alpha = bg_pil_image.split()[3] 
                    alpha = Image.eval(alpha, lambda x: x * self.template.background_opacity) 
                    bg_pil_image.putalpha(alpha) 
                        
                bg_tk_image = ImageTk.PhotoImage(bg_pil_image)
                self.canvas_image_refs.append(bg_tk_image) # Keep reference
                self.canvas.create_image(canvas_width/2, canvas_height/2, image=bg_tk_image)
            except Exception as e:
                print(f"Error loading background image for preview: {e}")
                self.canvas.create_text(canvas_width/2, canvas_height/2, text="خطا در بارگذاری بک‌گراند", font=self.base_font, fill="red")
        
        # Draw header image if available
        if self.template.header_image_path and os.path.exists(self.template.header_image_path):
            try:
                header_pil_image = Image.open(self.template.header_image_path)
                target_height = 80 * scale_y 
                ratio = header_pil_image.width / header_pil_image.height
                new_width = int(target_height * ratio)
                
                header_pil_image = header_pil_image.resize((new_width, int(target_height)), Image.LANCZOS)
                header_tk_image = ImageTk.PhotoImage(header_pil_image) 
                self.canvas_image_refs.append(header_tk_image) 
                
                x_pos = (canvas_width - new_width) / 2
                y_pos = 10 * scale_y 
                self.canvas.create_image(x_pos + new_width/2, y_pos + target_height/2, image=header_tk_image)

            except Exception as e:
                print(f"Error loading header image for preview: {e}")
                self.canvas.create_text(canvas_width/2, 30 * scale_y, text="خطا در بارگذاری هدر", font=self.base_font, fill="red")
        
        # Draw footer image if available
        if self.template.footer_image_path and os.path.exists(self.template.footer_image_path):
            try:
                footer_pil_image = Image.open(self.template.footer_image_path)
                target_height = 80 * scale_y 
                ratio = footer_pil_image.width / footer_pil_image.height
                new_width = int(target_height * ratio)
                
                footer_pil_image = footer_pil_image.resize((new_width, int(target_height)), Image.LANCZOS)
                footer_tk_image = ImageTk.PhotoImage(footer_pil_image) 
                self.canvas_image_refs.append(footer_tk_image) 
                
                x_pos = (canvas_width - new_width) / 2
                y_pos = canvas_height - (target_height + 10 * scale_y) 
                self.canvas.create_image(x_pos + new_width/2, y_pos + target_height/2, image=footer_tk_image)

            except Exception as e:
                print(f"Error loading footer image for preview: {e}")
                self.canvas.create_text(canvas_width/2, canvas_height - (30 * scale_y), text="خطا در بارگذاری فوتر", font=self.base_font, fill="red")

        # Draw static text elements from template_settings
        if 'static_text_elements' in self.template.template_settings:
            for element in self.template.template_settings['static_text_elements']:
                text = element.get('text', '')
                x_pdf = element.get('x_pos', 0) 
                y_pdf = element.get('y_pos', 0) 
                
                x_canvas = x_pdf * scale_x
                y_canvas = (self.a4_height_pt - y_pdf) * scale_y 

                align = element.get('align', 'right')
                font_size = int(element.get('font_size', 10) * min(scale_x, scale_y)) 
                font_bold = element.get('font_bold', False)
                
                # Replace placeholders with their names for preview
                text_for_display = re.sub(r'\{\{([a-zA-Z0-9_]+)\}\}', r'<\1>', text) 

                anchor_map = {
                    'left': 'w',    # West (left aligned text, anchor on left)
                    'right': 'e',   # East (right aligned text, anchor on right)
                    'center': 'center'
                }
                anchor = anchor_map.get(align, 'e') # Default to right

                font_tuple = (self.base_font[0], font_size, "bold" if font_bold else "")
                
                self.canvas.create_text(x_canvas, y_canvas, text=text_for_display, font=font_tuple, anchor=anchor, fill="black")

        # Draw placeholder for table if table_configs is present
        if 'table_configs' in self.template.template_settings:
            table_config = self.template.template_settings['table_configs'].get('invoice_items_table', {})
            x_start_pdf = table_config.get('x_start', 50)
            y_start_pdf = table_config.get('y_start', 400) 
            width_pdf = table_config.get('width', 500)
            row_height_pdf = table_config.get('row_height', 20)

            x_start_canvas = x_start_pdf * scale_x
            y_start_canvas = (self.a4_height_pt - y_start_pdf) * scale_y 
            width_canvas = width_pdf * scale_x
            
            total_table_height_canvas = (5 * row_height_pdf) * scale_y # Example: header + 4 item rows
            
            self.canvas.create_rectangle(x_start_canvas, y_start_canvas, x_start_canvas + width_canvas, y_start_canvas + total_table_height_canvas, outline="gray", width=1)
            # No general text like "جدول آیتم‌ها (پیش‌نمایش)" unless explicitly defined in HTML
            
            # Draw table headers (placeholders if defined in JSON)
            if 'header_elements' in table_config:
                for header_el in table_config['header_elements']:
                    header_text = header_el.get('text', '')
                    header_x_offset_pdf = header_el.get('x_offset', 0)
                    header_align = header_el.get('align', 'right')
                    header_font_size = int(header_el.get('font_size', 10) * min(scale_x, scale_y))
                    header_font_bold = header_el.get('font_bold', False)

                    header_x_canvas = (x_start_pdf + header_x_offset_pdf) * scale_x
                    header_y_canvas = y_start_canvas + (row_height_pdf * 0.5) * scale_y # Center vertically in header row

                    header_font_tuple = (self.base_font[0], header_font_size, "bold" if header_font_bold else "")
                    
                    header_anchor_map = {
                        'left': 'w',
                        'right': 'e',
                        'center': 'center'
                    }
                    header_anchor = header_anchor_map.get(header_align, 'e')
                    
                    self.canvas.create_text(header_x_canvas, header_y_canvas, text=header_text, font=header_font_tuple, anchor=header_anchor, fill="black")

            # Draw sample item rows (placeholders)
            if 'item_field_configs' in table_config:
                sample_item_data = {
                    'item_row_num': '۱',
                    'item_service_description': 'شرح نمونه خدمت',
                    'item_quantity': '۱',
                    'item_unit_price': '۱,۰۰۰',
                    'item_total_price': '۱,۰۰۰'
                }
                for i in range(1, 5): # 4 sample rows
                    row_y_canvas = y_start_canvas + (i * row_height_pdf) * scale_y + (row_height_pdf * 0.5 * scale_y) # Center in row
                    for field_config in table_config['item_field_configs']:
                        field_name = field_config.get('field', '')
                        x_offset_pdf = field_config.get('x_offset', 0)
                        item_align = field_config.get('align', 'right')
                        item_font_size = int(field_config.get('font_size', 10) * min(scale_x, scale_y))
                        item_font_bold = field_config.get('font_bold', False)

                        item_x_canvas = (x_start_pdf + x_offset_pdf) * scale_x
                        
                        item_text = sample_item_data.get(field_name, f'<{field_name}>') # Use placeholder name if not found
                        item_font_tuple = (self.base_font[0], item_font_size, "bold" if item_font_bold else "")
                        item_anchor = anchor_map.get(item_align, 'e')

                        self.canvas.create_text(item_x_canvas, row_y_canvas, text=item_text, font=item_font_tuple, anchor=item_anchor, fill="black")

        # Draw signature block (if defined in JSON)
        if 'signature_block_config' in self.template.template_settings:
            sig_config = self.template.template_settings['signature_block_config']
            
            seller_x_pdf = sig_config.get('seller_signature_x', None)
            seller_y_pdf = sig_config.get('seller_signature_y', None)
            buyer_x_pdf = sig_config.get('buyer_signature_x', None)
            buyer_y_pdf = sig_config.get('buyer_signature_y', None)

            font_size_sig = int(10 * min(scale_x, scale_y))
            font_tuple_sig = (self.base_font[0], font_size_sig, "bold")

            if seller_x_pdf is not None and seller_y_pdf is not None:
                seller_x_canvas = seller_x_pdf * scale_x
                seller_y_canvas = (self.a4_height_pt - seller_y_pdf) * scale_y
                self.canvas.create_text(seller_x_canvas, seller_y_canvas - (15 * scale_y), text="امضا و مهر فروشنده", font=font_tuple_sig, anchor="center", fill="black")
                self.canvas.create_line(seller_x_canvas - (50 * scale_x), seller_y_canvas, seller_x_canvas + (50 * scale_x), seller_y_canvas, fill="black")

            if buyer_x_pdf is not None and buyer_y_pdf is not None:
                buyer_x_canvas = buyer_x_pdf * scale_x
                buyer_y_canvas = (self.a4_height_pt - buyer_y_pdf) * scale_y
                self.canvas.create_text(buyer_x_canvas, buyer_y_canvas - (15 * scale_y), text="امضا و مهر خریدار", font=font_tuple_sig, anchor="center", fill="black")
                self.canvas.create_line(buyer_x_canvas - (50 * scale_x), buyer_y_canvas, buyer_x_canvas + (50 * scale_x), buyer_y_canvas, fill="black")


class SettingsUI(ctk.CTkFrame):
    def __init__(self, parent, db_manager, ui_colors, base_font, heading_font, button_font, nav_button_font):
        super().__init__(parent, fg_color="transparent")
        self.parent = parent
        self.db_manager = db_manager
        self.settings_manager = SettingsManager()
        self.service_manager = ServiceManager()
        self.invoice_template_manager = InvoiceTemplateManager()
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
        self.service_code_var = None
        self.service_table = None

        self.selected_template_id = None
        self.template_name_var = ctk.StringVar()
        self.template_type_var = ctk.StringVar(value="PDF_Standard") 

        self.available_invoice_fields = [
            "invoice_number", "customer_name", "customer_tax_id", "issue_date", "due_date", 
            "total_amount", "discount_percentage", "tax_percentage", "final_amount", "description",
            "item_service_description", "item_quantity", "item_unit_price", "item_total_price", 
            "seller_name", "seller_address", "seller_phone", "seller_tax_id", "seller_economic_code", 
            "contract_number", "contract_title", "contract_date", "contract_total_amount", "contract_description", "contract_payment_method"
        ]
        self.required_fields_vars = {} 

        self.header_image_path_var = ctk.StringVar()
        self.footer_image_path_var = ctk.StringVar()
        self.background_image_path_var = ctk.StringVar()
        self.background_opacity_var = ctk.DoubleVar(value=1.0) 
        self.is_active_var = ctk.IntVar(value=1) 

        self.template_table = None
        self.delete_template_button = None
        self.preview_template_button = None 
        
        self.template_settings_textbox = None 
        
        self.create_widgets()
        
        self.current_active_sub_button = None
        self.current_active_sub_page_name = None
        
        self.after(100, lambda: self.on_sub_nav_button_click("seller_info", self.seller_info_btn))


    def create_widgets(self):
        """ ایجاد ویجت‌های مربوط به تنظیمات برنامه را ایجاد می‌کند. """
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
        self.sub_navbar_frame.grid_rowconfigure(0, weight=1)
        self.sub_navbar_frame.grid_columnconfigure(0, weight=1)
        self.sub_navbar_frame.grid_columnconfigure(1, weight=0)
        self.sub_navbar_frame.grid_columnconfigure(2, weight=1)
        
        sub_buttons_container = ctk.CTkFrame(self.sub_navbar_frame, fg_color="transparent")
        sub_buttons_container.grid(row=0, column=1, sticky="nsew")
        
        sub_buttons_container.grid_columnconfigure(0, weight=0)
        sub_buttons_container.grid_columnconfigure(1, weight=0)
        sub_buttons_container.grid_columnconfigure(2, weight=0) 
        sub_buttons_container.grid_rowconfigure(0, weight=1)
        
        self.seller_info_btn = ctk.CTkButton(sub_buttons_container, text="اطلاعات فروشنده", 
                                              font=self.nav_button_font,
                                              fg_color=self.ui_colors["white"], 
                                              text_color=self.ui_colors["text_medium_gray"],
                                              hover_color=self.ui_colors["hover_light_blue"],
                                              corner_radius=8,
                                              command=lambda: self.on_sub_nav_button_click("seller_info", self.seller_info_btn))
        self.seller_info_btn.grid(row=0, column=2, padx=5, pady=10)

        self.service_types_btn = ctk.CTkButton(sub_buttons_container, text="انواع خدمات", 
                                                font=self.nav_button_font, 
                                                fg_color=self.ui_colors["white"], 
                                                text_color=self.ui_colors["text_medium_gray"],
                                                hover_color=self.ui_colors["hover_light_blue"],
                                                corner_radius=8,
                                                command=lambda: self.on_sub_nav_button_click("service_types", self.service_types_btn))
        self.service_types_btn.grid(row=0, column=1, padx=5, pady=10)

        self.invoice_templates_btn = ctk.CTkButton(sub_buttons_container, text="مدیریت قالب صورتحساب", 
                                                font=self.nav_button_font, 
                                                fg_color=self.ui_colors["white"], 
                                                text_color=self.ui_colors["text_medium_gray"],
                                                hover_color=self.ui_colors["hover_light_blue"],
                                                corner_radius=8,
                                                command=lambda: self.on_sub_nav_button_click("invoice_templates", self.invoice_templates_btn))
        self.invoice_templates_btn.grid(row=0, column=0, padx=5, pady=10)


        self.settings_content_frame = ctk.CTkFrame(settings_card_frame, fg_color="white") 
        self.settings_content_frame.grid(row=1, column=0, padx=20, pady=(20, 20), sticky="nsew") 
        self.settings_content_frame.grid_rowconfigure(0, weight=1)
        self.settings_content_frame.grid_columnconfigure(0, weight=1)

        self.seller_info_form = self.create_seller_info_form(self.settings_content_frame)
        self.frames["seller_info"] = self.seller_info_form
        self.seller_info_form.grid(row=0, column=0, sticky="nsew")

        self.service_types_page = self.create_service_types_form(self.settings_content_frame) 
        self.frames["service_types"] = self.service_types_page
        self.service_types_page.grid(row=0, column=0, sticky="nsew")

        self.invoice_templates_page = self.create_invoice_templates_form(self.settings_content_frame)
        self.frames["invoice_templates"] = self.invoice_templates_page
        self.invoice_templates_page.grid(row=0, column=0, sticky="nsew")


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
            ("نام فروشنده", "seller_name", "entry"), 
            ("آدرس", "seller_address", "entry"),     
            ("تلفن", "seller_phone", "entry"),       
            ("شناسه ملی", "seller_tax_id", "entry"),    
            ("کد اقتصادی", "seller_economic_code", "entry"), 
            ("لوگو", "seller_logo_path", "logo")     
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

        service_types_frame.grid_columnconfigure(0, weight=1) 
        service_types_frame.grid_columnconfigure(1, weight=0) 
        service_types_frame.grid_rowconfigure(0, weight=1) 

        form_frame = ctk.CTkFrame(service_types_frame, fg_color="white", corner_radius=10, 
                                  border_width=1, border_color=self.ui_colors["border_gray"])
        form_frame.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="nsew") 
        
        form_frame.grid_columnconfigure(0, weight=1) 
        form_frame.grid_columnconfigure(1, weight=0) 
        
        form_title_label = ctk.CTkLabel(form_frame, text="خدمت جدید / ویرایش خدمت", 
                                        font=self.heading_font, text_color=self.ui_colors["text_dark_gray"])
        form_title_label.grid(row=0, column=0, columnspan=2, padx=20, pady=15, sticky="e")

        ctk.CTkLabel(form_frame, text="کد خدمت", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=1, column=1, padx=10, pady=10, sticky="e")
        self.service_code_var = ctk.StringVar()
        service_code_entry = ctk.CTkEntry(form_frame, textvariable=self.service_code_var, width=250, justify="right",
                                          font=self.base_font, fg_color="#f8f8f8", border_color=self.ui_colors["border_gray"], corner_radius=5)
        service_code_entry.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(form_frame, text="شرح خدمت", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=2, column=1, padx=10, pady=10, sticky="e")
        self.service_description_var = ctk.StringVar() 
        description_entry = ctk.CTkEntry(form_frame, textvariable=self.service_description_var, width=250, justify="right",
                                         font=self.base_font, fg_color="#f8f8f8", border_color=self.ui_colors["border_gray"], corner_radius=5)
        description_entry.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        buttons_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        buttons_frame.grid(row=3, column=0, columnspan=2, pady=20) 
        
        save_button = ctk.CTkButton(buttons_frame, text="ذخیره", 
                                    font=self.button_font, fg_color=self.ui_colors["accent_blue"], 
                                    hover_color=self.ui_colors["accent_blue_hover"], text_color="white", corner_radius=8,
                                    command=self.save_service)
        save_button.pack(side="right", padx=5) 
        
        clear_button = ctk.CTkButton(buttons_frame, text="جدید", 
                                     font=self.button_font, fg_color="#999999", 
                                     hover_color="#777777", text_color="white", corner_radius=8,
                                     width=60, 
                                     height=30, 
                                     command=self.clear_service_form) 
        clear_button.pack(side="right", padx=5) 

        self.delete_service_button = ctk.CTkButton(buttons_frame, text="حذف", 
                                           font=self.button_font, fg_color="#dc3545", 
                                           hover_color="#c82333", text_color="white", corner_radius=8,
                                           width=60, 
                                           height=30, 
                                           command=self.delete_service_from_db, state="disabled") 
        self.delete_service_button.pack(side="left", padx=5) 

        table_frame = ctk.CTkFrame(service_types_frame, fg_color="white", corner_radius=10, 
                                   border_width=1, border_color=self.ui_colors["border_gray"])
        table_frame.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew") 
        
        table_frame.grid_rowconfigure(0, weight=1) 
        table_frame.grid_columnconfigure(0, weight=1)

        self.tree_scrollbar = ctk.CTkScrollbar(table_frame)
        self.tree_scrollbar.pack(side="right", fill="y")
        
        self.service_table = ttk.Treeview(table_frame, columns=("ID", "Code", "Description"), show="headings", 
                                           yscrollcommand=self.tree_scrollbar.set)
        self.service_table.pack(fill="both", expand=True)

        self.tree_scrollbar.configure(command=self.service_table.yview)

        self.service_table.heading("ID", text="شناسه", anchor="e") 
        self.service_table.heading("Code", text="کد خدمت", anchor="e") 
        self.service_table.heading("Description", text="شرح خدمت", anchor="e")

        self.service_table.column("ID", width=0, stretch=False) 
        self.service_table.column("Code", width=80, anchor="e", stretch=False) 
        self.service_table.column("Description", width=200, anchor="e", stretch=True) 

        self.service_table.bind("<<TreeviewSelect>>", self.on_service_select) 
        self.service_table.bind("<Double-1>", self.on_service_double_click) 

        tree_style = ttk.Style()
        tree_style.configure("Treeview", font=self.base_font, rowheight=25) 
        tree_style.configure("Treeview.Heading", font=self.button_font) 
        tree_style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nsew'})]) 

        self.load_services_to_table() 
        
        return service_types_frame 

    def create_invoice_templates_form(self, parent_frame):
        """ ایجاد فرم و جدول برای مدیریت قالب‌های صورتحساب """
        template_types_frame = ctk.CTkFrame(parent_frame, fg_color="white")
        template_types_frame.grid(row=0, column=0, sticky="nsew")
        parent_frame.grid_rowconfigure(0, weight=1)
        parent_frame.grid_columnconfigure(0, weight=1)

        template_types_frame.grid_columnconfigure(0, weight=1)
        template_types_frame.grid_columnconfigure(1, weight=1) 
        template_types_frame.grid_rowconfigure(0, weight=1)

        template_form_scroll_frame = ctk.CTkScrollableFrame(template_types_frame, fg_color="white", corner_radius=10, 
                                  border_width=1, border_color=self.ui_colors["border_gray"])
        template_form_scroll_frame.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="nsew")
        
        # پیکربندی ستون‌های داخلی ScrollableFrame
        template_form_scroll_frame.grid_columnconfigure(0, weight=1) 
        template_form_scroll_frame.grid_columnconfigure(1, weight=0) 

        form_title_label = ctk.CTkLabel(template_form_scroll_frame, text="قالب صورتحساب جدید / ویرایش قالب", 
                                        font=self.heading_font, text_color=self.ui_colors["text_dark_gray"])
        form_title_label.grid(row=0, column=0, columnspan=2, padx=20, pady=15, sticky="e")

        ctk.CTkLabel(template_form_scroll_frame, text="نام قالب", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=1, column=1, padx=10, pady=10, sticky="e")
        ctk.CTkEntry(template_form_scroll_frame, textvariable=self.template_name_var, width=250, justify="right",
                     font=self.base_font, fg_color="#f8f8f8", border_color=self.ui_colors["border_gray"], corner_radius=5).grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(template_form_scroll_frame, text="نوع قالب", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=2, column=1, padx=10, pady=10, sticky="e")
        ctk.CTkComboBox(template_form_scroll_frame, values=["PDF_Standard", "PDF_Tax", "HTML_Simple"], variable=self.template_type_var, width=250, justify="right",
                        font=self.base_font, fg_color="#f8f8f8", border_color=self.ui_colors["border_gray"], corner_radius=5).grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(template_form_scroll_frame, text="قالب فعال است؟", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=3, column=1, padx=10, pady=10, sticky="e")
        ctk.CTkCheckBox(template_form_scroll_frame, text="", variable=self.is_active_var, onvalue=1, offvalue=0,
                        font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=3, column=0, padx=10, pady=10, sticky="e")


        # Required Fields Checkboxes (still needed for UI)
        ctk.CTkLabel(template_form_scroll_frame, text="فیلدهای الزامی:", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=4, column=1, padx=10, pady=10, sticky="ne")
        required_fields_checkbox_frame = ctk.CTkScrollableFrame(template_form_scroll_frame, width=250, height=120, fg_color="#f8f8f8",
                                                                border_color=self.ui_colors["border_gray"], corner_radius=5)
        required_fields_checkbox_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")

        for i, field in enumerate(self.available_invoice_fields):
            var = ctk.IntVar()
            chk = ctk.CTkCheckBox(required_fields_checkbox_frame, text=field.replace("_", " ").title(), variable=var,
                                  font=self.base_font, text_color=self.ui_colors["text_dark_gray"])
            chk.pack(anchor="w", pady=2, padx=5)
            self.required_fields_vars[field] = var

        row_idx = 5 

        # Upload HTML Template section
        ctk.CTkLabel(template_form_scroll_frame, text="آپلود قالب HTML:", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_idx, column=1, padx=10, pady=5, sticky="e")
        upload_html_frame = ctk.CTkFrame(template_form_scroll_frame, fg_color="transparent")
        upload_html_frame.grid(row=row_idx, column=0, padx=10, pady=5, sticky="ew")
        upload_html_btn = ctk.CTkButton(upload_html_frame, text="انتخاب فایل HTML", font=(self.base_font[0], self.base_font[1]-1),
                                        command=self.upload_html_template)
        upload_html_btn.pack(side="right", fill="x", expand=True)
        row_idx += 1


        ctk.CTkLabel(template_form_scroll_frame, text="تنظیمات قالب (JSON):", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_idx, column=1, padx=10, pady=10, sticky="ne")
        self.template_settings_textbox = ctk.CTkTextbox(template_form_scroll_frame, width=350, height=200, font=(self.base_font[0], 11),
                                                       fg_color="#f8f8f8", border_color=self.ui_colors["border_gray"], corner_radius=5, wrap="word")
        self.template_settings_textbox.grid(row=row_idx, column=0, padx=10, pady=10, sticky="ew")
        row_idx += 1


        ctk.CTkLabel(template_form_scroll_frame, text="عکس هدر", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_idx, column=1, padx=10, pady=5, sticky="e")
        header_img_frame = ctk.CTkFrame(template_form_scroll_frame, fg_color="transparent")
        header_img_frame.grid(row=row_idx, column=0, padx=10, pady=5, sticky="ew")
        ctk.CTkEntry(header_img_frame, textvariable=self.header_image_path_var, width=200, justify="left", font=self.base_font, state="readonly").pack(side="right", expand=True, fill="x", padx=(0,5))
        ctk.CTkButton(header_img_frame, text="انتخاب", font=(self.base_font[0], self.base_font[1]-1), command=lambda: self.select_image_file(self.header_image_path_var)).pack(side="right")
        row_idx += 1

        ctk.CTkLabel(template_form_scroll_frame, text="عکس فوتر", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_idx, column=1, padx=10, pady=5, sticky="e")
        footer_img_frame = ctk.CTkFrame(template_form_scroll_frame, fg_color="transparent")
        footer_img_frame.grid(row=row_idx, column=0, padx=10, pady=5, sticky="ew")
        ctk.CTkEntry(footer_img_frame, textvariable=self.footer_image_path_var, width=200, justify="left", font=self.base_font, state="readonly").pack(side="right", expand=True, fill="x", padx=(0,5))
        ctk.CTkButton(footer_img_frame, text="انتخاب", font=(self.base_font[0], self.base_font[1]-1), command=lambda: self.select_image_file(self.footer_image_path_var)).pack(side="right")
        row_idx += 1
        
        # Disabled background image and opacity fields (now controlled by HTML/JSON via template_settings)
        ctk.CTkLabel(template_form_scroll_frame, text="عکس بک‌گراند", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_idx, column=1, padx=10, pady=5, sticky="e")
        bg_img_frame = ctk.CTkFrame(template_form_scroll_frame, fg_color="transparent")
        bg_img_frame.grid(row=row_idx, column=0, padx=10, pady=5, sticky="ew")
        ctk.CTkEntry(bg_img_frame, textvariable=self.background_image_path_var, width=200, justify="left", font=self.base_font, state="readonly").pack(side="right", expand=True, fill="x", padx=(0,5))
        ctk.CTkButton(bg_img_frame, text="انتخاب", font=(self.base_font[0], self.base_font[1]-1), command=lambda: self.select_image_file(self.background_image_path_var), state="disabled").pack(side="right")
        row_idx += 1

        ctk.CTkLabel(template_form_scroll_frame, text="شفافیت بک‌گراند (0-1)", font=self.base_font, text_color=self.ui_colors["text_dark_gray"]).grid(row=row_idx, column=1, padx=10, pady=5, sticky="e")
        ctk.CTkEntry(template_form_scroll_frame, textvariable=self.background_opacity_var, width=100, justify="right",
                     font=self.base_font, fg_color="#f8f8f8", border_color=self.ui_colors["border_gray"], corner_radius=5, state="readonly").grid(row=row_idx, column=0, padx=10, pady=5, sticky="e")
        row_idx += 1


        buttons_frame = ctk.CTkFrame(template_form_scroll_frame, fg_color="transparent")
        buttons_frame.grid(row=row_idx, column=0, columnspan=2, pady=20)
        
        save_button = ctk.CTkButton(buttons_frame, text="ذخیره", 
                                    font=self.button_font, fg_color=self.ui_colors["accent_blue"], 
                                    hover_color=self.ui_colors["accent_blue_hover"], text_color="white", corner_radius=8,
                                    command=self.save_invoice_template)
        save_button.pack(side="right", padx=5) 
        
        clear_button = ctk.CTkButton(buttons_frame, text="جدید", 
                                     font=self.button_font, fg_color="#999999", 
                                     hover_color="#777777", text_color="white", corner_radius=8,
                                     width=60, 
                                     height=30, 
                                     command=self.clear_template_form) 
        clear_button.pack(side="right", padx=5) 

        self.delete_template_button = ctk.CTkButton(buttons_frame, text="حذف", 
                                           font=self.button_font, fg_color="#dc3545", 
                                           hover_color="#c82333", text_color="white", corner_radius=8,
                                           width=60, 
                                           height=30, 
                                           command=self.delete_invoice_template_from_db, state="disabled") 
        self.delete_template_button.pack(side="left", padx=5) 

        self.preview_template_button = ctk.CTkButton(buttons_frame, text="پیش‌نمایش", 
                                            font=self.button_font, fg_color=self.ui_colors["accent_blue"], 
                                            hover_color=self.ui_colors["accent_blue_hover"], text_color="white", corner_radius=8,
                                            command=self.preview_invoice_template, state="disabled")
        self.preview_template_button.pack(side="left", padx=5)


        table_frame = ctk.CTkFrame(template_types_frame, fg_color="white", corner_radius=10, 
                                   border_width=1, border_color=self.ui_colors["border_gray"])
        table_frame.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew") 
        
        table_frame.grid_rowconfigure(0, weight=1) 
        table_frame.grid_columnconfigure(0, weight=1)

        self.template_tree_scrollbar = ctk.CTkScrollbar(table_frame)
        self.template_tree_scrollbar.pack(side="right", fill="y")
        
        self.template_table = ttk.Treeview(table_frame, columns=("ID", "Name", "Type", "Active"), show="headings", 
                                           yscrollcommand=self.template_tree_scrollbar.set)
        self.template_table.pack(fill="both", expand=True)

        self.template_tree_scrollbar.configure(command=self.template_table.yview)

        self.template_table.heading("ID", text="شناسه", anchor="e") 
        self.template_table.heading("Name", text="نام قالب", anchor="e") 
        self.template_table.heading("Type", text="نوع", anchor="e")
        self.template_table.heading("Active", text="فعال", anchor="e")

        self.template_table.column("ID", width=0, stretch=False) 
        self.template_table.column("Name", width=150, anchor="e", stretch=True) 
        self.template_table.column("Type", width=100, anchor="e", stretch=False) 
        self.template_table.column("Active", width=50, anchor="center", stretch=False) 

        self.template_table.bind("<<TreeviewSelect>>", self.on_template_select) 
        self.template_table.bind("<Double-1>", self.on_template_double_click) 

        tree_style = ttk.Style()
        tree_style.configure("Treeview", font=self.base_font, rowheight=25) 
        tree_style.configure("Treeview.Heading", font=self.button_font) 
        tree_style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nsew'})]) 

        self.load_invoice_templates_to_table()
        self.clear_template_form()
        
        return template_types_frame

    def select_image_file(self, target_var):
        """ باز کردن دیالوگ انتخاب فایل برای تصاویر (هدر، فوتر، بک‌گراند) """
        file_path = filedialog.askopenfilename(
            title="انتخاب فایل تصویر",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")],
            master=self 
        )
        if file_path:
            target_var.set(file_path)

    def select_logo_file(self):
        """ باز کردن دیالوگ انتخاب فایل برای لوگو (متد موجود) """
        file_path = filedialog.askopenfilename(
            title="انتخاب فایل لوگو",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")],
            master=self 
        )
        if file_path:
            self.logo_path_var.set(file_path)
            self.display_logo_preview(file_path)
            if hasattr(self.parent, 'master') and hasattr(self.parent.master, 'load_and_display_logo'):
                self.parent.master.load_and_display_logo()

    def display_logo_preview(self, file_path):
        """ نمایش پیش‌نمایش لوگو در UI (متد موجود) """
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
            if hasattr(self.parent, 'master') and hasattr(self.parent.master, 'load_and_display_logo'):
                self.parent.master.load_and_display_logo()
        else:
            messagebox.showerror("خطا در ذخیره تنظیمات", "خطا در ذخیره تنظیمات.", master=self)

    def load_services_to_table(self):
        """ بارگذاری خدمات از دیتابیس به جدول (در فرم خدمات) """
        for item in self.service_table.get_children():
            self.service_table.delete(item) 

        services, message = self.service_manager.get_all_services()
        if not services:
            pass 

        for service in services:
            self.service_table.insert("", "end", iid=service.id, 
                                     values=(service.id, service.service_code, service.description))

    def clear_service_form(self):
        """ پاک کردن فیلدهای فرم خدمات و غیرفعال کردن دکمه حذف """
        self.service_description_var.set("")
        self.service_code_var.set(str(self.service_manager.get_next_service_code()))
        self.selected_service_id = None
        self.delete_service_button.configure(state="disabled") 

    def save_service(self):
        """ ذخیره (افزودن/ویرایش) خدمت در دیتابیس """
        description = self.service_description_var.get().strip()
        service_code_str = self.service_code_var.get().strip()
        service_code = None

        if service_code_str:
            try:
                service_code = int(service_code_str)
            except ValueError:
                messagebox.showwarning("خطای ورودی", "کد خدمت باید یک عدد باشد.", master=self)
                return
        else: # اگر کد خدمت وارد نشده بود، به صورت خودکار تولید شود
            service_code = self.service_manager.get_next_service_code()


        if not description:
            messagebox.showwarning("خطای ورودی", "شرح خدمت نمی‌تواند خالی باشد.", master=self)
            return
        
        if self.selected_service_id: 
            service_obj = Service(id=self.selected_service_id, service_code=service_code, description=description)
            success, message = self.service_manager.update_service(service_obj)
        else: 
            service_obj = Service(service_code=service_code, description=description)
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

    # اضافه شدن متدهای on_service_select و on_service_double_click
    def on_service_select(self, event):
        """ رویداد انتخاب سطر در جدول خدمات (تک کلیک) """
        selected_items = self.service_table.selection()
        if selected_items:
            selected_item_id = selected_items[0]
            service_id = int(selected_item_id)
            service_obj, _ = self.service_manager.get_service_by_id(service_id)

            if service_obj:
                self.selected_service_id = service_obj.id
                self.service_code_var.set(str(service_obj.service_code))
                self.service_description_var.set(service_obj.description)
                self.delete_service_button.configure(state="normal")
        else:
            self.clear_service_form()

    def on_service_double_click(self, event):
        """ رویداد دابل کلیک روی سطر در جدول خدمات """
        self.on_service_select(event)


    def upload_html_template(self):
        """ باز کردن دیالوگ انتخاب فایل HTML و تبدیل آن به JSON برای template_settings """
        file_path = filedialog.askopenfilename(
            title="انتخاب فایل HTML قالب",
            filetypes=[("HTML files", "*.html *.htm"), ("All files", "*.*")],
            master=self 
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                template_settings_json = self.html_to_template_settings(html_content)
                self.template_settings_textbox.delete("1.0", "end")
                self.template_settings_textbox.insert("1.0", json.dumps(template_settings_json, indent=4, ensure_ascii=False))
                messagebox.showinfo("موفقیت", "فایل HTML با موفقیت بارگذاری و به JSON تبدیل شد.", master=self)

            except Exception as e:
                messagebox.showerror("خطا در بارگذاری/تبدیل HTML", f"خطا: {e}\nلطفاً از فرمت صحیح HTML و CSS مطمئن شوید.", master=self)

    def html_to_template_settings(self, html_content: str) -> dict:
        """
        این تابع HTML را تجزیه کرده و آن را به فرمت JSON برای template_settings تبدیل می‌کند.
        فقط عناصر با position: absolute و استایل‌های مربوطه را استخراج می‌کند.
        
        Args:
            html_content (str): محتوای کامل فایل HTML.
            
        Returns:
            dict: دیکشنری شامل template_settings در قالب JSON.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        static_text_elements = []
        
        a4_width_pt = 595
        a4_height_pt = 842 

        # Extract elements with position: absolute
        for el in soup.find_all(style=re.compile(r'position:\s*absolute')):
            style = el.get('style', '')
            
            left_match = re.search(r'left:\s*(\d+\.?\d*)\s*(pt|px|em)?', style)
            top_match = re.search(r'top:\s*(\d+\.?\d*)\s*(pt|px|em)?', style)
            right_match = re.search(r'right:\s*(\d+\.?\d*)\s*(pt|px|em)?', style)
            
            x_pos = 0.0
            
            if left_match:
                x_pos = float(left_match.group(1))
            elif right_match:
                right_val = float(right_match.group(1))
                x_pos = a4_width_pt - right_val # For 'right' alignment, this is the position of the right edge of the text.
            
            y_pos_html = 0.0 
            if top_match:
                y_pos_html = float(top_match.group(1))
            
            y_pos_pdf = a4_height_pt - y_pos_html # Convert HTML top-origin to PDF bottom-origin

            font_size_match = re.search(r'font-size:\s*(\d+\.?\d*)\s*(pt|px|em)?', style)
            font_size = float(font_size_match.group(1)) if font_size_match else 10 
            
            font_bold = False
            font_weight_match = re.search(r'font-weight:\s*(bold|700)', style)
            if font_weight_match:
                font_bold = True
            
            text_align_match = re.search(r'text-align:\s*(left|right|center)', style)
            align = text_align_match.group(1) if text_align_match else 'right' 

            text_content = el.get_text(strip=True)
            placeholders = re.findall(r'\{\{([a-zA-Z0-9_]+)\}\}', text_content)
            
            element_data = {
                "text": text_content,
                "x_pos": round(x_pos, 2),
                "y_pos": round(y_pos_pdf, 2),
                "align": align,
                "font_size": font_size,
                "font_bold": font_bold,
                "can_contain_field": bool(placeholders),
                "field_placeholders": placeholders,
                "tag": el.name 
            }
            static_text_elements.append(element_data)
        
        # --- Extract Table Configs ---
        table_configs = {}
        # Find a table element (e.g., <table id="invoice_items_table">)
        invoice_table = soup.find('table', id='invoice_items_table')
        if invoice_table:
            # Get table position (assuming it also uses absolute positioning, or fallback)
            table_style = invoice_table.get('style', '')
            table_left_match = re.search(r'left:\s*(\d+\.?\d*)\s*(pt|px|em)?', table_style)
            table_top_match = re.search(r'top:\s*(\d+\.?\d*)\s*(pt|px|em)?', table_style)
            table_width_match = re.search(r'width:\s*(\d+\.?\d*)\s*(pt|px|em)?', table_style)
            
            table_x_start = float(table_left_match.group(1)) if table_left_match else 50
            table_y_start_html = float(table_top_match.group(1)) if table_top_match else 400
            table_width = float(table_width_match.group(1)) if table_width_match else 500
            
            table_y_start_pdf = a4_height_pt - table_y_start_html

            header_elements = []
            # Assuming headers are in <thead><th>...</th></thead>
            for th in invoice_table.find_all('th'):
                header_text = th.get_text(strip=True)
                th_style = th.get('style', '')
                # Try to get horizontal position (offset from table_x_start) and width if defined
                th_left_match = re.search(r'left:\s*(\d+\.?\d*)\s*(pt|px|em)?', th_style) # Might not be directly in th
                th_width_match = re.search(r'width:\s*(\d+\.?\d*)\s*(pt|px|em)?', th_style)
                th_align_match = re.search(r'text-align:\s*(left|right|center)', th_style)

                th_x_offset = float(th_left_match.group(1)) if th_left_match else 0 # If header has absolute left
                th_width = float(th_width_match.group(1)) if th_width_match else 100
                th_align = th_align_match.group(1) if th_align_match else 'right'
                
                header_elements.append({
                    "text": header_text,
                    "x_offset": round(th_x_offset, 2), # This is relative to table_x_start in current PDF generation logic
                    "width": round(th_width, 2),
                    "align": th_align,
                    "font_size": 10, # Default, can be parsed from CSS
                    "font_bold": True # Default, can be parsed from CSS
                })

            item_field_configs = []
            # Parse one sample row (e.g., first <tr> in <tbody>) for field structure
            sample_tr = invoice_table.find('tbody').find('tr') if invoice_table.find('tbody') else None
            if sample_tr:
                for td in sample_tr.find_all('td'):
                    td_text = td.get_text(strip=True) # Contains placeholder like {{item_service_description}}
                    td_style = td.get('style', '')
                    td_left_match = re.search(r'left:\s*(\d+\.?\d*)\s*(pt|px|em)?', td_style)
                    td_width_match = re.search(r'width:\s*(\d+\.?\d*)\s*(pt|px|em)?', td_style)
                    td_align_match = re.search(r'text-align:\s*(left|right|center)', td_style)

                    td_x_offset = float(td_left_match.group(1)) if td_left_match else 0
                    td_width = float(td_width_match.group(1)) if td_width_match else 100
                    td_align = td_align_match.group(1) if td_align_match else 'right'

                    # Extract placeholder from text
                    placeholder_match = re.search(r'\{\{([a-zA-Z0-9_]+)\}\}', td_text)
                    field_name = placeholder_match.group(1) if placeholder_match else 'unknown_field'

                    item_field_configs.append({
                        "field": field_name,
                        "x_offset": round(td_x_offset, 2),
                        "width": round(td_width, 2),
                        "align": td_align,
                        "font_size": 10,
                        "font_bold": False
                    })
            
            table_configs['invoice_items_table'] = {
                "x_start": round(table_x_start, 2),
                "y_start": round(table_y_start_pdf, 2),
                "width": round(table_width, 2),
                "row_height": 20, # This needs to be parsed from CSS if available, or be a default
                "header_elements": header_elements,
                "item_field_configs": item_field_configs
            }

        # --- Extract Signature Block Config ---
        signature_block_config = {}
        # You'll need to define specific elements in your HTML for seller/buyer signatures
        # For example, <div id="seller_signature_block" style="position: absolute; left: 150pt; top: 750pt;">امضا و مهر فروشنده</div>
        
        seller_sig_el = soup.find(id='seller_signature_block')
        if seller_sig_el:
            seller_style = seller_sig_el.get('style', '')
            seller_left_match = re.search(r'left:\s*(\d+\.?\d*)\s*(pt|px|em)?', seller_style)
            seller_top_match = re.search(r'top:\s*(\d+\.?\d*)\s*(pt|px|em)?', seller_style)
            
            if seller_left_match and seller_top_match:
                seller_x_pos = float(seller_left_match.group(1))
                seller_y_pos_html = float(seller_top_match.group(1))
                signature_block_config["seller_signature_x"] = round(seller_x_pos, 2)
                signature_block_config["seller_signature_y"] = round(a4_height_pt - seller_y_pos_html, 2)

        buyer_sig_el = soup.find(id='buyer_signature_block')
        if buyer_sig_el:
            buyer_style = buyer_sig_el.get('style', '')
            buyer_left_match = re.search(r'left:\s*(\d+\.?\d*)\s*(pt|px|em)?', buyer_style)
            buyer_top_match = re.search(r'top:\s*(\d+\.?\d*)\s*(pt|px|em)?', buyer_style)
            
            if buyer_left_match and buyer_top_match:
                buyer_x_pos = float(buyer_left_match.group(1))
                buyer_y_pos_html = float(buyer_top_match.group(1))
                signature_block_config["buyer_signature_x"] = round(buyer_x_pos, 2)
                signature_block_config["buyer_signature_y"] = round(a4_height_pt - buyer_y_pos_html, 2)


        # --- Extract Background Image and Opacity from HTML (e.g., from <body> style) ---
        body_style = soup.find('body').get('style', '') if soup.find('body') else ''
        bg_image_match = re.search(r'background-image:\s*url\([\'"]?([^\)]+)[\'"]?\);?', body_style)
        bg_opacity_match = re.search(r'opacity:\s*(\d+\.?\d*);?', body_style)

        background_image_path = bg_image_match.group(1) if bg_image_match else None
        background_opacity = float(bg_opacity_match.group(1)) if bg_opacity_match else 1.0

        # --- Combine all extracted data ---
        template_settings = {
            "default_settings": {"tax_percentage": 9, "discount_editable": True}, # These would be hardcoded or from a separate config in HTML
            "static_text_elements": static_text_elements,
            "table_configs": table_configs,
            "signature_block_config": signature_block_config,
            "background_image_path": background_image_path,
            "background_opacity": background_opacity,
        }
        
        return template_settings

    def load_invoice_templates_to_table(self):
        """ بارگذاری قالب‌های صورتحساب از دیتابیس به جدول """
        for item in self.template_table.get_children():
            self.template_table.delete(item)
        
        templates, message = self.invoice_template_manager.get_all_templates(active_only=False)
        if not templates:
            pass

        for template in templates:
            is_active_text = "بله" if template.is_active == 1 else "خیر"
            self.template_table.insert("", "end", iid=template.id, 
                                       values=(template.id, template.template_name, template.template_type, is_active_text))

    def clear_template_form(self):
        """ پاک کردن فیلدهای فرم قالب صورتحساب و غیرفعال کردن دکمه حذف و پیش نمایش """
        self.selected_template_id = None
        self.template_name_var.set("")
        self.template_type_var.set("PDF_Standard")
        self.is_active_var.set(1) 
        
        for field, var in self.required_fields_vars.items():
            var.set(0) 
        
        self.header_image_path_var.set("")
        self.footer_image_path_var.set("")
        self.background_image_path_var.set("")
        self.background_opacity_var.set(1.0)

        self.template_settings_textbox.delete("1.0", "end")
        self.template_settings_textbox.insert("1.0", json.dumps(
            {
                "default_settings": {"tax_percentage": 9, "discount_editable": True},
                "static_text_elements": [],
                "table_configs": {},
                "signature_block_config": {},
                "background_image_path": None, 
                "background_opacity": 1.0,     
            }, indent=4, ensure_ascii=False
        ))

        self.delete_template_button.configure(state="disabled")
        self.preview_template_button.configure(state="disabled") 


    def save_invoice_template(self):
        """ اطلاعات وارد شده در UI را دریافت کرده و اعتبارسنجی کرده و در دیتابیس ذخیره می‌کند. """
        template_name = self.template_name_var.get().strip()
        template_type = self.template_type_var.get()
        is_active = self.is_active_var.get()

        if not template_name:
            messagebox.showwarning("خطای ورودی", "نام قالب نمی‌تواند خالی باشد.", master=self)
            return
        if not template_type:
            messagebox.showwarning("خطای ورودی", "نوع قالب نمی‌تواند خالی باشد.", master=self)
            return

        required_fields = [field for field, var in self.required_fields_vars.items() if var.get() == 1]
        
        template_settings_str = self.template_settings_textbox.get("1.0", "end").strip()
        try:
            template_settings_json = json.loads(template_settings_str)
        except json.JSONDecodeError as e:
            messagebox.showwarning("خطای ورودی", f"فرمت JSON تنظیمات قالب نامعتبر است: {e}", master=self)
            return

        header_image_path = self.header_image_path_var.get() or None
        footer_image_path = self.footer_image_path_var.get() or None
        
        background_image_path_from_json = template_settings_json.get("background_image_path", None)
        background_opacity_from_json = template_settings_json.get("background_opacity", 1.0)


        updated_template = InvoiceTemplate(
            id=self.selected_template_id,
            template_name=template_name,
            template_type=template_type,
            required_fields=required_fields,
            template_settings=template_settings_json, 
            is_active=is_active,
            header_image_path=header_image_path,
            footer_image_path=footer_image_path,
            background_image_path=background_image_path_from_json, 
            background_opacity=background_opacity_from_json
        )

        if self.selected_template_id:
            success, message = self.invoice_template_manager.update_template(updated_template)
        else:
            success, message = self.invoice_template_manager.add_template(updated_template)

        if success:
            messagebox.showinfo("موفقیت", message, master=self)
            self.clear_template_form()
            self.load_invoice_templates_to_table()
        else:
            messagebox.showerror("خطا", message, master=self)

    def delete_invoice_template_from_db(self):
        """ حذف قالب صورتحساب از دیتابیس """
        if self.selected_template_id:
            confirm = messagebox.askyesno("تایید حذف", f"آیا مطمئنید می‌خواهید قالب '{self.template_name_var.get()}' را حذف کنید؟", master=self)
            if confirm:
                success, message = self.invoice_template_manager.delete_template(self.selected_template_id)
                if success:
                    messagebox.showinfo("موفقیت", message, master=self)
                    self.clear_template_form()
                    self.load_invoice_templates_to_table()
                else:
                    messagebox.showerror("خطا", message, master=self)
        else:
            messagebox.showwarning("هشدار", "هیچ قالبی برای حذف انتخاب نشده است.", master=self)

    def on_template_select(self, event):
        """ رویداد انتخاب سطر در جدول قالب‌ها (تک کلیک) """
        selected_items = self.template_table.selection()
        if selected_items:
            selected_item_id = selected_items[0]
            template_id = int(selected_item_id) 
            template_obj, _ = self.invoice_template_manager.get_template_by_id(template_id) 

            if template_obj:
                self.selected_template_id = template_obj.id
                self.template_name_var.set(template_obj.template_name)
                self.template_type_var.set(template_obj.template_type)
                self.is_active_var.set(template_obj.is_active)
                
                for field, var in self.required_fields_vars.items():
                    var.set(1 if field in template_obj.required_fields else 0)
                
                # Display template_settings JSON
                try:
                    self.template_settings_textbox.delete("1.0", "end")
                    self.template_settings_textbox.insert("1.0", json.dumps(template_obj.template_settings, indent=4, ensure_ascii=False))
                except Exception as e:
                    self.template_settings_textbox.delete("1.0", "end")
                    self.template_settings_textbox.insert("1.0", f"Error loading settings JSON: {e}")
                
                # Image paths
                self.header_image_path_var.set(template_obj.header_image_path or "")
                self.footer_image_path_var.set(template_obj.footer_image_path or "")
                self.background_image_path_var.set(template_obj.background_image_path or "")
                self.background_opacity_var.set(template_obj.background_opacity if template_obj.background_opacity is not None else 1.0)


                self.delete_template_button.configure(state="normal")
                self.preview_template_button.configure(state="normal") 
        else:
            self.clear_template_form()

    def on_template_double_click(self, event):
        """ رویداد دابل کلیک روی سطر در جدول قالب‌ها """
        self.on_template_select(event)

    def preview_invoice_template(self):
        """ نمایش پیش‌نمایش قالب صورتحساب (هدر، فوتر، بک‌گراند) """
        if not self.selected_template_id:
            messagebox.showwarning("هشدار", "لطفاً یک قالب را برای پیش‌نمایش انتخاب کنید.", master=self)
            return
        
        # Read current JSON from textbox for preview
        template_settings_str = self.template_settings_textbox.get("1.0", "end").strip()
        try:
            current_template_settings = json.loads(template_settings_str)
        except json.JSONDecodeError as e:
            messagebox.showwarning("خطا", f"JSON تنظیمات قالب نامعتبر است: {e}", master=self)
            return

        # Create a temporary InvoiceTemplate object with current UI values for preview
        temp_template = InvoiceTemplate(
            id=self.selected_template_id,
            template_name=self.template_name_var.get().strip(),
            template_type=self.template_type_var.get(),
            required_fields=[field for field, var in self.required_fields_vars.items() if var.get() == 1],
            template_settings=current_template_settings, 
            is_active=self.is_active_var.get(),
            header_image_path=self.header_image_path_var.get() or None,
            footer_image_path=self.footer_image_path_var.get() or None,
            background_image_path=self.background_image_path_var.get() or None, 
            background_opacity=self.background_opacity_var.get() if self.background_opacity_var.get() is not None else 1.0 
        )
        
        InvoiceTemplatePreviewWindow(self, temp_template, self.ui_colors, self.base_font, self.heading_font) 

    def show_sub_frame(self, page_name):
        """ نمایش یک فریم خاص در منوی تنظیمات """
        frame = self.frames.get(page_name)
        if frame:
            frame.tkraise()
            self.current_active_sub_page_name = page_name
            if page_name == "service_types":
                self.load_services_to_table()
                self.clear_service_form()
            elif page_name == "invoice_templates":
                self.load_invoice_templates_to_table()
                self.clear_template_form()
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
                elif self.current_active_sub_page_name == "invoice_templates":
                    self.invoice_templates_btn.configure(
                        fg_color=self.ui_colors["active_sub_button_bg"],
                        text_color=self.ui_colors["active_sub_button_text"],
                        border_width=2,
                        border_color=self.ui_colors["active_sub_button_border"]
                    )
                    self.current_active_sub_button = self.invoice_templates_btn


# --- بلاک تست مستقل UI ---
if __name__ == "__main__":
    root = ctk.CTk()
    root.title("تنظیمات easy_invoice (تست مستقل)")
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

    from invoice_template_manager import InvoiceTemplateManager
    tmpl_man = InvoiceTemplateManager()
    if not tmpl_man.get_all_templates(active_only=False)[0]:
        tmpl_man.add_template(InvoiceTemplate(
            template_name="قالب پیش‌فرض",
            template_type="PDF_Standard",
            required_fields=["invoice_number", "customer_name", "total_amount"],
            template_settings={"default_settings": {"tax_percentage": 9, "discount_editable": True}, "static_text_elements": [], "table_configs": {}, "signature_block_config": {}},
            is_active=1
        ))

    settings_frame = SettingsUI(root, temp_db_manager, test_ui_colors, base_font_tuple, heading_font_tuple, button_font_tuple, nav_button_font_tuple)
    settings_frame.pack(fill="both", expand=True)

    root.mainloop()