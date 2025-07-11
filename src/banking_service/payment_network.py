"""Payment Network Service - Routes transactions between issuer and acquirer"""
import random
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional, Tuple
from src.models.bank_network_models import db, BankConfiguration, NetworkTransaction, TransactionStatus, BankType
from src.banking_service.issuer_service import IssuerBankService
from src.banking_service.acquirer_service import AcquirerBankService

class PaymentNetworkService:
    def __init__(self):
        self.issuer_service = IssuerBankService()
        self.acquirer_service = AcquirerBankService()
        
        # Routing preferences based on various factors
        self.routing_preferences = {
            'cost_optimization': 0.3,
            'success_rate_optimization': 0.4,
            'response_time_optimization': 0.3
        }
    
    def get_available_acquirers(self, currency: str = 'USD') -> list:
        """Get available acquirer banks for currency"""
        try:
            acquirers = BankConfiguration.query.filter(
                BankConfiguration.bank_type.in_([BankType.ACQUIRER, BankType.DUAL]),
                BankConfiguration.is_active == True
            ).all()
            
            # Filter by currency support
            available_acquirers = []
            for acquirer in acquirers:
                if currency in acquirer.get_supported_currencies():
                    available_acquirers.append(acquirer)
            
            return available_acquirers
            
        except Exception:
            return []
    
    def select_optimal_acquirer(self, merchant_id: str, amount: Decimal, currency: str) -> Optional[BankConfiguration]:
        """Select optimal acquirer based on cost, success rate, and speed"""
        available_acquirers = self.get_available_acquirers(currency)
        
        if not available_acquirers:
            return None
        
        # Score each acquirer
        scored_acquirers = []
        for acquirer in available_acquirers:
            score = self._calculate_acquirer_score(acquirer, amount)
            scored_acquirers.append((acquirer, score))
        
        # Sort by score (higher is better)
        scored_acquirers.sort(key=lambda x: x[1], reverse=True)
        
        # Return best acquirer
        return scored_acquirers[0][0] if scored_acquirers else None
    
    def _calculate_acquirer_score(self, acquirer: BankConfiguration, amount: Decimal) -> float:
        """Calculate acquirer score based on multiple factors"""
        # Cost score (lower cost = higher score)
        total_fee = acquirer.per_transaction_fee + (amount * acquirer.percentage_fee / 100)
        cost_score = max(0, 10 - float(total_fee))
        
        # Success rate score
        success_score = float(acquirer.success_rate) * 10
        
        # Speed score (lower response time = higher score)
        speed_score = max(0, 10 - (acquirer.base_response_time_ms / 100))
        
        # Weighted final score
        final_score = (
            cost_score * self.routing_preferences['cost_optimization'] +
            success_score * self.routing_preferences['success_rate_optimization'] +
            speed_score * self.routing_preferences['response_time_optimization']
        )
        
        return final_score
    
    def process_two_party_transaction(self, payment_data: Dict) -> Dict:
        """Process transaction through issuer-acquirer network"""
        try:
            payment_id = payment_data['payment_id']
            amount = Decimal(str(payment_data['amount']))
            currency = payment_data['currency']
            bank_account_id = payment_data['bank_account_id']
            merchant_id = payment_data['merchant_id']
            
            print(f"🔄 Processing {amount} {currency} payment from {merchant_id}")
            
            # Get issuer bank from customer's account
            from src.models.banking_models import BankAccount
            bank_account = BankAccount.query.get(bank_account_id)
            if not bank_account:
                print(f"❌ Bank account {bank_account_id} not found")
                return {
                    'success': False,
                    'error': 'Bank account not found',
                    'transaction_details': None
                }
            
            issuer_bank_code = bank_account.bank_code
            print(f"🏦 Issuer bank: {issuer_bank_code}")
            
            # Select optimal acquirer
            optimal_acquirer = self.select_optimal_acquirer(merchant_id, amount, currency)
            if not optimal_acquirer:
                print(f"❌ No available acquirer found for {currency}")
                return {
                    'success': False,
                    'error': f'No available acquirer found for {currency}',
                    'transaction_details': None
                }
            
            acquirer_bank_code = optimal_acquirer.bank_code
            print(f"🏪 Selected acquirer: {acquirer_bank_code}")
            
            # Create network transaction record
            network_transaction = NetworkTransaction(
                payment_id=payment_id,
                issuer_bank_code=issuer_bank_code,
                acquirer_bank_code=acquirer_bank_code,
                amount=amount,
                currency=currency,
                transaction_type='purchase'
            )
            
            db.session.add(network_transaction)
            db.session.flush()  # Get ID
            
            total_start_time = datetime.now()
            
            # Step 1: Issuer Authorization
            print(f"🏦 Step 1: Requesting authorization from issuer {issuer_bank_code}")
            issuer_start = datetime.now()
            
            issuer_result = self.issuer_service.authorize_transaction(
                bank_account_id, amount, payment_id, merchant_id
            )
            
            issuer_end = datetime.now()
            issuer_time = int((issuer_end - issuer_start).total_seconds() * 1000)
            
            print(f"🏦 Issuer response: {issuer_result['success']} ({issuer_time}ms)")
            
            # Update network transaction with issuer response
            network_transaction.issuer_response_time_ms = issuer_time
            network_transaction.issuer_response_code = issuer_result['response_code']
            network_transaction.issuer_processed_at = issuer_end
            
            if not issuer_result['success']:
                network_transaction.issuer_status = TransactionStatus.DECLINED
                network_transaction.final_status = TransactionStatus.DECLINED
                network_transaction.decline_reason = issuer_result['decline_reason']
                network_transaction.completed_at = datetime.now()
                
                db.session.commit()
                
                print(f"❌ Issuer declined: {issuer_result['decline_reason']}")
                
                return {
                    'success': False,
                    'error': f"Issuer declined: {issuer_result['decline_reason']}",
                    'response_code': issuer_result['response_code'],
                    'transaction_details': {
                        'issuer_bank': issuer_bank_code,
                        'acquirer_bank': acquirer_bank_code,
                        'issuer_response_time_ms': issuer_time,
                        'decline_reason': issuer_result['decline_reason']
                    }
                }
            
            network_transaction.issuer_status = TransactionStatus.AUTHORIZED
            
            # Step 2: Acquirer Settlement
            print(f"🏪 Step 2: Processing settlement with acquirer {acquirer_bank_code}")
            acquirer_start = datetime.now()
            
            # Find merchant account that matches currency
            merchant_account = self.acquirer_service.get_merchant_account(
                merchant_id, currency, acquirer_bank_code
            )
            
            if not merchant_account:
                print(f"❌ No merchant account found for {merchant_id} in {currency} with {acquirer_bank_code}")
                # Try to find any merchant account for this merchant in this currency
                merchant_account = self.acquirer_service.get_merchant_account(
                    merchant_id, currency
                )
                
                if merchant_account:
                    # Update acquirer_bank_code to match the found account
                    old_acquirer = acquirer_bank_code
                    acquirer_bank_code = merchant_account.acquirer_bank_code
                    print(f"🔄 Switched from {old_acquirer} to {acquirer_bank_code} for currency {currency}")
                else:
                    # No merchant account found for this currency
                    network_transaction.final_status = TransactionStatus.FAILED
                    network_transaction.decline_reason = f"No merchant account found for {merchant_id} in {currency}"
                    network_transaction.completed_at = datetime.now()
                    
                    db.session.commit()
                    
                    print(f"❌ No merchant account found for {merchant_id} in {currency}")
                    
                    return {
                        'success': False,
                        'error': f'No merchant account found for {merchant_id} in {currency}',
                        'transaction_details': {
                            'issuer_bank': issuer_bank_code,
                            'acquirer_bank': 'NOT_FOUND',
                            'issuer_response_time_ms': issuer_time,
                            'decline_reason': f"No merchant account for currency {currency}"
                        }
                    }
            
            acquirer_result = self.acquirer_service.process_settlement(
                merchant_id, amount, currency, payment_id, acquirer_bank_code
            )
            
            acquirer_end = datetime.now()
            acquirer_time = int((acquirer_end - acquirer_start).total_seconds() * 1000)
            
            print(f"🏪 Acquirer response: {acquirer_result['success']} ({acquirer_time}ms)")
            
            # Update network transaction with acquirer response
            network_transaction.acquirer_response_time_ms = acquirer_time
            network_transaction.acquirer_response_code = acquirer_result['response_code']
            network_transaction.acquirer_processed_at = acquirer_end
            
            total_end_time = datetime.now()
            total_time = int((total_end_time - total_start_time).total_seconds() * 1000)
            network_transaction.total_processing_time_ms = total_time
            
            if not acquirer_result['success']:
                network_transaction.acquirer_status = TransactionStatus.DECLINED
                network_transaction.final_status = TransactionStatus.FAILED
                network_transaction.decline_reason = acquirer_result['decline_reason']
                network_transaction.completed_at = datetime.now()
                
                db.session.commit()
                
                print(f"❌ Acquirer failed: {acquirer_result['decline_reason']}")
                
                return {
                    'success': False,
                    'error': f"Acquirer failed: {acquirer_result['decline_reason']}",
                    'response_code': acquirer_result['response_code'],
                    'transaction_details': {
                        'issuer_bank': issuer_bank_code,
                        'acquirer_bank': acquirer_bank_code,
                        'issuer_response_time_ms': issuer_time,
                        'acquirer_response_time_ms': acquirer_time,
                        'total_processing_time_ms': total_time,
                        'decline_reason': acquirer_result['decline_reason']
                    }
                }
            
            # Step 3: Capture funds from issuer
            print(f"💰 Step 3: Capturing funds from issuer")
            capture_result = self.issuer_service.capture_authorization(
                bank_account_id, 
                amount, 
                issuer_result.get('authorization_code', 'N/A'),
                payment_id
            )
            
            if not capture_result['success']:
                network_transaction.final_status = TransactionStatus.FAILED
                network_transaction.decline_reason = "Capture failed"
                db.session.commit()
                
                print(f"❌ Capture failed: {capture_result['error']}")
                
                return {
                    'success': False,
                    'error': f"Capture failed: {capture_result['error']}",
                    'transaction_details': {
                        'issuer_bank': issuer_bank_code,
                        'acquirer_bank': acquirer_bank_code,
                        'issuer_response_time_ms': issuer_time,
                        'acquirer_response_time_ms': acquirer_time,
                        'total_processing_time_ms': total_time
                    }
                }
            
            # SUCCESS - Transaction completed
            network_transaction.acquirer_status = TransactionStatus.SETTLED
            network_transaction.final_status = TransactionStatus.SETTLED
            network_transaction.completed_at = datetime.now()
            
            db.session.commit()
            
            print(f"✅ Transaction completed successfully through {issuer_bank_code} → {acquirer_bank_code}")
            
            return {
                'success': True,
                'authorization_code': issuer_result.get('authorization_code'),
                'settlement_id': acquirer_result.get('settlement_id'),
                'fee_info': acquirer_result.get('fee_info'),
                'transaction_details': {
                    'network_transaction_id': network_transaction.id,
                    'issuer_bank': issuer_bank_code,
                    'acquirer_bank': acquirer_bank_code,
                    'issuer_response_time_ms': issuer_time,
                    'acquirer_response_time_ms': acquirer_time,
                    'total_processing_time_ms': total_time,
                    'routing_reason': f'Selected {acquirer_bank_code} for optimal cost/performance'
                }
            }
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Network processing error: {str(e)}")
            return {
                'success': False,
                'error': f'Network processing error: {str(e)}',
                'transaction_details': None
            }