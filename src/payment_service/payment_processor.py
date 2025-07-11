import decimal
from decimal import Decimal
import random
import time
from datetime import datetime
from src.models.payment_models import db, Payment, Refund, Transaction, PaymentStatus, PaymentMethod
from src.banking_service.banking_processor import BankingService
from src.models.banking_models import BankAccount
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

class PaymentProcessor:
    def __init__(self):
        self.supported_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD']
        self.max_amount = Decimal('10000.00')
        self.min_amount = Decimal('0.01')
        self.banking_service = BankingService()
    
    def validate_payment_request(self, payment_data):
        """Validate payment request data"""
        errors = []
        
        # Amount validation
        try:
            amount = Decimal(str(payment_data.get('amount', 0)))
            if amount < self.min_amount:
                errors.append(f"Amount must be at least {self.min_amount}")
            if amount > self.max_amount:
                errors.append(f"Amount cannot exceed {self.max_amount}")
        except (ValueError, TypeError, decimal.InvalidOperation):
            errors.append("Invalid amount format")
        
        # Currency validation
        currency = payment_data.get('currency', 'USD').upper()
        if currency not in self.supported_currencies:
            errors.append(f"Currency {currency} not supported. Supported: {', '.join(self.supported_currencies)}")
        
        # Required fields
        required_fields = ['merchant_id', 'customer_id', 'payment_method']
        for field in required_fields:
            if not payment_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Payment method validation
        payment_method = payment_data.get('payment_method')
        try:
            PaymentMethod(payment_method)
        except ValueError:
            valid_methods = [method.value for method in PaymentMethod]
            errors.append(f"Invalid payment method: {payment_method}. Valid methods: {', '.join(valid_methods)}")
        
        return errors
    
    def _find_customer_bank_account(self, customer_id, currency='USD'):
        """Find active bank account for customer"""
        try:
            accounts_result = self.banking_service.find_customer_accounts(customer_id)
            if not accounts_result['success']:
                return None
            
            # Find active account with matching currency
            for account in accounts_result['accounts']:
                if (account['status'] == 'active' and 
                    account['currency'] == currency and
                    account['account_type'] in ['checking', 'savings']):
                    return account
            
            return None
        except Exception:
            return None
    
    def create_payment(self, payment_data):
        """Create a new payment with bank account validation"""
        validation_errors = self.validate_payment_request(payment_data)
        if validation_errors:
            return {'success': False, 'errors': validation_errors}
        
        try:
            # Find customer's bank account
            currency = payment_data.get('currency', 'USD').upper()
            bank_account = self._find_customer_bank_account(
                payment_data['customer_id'], 
                currency
            )
            
            if not bank_account:
                return {
                    'success': False, 
                    'errors': [f'No active bank account found for customer {payment_data["customer_id"]} in {currency}']
                }
            
            payment = Payment(
                merchant_id=payment_data['merchant_id'],
                customer_id=payment_data['customer_id'],
                amount=Decimal(str(payment_data['amount'])),
                currency=currency,
                payment_method=PaymentMethod(payment_data['payment_method']),
                description=payment_data.get('description', ''),
                card_last_four=payment_data.get('card_last_four'),
                card_type=payment_data.get('card_type'),
                bank_account_id=bank_account['id']  # Link to bank account
            )
            
            db.session.add(payment)
            db.session.commit()
            
            return {'success': True, 'payment': payment.to_dict()}
        
        except SQLAlchemyError as e:
            db.session.rollback()
            return {'success': False, 'errors': [f'Database error: {str(e)}']}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'errors': [str(e)]}

    def process_payment(self, payment_id):
        """Process a pending payment through multi-bank network"""
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                return {'success': False, 'errors': ['Payment not found']}
            
            if payment.status != PaymentStatus.PENDING:
                return {'success': False, 'errors': [f'Payment is not in pending status. Current status: {payment.status.value}']}
            
            # Update payment status to processing
            payment.status = PaymentStatus.PROCESSING
            db.session.commit()
            
            print(f"🚀 Processing payment {payment_id} through multi-bank network")
            
            # Process through payment network if bank account is linked
            if hasattr(payment, 'bank_account_id') and payment.bank_account_id:
                from src.banking_service.payment_network import PaymentNetworkService
                
                network_service = PaymentNetworkService()
                
                payment_data = {
                    'payment_id': payment.id,
                    'amount': payment.amount,
                    'currency': payment.currency,
                    'bank_account_id': payment.bank_account_id,
                    'merchant_id': payment.merchant_id
                }
                
                network_result = network_service.process_two_party_transaction(payment_data)
                
                if network_result['success']:
                    # Network processing succeeded
                    payment.status = PaymentStatus.COMPLETED
                    payment.processed_at = datetime.utcnow()
                    
                    # Create comprehensive transaction record
                    transaction = Transaction(
                        payment_id=payment.id,
                        transaction_type='charge',
                        amount=payment.amount,
                        gateway_response=f"SUCCESS via {network_result['transaction_details']['issuer_bank']} → {network_result['transaction_details']['acquirer_bank']}",
                        gateway_transaction_id=network_result.get('authorization_code', f"net_{random.randint(100000, 999999)}")
                    )
                    db.session.add(transaction)
                    
                    # Store network details in payment (if you want to extend the model)
                    db.session.commit()
                    
                    result = payment.to_dict()
                    result['network_details'] = network_result['transaction_details']
                    
                    return {'success': True, 'payment': result}
                else:
                    # Network processing failed
                    payment.status = PaymentStatus.FAILED
                    
                    transaction = Transaction(
                        payment_id=payment.id,
                        transaction_type='charge',
                        amount=payment.amount,
                        gateway_response=f"NETWORK_DECLINED: {network_result['error']}",
                        gateway_transaction_id=f"net_fail_{random.randint(100000, 999999)}"
                    )
                    db.session.add(transaction)
                    db.session.commit()
                    
                    result = payment.to_dict()
                    if network_result.get('transaction_details'):
                        result['network_details'] = network_result['transaction_details']
                    
                    return {'success': True, 'payment': result}
            else:
                # Fallback to old processing logic
                time.sleep(0.1)
                success = random.random() > 0.1
                
                if success:
                    payment.status = PaymentStatus.COMPLETED
                    payment.processed_at = datetime.utcnow()
                    
                    transaction = Transaction(
                        payment_id=payment.id,
                        transaction_type='charge',
                        amount=payment.amount,
                        gateway_response='SUCCESS (fallback)',
                        gateway_transaction_id=f"fallback_{random.randint(100000, 999999)}"
                    )
                    db.session.add(transaction)
                else:
                    payment.status = PaymentStatus.FAILED
                    
                    transaction = Transaction(
                        payment_id=payment.id,
                        transaction_type='charge',
                        amount=payment.amount,
                        gateway_response='DECLINED (fallback)',
                        gateway_transaction_id=f"fallback_fail_{random.randint(100000, 999999)}"
                    )
                    db.session.add(transaction)
                
                db.session.commit()
                return {'success': True, 'payment': payment.to_dict()}
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return {'success': False, 'errors': [f'Database error: {str(e)}']}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'errors': [str(e)]}
    
    
    def refund_payment(self, payment_id, refund_data):
        """Process a refund for a payment with bank account credit"""
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                return {'success': False, 'errors': ['Payment not found']}
            
            if payment.status != PaymentStatus.COMPLETED:
                return {'success': False, 'errors': [f'Payment is not completed. Current status: {payment.status.value}']}
            
            refund_amount = Decimal(str(refund_data.get('amount', payment.amount)))
            
            # Calculate total refunded amount
            total_refunded = db.session.query(func.sum(Refund.amount)).filter(
                Refund.payment_id == payment.id,
                Refund.status == PaymentStatus.COMPLETED
            ).scalar() or Decimal('0')
            
            if total_refunded + refund_amount > payment.amount:
                available_amount = payment.amount - total_refunded
                return {'success': False, 'errors': [f'Refund amount {refund_amount} exceeds available amount {available_amount}']}
            
            refund = Refund(
                payment_id=payment.id,
                amount=refund_amount,
                reason=refund_data.get('reason', 'Customer request'),
                status=PaymentStatus.COMPLETED,
                processed_at=datetime.utcnow()
            )
            
            db.session.add(refund)
            
            # Credit the bank account if bank_account_id exists
            if hasattr(payment, 'bank_account_id') and payment.bank_account_id:
                credit_result = self.banking_service.credit_account(
                    payment.bank_account_id,
                    refund_amount,
                    reference_id=refund.id,
                    reference_type='refund',
                    description=f'Refund from {payment.merchant_id}'
                )
                
                if not credit_result['success']:
                    db.session.rollback()
                    return {'success': False, 'errors': ['Failed to credit bank account']}
            
            # Update payment status
            new_total_refunded = total_refunded + refund_amount
            if new_total_refunded == payment.amount:
                payment.status = PaymentStatus.REFUNDED
            else:
                payment.status = PaymentStatus.PARTIAL_REFUNDED
            
            # Create transaction record
            transaction = Transaction(
                payment_id=payment.id,
                transaction_type='refund',
                amount=refund_amount,
                gateway_response='SUCCESS',
                gateway_transaction_id=f"ref_{random.randint(100000, 999999)}"
            )
            db.session.add(transaction)
            
            db.session.commit()
            return {'success': True, 'refund': refund.to_dict()}
        
        except SQLAlchemyError as e:
            db.session.rollback()
            return {'success': False, 'errors': [f'Database error: {str(e)}']}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'errors': [str(e)]}
    
    def get_payment(self, payment_id):
        """Get payment details"""
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                return {'success': False, 'errors': ['Payment not found']}
            
            return {'success': True, 'payment': payment.to_dict()}
        
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}
    
    def get_payment_transactions(self, payment_id):
        """Get all transactions for a payment"""
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                return {'success': False, 'errors': ['Payment not found']}
            
            transactions = Transaction.query.filter_by(payment_id=payment_id).order_by(Transaction.created_at.desc()).all()
            return {
                'success': True, 
                'transactions': [t.to_dict() for t in transactions]
            }
        
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}

    def validate_payment_request(self, payment_data):
        errors = []
        
        # Amount validation
        try:
            amount = Decimal(str(payment_data.get('amount', 0)))
            currency = payment_data.get('currency', 'USD').upper()
            
            # Different validation for JPY (no decimals, higher amounts)
            if currency == 'JPY':
                min_amount = Decimal('1')
                max_amount = Decimal('1000000')  # 1 million JPY (~$7,500)
            else:
                min_amount = self.min_amount
                max_amount = self.max_amount
                
            if amount < min_amount:
                errors.append(f"Amount must be at least {min_amount} {currency}")
            if amount > max_amount:
                errors.append(f"Amount cannot exceed {max_amount} {currency}")
                
        except (ValueError, TypeError, decimal.InvalidOperation):
            errors.append("Invalid amount format")
        
        # Currency validation
        currency = payment_data.get('currency', 'USD').upper()
        if currency not in self.supported_currencies:
            errors.append(f"Currency {currency} not supported. Supported: {', '.join(self.supported_currencies)}")
        
        # Required fields
        required_fields = ['merchant_id', 'customer_id', 'payment_method']
        for field in required_fields:
            if not payment_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Payment method validation
        payment_method = payment_data.get('payment_method')
        try:
            PaymentMethod(payment_method)
        except ValueError:
            valid_methods = [method.value for method in PaymentMethod]
            errors.append(f"Invalid payment method: {payment_method}. Valid methods: {', '.join(valid_methods)}")
        
        return errors
    """Validate payment request data"""
        