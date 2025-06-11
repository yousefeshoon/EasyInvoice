# invoice_generator.py
import fitz  # PyMuPDF
import jdatetime
import os
from PIL import Image
import json
import subprocess # برای باز کردن فایل‌ها

class InvoiceGenerator:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.doc = None
        self.page = None
        self.y_cursor = 0 # برای مدیریت موقعیت عمودی در صفحه

    def create_invoice_pdf(self, invoice_data, customer_data, invoice_items, output_path="invoice.pdf"):
        self.doc = fitz.open()
        self.page = self.doc.new_page(width=595, height=842) # A4 size in points
        self.y_cursor = 800 # شروع از بالای صفحه

        # تنظیم فونت فارسی
        # برای نمایش درست فارسی، نیاز به یک فایل فونت فارسی (مثلاً Vazirmatn-Regular.ttf) داری
        # فرض می‌کنیم فونت Vazirmatn-Regular.ttf در کنار فایل‌های پروژه قرار دارد
        font_path = os.path.join(os.path.dirname(__file__), "Vazirmatn-Regular.ttf")
        
        # اگر فونت موجود نباشد، از فونت پیش‌فرض استفاده کند (ممکن است فارسی را به هم ریخته نمایش دهد)
        try:
            self.page.insert_font(fontname="fa", fontfile=font_path)
            self.font_name = "fa"
        except Exception:
            print("Warning: Vazirmatm font not found or could not be loaded. Using default font. Persian text might not render correctly.")
            self.font_name = "helv" # Fallback to a standard font


        # Header (عنوان صورتحساب و لوگو)
        self._draw_header(invoice_data, customer_data)

        # اطلاعات فروشنده و خریدار
        self._draw_seller_customer_info(customer_data)

        # جدول آیتم‌های صورتحساب
        self._draw_invoice_items_table(invoice_items)

        # جمع کل، تخفیف، مالیات و مبلغ نهایی
        self._draw_totals(invoice_data)

        # توضیحات
        self._draw_description(invoice_data)

        # امضا و مهر
        self._draw_signature_section()

        self.doc.save(output_path)
        self.doc.close()
        return True, output_path

    # اصلاح شد: محاسبه دستی موقعیت برای تراز راست
    def _draw_text_right_to_left(self, page, point, text, fontname, fontsize, color=(0, 0, 0), align_right=True, center_x=False):
        """
        این تابع متن را با قابلیت تراز راست یا مرکز (با محاسبه دستی) درج می‌کند.
        برای پشتیبانی کامل از bidi و شکست خط، ممکن است نیاز به کتابخانه‌های پیچیده‌تر باشد.
        """
        if fontname not in page.get_fonts(): # اطمینان از اینکه فونت در صفحه موجود است
            page.insert_font(fontname=fontname, fontfile=None) # اگر فونت از قبل بارگذاری نشده بود

        # محاسبه عرض متن
        # توجه: این متد ممکن است برای متن فارسی با فونت‌های پیچیده 100% دقیق نباشد
        # برای دقت بالا، باید از ابزارهای رندرینگ متن قوی‌تر استفاده کرد.
        text_width = page.get_text_length(text, fontname=fontname, fontsize=fontsize)

        x, y = point.x, point.y

        if align_right and not center_x:
            # برای تراز راست، x باید به اندازه عرض متن به چپ منتقل شود
            x = x - text_width
        elif center_x:
            # برای تراز مرکز، x باید به اندازه نصف عرض متن به چپ منتقل شود
            x = x - (text_width / 2)

        page.insert_text(fitz.Point(x, y), text, fontname=fontname, fontsize=fontsize, color=color)


    def _draw_header(self, invoice_data, customer_data):
        # Title (اکنون با center_x=True برای تراز وسط)
        self._draw_text_right_to_left(self.page, fitz.Point(self.page.rect.width / 2, self.y_cursor), "صورتحساب", self.font_name, 24, center_x=True)
        self.y_cursor -= 30

        # Invoice Number (تراز به راست پیش‌فرض)
        invoice_number_text = f"شماره صورتحساب: {invoice_data.invoice_number}"
        self._draw_text_right_to_left(self.page, fitz.Point(self.page.rect.width - 50, self.y_cursor), invoice_number_text, self.font_name, 12)
        self.y_cursor -= 20

        # Issue Date (تراز به راست پیش‌فرض)
        issue_date_text = f"تاریخ صدور: {invoice_data.issue_date}"
        self._draw_text_right_to_left(self.page, fitz.Point(self.page.rect.width - 50, self.y_cursor), issue_date_text, self.font_name, 12)
        self.y_cursor -= 20

        # Logo (optional)
        settings = self.settings_manager.get_settings()
        logo_path = settings.seller_logo_path
        if logo_path and os.path.exists(logo_path):
            try:
                # Resize logo to fit
                logo_rect = fitz.Rect(50, 750, 150, 800) # x0, y0, x1, y1 (top-left, bottom-right)
                pix = fitz.Pixmap(logo_path)
                if pix.alpha:
                    pix = fitz.Pixmap(pix, 0) # Convert to RGB if it has alpha channel
                self.page.insert_image(logo_rect, pixmap=pix)
            except Exception as e:
                print(f"Error inserting logo: {e}")
        
        self.y_cursor -= 20 # Add some space after header

    def _draw_seller_customer_info(self, customer_data):
        # Box for Seller Info
        seller_box_rect = fitz.Rect(self.page.rect.width / 2 + 10, self.y_cursor - 100, self.page.rect.width - 50, self.y_cursor - 10)
        self.page.draw_rect(seller_box_rect, color=(0.8, 0.8, 0.8), fill=(0.95, 0.95, 0.95), width=1)
        
        # Box for Customer Info
        customer_box_rect = fitz.Rect(50, self.y_cursor - 100, self.page.rect.width / 2 - 10, self.y_cursor - 10)
        self.page.draw_rect(customer_box_rect, color=(0.8, 0.8, 0.8), fill=(0.95, 0.95, 0.95), width=1)

        settings = self.settings_manager.get_settings()

        # Seller Info (همه به راست تراز شدند)
        seller_y = self.y_cursor - 20
        self._draw_text_right_to_left(self.page, fitz.Point(self.page.rect.width - 60, seller_y), "اطلاعات فروشنده:", self.font_name, 12, (0,0,0.5))
        seller_y -= 20
        self._draw_text_right_to_left(self.page, fitz.Point(self.page.rect.width - 60, seller_y), f"نام: {settings.seller_name}", self.font_name, 10)
        seller_y -= 15
        self._draw_text_right_to_left(self.page, fitz.Point(self.page.rect.width - 60, seller_y), f"آدرس: {settings.seller_address}", self.font_name, 10)
        seller_y -= 15
        self._draw_text_right_to_left(self.page, fitz.Point(self.page.rect.width - 60, seller_y), f"تلفن: {settings.seller_phone}", self.font_name, 10)
        seller_y -= 15
        self._draw_text_right_to_left(self.page, fitz.Point(self.page.rect.width - 60, seller_y), f"شناسه ملی/کد اقتصادی: {settings.seller_tax_id}/{settings.seller_economic_code}", self.font_name, 10)

        # Customer Info (همه به راست تراز شدند)
        customer_y = self.y_cursor - 20
        self._draw_text_right_to_left(self.page, fitz.Point(self.page.rect.width / 2 - 20, customer_y), "اطلاعات خریدار:", self.font_name, 12, (0,0,0.5))
        customer_y -= 20
        self._draw_text_right_to_left(self.page, fitz.Point(self.page.rect.width / 2 - 20, customer_y), f"نام: {customer_data.name}", self.font_name, 10)
        customer_y -= 15
        self._draw_text_right_to_left(self.page, fitz.Point(self.page.rect.width / 2 - 20, customer_y), f"آدرس: {customer_data.address if customer_data.address else ''}", self.font_name, 10)
        customer_y -= 15
        self._draw_text_right_to_left(self.page, fitz.Point(self.page.rect.width / 2 - 20, customer_y), f"تلفن: {customer_data.phone if customer_data.phone else ''}", self.font_name, 10)
        customer_y -= 15
        tax_id_label = "شناسه ملی/کد اقتصادی:" if customer_data.customer_type == "حقوقی" else "کد ملی:"
        self._draw_text_right_to_left(self.page, fitz.Point(self.page.rect.width / 2 - 20, customer_y), f"{tax_id_label} {customer_data.tax_id if customer_data.tax_id else ''}", self.font_name, 10)

        self.y_cursor -= 120 # Space after info boxes

    def _draw_invoice_items_table(self, invoice_items):
        table_start_y = self.y_cursor - 10 # شروع جدول از این ارتفاع
        table_x0 = 50
        table_x1 = self.page.rect.width - 50
        # ستون‌ها از راست به چپ: مبلغ کل، قیمت واحد، شرح کالا/خدمت، تعداد، ردیف
        # col_widths = [80, 80, 200, 100, 50] 
        col_x_positions = [table_x1 - 80, # مبلغ کل (از راست 50 شروع)
                           table_x1 - 80 - 80, # قیمت واحد
                           table_x1 - 80 - 80 - 200, # شرح کالا/خدمت
                           table_x1 - 80 - 80 - 200 - 100, # تعداد
                           table_x1 - 80 - 80 - 200 - 100 - 50] # ردیف
        
        # Table Headers (تراز به راست هر ستون)
        header_y = table_start_y - 15
        self._draw_text_right_to_left(self.page, fitz.Point(col_x_positions[0] + 70, header_y), "مبلغ کل", self.font_name, 10, (0.2,0.2,0.2))
        self._draw_text_right_to_left(self.page, fitz.Point(col_x_positions[1] + 70, header_y), "قیمت واحد", self.font_name, 10, (0.2,0.2,0.2))
        self._draw_text_right_to_left(self.page, fitz.Point(col_x_positions[2] + 190, header_y), "شرح کالا / خدمات", self.font_name, 10, (0.2,0.2,0.2)) 
        self._draw_text_right_to_left(self.page, fitz.Point(col_x_positions[3] + 90, header_y), "تعداد", self.font_name, 10, (0.2,0.2,0.2))
        self._draw_text_right_to_left(self.page, fitz.Point(col_x_positions[4] + 40, header_y), "ردیف", self.font_name, 10, (0.2,0.2,0.2))

        # Draw header underline
        self.page.draw_line(fitz.Point(table_x0, header_y - 5), fitz.Point(table_x1, header_y - 5))

        current_y = header_y - 25
        row_height = 20

        for i, item in enumerate(invoice_items):
            item_text = self.settings_manager.get_service_description_by_id(item.service_id)
            if not item_text: # اگر توضیحات سرویس یافت نشد، از توصیف آیتم فاکتور استفاده کن
                item_text = "توضیحات نامشخص"
            
            # تراز به راست برای هر سلول
            self._draw_text_right_to_left(self.page, fitz.Point(col_x_positions[4] + 40, current_y), str(i+1), self.font_name, 9)
            self._draw_text_right_to_left(self.page, fitz.Point(col_x_positions[3] + 90, current_y), f"{item.quantity:g}", self.font_name, 9)
            self._draw_text_right_to_left(self.page, fitz.Point(col_x_positions[2] + 190, current_y), item_text, self.font_name, 9) 
            self._draw_text_right_to_left(self.page, fitz.Point(col_x_positions[1] + 70, current_y), f"{int(item.unit_price):,}", self.font_name, 9)
            self._draw_text_right_to_left(self.page, fitz.Point(col_x_positions[0] + 70, current_y), f"{int(item.total_price):,}", self.font_name, 9)
            
            current_y -= row_height

        self.y_cursor = current_y - 20 # Space after table

    def _draw_totals(self, invoice_data):
        total_x_align = self.page.rect.width - 60 # نقطه برای تراز راست
        line_height = 20

        total_amount_text = f"جمع کل: {int(invoice_data.total_amount):,} ریال"
        self._draw_text_right_to_left(self.page, fitz.Point(total_x_align, self.y_cursor), total_amount_text, self.font_name, 10)
        self.y_cursor -= line_height

        discount_amount = invoice_data.total_amount * (invoice_data.discount_percentage / 100)
        discount_text = f"تخفیف ({invoice_data.discount_percentage}%): {int(discount_amount):,} ریال"
        self._draw_text_right_to_left(self.page, fitz.Point(total_x_align, self.y_cursor), discount_text, self.font_name, 10)
        self.y_cursor -= line_height

        tax_amount = (invoice_data.total_amount - discount_amount) * (invoice_data.tax_percentage / 100)
        tax_text = f"مالیات ({invoice_data.tax_percentage}%): {int(tax_amount):,} ریال"
        self._draw_text_right_to_left(self.page, fitz.Point(total_x_align, self.y_cursor), tax_text, self.font_name, 10)
        self.y_cursor -= line_height

        self.page.draw_line(fitz.Point(total_x_align - 100, self.y_cursor - 5), fitz.Point(total_x_align + 10, self.y_cursor - 5))
        self.y_cursor -= line_height

        final_amount_text = f"مبلغ نهایی: {int(invoice_data.final_amount):,} ریال"
        self._draw_text_right_to_left(self.page, fitz.Point(total_x_align, self.y_cursor), final_amount_text, self.font_name, 14, color=(0,0,0.8))
        self.y_cursor -= line_height * 2

    def _draw_description(self, invoice_data):
        if invoice_data.description:
            desc_text = f"توضیحات: {invoice_data.description}"
            self._draw_text_right_to_left(self.page, fitz.Point(self.page.rect.width - 60, self.y_cursor), desc_text, self.font_name, 10)
            self.y_cursor -= 40

    def _draw_signature_section(self):
        # Placeholder for signature
        self.page.draw_line(fitz.Point(100, self.y_cursor - 50), fitz.Point(250, self.y_cursor - 50))
        self._draw_text_right_to_left(self.page, fitz.Point(175, self.y_cursor - 65), "امضا و مهر فروشنده", self.font_name, 10)

# --- بلاک تست مستقل ---
if __name__ == "__main__":
    from models import AppSettings, Customer, Invoice, InvoiceItem, Service
    from settings_manager import SettingsManager
    from db_manager import DBManager, DATABASE_NAME
    import sys
    from service_manager import ServiceManager 

    # Setup a temporary database for testing
    current_dir_path = os.path.dirname(os.path.abspath(__file__)) 
    temp_db_path = os.path.join(current_dir_path, DATABASE_NAME)
    
    # Initialize DBManager and ensure tables/migrations are run
    db_manager_test = DBManager(temp_db_path)
    if db_manager_test.connect():
        db_manager_test.create_tables()
        db_manager_test.migrate_database()
        db_manager_test.close()
    else:
        print("Failed to connect to database for test setup.")
        sys.exit(1)

    settings_manager = SettingsManager()

    # Create dummy settings
    dummy_settings = AppSettings(
        id=1,
        seller_name="شرکت توسعه نرم‌افزار آسان",
        seller_address="تهران، خیابان آزادی، پلاک ۱۰۰",
        seller_phone="021-12345678",
        seller_tax_id="12345678901",
        seller_economic_code="0987654321",
        seller_logo_path=os.path.join(current_dir_path, "test_logo.png") # Put a test_logo.png next to this file
    )
    settings_manager.save_settings(dummy_settings)

    # Create a dummy customer
    dummy_customer = Customer(
        id=1,
        name="شرکت خریدار نمونه",
        customer_type="حقوقی",
        address="اصفهان، خیابان چهارباغ، کوچه اول",
        phone="031-98765432",
        tax_id="00000000001",
        email="customer@example.com"
    )
    # Ensure customer exists in DB for foreign key constraint
    # Using DBManager directly for simplicity in this test block
    db_manager_test.connect()
    db_manager_test.execute_query("INSERT OR IGNORE INTO Customers (id, customer_code, name, customer_type, address, phone, email, tax_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                 (dummy_customer.id, 1001, dummy_customer.name, dummy_customer.customer_type, dummy_customer.address, dummy_customer.phone, dummy_customer.email, dummy_customer.tax_id))
    db_manager_test.close()

    # Create dummy services
    svc_man = ServiceManager() # ایجاد یک شیء از ServiceManager برای استفاده از متدهای آن
    dummy_service1 = Service(id=1, service_code=101, description="خدمات طراحی وبسایت")
    dummy_service2 = Service(id=2, service_code=102, description="پشتیبانی نرم‌افزار (ماهانه)")
    # اضافه کردن خدمات با استفاده از service_manager
    svc_man.add_service(dummy_service1)
    svc_man.add_service(dummy_service2)


    # Create dummy invoice data
    invoice = Invoice(
        invoice_number="INV-1403-001",
        customer_id=dummy_customer.id,
        issue_date=jdatetime.date.today().strftime("%Y/%m/%d"),
        total_amount=120000000,
        discount_percentage=5,
        tax_percentage=9,
        final_amount=0, # This will be calculated by the generator or UI
        description="این صورتحساب بابت خدمات ارائه شده در خرداد ماه 1403 می‌باشد."
    )

    # Create dummy invoice items
    invoice_items_list = [
        InvoiceItem(invoice_id=None, service_id=dummy_service1.id, quantity=1, unit_price=100000000, total_price=100000000),
        InvoiceItem(invoice_id=None, service_id=dummy_service2.id, quantity=2, unit_price=10000000, total_price=20000000),
    ]

    # Calculate final amount for the dummy invoice
    total_items_amount = sum(item.total_price for item in invoice_items_list)
    discount_amount = total_items_amount * (invoice.discount_percentage / 100)
    tax_amount = (total_items_amount - discount_amount) * (invoice.tax_percentage / 100)
    invoice.final_amount = total_items_amount - discount_amount + tax_amount

    # Generate PDF
    invoice_gen = InvoiceGenerator(settings_manager)
    success, pdf_path = invoice_gen.create_invoice_pdf(invoice, dummy_customer, invoice_items_list, "sample_invoice.pdf")

    if success:
        print(f"Sample invoice generated at: {pdf_path}")
        # Open the PDF for preview (platform-dependent)
        try:
            if sys.platform == "win32":
                os.startfile(pdf_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", pdf_path])
            else:
                subprocess.run(["xdg-open", pdf_path])
        except Exception as e:
            print(f"Could not open PDF automatically: {e}")
    else:
        print(f"Failed to generate invoice PDF: {pdf_path}")

    print("\n--- End of InvoiceGenerator Test ---")