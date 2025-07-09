import random
import time
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from src.models.banking_models import db, BankAccount, AccountTransaction, AccountStatus, AccountType, TransactionType

class BankingService:
    def __init__(self):
        self.supported_banks = {
            'WF': 'Wells Fargo Bank',
            'BOA': 'Bank of America', 
            'CITI': 'Citibank',
            'CHASE': 'JPMorgan Chase',
            'USB': 'US Bank'
        }
    
    def create_bank_account(self, account_data):
        """Create a new bank account"""
        try:
            # Validate input
            validation_errors = self._validate_account_creation(account_data)
            if validation_errors:
                return {'success': False, 'errors': validation_errors}
            
            # Set default bank if not provided
            bank_code = account_data.get('bank_code', 'WF')
            bank_name = self.supported_banks.get(bank_code, 'Demo Bank')
            
            account = BankAccount(
                customer_id=account_data['customer_id'],
                bank_name=bank_name,
                bank_code=bank_code,
                account_type=AccountType(account_data.get('account_type', 'checking')),
                current_balance=Decimal(str(account_data.get('initial_balance', '1000.00'))),
                available_balance=Decimal(str(account_data.get('initial_balance', '1000.00'))),
                currency=account_data.get('currency', 'USD'),
                daily_limit=Decimal(str(account_data.get('daily_limit', '5000.00'))),
                overdraft_limit=Decimal(str(account_data.get('overdraft_limit', '500.00')))
            )
            
            db.session.add(account)
            db.session.flush()  # Get the ID
            
            # Create initial balance transaction if there's a starting balance
            if account.current_balance > 0:
                initial_transaction = AccountTransaction(
                    account_id=account.id,
                    transaction_type=TransactionType.CREDIT,
                    amount=account.current_balance,
                    balance_before=Decimal('0.00'),
                    balance_after=account.current_balance,
                    reference_type='initial_deposit',
                    description='Initial account balance',
                    processed_by='system'
                )
                db.session.add(initial_transaction)
            
            db.session.commit()
            return {'success': True, 'account': account.to_dict()}
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return {'success': False, 'errors': [f'Database error: {str(e)}']}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'errors': [str(e)]}
    
    def get_account_balance(self, account_id):
        """Get current account balance"""
        try:
            account = BankAccount.query.get(account_id)
            if not account:
                return {'success': False, 'errors': ['Account not found']}
            
            return {
                'success': True,
                'balance': {
                    'current_balance': float(account.current_balance),
                    'available_balance': float(account.available_balance),
                    'effective_balance': float(account.effective_balance),
                    'currency': account.currency,
                    'status': account.status.value
                }
            }
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}
    
    def debit_account(self, account_id, amount, reference_id=None, reference_type='payment', description=None):
        """Debit amount from account (for payments)"""
        try:
            account = BankAccount.query.get(account_id)
            if not account:
                return {'success': False, 'errors': ['Account not found']}
            
            amount = Decimal(str(amount))
            
            # Check account status
            if not account.is_active():
                return {'success': False, 'errors': [f'Account is {account.status.value}']}
            
            # Check sufficient balance
            if not account.has_sufficient_balance(amount):
                return {
                    'success': False, 
                    'errors': [f'Insufficient funds. Available: {account.effective_balance}, Requested: {amount}']
                }
            
            # Check daily limit
            daily_total = self._get_daily_debit_total(account_id)
            if daily_total + amount > account.daily_limit:
                return {
                    'success': False,
                    'errors': [f'Daily limit exceeded. Limit: {account.daily_limit}, Used today: {daily_total}']
                }
            
            # Process debit
            balance_before = account.current_balance
            account.current_balance -= amount
            account.available_balance = account.current_balance
            account.last_transaction_at = datetime.utcnow()
            
            # Create transaction record
            transaction = AccountTransaction(
                account_id=account.id,
                transaction_type=TransactionType.PAYMENT_DEBIT,
                amount=amount,
                balance_before=balance_before,
                balance_after=account.current_balance,
                reference_id=reference_id,
                reference_type=reference_type,
                description=description or f'Payment debit - {reference_id}',
                processed_by='payment_system'
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            return {
                'success': True,
                'transaction': transaction.to_dict(),
                'new_balance': float(account.current_balance)
            }
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return {'success': False, 'errors': [f'Database error: {str(e)}']}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'errors': [str(e)]}
    
    def credit_account(self, account_id, amount, reference_id=None, reference_type='refund', description=None):
        """Credit amount to account (for refunds)"""
        try:
            account = BankAccount.query.get(account_id)
            if not account:
                return {'success': False, 'errors': ['Account not found']}
            
            amount = Decimal(str(amount))
            
            # Process credit
            balance_before = account.current_balance
            account.current_balance += amount
            account.available_balance = account.current_balance
            account.last_transaction_at = datetime.utcnow()
            
            # Create transaction record
            transaction = AccountTransaction(
                account_id=account.id,
                transaction_type=TransactionType.REFUND_CREDIT,
                amount=amount,
                balance_before=balance_before,
                balance_after=account.current_balance,
                reference_id=reference_id,
                reference_type=reference_type,
                description=description or f'Refund credit - {reference_id}',
                processed_by='payment_system'
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            return {
                'success': True,
                'transaction': transaction.to_dict(),
                'new_balance': float(account.current_balance)
            }
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return {'success': False, 'errors': [f'Database error: {str(e)}']}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'errors': [str(e)]}
    
    def get_account_transactions(self, account_id, limit=50, offset=0):
        """Get account transaction history"""
        try:
            account = BankAccount.query.get(account_id)
            if not account:
                return {'success': False, 'errors': ['Account not found']}
            
            transactions = AccountTransaction.query.filter_by(account_id=account_id)\
                .order_by(AccountTransaction.created_at.desc())\
                .offset(offset).limit(limit).all()
            
            total = AccountTransaction.query.filter_by(account_id=account_id).count()
            
            return {
                'success': True,
                'transactions': [t.to_dict() for t in transactions],
                'total': total,
                'offset': offset,
                'limit': limit
            }
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}
    
    def update_account_status(self, account_id, status, reason=None):
        """Update account status (freeze, activate, etc.)"""
        try:
            account = BankAccount.query.get(account_id)
            if not account:
                return {'success': False, 'errors': ['Account not found']}
            
            old_status = account.status
            account.status = AccountStatus(status)
            account.updated_at = datetime.utcnow()
            
            # Create audit transaction
            transaction = AccountTransaction(
                account_id=account.id,
                transaction_type=TransactionType.DEBIT if status == 'frozen' else TransactionType.CREDIT,
                amount=Decimal('0.00'),
                balance_before=account.current_balance,
                balance_after=account.current_balance,
                reference_type='status_change',
                description=f'Status changed from {old_status.value} to {status}. Reason: {reason or "System action"}',
                processed_by='admin_system'
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            return {
                'success': True,
                'account': account.to_dict(),
                'old_status': old_status.value,
                'new_status': status
            }
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return {'success': False, 'errors': [f'Database error: {str(e)}']}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'errors': [str(e)]}
    
    def find_customer_accounts(self, customer_id):
        """Find all accounts for a customer"""
        try:
            accounts = BankAccount.query.filter_by(customer_id=customer_id).all()
            return {
                'success': True,
                'accounts': [account.to_dict() for account in accounts]
            }
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}
    
    def _validate_account_creation(self, account_data):
        """Validate account creation data"""
        errors = []
        
        if not account_data.get('customer_id'):
            errors.append('Customer ID is required')
        
        # Validate account type
        account_type = account_data.get('account_type', 'checking')
        try:
            AccountType(account_type)
        except ValueError:
            valid_types = [t.value for t in AccountType]
            errors.append(f'Invalid account type. Valid types: {", ".join(valid_types)}')
        
        # Validate initial balance
        try:
            initial_balance = Decimal(str(account_data.get('initial_balance', '0')))
            if initial_balance < 0:
                errors.append('Initial balance cannot be negative')
        except (ValueError, TypeError):
            errors.append('Invalid initial balance format')
        
        return errors
    
    def _get_daily_debit_total(self, account_id):
        """Calculate total debits for today"""
        today = datetime.utcnow().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())
        
        total = db.session.query(func.sum(AccountTransaction.amount))\
            .filter(
                AccountTransaction.account_id == account_id,
                AccountTransaction.transaction_type.in_([
                    TransactionType.DEBIT, 
                    TransactionType.PAYMENT_DEBIT,
                    TransactionType.TRANSFER_OUT
                ]),
                AccountTransaction.created_at.between(start_of_day, end_of_day)
            ).scalar() or Decimal('0')
        
        return total