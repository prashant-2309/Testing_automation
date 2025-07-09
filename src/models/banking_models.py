from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from enum import Enum
from decimal import Decimal
from .payment_models import db

class AccountStatus(Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"
    SUSPENDED = "suspended"

class AccountType(Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT = "credit"

class TransactionType(Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    PAYMENT_DEBIT = "payment_debit"
    REFUND_CREDIT = "refund_credit"

class BankAccount(db.Model):
    __tablename__ = 'bank_accounts'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.String(100), nullable=False, index=True)
    bank_name = db.Column(db.String(100), nullable=False)
    bank_code = db.Column(db.String(10), nullable=False)
    account_type = db.Column(db.Enum(AccountType), nullable=False, default=AccountType.CHECKING)
    status = db.Column(db.Enum(AccountStatus), nullable=False, default=AccountStatus.ACTIVE)
    
    # Balance information
    current_balance = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    available_balance = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    currency = db.Column(db.String(3), nullable=False, default='USD')
    
    # Limits and overdraft
    daily_limit = db.Column(db.Numeric(10, 2), default=Decimal('5000.00'))
    overdraft_limit = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_transaction_at = db.Column(db.DateTime)
    
    # Relationships
    transactions = db.relationship('AccountTransaction', backref='account', lazy=True, cascade='all, delete-orphan')
    
    # Indexes
    __table_args__ = (
        db.Index('idx_customer_bank', 'customer_id', 'bank_code'),
        db.Index('idx_status_balance', 'status', 'current_balance'),
        db.Index('idx_account_type_status', 'account_type', 'status'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.account_number:
            self.account_number = self.generate_account_number()
    
    def generate_account_number(self):
        """Generate unique account number"""
        import random
        return f"{self.bank_code}{random.randint(100000000, 999999999)}"
    
    @property
    def effective_balance(self):
        """Balance including overdraft"""
        return self.current_balance + self.overdraft_limit
    
    def is_active(self):
        """Check if account is active"""
        return self.status == AccountStatus.ACTIVE
    
    def has_sufficient_balance(self, amount):
        """Check if account has sufficient balance"""
        return self.effective_balance >= Decimal(str(amount))
    
    def to_dict(self):
        return {
            'id': self.id,
            'account_number': self.account_number,
            'customer_id': self.customer_id,
            'bank_name': self.bank_name,
            'bank_code': self.bank_code,
            'account_type': self.account_type.value,
            'status': self.status.value,
            'current_balance': float(self.current_balance),
            'available_balance': float(self.available_balance),
            'currency': self.currency,
            'daily_limit': float(self.daily_limit),
            'overdraft_limit': float(self.overdraft_limit),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_transaction_at': self.last_transaction_at.isoformat() if self.last_transaction_at else None
        }

class AccountTransaction(db.Model):
    __tablename__ = 'account_transactions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = db.Column(db.String(36), db.ForeignKey('bank_accounts.id'), nullable=False, index=True)
    transaction_type = db.Column(db.Enum(TransactionType), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    balance_before = db.Column(db.Numeric(15, 2), nullable=False)
    balance_after = db.Column(db.Numeric(15, 2), nullable=False)
    
    # Reference information
    reference_id = db.Column(db.String(100), index=True)  # Payment ID, Transfer ID, etc.
    reference_type = db.Column(db.String(20))  # payment, transfer, adjustment
    description = db.Column(db.Text)
    
    # Transaction details
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    processed_by = db.Column(db.String(100))  # System or user who processed
    
    # Indexes
    __table_args__ = (
        db.Index('idx_account_date', 'account_id', 'created_at'),
        db.Index('idx_reference', 'reference_type', 'reference_id'),
        db.Index('idx_transaction_type_date', 'transaction_type', 'created_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'transaction_type': self.transaction_type.value,
            'amount': float(self.amount),
            'balance_before': float(self.balance_before),
            'balance_after': float(self.balance_after),
            'reference_id': self.reference_id,
            'reference_type': self.reference_type,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'processed_by': self.processed_by
        }