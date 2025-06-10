# models.py

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
    """ مدل داده‌ای برای مشتریان """
    def __init__(self, id=None, name=None, company_name=None, address=None,
                 phone=None, email=None, tax_id=None, registration_date=None):
        self.id = id
        self.name = name
        self.company_name = company_name
        self.address = address
        self.phone = phone
        self.email = email
        self.tax_id = tax_id
        self.registration_date = registration_date

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "company_name": self.company_name,
            "address": self.address,
            "phone": self.phone,
            "email": self.email,
            "tax_id": self.tax_id,
            "registration_date": self.registration_date
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class Service:
    """ مدل داده‌ای برای خدمات (تغییر یافته) """
    def __init__(self, id=None, service_code=None, description=None, settlement_type=None): # --- تغییرات اینجا: service_code اضافه شد ---
        self.id = id
        self.service_code = service_code # --- ستون جدید ---
        self.description = description
        self.settlement_type = settlement_type

    def to_dict(self):
        return {
            "id": self.id,
            "service_code": self.service_code, # --- ستون جدید ---
            "description": self.description,
            "settlement_type": self.settlement_type
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class Contract:
    """ مدل داده‌ای برای قراردادها """
    def __init__(self, id=None, customer_id=None, contract_number=None,
                 start_date=None, end_date=None, total_amount=None, description=None):
        self.id = id
        self.customer_id = customer_id
        self.contract_number = contract_number
        self.start_date = start_date
        self.end_date = end_date
        self.total_amount = total_amount
        self.description = description

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "contract_number": self.contract_number,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "total_amount": self.total_amount,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


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