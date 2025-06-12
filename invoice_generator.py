# invoice_generator.py
import fitz  # PyMuPDF
import jdatetime
import os
from PIL import Image # از PIL.Image فقط Image رو وارد می‌کنیم
import json
import subprocess 
import re # اضافه شد برای Regex
from reportlab.pdfbase import pdfmetrics # اضافه شد
from reportlab.pdfbase.ttfonts import TTFont # اضافه شد

class InvoiceGenerator:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.doc = None
        self.page = None
        self.y_cursor = 0 # برای مدیریت موقعیت عمودی در صفحه
        # A4 dimensions in points
        self.A4_WIDTH = 595
        self.A4_HEIGHT = 842
        
        # Load default font for Persian text (Vazirmatn)
        self.font_path = os.path.join(os.path.dirname(__file__), "Vazirmatn-Regular.ttf")
        self.bold_font_path = os.path.join(os.path.dirname(__file__), "Vazirmatn-Bold.ttf") # assuming a bold variant exists
        self.font_registered = False
        try:
            if os.path.exists(self.font_path):
                pdfmetrics.registerFont(TTFont('Vazirmatn', self.font_path))
                pdfmetrics.registerFont(TTFont('Vazirmatn-Bold', self.bold_font_path))
                self.font_registered = True
                print("Vazirmatn fonts registered for PDF generation.")
            else:
                print(f"Warning: Vazirmatn-Regular.ttf not found at {self.font_path}. Using default font.")
        except Exception as e:
            print(f"Error registering Vazirmatn font: {e}. Using default font.")


    def create_invoice_pdf(self, invoice_data, customer_data, invoice_items, output_path="invoice.pdf", invoice_template=None): # تغییر: invoice_template اضافه شد
        self.doc = fitz.open()
        self.page = self.doc.new_page(width=self.A4_WIDTH, height=self.A4_HEIGHT) 
        self.y_cursor = self.A4_HEIGHT # Start from top of the page, moving downwards

        # Prepare context data for placeholders
        context_data = self._populate_template_data(invoice_data, customer_data, invoice_items)
        
        template_settings = {}
        if invoice_template and invoice_template.template_settings:
            template_settings = invoice_template.template_settings
        
        # --- Draw Background Image ---
        # This can be set in template_settings JSON or directly in InvoiceTemplate object
        bg_image_path = invoice_template.background_image_path if invoice_template else None
        bg_opacity = invoice_template.background_opacity if invoice_template else 1.0

        if bg_image_path and os.path.exists(bg_image_path):
            self._draw_background_image(self.page, bg_image_path, bg_opacity)

        # --- Draw Header Image ---
        header_image_path = invoice_template.header_image_path if invoice_template else None
        if header_image_path and os.path.exists(header_image_path):
            self._draw_image(self.page, header_image_path, "header")
        
        # --- Draw Static Text Elements & Dynamic Fields ---
        if 'static_text_elements' in template_settings:
            for element_config in template_settings['static_text_elements']:
                text = element_config.get('text', '')
                x_pos = element_config.get('x_pos', 0)
                y_pos = element_config.get('y_pos', 0)
                align = element_config.get('align', 'right')
                font_size = element_config.get('font_size', 12)
                font_bold = element_config.get('font_bold', False)
                
                # Replace placeholders with actual data
                for placeholder in element_config.get('field_placeholders', []):
                    # Ensure placeholder is in context_data, otherwise keep it as is or replace with empty
                    if placeholder in context_data:
                        text = text.replace(f'{{{{{placeholder}}}}}', str(context_data[placeholder]))
                    else:
                        text = text.replace(f'{{{{{placeholder}}}}}', '') # Replace missing data with empty string

                self._draw_text(self.page, x_pos, y_pos, text, 
                                font_size, align, font_bold)

        # --- Draw Invoice Items Table (Placeholder for now) ---
        if 'table_configs' in template_settings and 'invoice_items_table' in template_settings['table_configs']:
            self._draw_invoice_items_dynamic_table(invoice_items, template_settings['table_configs']['invoice_items_table'], context_data)

        # --- Draw Signature Section (Placeholder for now) ---
        if 'signature_block_config' in template_settings:
            self._draw_signature_section_from_template(template_settings['signature_block_config'], context_data)


        # --- Draw Footer Image ---
        footer_image_path = invoice_template.footer_image_path if invoice_template else None
        if footer_image_path and os.path.exists(footer_image_path):
            self._draw_image(self.page, footer_image_path, "footer")

        try:
            self.doc.save(output_path)
            self.doc.close()
            return True, output_path
        except Exception as e:
            print(f"Error saving PDF: {e}")
            return False, f"خطا در ذخیره فایل PDF: {e}"

    def _populate_template_data(self, invoice, customer, items):
        """ Populates a dictionary with all available data for template rendering. """
        data = {}

        # Invoice Data
        data['invoice_number'] = invoice.invoice_number
        data['issue_date'] = invoice.issue_date
        data['due_date'] = invoice.due_date if invoice.due_date else ''
        data['total_amount'] = f"{int(invoice.total_amount):,}"
        data['discount_percentage'] = f"{invoice.discount_percentage:g}"
        data['tax_percentage'] = f"{invoice.tax_percentage:g}"
        data['final_amount'] = f"{int(invoice.final_amount):,}"
        data['invoice_description'] = invoice.description if invoice.description else ''

        # Customer Data
        data['customer_name'] = customer.name
        data['customer_type'] = customer.customer_type
        data['customer_address'] = customer.address if customer.address else ''
        data['customer_phone'] = customer.phone if customer.phone else ''
        data['customer_phone2'] = customer.phone2 if customer.phone2 else ''
        data['customer_mobile'] = customer.mobile if customer.mobile else ''
        data['customer_email'] = customer.email if customer.email else ''
        data['customer_tax_id'] = customer.tax_id if customer.tax_id else ''
        data['customer_postal_code'] = customer.postal_code if customer.postal_code else ''
        data['customer_notes'] = customer.notes if customer.notes else ''

        # Seller Data (from AppSettings)
        settings = self.settings_manager.get_settings()
        data['seller_name'] = settings.seller_name if settings.seller_name else ''
        data['seller_address'] = settings.seller_address if settings.seller_address else ''
        data['seller_phone'] = settings.seller_phone if settings.seller_phone else ''
        data['seller_tax_id'] = settings.seller_tax_id if settings.seller_tax_id else ''
        data['seller_economic_code'] = settings.seller_economic_code if settings.seller_economic_code else ''
        data['seller_logo_path'] = settings.seller_logo_path if settings.seller_logo_path else ''

        # Contract Data (if available)
        if invoice.contract_id:
            contract, _ = self.settings_manager.contract_manager.get_contract_by_id(invoice.contract_id) # Need to access contract_manager
            if contract:
                data['contract_number'] = contract.contract_number if contract.contract_number else ''
                data['contract_title'] = contract.title if contract.title else ''
                data['contract_date'] = contract.contract_date if contract.contract_date else ''
                data['contract_total_amount'] = f"{int(contract.total_amount):,}" if contract.total_amount else ''
                data['contract_description'] = contract.description if contract.description else ''
                data['contract_payment_method'] = contract.payment_method if contract.payment_method else ''
            else:
                data['contract_number'] = data['contract_title'] = data['contract_date'] = ''
                data['contract_total_amount'] = data['contract_description'] = data['contract_payment_method'] = ''
        else:
            data['contract_number'] = data['contract_title'] = data['contract_date'] = ''
            data['contract_total_amount'] = data['contract_description'] = data['contract_payment_method'] = ''

        # Invoice Items Data (for internal use, not direct placeholder)
        # This is passed separately, but useful for context if needed
        # data['invoice_items'] = items 

        return data

    def _draw_text(self, page, x_pos, y_pos, text, font_size, align, font_bold=False):
        """
        Draws text on the page with specified position, size, alignment, and boldness.
        x_pos, y_pos are expected in PDF coordinates (bottom-left origin).
        """
        if not text:
            return

        # Choose font based on boldness and availability
        selected_font_name = 'Vazirmatn'
        if font_bold:
            selected_font_name = 'Vazirmatn-Bold' if self.font_registered and os.path.exists(self.bold_font_path) else 'Vazirmatn'
        
        # Fallback if Vazirmatn is not registered
        if not self.font_registered:
            selected_font_name = "helv" # Helvetica is a default font

        # Adjust x_pos based on alignment
        text_len = page.text_length(text, fontname=selected_font_name, fontsize=font_size)
        if align == 'center':
            x_pos -= text_len / 2
        elif align == 'right':
            x_pos -= text_len # This is for RTL, so right-aligned means start further right
        
        # In PyMuPDF, text is drawn from its baseline.
        # Persian text also needs RTL handling for rendering, but PyMuPDF's text_length usually works.
        try:
            page.insert_text(fitz.Point(x_pos, y_pos), text, 
                             fontname=selected_font_name, fontsize=font_size, 
                             color=(0, 0, 0)) # Default to black
        except Exception as e:
            print(f"Error drawing text '{text}' at ({x_pos}, {y_pos}) with font {selected_font_name}: {e}")
            page.insert_text(fitz.Point(x_pos, y_pos), text, fontname="helv", fontsize=font_size, color=(1,0,0))


    def _draw_image(self, page, image_path, image_type):
        """ Draws header or footer images based on type. """
        if not os.path.exists(image_path):
            print(f"Warning: {image_type.capitalize()} image not found at {image_path}")
            return
        try:
            img_pil = Image.open(image_path)
            
            if image_type == "header":
                target_height = 100 # Example fixed height for header
                y_pos = self.A4_HEIGHT - 100 - 10 # 10 units from top, 100 height
            elif image_type == "footer":
                target_height = 100 # Example fixed height for footer
                y_pos = 10 # 10 units from bottom
            else: # background, though handled in a separate method
                target_height = self.A4_HEIGHT
                y_pos = 0

            ratio = img_pil.width / img_pil.height
            new_width = int(target_height * ratio)
            
            # Scale down if too wide
            if new_width > self.A4_WIDTH - 20:
                new_width = self.A4_WIDTH - 20
                target_height = int(new_width / ratio)

            # Center horizontally
            x_pos = (self.A4_WIDTH - new_width) / 2
            
            img_rect = fitz.Rect(x_pos, y_pos, x_pos + new_width, y_pos + target_height)
            
            pix = fitz.Pixmap(img_pil.mode, img_pil.size, img_pil.tobytes())
            if pix.alpha:
                pix = fitz.Pixmap(pix, 0) # Remove alpha for consistent rendering
            
            page.insert_image(img_rect, pixmap=pix)

        except Exception as e:
            print(f"Error drawing {image_type} image {image_path}: {e}")


    def _draw_background_image(self, page, image_path, opacity=1.0):
        if not os.path.exists(image_path):
            print(f"Warning: Background image not found at {image_path}")
            return

        try:
            img_pil = Image.open(image_path)
            img_pil = img_pil.resize((int(self.A4_WIDTH), int(self.A4_HEIGHT)), Image.LANCZOS)

            if opacity < 1.0:
                if img_pil.mode != 'RGBA':
                    img_pil = img_pil.convert('RGBA')
                alpha = img_pil.split()[3] 
                alpha = Image.eval(alpha, lambda x: x * opacity) 
                img_pil.putalpha(alpha) 

            pix = fitz.Pixmap(img_pil.mode, img_pil.size, img_pil.tobytes())
            page.insert_image(page.rect, pixmap=pix)

        except Exception as e:
            print(f"Error drawing background image {image_path}: {e}")


    def _draw_invoice_items_dynamic_table(self, invoice_items, table_config, context_data):
        """
        Draws the invoice items table dynamically based on table_config.
        This is a preliminary implementation. Full page-break logic and detailed
        item rendering requires a more comprehensive table config from HTML.
        """
        
        # Default font for table content if not specified in config
        table_font_size = 10
        table_font_bold = False
        table_align = 'right'

        # Extract table common settings
        table_x_start = table_config.get('x_start', 50)
        table_y_start_html = table_config.get('y_start', 400) # HTML top-origin Y
        table_width = table_config.get('width', 500)
        row_height = table_config.get('row_height', 20)
        
        # Convert HTML top-origin Y to PDF bottom-origin Y
        table_y_start_pdf = self.A4_HEIGHT - table_y_start_html

        # Store current y_cursor to adjust later sections
        current_y = table_y_start_pdf 

        # Draw Headers
        header_elements = table_config.get('header_elements', [])
        for header_el in header_elements:
            text = header_el.get('text', '')
            x_offset = header_el.get('x_offset', 0)
            align = header_el.get('align', table_align)
            font_size = header_el.get('font_size', table_font_size)
            font_bold = header_el.get('font_bold', table_font_bold)
            
            self._draw_text(self.page, table_x_start + x_offset, current_y, text, 
                            font_size, align, font_bold)

        current_y -= row_height # Move down after headers for first item row

        # Draw Items
        item_field_configs = table_config.get('item_field_configs', [])
        for idx, item in enumerate(invoice_items):
            # To handle item-specific placeholders (like {{item_quantity}}),
            # we need to create an item-specific context
            item_context = {
                'item_row_num': idx + 1,
                'item_service_description': self.settings_manager.get_service_description_by_id(item.service_id) or "N/A",
                'item_quantity': f"{item.quantity:g}",
                'item_unit_price': f"{int(item.unit_price):,}",
                'item_total_price': f"{int(item.total_price):,}"
            }
            
            for field_config in item_field_configs:
                field_name = field_config.get('field', '')
                x_offset = field_config.get('x_offset', 0)
                align = field_config.get('align', table_align)
                font_size = field_config.get('font_size', table_font_size)
                font_bold = field_config.get('font_bold', table_font_bold)
                
                # Get the actual value from item_context
                text_to_draw = item_context.get(field_name, '')

                self._draw_text(self.page, table_x_start + x_offset, current_y, text_to_draw,
                                font_size, align, font_bold)
            
            current_y -= row_height # Move down for next item

            # Basic page break check (needs full implementation)
            if current_y < 50: # If approaching bottom of page
                self.page = self.doc.new_page(width=self.A4_WIDTH, height=self.A4_HEIGHT)
                current_y = self.A4_HEIGHT - 50 # Start near top of new page
                # TODO: Redraw table headers on new page here

        self.y_cursor = current_y # Update the main y_cursor for subsequent sections


    def _draw_signature_section_from_template(self, signature_config, context_data):
        """ Draws signature blocks based on template config. """
        seller_x = signature_config.get('seller_signature_x', 150)
        seller_y = signature_config.get('seller_signature_y', 100)
        buyer_x = signature_config.get('buyer_signature_x', 450)
        buyer_y = signature_config.get('buyer_signature_y', 100)
        
        font_size = 10
        
        self._draw_text(self.page, seller_x, seller_y + 15, "امضا و مهر فروشنده", font_size, 'center', True)
        self.page.draw_line(fitz.Point(seller_x - 50, seller_y), fitz.Point(seller_x + 50, seller_y))

        self._draw_text(self.page, buyer_x, buyer_y + 15, "امضا و مهر خریدار", font_size, 'center', True)
        self.page.draw_line(fitz.Point(buyer_x - 50, buyer_y), fitz.Point(buyer_x + 50, buyer_y))

        self.y_cursor = min(seller_y, buyer_y) - 20 # Update cursor to below signature lines


# --- بلاک تست مستقل ---
if __name__ == "__main__":
    from models import AppSettings, Customer, Invoice, InvoiceItem, Service, InvoiceTemplate 
    from settings_manager import SettingsManager
    from db_manager import DBManager, DATABASE_NAME
    import sys
    from service_manager import ServiceManager 
    from contract_manager import ContractManager # اضافه شد برای تست Contract Data

    temp_db_name_for_test = "test_invoice_generator_v2.db" # Changed DB name to avoid conflicts
    temp_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), temp_db_name_for_test)
    
    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)

    db_manager_test = DBManager(temp_db_path)
    if db_manager_test.connect():
        db_manager_test.create_tables()
        db_manager_test.migrate_database()
        db_manager_test.close()
    else:
        print("Failed to connect to database for test setup.")
        sys.exit(1)

    settings_manager = SettingsManager()
    settings_manager.db_manager = DBManager(temp_db_path) # Ensure settings_manager uses the test DB
    settings_manager.customer_manager = CustomerManager() # Initialize customer_manager
    settings_manager.customer_manager.db_manager = DBManager(temp_db_path) # Ensure it uses test DB
    settings_manager.contract_manager = ContractManager() # Initialize contract_manager
    settings_manager.contract_manager.db_manager = DBManager(temp_db_path) # Ensure it uses test DB

    dummy_settings = AppSettings(
        id=1,
        seller_name="شرکت توسعه نرم‌افزار آسان",
        seller_address="تهران، خیابان آزادی، پلاک ۱۰۰",
        seller_phone="021-12345678",
        seller_tax_id="12345678901",
        seller_economic_code="0987654321",
        seller_logo_path=os.path.join(os.path.dirname(__file__), "test_logo.png") 
    )
    settings_manager.save_settings(dummy_settings)

    dummy_customer = Customer(
        id=1,
        name="شرکت خریدار نمونه",
        customer_type="حقوقی",
        address="اصفهان، خیابان چهارباغ، کوچه اول",
        phone="031-98765432",
        tax_id="00000000001",
        email="customer@example.com",
        customer_code=1001
    )
    db_manager_test.connect() # Reconnect for customer insert
    db_manager_test.execute_query("""
        INSERT OR IGNORE INTO Customers (id, customer_code, name, customer_type, address, phone, email, tax_id) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (dummy_customer.id, dummy_customer.customer_code, dummy_customer.name, dummy_customer.customer_type, 
          dummy_customer.address, dummy_customer.phone, dummy_customer.email, dummy_customer.tax_id))
    db_manager_test.close()

    svc_man = ServiceManager() 
    svc_man.db_manager = DBManager(temp_db_path) # Ensure it uses test DB
    dummy_service1 = Service(id=1, service_code=101, description="خدمات طراحی وبسایت")
    dummy_service2 = Service(id=2, service_code=102, description="پشتیبانی نرم‌افزار (ماهانه)")
    svc_man.add_service(dummy_service1)
    svc_man.add_service(dummy_service2)

    # Add a dummy contract for testing contract data
    dummy_contract = Contract(
        id=1, customer_id=dummy_customer.id, contract_number="CON-SAMPLE-001",
        contract_date=jdatetime.date.today().strftime("%Y/%m/%d"), total_amount=150000000,
        description="خدمات توسعه نرم افزار و پشتیبانی", title="قرارداد توسعه و پشتیبانی",
        payment_method="ماهانه", scanned_pages="[]"
    )
    db_manager_test.connect() # Reconnect for contract insert
    db_manager_test.execute_query("""
        INSERT OR IGNORE INTO Contracts (id, customer_id, contract_number, contract_date, total_amount, description, title, payment_method, scanned_pages)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (dummy_contract.id, dummy_contract.customer_id, dummy_contract.contract_number, dummy_contract.contract_date,
          dummy_contract.total_amount, dummy_contract.description, dummy_contract.title, dummy_contract.payment_method, dummy_contract.scanned_pages))
    db_manager_test.close()

    # ایجاد یک قالب صورتحساب dummy برای تست (اینجا از ساختار جدید template_settings استفاده می‌کنیم)
    dummy_template = InvoiceTemplate(
        template_name="قالب استاندارد تست با JSON",
        template_type="PDF_Standard",
        required_fields=["invoice_number", "customer_name", "total_amount"],
        template_settings={ # ساختار جدید JSON
            "default_settings": {"tax_percentage": 9, "discount_editable": True},
            "static_text_elements": [
                {"text": "تاریخ: {{issue_date}}", "x_pos": 50, "y_pos": 800, "align": "left", "font_size": 12, "font_bold": False, "field_placeholders": ["issue_date"]},
                {"text": "شماره صورتحساب: {{invoice_number}}", "x_pos": 50, "y_pos": 780, "align": "left", "font_size": 12, "font_bold": False, "field_placeholders": ["invoice_number"]},
                {"text": "فاکتور", "x_pos": 297.5, "y_pos": 810, "align": "center", "font_size": 24, "font_bold": True},
                {"text": "نام فروشنده: {{seller_name}}", "x_pos": 545, "y_pos": 700, "align": "right", "font_size": 10, "font_bold": False, "field_placeholders": ["seller_name"]},
                {"text": "آدرس فروشنده: {{seller_address}}", "x_pos": 545, "y_pos": 685, "align": "right", "font_size": 10, "font_bold": False, "field_placeholders": ["seller_address"]},
                {"text": "تلفن فروشنده: {{seller_phone}}", "x_pos": 545, "y_pos": 670, "align": "right", "font_size": 10, "font_bold": False, "field_placeholders": ["seller_phone"]},
                {"text": "نام مشتری: {{customer_name}}", "x_pos": 50, "y_pos": 700, "align": "left", "font_size": 10, "font_bold": False, "field_placeholders": ["customer_name"]},
                {"text": "آدرس مشتری: {{customer_address}}", "x_pos": 50, "y_pos": 685, "align": "left", "font_size": 10, "font_bold": False, "field_placeholders": ["customer_address"]},
                {"text": "قرارداد مربوطه: {{contract_number}} - {{contract_title}}", "x_pos": 50, "y_pos": 650, "align": "left", "font_size": 10, "font_bold": False, "field_placeholders": ["contract_number", "contract_title"]},
                {"text": "جمع کل: {{total_amount}} ریال", "x_pos": 545, "y_pos": 180, "align": "right", "font_size": 12, "font_bold": False, "field_placeholders": ["total_amount"]},
                {"text": "تخفیف ({{discount_percentage}}%): {{discount_amount}} ریال", "x_pos": 545, "y_pos": 160, "align": "right", "font_size": 12, "font_bold": False, "field_placeholders": ["discount_percentage", "discount_amount"]},
                {"text": "مالیات ({{tax_percentage}}%): {{tax_amount}} ریال", "x_pos": 545, "y_pos": 140, "align": "right", "font_size": 12, "font_bold": False, "field_placeholders": ["tax_percentage", "tax_amount"]},
                {"text": "مبلغ نهایی: {{final_amount}} ریال", "x_pos": 545, "y_pos": 100, "align": "right", "font_size": 14, "font_bold": True, "field_placeholders": ["final_amount"]},
                {"text": "توضیحات: {{invoice_description}}", "x_pos": 50, "y_pos": 100, "align": "left", "font_size": 10, "font_bold": False, "field_placeholders": ["invoice_description"]},
            ],
            "table_configs": {
                "invoice_items_table": {
                    "x_start": 50, 
                    "y_start": 500, # HTML top origin
                    "width": 495, 
                    "row_height": 20, 
                    "header_elements": [
                        {"text": "ردیف", "x_offset": 450, "width": 45, "align": "center", "font_size": 10, "font_bold": True},
                        {"text": "شرح کالا / خدمات", "x_offset": 250, "width": 200, "align": "right", "font_size": 10, "font_bold": True},
                        {"text": "تعداد", "x_offset": 180, "width": 70, "align": "center", "font_size": 10, "font_bold": True},
                        {"text": "قیمت واحد", "x_offset": 90, "width": 90, "align": "right", "font_size": 10, "font_bold": True},
                        {"text": "مبلغ کل", "x_offset": 0, "width": 90, "align": "right", "font_size": 10, "font_bold": True}
                    ],
                    "item_field_configs": [
                        {"field": "item_row_num", "x_offset": 450, "width": 45, "align": "center", "font_size": 10},
                        {"field": "item_service_description", "x_offset": 250, "width": 200, "align": "right", "font_size": 10},
                        {"field": "item_quantity", "x_offset": 180, "width": 70, "align": "center", "font_size": 10},
                        {"field": "item_unit_price", "x_offset": 90, "width": 90, "align": "right", "font_size": 10},
                        {"field": "item_total_price", "x_offset": 0, "width": 90, "align": "right", "font_size": 10}
                    ]
                }
            },
            "signature_block_config": {
                "seller_signature_x": 150, "seller_signature_y": 50,
                "buyer_signature_x": 450, "buyer_signature_y": 50
            }
        },
        is_active=1,
        header_image_path=os.path.join(os.path.dirname(__file__), "test_header.png"), 
        footer_image_path=os.path.join(os.path.dirname(__file__), "test_footer.png"), 
        background_image_path=os.path.join(os.path.dirname(__file__), "test_background.png"), 
        background_opacity=0.2
    )

    # Save dummy template (for testing generation)
    from invoice_template_manager import InvoiceTemplateManager
    tmpl_man = InvoiceTemplateManager()
    tmpl_man.db_manager = DBManager(temp_db_path) # Ensure it uses test DB
    tmpl_man.add_template(dummy_template)
    
    invoice = Invoice(
        invoice_number="INV-1403-001",
        customer_id=dummy_customer.id,
        contract_id=dummy_contract.id, # Link to the dummy contract
        issue_date=jdatetime.date.today().strftime("%Y/%m/%d"),
        total_amount=120000000,
        discount_percentage=5,
        tax_percentage=9,
        final_amount=0, 
        description="این صورتحساب بابت خدمات ارائه شده در خرداد ماه 1403 می‌باشد."
    )

    invoice_items_list = [
        InvoiceItem(invoice_id=None, service_id=dummy_service1.id, quantity=1, unit_price=100000000, total_price=100000000),
        InvoiceItem(invoice_id=None, service_id=dummy_service2.id, quantity=2, unit_price=10000000, total_price=20000000),
        InvoiceItem(invoice_id=None, service_id=dummy_service1.id, quantity=0.5, unit_price=5000000, total_price=2500000),
        InvoiceItem(invoice_id=None, service_id=dummy_service2.id, quantity=3, unit_price=1000000, total_price=3000000),
        InvoiceItem(invoice_id=None, service_id=dummy_service1.id, quantity=1, unit_price=10000000, total_price=10000000),
        InvoiceItem(invoice_id=None, service_id=dummy_service2.id, quantity=2, unit_price=10000000, total_price=20000000),
        InvoiceItem(invoice_id=None, service_id=dummy_service1.id, quantity=0.5, unit_price=5000000, total_price=2500000),
        InvoiceItem(invoice_id=None, service_id=dummy_service2.id, quantity=3, unit_price=1000000, total_price=3000000),
        InvoiceItem(invoice_id=None, service_id=dummy_service1.id, quantity=1, unit_price=10000000, total_price=10000000),
        InvoiceItem(invoice_id=None, service_id=dummy_service2.id, quantity=2, unit_price=10000000, total_price=20000000),
        InvoiceItem(invoice_id=None, service_id=dummy_service1.id, quantity=0.5, unit_price=5000000, total_price=2500000),
        InvoiceItem(invoice_id=None, service_id=dummy_service2.id, quantity=3, unit_price=1000000, total_price=3000000),
    ]

    total_items_amount = sum(item.total_price for item in invoice_items_list)
    discount_amount = total_items_amount * (invoice.discount_percentage / 100)
    tax_amount = (total_items_amount - discount_amount) * (invoice.tax_percentage / 100)
    invoice.final_amount = total_items_amount - discount_amount + tax_amount
    
    # برای تست، مقدار discount_amount و tax_amount رو به context_data اضافه می‌کنیم.
    # در تابع populate_template_data، اینها باید محاسبه شوند.
    invoice.discount_amount = discount_amount
    invoice.tax_amount = tax_amount


    invoice_gen = InvoiceGenerator(settings_manager)
    test_output_pdf_path = "sample_invoice_with_dynamic_template.pdf"
    success, pdf_path = invoice_gen.create_invoice_pdf(invoice, dummy_customer, invoice_items_list, test_output_pdf_path, dummy_template) 

    if success:
        print(f"Sample invoice generated at: {pdf_path}")
        try:
            if sys.platform == "win32":
                subprocess.run(["start", pdf_path], shell=True) 
            elif sys.platform == "darwin":
                subprocess.run(["open", pdf_path])
            else:
                subprocess.run(["xdg-open", pdf_path])
        except Exception as e:
            print(f"Could not open PDF automatically: {e}")
    else:
        print(f"Failed to generate invoice PDF: {pdf_path}")

    print("\n--- End of InvoiceGenerator Test ---")