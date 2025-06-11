# models.py
import json 

class AppSettings:
    """ مدل داده‌ای برای تنظیمات برنامه """
    def __init__(self, id=None, seller_name=None, seller_address=None, seller_phone=None,
                 seller_tax_id=None, seller_economic_code=None, seller_logo_path=None,
                 db_version=1):
        self.id = id
        self.seller_name = seller_name
        self.seller_address = seller_address
        self.seller_phone = seller_phone
        self.seller_tax_id = seller_tax_id
        self.seller_economic_code = seller_economic_code
        self.seller_logo_path = seller_logo_path
        self.db_version = db_version

    def to_dict(self):
        return {
            "id": self.id,
            "seller_name": self.seller_name,
            "seller_address": self.seller_address,
            "seller_phone": self.seller_phone,
            "seller_tax_id": self.seller_tax_id,
            "seller_economic_code": self.seller_economic_code,
            "seller_logo_path": self.seller_logo_path,
            "db_version": self.db_version
        }

    @classmethod
    def from_dict(cls, data):
        filtered_data = {k: v for k, v in data.items() if k not in ["invoice_number_format", "last_invoice_number"]}
        return cls(**filtered_data)


class Customer:
    """ مدل داده‌ای برای مشتریان (company_name حذف شد) """
    def __init__(self, id=None, customer_code=None, name=None, customer_type=None, address=None,
                 phone=None, phone2=None, mobile=None, email=None, tax_id=None, postal_code=None, notes=None, registration_date=None):
        self.id = id
        self.customer_code = customer_code
        self.name = name
        self.customer_type = customer_type
        self.address = address
        self.phone = phone
        self.phone2 = phone2
        self.mobile = mobile
        self.email = email
        self.tax_id = tax_id
        self.postal_code = postal_code
        self.notes = notes
        self.registration_date = registration_date

    def to_dict(self):
        return {
            "id": self.id,
            "customer_code": self.customer_code,
            "name": self.name,
            "customer_type": self.customer_type,
            "address": self.address,
            "phone": self.phone,
            "phone2": self.phone2,
            "mobile": self.mobile,
            "email": self.email,
            "tax_id": self.tax_id,
            "postal_code": self.postal_code,
            "notes": self.notes,
            "registration_date": self.registration_date
        }

    @classmethod
    def from_dict(cls, data):
        data_copy = data.copy()
        data_copy.pop('company_name', None) 
        return cls(**data_copy)


class Service:
    """ مدل داده‌ای برای خدمات (settlement_type حذف شد) """
    def __init__(self, id=None, service_code=None, description=None):
        self.id = id
        self.service_code = service_code
        self.description = description

    def to_dict(self):
        return {
            "id": self.id,
            "service_code": self.service_code,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data):
        data_copy = data.copy()
        data_copy.pop('settlement_type', None)
        return cls(**data_copy)


class Contract:
    """ مدل داده‌ای برای قراردادها (ساده‌سازی فیلدها با بازگشت title و payment_method) """
    def __init__(self, id=None, customer_id=None, contract_number=None,
                 contract_date=None,  
                 total_amount=None, description=None,
                 title=None, # فیلد عنوان قرارداد (باقی ماند)
                 payment_method=None, # فیلد نحوه پرداخت (باقی ماند)
                 scanned_pages=None
                 ):
        self.id = id
        self.customer_id = customer_id
        self.contract_number = contract_number
        self.contract_date = contract_date 
        self.total_amount = total_amount
        self.description = description
        self.title = title # باقی ماند
        self.payment_method = payment_method # باقی ماند
        
        if isinstance(scanned_pages, str): 
            try: 
                self.scanned_pages = json.loads(scanned_pages) 
            except json.JSONDecodeError: 
                self.scanned_pages = [] 
        else: 
            self.scanned_pages = scanned_pages if scanned_pages is not None else [] 
            
        self.customer_name = None 

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "contract_number": self.contract_number,
            "contract_date": self.contract_date, 
            "total_amount": self.total_amount,
            "description": self.description,
            "title": self.title, 
            "payment_method": self.payment_method, 
            "scanned_pages": json.dumps(self.scanned_pages) 
        }

    @classmethod
    def from_dict(cls, data):
        data_copy = data.copy()
        
        if 'scanned_pages' in data_copy and isinstance(data_copy['scanned_pages'], str): 
            try: 
                data_copy['scanned_pages'] = json.loads(data_copy['scanned_pages']) 
            except json.JSONDecodeError: 
                data_copy['scanned_pages'] = [] 
        else: 
            data_copy['scanned_pages'] = [] 
            
        data_copy.pop('customer_name', None) 
        
        # حذف فیلدهایی که دیگر وجود ندارند تا هنگام ساخت شیء خطا ندهد
        data_copy.pop('start_date', None)
        data_copy.pop('end_date', None)
        data_copy.pop('services_provided', None)
        data_copy.pop('fiscal_year', None)

        return cls(**data_copy)


class Invoice:
    """ مدل داده‌ای برای صورتحساب‌ها """
    def __init__(self, id=None, invoice_number=None, customer_id=None, contract_id=None,
                 issue_date=None, due_date=None, total_amount=None,
                 discount_percentage=0, tax_percentage=0, final_amount=None, description=None):
        self.id = id
        self.invoice_number = invoice_number
        self.customer_id = customer_id
        self.contract_id = contract_id
        self.issue_date = issue_date
        self.due_date = due_date
        self.total_amount = total_amount
        self.discount_percentage = discount_percentage
        self.tax_percentage = tax_percentage
        self.final_amount = final_amount
        self.description = description
        self.customer_name = None # اضافه شد برای نمایش در لیست UI

    def to_dict(self):
        return {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "customer_id": self.customer_id,
            "contract_id": self.contract_id,
            "issue_date": self.issue_date,
            "due_date": self.due_date,
            "total_amount": self.total_amount,
            "discount_percentage": self.discount_percentage,
            "tax_percentage": self.tax_percentage,
            "final_amount": self.final_amount,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class InvoiceItem:
    """ مدل داده‌ای برای آیتم‌های هر صورتحساب """
    def __init__(self, id=None, invoice_id=None, service_id=None,
                 quantity=None, unit_price=None, total_price=None):
        self.id = id
        self.invoice_id = invoice_id
        self.service_id = service_id
        self.quantity = quantity
        self.unit_price = unit_price
        self.total_price = total_price

    def to_dict(self):
        return {
            "id": self.id,
            "invoice_id": self.invoice_id,
            "service_id": self.service_id,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total_price": self.total_price
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


# اضافه شد: مدل InvoiceTemplate
class InvoiceTemplate:
    """ مدل داده‌ای برای قالب‌های صورتحساب """
    def __init__(self, id=None, template_name=None, template_type=None, 
                 required_fields=None, default_settings=None, is_active=1, 
                 header_image_path=None, footer_image_path=None, 
                 background_image_path=None, background_opacity=1.0): # تغییرات جدید
        self.id = id
        self.template_name = template_name
        self.template_type = template_type
        
        # هندل کردن فیلدهای JSON
        if isinstance(required_fields, str):
            try:
                self.required_fields = json.loads(required_fields)
            except json.JSONDecodeError:
                self.required_fields = []
        else:
            self.required_fields = required_fields if required_fields is not None else []
            
        if isinstance(default_settings, str):
            try:
                self.default_settings = json.loads(default_settings)
            except json.JSONDecodeError:
                self.default_settings = {}
        else:
            self.default_settings = default_settings if default_settings is not None else {}
            
        self.is_active = is_active
        # self.notes = notes # حذف شد
        self.header_image_path = header_image_path
        self.footer_image_path = footer_image_path
        self.background_image_path = background_image_path
        self.background_opacity = background_opacity

    def to_dict(self):
        return {
            "id": self.id,
            "template_name": self.template_name,
            "template_type": self.template_type,
            "required_fields": json.dumps(self.required_fields),
            "default_settings": json.dumps(self.default_settings),
            "is_active": self.is_active,
            # "notes": self.notes, # حذف شد
            "header_image_path": self.header_image_path,
            "footer_image_path": self.footer_image_path,
            "background_image_path": self.background_image_path,
            "background_opacity": self.background_opacity
        }

    @classmethod
    def from_dict(cls, data):
        # مطمئن شوید که فیلدهای JSON به درستی از رشته به دیکشنری/لیست تبدیل می‌شوند
        data_copy = data.copy()
        if 'required_fields' in data_copy and isinstance(data_copy['required_fields'], str):
            data_copy['required_fields'] = json.loads(data_copy['required_fields'])
        if 'default_settings' in data_copy and isinstance(data_copy['default_settings'], str):
            data_copy['default_settings'] = json.loads(data_copy['default_settings'])
        
        # حذف فیلد notes اگر هنوز در دیتابیس وجود داشت
        data_copy.pop('notes', None)

        return cls(**data_copy)