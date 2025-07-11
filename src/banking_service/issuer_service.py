"""Issuer Bank Service - Handles customer account authorization"""
import random
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional, Tuple
from sqlalchemy.exc import SQLAlchemyError
from src.models.banking_models import db, BankAccount, AccountTransaction, AccountStatus, TransactionType
from src.models.bank_network_models import BankConfiguration, NetworkTransaction, TransactionStatus

class IssuerBankService:
    def __init__(self):
        self.response_codes = {
            'approved': '00',
            'insufficient_funds': '51', 
            'invalid_account': '14',
            'expired_card': '54',
            'fraud_suspected': '59',
            'daily_limit_exceeded': '61',
            'system_error': '96',
            'timeout': '68'
        }
    
    def get_bank_configuration(self, bank_code: str) -> Optional[BankConfiguration]:
        """Get bank configuration"""
        try:
            return BankConfiguration.query.filter_by(
                bank_code=bank_code,
                is_active=True
            ).first()
        except Exception:
            return None
    
    def simulate_network_delay(self, bank_config: BankConfiguration) -> int:
        """Simulate realistic bank response time"""
        base_time = bank_config.base_response_time_ms
        
        # Add randomness based on bank tier
        if bank_config.bank_tier.value == 'tier_1':
            # Tier 1 banks: faster, more consistent
            variation = random.randint(-50, 100)
        elif bank_config.bank_tier.value == 'tier_2':
            # Tier 2 banks: moderate speed
            variation = random.randint(-100, 300)
        else:
            # Tier 3 banks: slower, more variable
            variation = random.randint(-200, 800)
        
        # Business hours consideration
        current_hour = datetime.now().hour
        if (not bank_config.supports_24_7 and 
            (current_hour < bank_config.business_hours_start or 
             current_hour > bank_config.business_hours_end)):
            # Outside business hours - slower response
            variation += random.randint(500, 2000)
        
        response_time = max(50, base_time + variation)  # Minimum 50ms
        
        # Actually delay for simulation
        time.sleep(response_time / 1000.0)
        
        return response_time
    
    def check_fraud_indicators(self, bank_account: BankAccount, amount: Decimal, bank_config: BankConfiguration) -> Tuple[bool, str]:
        """Check for fraud indicators"""
        if bank_config.fraud_detection_level == 'low':
            return False, None
        
        # High amount check
        if amount > bank_account.daily_limit * Decimal('0.8'):
            if random.random() < 0.1:  # 10% chance of fraud flag for high amounts
                return True, "High amount transaction"
        
        # Velocity check (simplified)
        if bank_config.fraud_detection_level == 'high':
            # In high-security banks, random fraud detection
            if random.random() < 0.02:  # 2% chance
                return True, "Velocity check failed"
        
        return False, None
    
    def authorize_transaction(self, bank_account_id: str, amount: Decimal, payment_id: str, merchant_id: str) -> Dict:
        """Authorize transaction against customer's bank account"""
        try:
            # Get bank account
            bank_account = BankAccount.query.get(bank_account_id)
            if not bank_account:
                return {
                    'success': False,
                    'response_code': self.response_codes['invalid_account'],
                    'decline_reason': 'Account not found',
                    'response_time_ms': 100
                }
            
            # Get bank configuration
            bank_config = self.get_bank_configuration(bank_account.bank_code)
            if not bank_config:
                return {
                    'success': False,
                    'response_code': self.response_codes['system_error'],
                    'decline_reason': 'Bank configuration not found',
                    'response_time_ms': 100
                }
            
            # Simulate network delay
            start_time = datetime.now()
            response_time = self.simulate_network_delay(bank_config)
            
            # Check account status
            if bank_account.status != AccountStatus.ACTIVE:
                return {
                    'success': False,
                    'response_code': self.response_codes['invalid_account'],
                    'decline_reason': f'Account status: {bank_account.status.value}',
                    'response_time_ms': response_time,
                    'bank_code': bank_account.bank_code
                }
            
            # Check currency support
            supported_currencies = bank_config.get_supported_currencies()
            if bank_account.currency not in supported_currencies:
                return {
                    'success': False,
                    'response_code': self.response_codes['system_error'],
                    'decline_reason': f'Currency {bank_account.currency} not supported',
                    'response_time_ms': response_time,
                    'bank_code': bank_account.bank_code
                }
            
            # Check single transaction limit
            if amount > bank_config.single_transaction_limit:
                return {
                    'success': False,
                    'response_code': self.response_codes['daily_limit_exceeded'],
                    'decline_reason': f'Amount exceeds single transaction limit',
                    'response_time_ms': response_time,
                    'bank_code': bank_account.bank_code
                }
            
            # Check sufficient funds
            if not bank_account.has_sufficient_balance(amount):
                return {
                    'success': False,
                    'response_code': self.response_codes['insufficient_funds'],
                    'decline_reason': 'Insufficient funds',
                    'response_time_ms': response_time,
                    'bank_code': bank_account.bank_code
                }
            
            # Check daily limit
            from src.banking_service.banking_processor import BankingService
            banking_service = BankingService()
            daily_total = banking_service._get_daily_debit_total(bank_account.id)
            if daily_total + amount > bank_account.daily_limit:
                return {
                    'success': False,
                    'response_code': self.response_codes['daily_limit_exceeded'],
                    'decline_reason': 'Daily limit exceeded',
                    'response_time_ms': response_time,
                    'bank_code': bank_account.bank_code
                }
            
            # Fraud detection
            is_fraud, fraud_reason = self.check_fraud_indicators(bank_account, amount, bank_config)
            if is_fraud:
                return {
                    'success': False,
                    'response_code': self.response_codes['fraud_suspected'],
                    'decline_reason': fraud_reason,
                    'response_time_ms': response_time,
                    'bank_code': bank_account.bank_code
                }
            
            # Simulate bank success rate
            if random.random() > float(bank_config.success_rate):
                decline_reasons = [
                    'System temporarily unavailable',
                    'Network timeout',
                    'Processing error',
                    'Temporary decline'
                ]
                return {
                    'success': False,
                    'response_code': self.response_codes['system_error'],
                    'decline_reason': random.choice(decline_reasons),
                    'response_time_ms': response_time,
                    'bank_code': bank_account.bank_code
                }
            
            # SUCCESS - Authorization approved
            return {
                'success': True,
                'response_code': self.response_codes['approved'],
                'decline_reason': None,
                'response_time_ms': response_time,
                'bank_code': bank_account.bank_code,
                'authorization_code': f"AUTH{random.randint(100000, 999999)}",
                'available_balance': float(bank_account.effective_balance - amount)
            }
            
        except Exception as e:
            return {
                'success': False,
                'response_code': self.response_codes['system_error'],
                'decline_reason': f'System error: {str(e)}',
                'response_time_ms': 500,
                'bank_code': bank_account.bank_code if 'bank_account' in locals() else 'UNKNOWN'
            }
    
    def capture_authorization(self, bank_account_id: str, amount: Decimal, authorization_code: str, payment_id: str) -> Dict:
        """Capture (settle) an authorized transaction"""
        try:
            from src.banking_service.banking_processor import BankingService
            banking_service = BankingService()
            
            # Debit the account
            result = banking_service.debit_account(
                bank_account_id,
                amount,
                reference_id=payment_id,
                reference_type='payment_capture',
                description=f'Payment capture - Auth: {authorization_code}'
            )
            
            if result['success']:
                return {
                    'success': True,
                    'transaction_id': result['transaction']['id'],
                    'new_balance': result['new_balance']
                }
            else:
                return {
                    'success': False,
                    'error': result['errors'][0] if result['errors'] else 'Capture failed'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Capture error: {str(e)}'
            }