"""Acquirer Bank Service - Handles merchant settlement"""
import random
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional
from sqlalchemy.exc import SQLAlchemyError
from src.models.bank_network_models import db, BankConfiguration, MerchantAccount, NetworkTransaction, TransactionStatus

class AcquirerBankService:
    def __init__(self):
        self.response_codes = {
            'approved': '00',
            'invalid_merchant': '03',
            'merchant_limit_exceeded': '61',
            'system_error': '96',
            'processing_error': '91'
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
    
    def get_merchant_account(self, merchant_id: str, currency: str, preferred_acquirer: str = None) -> Optional[MerchantAccount]:
        """Get merchant account for specific currency, optionally with preferred acquirer"""
        try:
            query = MerchantAccount.query.filter_by(
                merchant_id=merchant_id,
                currency=currency,
                status='active'
            )
            
            # If preferred acquirer specified, try that first
            if preferred_acquirer:
                preferred_account = query.filter_by(acquirer_bank_code=preferred_acquirer).first()
                if preferred_account:
                    return preferred_account
            
            # Otherwise, return any matching account
            return query.first()
            
        except Exception:
            return None
    
    def simulate_processing_delay(self, bank_config: BankConfiguration) -> int:
        """Simulate acquirer processing time"""
        base_time = bank_config.base_response_time_ms
        
        # Acquirers are typically faster than issuers
        acquirer_time = int(base_time * 0.6)
        
        # Add some randomness
        variation = random.randint(-50, 150)
        response_time = max(30, acquirer_time + variation)
        
        # Simulate delay
        time.sleep(response_time / 1000.0)
        
        return response_time
    
    def calculate_fees(self, amount: Decimal, bank_config: BankConfiguration) -> Dict:
        """Calculate processing fees"""
        per_transaction_fee = bank_config.per_transaction_fee
        percentage_fee = amount * (bank_config.percentage_fee / 100)
        total_fee = per_transaction_fee + percentage_fee
        
        return {
            'per_transaction_fee': float(per_transaction_fee),
            'percentage_fee': float(percentage_fee),
            'total_fee': float(total_fee),
            'net_amount': float(amount - total_fee)
        }
    
    def process_settlement(self, merchant_id: str, amount: Decimal, currency: str, payment_id: str, acquirer_bank_code: str) -> Dict:
        """Process settlement for merchant"""
        try:
            # Get bank configuration
            bank_config = self.get_bank_configuration(acquirer_bank_code)
            if not bank_config:
                return {
                    'success': False,
                    'response_code': self.response_codes['system_error'],
                    'decline_reason': 'Acquirer bank configuration not found',
                    'response_time_ms': 100
                }
            
            # Simulate processing delay
            start_time = datetime.now()
            response_time = self.simulate_processing_delay(bank_config)
            
            # Get merchant account with currency matching
            merchant_account = self.get_merchant_account(merchant_id, currency, acquirer_bank_code)
            if not merchant_account:
                return {
                    'success': False,
                    'response_code': self.response_codes['invalid_merchant'],
                    'decline_reason': f'Merchant account not found for {merchant_id} in {currency}',
                    'response_time_ms': response_time,
                    'acquirer_bank_code': acquirer_bank_code
                }
            
            # Check daily volume limit
            today = datetime.now().date()
            daily_volume = self._get_daily_volume(merchant_account.id, today)
            if daily_volume + amount > merchant_account.daily_volume_limit:
                return {
                    'success': False,
                    'response_code': self.response_codes['merchant_limit_exceeded'],
                    'decline_reason': 'Daily volume limit exceeded',
                    'response_time_ms': response_time,
                    'acquirer_bank_code': acquirer_bank_code
                }
            
            # Calculate fees
            fee_info = self.calculate_fees(amount, bank_config)
            
            # Simulate acquirer success rate (typically higher than issuer)
            acquirer_success_rate = min(0.99, float(bank_config.success_rate) + 0.02)
            if random.random() > acquirer_success_rate:
                return {
                    'success': False,
                    'response_code': self.response_codes['processing_error'],
                    'decline_reason': 'Acquirer processing error',
                    'response_time_ms': response_time,
                    'acquirer_bank_code': acquirer_bank_code
                }
            
            # Update merchant account balance (add net amount)
            net_amount = Decimal(str(fee_info['net_amount']))
            merchant_account.current_balance += net_amount
            merchant_account.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            # SUCCESS
            return {
                'success': True,
                'response_code': self.response_codes['approved'],
                'decline_reason': None,
                'response_time_ms': response_time,
                'acquirer_bank_code': acquirer_bank_code,
                'settlement_id': f"SETTLE{random.randint(100000, 999999)}",
                'fee_info': fee_info,
                'merchant_balance': float(merchant_account.current_balance)
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'response_code': self.response_codes['system_error'],
                'decline_reason': f'Settlement error: {str(e)}',
                'response_time_ms': 500,
                'acquirer_bank_code': acquirer_bank_code
            }
    
    def _get_daily_volume(self, merchant_account_id: str, date) -> Decimal:
        """Get daily transaction volume for merchant"""
        # This would typically query transaction history
        # For now, return a random amount for simulation
        return Decimal(str(random.uniform(0, 10000)))
    
    def create_merchant_account(self, merchant_data: Dict) -> Dict:
        """Create new merchant account"""
        try:
            merchant_account = MerchantAccount(
                merchant_id=merchant_data['merchant_id'],
                acquirer_bank_code=merchant_data['acquirer_bank_code'],
                business_name=merchant_data['business_name'],
                business_type=merchant_data.get('business_type', 'retail'),
                mcc_code=merchant_data.get('mcc_code', '5999'),
                currency=merchant_data.get('currency', 'USD'),
                monthly_volume_limit=Decimal(str(merchant_data.get('monthly_volume_limit', '500000.00'))),
                daily_volume_limit=Decimal(str(merchant_data.get('daily_volume_limit', '50000.00'))),
                risk_level=merchant_data.get('risk_level', 'low')
            )
            
            db.session.add(merchant_account)
            db.session.commit()
            
            return {
                'success': True,
                'merchant_account': merchant_account.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': f'Failed to create merchant account: {str(e)}'
            }