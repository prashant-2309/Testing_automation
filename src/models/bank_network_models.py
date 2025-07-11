from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from enum import Enum
from decimal import Decimal
from .payment_models import db

class BankType(Enum):
    ISSUER = "issuer"           # Customer's bank
    ACQUIRER = "acquirer"       # Merchant's bank
    DUAL = "dual"              # Both issuer and acquirer

class BankTier(Enum):
    TIER_1 = "tier_1"          # Large national banks
    TIER_2 = "tier_2"          # Regional banks
    TIER_3 = "tier_3"          # Community banks

class TransactionStatus(Enum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    DECLINED = "declined"
    SETTLED = "settled"
    FAILED = "failed"

class BankConfiguration(db.Model):
    __tablename__ = 'bank_configurations'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    bank_code = db.Column(db.String(10), unique=True, nullable=False, index=True)
    bank_name = db.Column(db.String(100), nullable=False)
    bank_type = db.Column(db.Enum(BankType), nullable=False)
    bank_tier = db.Column(db.Enum(BankTier), nullable=False, default=BankTier.TIER_2)
    
    # Processing characteristics
    base_response_time_ms = db.Column(db.Integer, default=500)  # Base response time
    success_rate = db.Column(db.Numeric(3, 2), default=Decimal('0.95'))  # 95% success rate
    daily_transaction_limit = db.Column(db.Numeric(15, 2), default=Decimal('100000.00'))
    single_transaction_limit = db.Column(db.Numeric(10, 2), default=Decimal('10000.00'))
    
    # Fees and costs
    per_transaction_fee = db.Column(db.Numeric(5, 2), default=Decimal('0.30'))
    percentage_fee = db.Column(db.Numeric(4, 3), default=Decimal('0.025'))  # 2.5%
    
    # Geographic and currency support
    supported_currencies = db.Column(db.Text)  # JSON string of supported currencies
    country_code = db.Column(db.String(2), default='US')
    
    # Operating hours (for simulation)
    business_hours_start = db.Column(db.Integer, default=9)    # 9 AM
    business_hours_end = db.Column(db.Integer, default=17)     # 5 PM
    supports_24_7 = db.Column(db.Boolean, default=True)
    
    # Risk management
    fraud_detection_level = db.Column(db.String(20), default='medium')  # low, medium, high
    requires_3ds = db.Column(db.Boolean, default=False)  # 3D Secure requirement
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    def get_supported_currencies(self):
        """Get list of supported currencies"""
        if self.supported_currencies:
            try:
                import json
                # Handle both string (JSON) and already parsed data
                if isinstance(self.supported_currencies, str):
                    return json.loads(self.supported_currencies)
                elif isinstance(self.supported_currencies, list):
                    return self.supported_currencies
                else:
                    return ['USD']  # Default fallback
            except (json.JSONDecodeError, TypeError):
                return ['USD']  # Default fallback
        return ['USD']
    
    def set_supported_currencies(self, currencies):
        """Set supported currencies"""
        import json
        if isinstance(currencies, list):
            self.supported_currencies = json.dumps(currencies)
        elif isinstance(currencies, str):
            self.supported_currencies = currencies  # Already JSON string
        else:
            self.supported_currencies = json.dumps(['USD'])
    
    def to_dict(self):
        return {
            'id': self.id,
            'bank_code': self.bank_code,
            'bank_name': self.bank_name,
            'bank_type': self.bank_type.value,
            'bank_tier': self.bank_tier.value,
            'base_response_time_ms': self.base_response_time_ms,
            'success_rate': float(self.success_rate),
            'daily_transaction_limit': float(self.daily_transaction_limit),
            'single_transaction_limit': float(self.single_transaction_limit),
            'per_transaction_fee': float(self.per_transaction_fee),
            'percentage_fee': float(self.percentage_fee),
            'supported_currencies': self.get_supported_currencies(),
            'country_code': self.country_code,
            'business_hours_start': self.business_hours_start,
            'business_hours_end': self.business_hours_end,
            'supports_24_7': self.supports_24_7,
            'fraud_detection_level': self.fraud_detection_level,
            'requires_3ds': self.requires_3ds,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class MerchantAccount(db.Model):
    __tablename__ = 'merchant_accounts'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    merchant_id = db.Column(db.String(100), nullable=False, index=True)
    acquirer_bank_code = db.Column(db.String(10), nullable=False, index=True)
    account_number = db.Column(db.String(20), nullable=False)
    
    # Account details
    business_name = db.Column(db.String(200), nullable=False)
    business_type = db.Column(db.String(50), default='retail')  # retail, ecommerce, service, etc.
    mcc_code = db.Column(db.String(4))  # Merchant Category Code
    
    # Financial details
    current_balance = db.Column(db.Numeric(15, 2), default=Decimal('0.00'))
    reserved_balance = db.Column(db.Numeric(15, 2), default=Decimal('0.00'))
    currency = db.Column(db.String(3), default='USD')
    
    # Risk and limits
    monthly_volume_limit = db.Column(db.Numeric(15, 2), default=Decimal('500000.00'))
    daily_volume_limit = db.Column(db.Numeric(12, 2), default=Decimal('50000.00'))
    risk_level = db.Column(db.String(20), default='low')  # low, medium, high
    
    # Settlement
    settlement_frequency = db.Column(db.String(20), default='daily')  # daily, weekly, monthly
    settlement_delay_days = db.Column(db.Integer, default=2)
    
    # Status
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def generate_account_number(self):
        """Generate unique merchant account number"""
        import random
        return f"{self.acquirer_bank_code}M{random.randint(10000000, 99999999)}"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.account_number:
            self.account_number = self.generate_account_number()
    
    def to_dict(self):
        return {
            'id': self.id,
            'merchant_id': self.merchant_id,
            'acquirer_bank_code': self.acquirer_bank_code,
            'account_number': self.account_number,
            'business_name': self.business_name,
            'business_type': self.business_type,
            'mcc_code': self.mcc_code,
            'current_balance': float(self.current_balance),
            'reserved_balance': float(self.reserved_balance),
            'currency': self.currency,
            'monthly_volume_limit': float(self.monthly_volume_limit),
            'daily_volume_limit': float(self.daily_volume_limit),
            'risk_level': self.risk_level,
            'settlement_frequency': self.settlement_frequency,
            'settlement_delay_days': self.settlement_delay_days,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class NetworkTransaction(db.Model):
    __tablename__ = 'network_transactions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_id = db.Column(db.String(36), nullable=False, index=True)
    
    # Bank routing
    issuer_bank_code = db.Column(db.String(10), nullable=False, index=True)
    acquirer_bank_code = db.Column(db.String(10), nullable=False, index=True)
    
    # Transaction details
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    transaction_type = db.Column(db.String(20), default='purchase')  # purchase, refund, reversal
    
    # Processing details
    issuer_response_time_ms = db.Column(db.Integer)
    acquirer_response_time_ms = db.Column(db.Integer)
    total_processing_time_ms = db.Column(db.Integer)
    
    # Status tracking
    issuer_status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)
    acquirer_status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)
    final_status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)
    
    # Response codes
    issuer_response_code = db.Column(db.String(10))
    acquirer_response_code = db.Column(db.String(10))
    decline_reason = db.Column(db.String(100))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    issuer_processed_at = db.Column(db.DateTime)
    acquirer_processed_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'payment_id': self.payment_id,
            'issuer_bank_code': self.issuer_bank_code,
            'acquirer_bank_code': self.acquirer_bank_code,
            'amount': float(self.amount),
            'currency': self.currency,
            'transaction_type': self.transaction_type,
            'issuer_response_time_ms': self.issuer_response_time_ms,
            'acquirer_response_time_ms': self.acquirer_response_time_ms,
            'total_processing_time_ms': self.total_processing_time_ms,
            'issuer_status': self.issuer_status.value,
            'acquirer_status': self.acquirer_status.value,
            'final_status': self.final_status.value,
            'issuer_response_code': self.issuer_response_code,
            'acquirer_response_code': self.acquirer_response_code,
            'decline_reason': self.decline_reason,
            'created_at': self.created_at.isoformat(),
            'issuer_processed_at': self.issuer_processed_at.isoformat() if self.issuer_processed_at else None,
            'acquirer_processed_at': self.acquirer_processed_at.isoformat() if self.acquirer_processed_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }