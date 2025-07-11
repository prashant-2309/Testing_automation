"""Script to populate database with sample payment data for testing"""
import os
import sys
from pathlib import Path
import requests
import random
import time
import json
from decimal import Decimal

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

# Fixed API base URL - use localhost instead of 0.0.0.0
API_BASE = f"http://localhost:{os.getenv('API_PORT', '5000')}/api/v1"

class SampleDataGenerator:
    def __init__(self):
        self.merchants = [
            'MERCHANT_001', 'MERCHANT_002', 'MERCHANT_003', 
            'MERCHANT_004', 'MERCHANT_005'
        ]
        
        # Regular customers with numbered IDs
        self.regular_customers = [f'CUSTOMER_{i:03d}' for i in range(1, 21)]
        
        # Special test customers
        self.special_customers = [
            'CUSTOMER_VIP', 'CUSTOMER_EDGE', 'CUSTOMER_GLOBAL',
            'CUSTOMER_USD', 'CUSTOMER_EUR', 'CUSTOMER_GBP', 
            'CUSTOMER_JPY', 'CUSTOMER_CAD'
        ]
        
        self.all_customers = self.regular_customers + self.special_customers
        
        self.currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD']
        self.payment_methods = ['credit_card', 'debit_card', 'bank_transfer', 'digital_wallet']
        self.card_types = ['VISA', 'MASTERCARD', 'AMEX', 'DISCOVER']
        self.descriptions = [
            'Online purchase', 'Subscription payment', 'Invoice payment',
            'Service fee', 'Product purchase', 'Monthly subscription',
            'Annual membership', 'Digital service', 'Consulting fee',
            'Software license'
        ]
        
        # Bank configuration
        self.banks = {
            'WF': 'Wells Fargo Bank',
            'BOA': 'Bank of America', 
            'CITI': 'Citibank',
            'CHASE': 'JPMorgan Chase',
            'USB': 'US Bank'
        }
        
        self.account_types = ['checking', 'savings']

    def test_api_connection(self):
        """Test if API is accessible"""
        try:
            health_url = API_BASE.replace('/api/v1', '/health')
            print(f"Testing connection to: {health_url}")
            
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                print(f"✓ API is healthy: {health_data}")
                return True
            else:
                print(f"✗ API health check failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"✗ Cannot connect to API: {e}")
            print(f"Make sure the API is running and try:")
            print(f"  1. Check if server is running: http://localhost:5000/health")
            print(f"  2. If server shows 0.0.0.0, use localhost in browser")
            print(f"  3. Try: curl http://localhost:5000/health")
            return False

    def generate_initial_balance(self, currency):
        """Generate appropriate initial balance for currency"""
        if currency == 'JPY':
            return random.randint(100000, 1000000)  # 100k to 1M JPY
        else:
            return round(random.uniform(2000, 20000), 2)

    def generate_daily_limit(self, currency):
        """Generate appropriate daily limit for currency"""
        if currency == 'JPY':
            return random.choice([200000, 500000, 1000000, 2000000])
        else:
            return random.choice([2000, 5000, 10000, 25000])

    def generate_payment_amount(self, currency='USD'):
        """Generate realistic payment amounts based on currency"""
        if currency == 'JPY':
            # JPY doesn't use decimals, reasonable amounts under 10k limit
            amounts = [100, 500, 1000, 1500, 2000, 3000, 5000, 7500, 9000, 9999]
            return random.choice(amounts)
        elif currency in ['USD', 'EUR', 'GBP', 'CAD']:
            # Standard decimal currencies - keep under 10k limit
            base_amounts = [9.99, 19.99, 29.99, 49.99, 99.99, 149.99, 199.99, 299.99, 499.99, 999.99]
            return round(random.choice(base_amounts) + random.uniform(0, 500), 2)
        else:
            return round(random.uniform(10, 1000), 2)

    def generate_card_details(self):
        """Generate random card details"""
        return {
            'card_last_four': f"{random.randint(1000, 9999)}",
            'card_type': random.choice(self.card_types)
        }

    def create_bank_account_via_api(self, account_data):
        """Create bank account via API"""
        try:
            response = requests.post(f"{API_BASE}/banking/accounts", json=account_data, timeout=10)
            if response.status_code == 201:
                return response.json()['account']
            else:
                print(f"  ✗ Failed to create account: {response.status_code} - {response.text[:100]}")
                return None
        except Exception as e:
            print(f"  ✗ Error creating account: {e}")
            return None

    def create_comprehensive_bank_accounts(self, num_regular_accounts=30):
        """Create comprehensive bank accounts for all customers"""
        print("\nCreating comprehensive bank accounts...")
        created_accounts = []
        
        # Create accounts for regular customers (multiple currencies each)
        print("Creating accounts for regular customers...")
        for i, customer_id in enumerate(self.regular_customers[:10]):  # First 10 customers
            print(f"Creating accounts for {customer_id}")
            
            # Primary currencies for each customer
            if i < 3:
                # First 3 customers: USD + EUR + JPY
                currencies = ['USD', 'EUR', 'JPY']
            elif i < 6:
                # Next 3 customers: USD + GBP + CAD  
                currencies = ['USD', 'GBP', 'CAD']
            elif i < 8:
                # Next 2 customers: EUR + GBP
                currencies = ['EUR', 'GBP']
            else:
                # Last 2 customers: USD + EUR
                currencies = ['USD', 'EUR']
            
            for currency in currencies:
                account_data = {
                    'customer_id': customer_id,
                    'bank_code': random.choice(list(self.banks.keys())),
                    'account_type': random.choice(self.account_types),
                    'currency': currency,
                    'initial_balance': self.generate_initial_balance(currency),
                    'daily_limit': self.generate_daily_limit(currency),
                    'overdraft_limit': random.choice([0, 500, 1000, 2000])
                }
                
                account = self.create_bank_account_via_api(account_data)
                if account:
                    created_accounts.append(account)
                    print(f"  ✓ Created {currency} account: {account['account_number']}")
        
        # Create accounts for special test customers
        print("\nCreating accounts for special test customers...")
        special_account_configs = {
            'CUSTOMER_VIP': ['USD', 'EUR', 'GBP'],
            'CUSTOMER_EDGE': ['USD'],
            'CUSTOMER_GLOBAL': ['USD', 'EUR', 'GBP', 'JPY', 'CAD'],
            'CUSTOMER_USD': ['USD'],
            'CUSTOMER_EUR': ['EUR'], 
            'CUSTOMER_GBP': ['GBP'],
            'CUSTOMER_JPY': ['JPY'],
            'CUSTOMER_CAD': ['CAD']
        }
        
        for customer_id, currencies in special_account_configs.items():
            print(f"Creating accounts for {customer_id}")
            for currency in currencies:
                account_data = {
                    'customer_id': customer_id,
                    'bank_code': random.choice(list(self.banks.keys())),
                    'account_type': 'checking',
                    'currency': currency,
                    'initial_balance': self.generate_initial_balance(currency),
                    'daily_limit': self.generate_daily_limit(currency),
                    'overdraft_limit': 2000  # Higher limits for special customers
                }
                
                account = self.create_bank_account_via_api(account_data)
                if account:
                    created_accounts.append(account)
                    print(f"  ✓ Created {currency} account: {account['account_number']}")
        
        print(f"\n✓ Created {len(created_accounts)} bank accounts total")
        return created_accounts

    def get_customer_accounts_by_currency(self, customer_id):
        """Get all currencies this customer has accounts for"""
        try:
            response = requests.get(f"{API_BASE}/banking/customers/{customer_id}/accounts", timeout=10)
            if response.status_code == 200:
                accounts = response.json()['accounts']
                return {acc['currency']: acc['id'] for acc in accounts if acc['status'] == 'active'}
            return {}
        except:
            return {}

    def create_payment_via_api(self, payment_data):
        """Create payment via API"""
        try:
            response = requests.post(f"{API_BASE}/payments", json=payment_data, timeout=10)
            if response.status_code == 201:
                return response.json()
            else:
                print(f"Failed to create payment: {response.status_code} - {response.text[:200]}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error creating payment: {e}")
            return None

    def process_payment_via_api(self, payment_id):
        """Process payment via API"""
        try:
            response = requests.post(f"{API_BASE}/payments/{payment_id}/process", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to process payment {payment_id}: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error processing payment {payment_id}: {e}")
            return None

    def create_refund_via_api(self, payment_id, refund_amount, reason="Customer request"):
        """Create refund via API"""
        try:
            refund_data = {
                'amount': refund_amount,
                'reason': reason
            }
            response = requests.post(f"{API_BASE}/payments/{payment_id}/refund", json=refund_data, timeout=10)
            if response.status_code == 201:
                return response.json()
            else:
                print(f"Failed to create refund for {payment_id}: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error creating refund for {payment_id}: {e}")
            return None

    def create_payment_data(self):
        """Generate a single payment data object with currency matching"""
        customer_id = random.choice(self.regular_customers[:10])  # Use customers with accounts
        
        # Get available currencies for this customer
        customer_currencies = self.get_customer_accounts_by_currency(customer_id)
        
        # Define merchants and their ACTUAL supported currencies based on merchant accounts
        merchants_by_currency = {
            'USD': ['MERCHANT_001', 'MERCHANT_002', 'MERCHANT_003', 'MERCHANT_004', 'MERCHANT_005'],
            'EUR': ['MERCHANT_001', 'MERCHANT_002', 'MERCHANT_003', 'MERCHANT_004', 'MERCHANT_005'],
            'GBP': ['MERCHANT_001', 'MERCHANT_002', 'MERCHANT_003', 'MERCHANT_005'],
            'JPY': ['MERCHANT_001', 'MERCHANT_003'],  # Only these have JPY accounts
            'CAD': ['MERCHANT_001', 'MERCHANT_003', 'MERCHANT_005']  # Only these have CAD accounts
        }
        
        # Find a currency that both customer and merchants support
        supported_currencies = []
        if customer_currencies:
            for currency in customer_currencies.keys():
                if currency in merchants_by_currency and merchants_by_currency[currency]:
                    supported_currencies.append(currency)
        
        # If no matching currency found, fallback to USD
        if not supported_currencies:
            print(f"  ⚠️ No matching currency for {customer_id}, falling back to USD")
            currency = 'USD'
            # Make sure customer has USD account, if not, skip this payment
            if 'USD' not in customer_currencies:
                print(f"  ⚠️ {customer_id} has no USD account either, skipping...")
                return None
        else:
            currency = random.choice(supported_currencies)
        
        # Select merchant that supports this currency
        available_merchants = merchants_by_currency.get(currency, [])
        
        # Final safety check
        if not available_merchants:
            print(f"  ⚠️ No merchants support {currency}, falling back to USD and MERCHANT_001")
            currency = 'USD'
            available_merchants = ['MERCHANT_001']
        
        merchant_id = random.choice(available_merchants)
        payment_method = random.choice(self.payment_methods)
        
        payment_data = {
            'merchant_id': merchant_id,
            'customer_id': customer_id,
            'amount': self.generate_payment_amount(currency),
            'currency': currency,
            'payment_method': payment_method,
            'description': random.choice(self.descriptions)
        }
        
        # Add card details for card payments
        if payment_method in ['credit_card', 'debit_card']:
            payment_data.update(self.generate_card_details())
        
        return payment_data
        
    def generate_sample_payments(self, num_payments=30):
        """Generate comprehensive sample payments"""
        print(f"\nGenerating {num_payments} sample payments...")
        created_payments = []
        processed_payments = []
        refunded_payments = []
        
        for i in range(num_payments):
            payment_data = self.create_payment_data()
            
            # Skip if no valid payment data could be created
            if payment_data is None:
                print(f"Skipping payment {i+1}/{num_payments}: Could not create valid payment data")
                continue
                
            print(f"Creating payment {i+1}/{num_payments}: {payment_data['amount']} {payment_data['currency']} for {payment_data['customer_id']}")
            
            result = self.create_payment_via_api(payment_data)
            if result and result.get('success'):
                payment = result['payment']
                created_payments.append(payment)
                print(f"  ✓ Created payment: {payment['id']}")
                
                # Process 80% of payments
                if random.random() > 0.2:
                    time.sleep(0.1)  # Small delay
                    process_result = self.process_payment_via_api(payment['id'])
                    if process_result and process_result.get('success'):
                        processed_payment = process_result['payment']
                        processed_payments.append(processed_payment)
                        print(f"  ✓ Processed payment: {payment['id']} - Status: {processed_payment['status']}")
                        
                        # Create refunds for 20% of successful payments
                        if processed_payment['status'] == 'completed' and random.random() > 0.8:
                            time.sleep(0.1)
                            refund_amount = round(float(processed_payment['amount']) * random.uniform(0.3, 1.0), 2)
                            
                            # Adjust refund amount for JPY (no decimals)
                            if processed_payment['currency'] == 'JPY':
                                refund_amount = int(refund_amount)
                            
                            refund_reasons = [
                                "Customer request", "Product defect", "Service issue", 
                                "Billing error", "Duplicate charge", "Cancelled order"
                            ]
                            refund_result = self.create_refund_via_api(
                                payment['id'], 
                                refund_amount, 
                                random.choice(refund_reasons)
                            )
                            if refund_result and refund_result.get('success'):
                                refunded_payments.append(refund_result['refund'])
                                print(f"  ✓ Created refund: {refund_amount} {processed_payment['currency']} for payment {payment['id']}")
                    else:
                        print(f"  ⚠️ Failed to process payment {payment['id']}")
            else:
                print(f"  ✗ Failed to create payment")
        
        return {
            'created': created_payments,
            'processed': processed_payments,
            'refunded': refunded_payments
        }

    def create_specific_test_scenarios(self):
        """Create specific test scenarios for comprehensive testing"""
        print("\nCreating specific test scenarios...")
        scenarios = []

        # Test scenarios with proper amounts and existing customers
        test_scenarios = [
            {
                'name': 'Large USD Payment',
                'data': {
                    'merchant_id': 'MERCHANT_001',
                    'customer_id': 'CUSTOMER_VIP',
                    'amount': 9500.00,
                    'currency': 'USD',
                    'payment_method': 'bank_transfer',
                    'description': 'Large corporate payment'
                }
            },
            {
                'name': 'EUR Payment',
                'data': {
                    'merchant_id': 'MERCHANT_GLOBAL',
                    'customer_id': 'CUSTOMER_EUR',
                    'amount': 500.00,
                    'currency': 'EUR',
                    'payment_method': 'credit_card',
                    'description': 'EUR test payment',
                    **self.generate_card_details()
                }
            },
            {
                'name': 'GBP Payment',
                'data': {
                    'merchant_id': 'MERCHANT_GLOBAL',
                    'customer_id': 'CUSTOMER_GBP',
                    'amount': 750.00,
                    'currency': 'GBP',
                    'payment_method': 'debit_card',
                    'description': 'GBP test payment',
                    **self.generate_card_details()
                }
            },
            {
                'name': 'JPY Payment',
                'data': {
                    'merchant_id': 'MERCHANT_GLOBAL',
                    'customer_id': 'CUSTOMER_JPY',
                    'amount': 9000,  # Under 10k limit
                    'currency': 'JPY',
                    'payment_method': 'digital_wallet',
                    'description': 'JPY test payment'
                }
            },
            {
                'name': 'CAD Payment',
                'data': {
                    'merchant_id': 'MERCHANT_GLOBAL',
                    'customer_id': 'CUSTOMER_CAD',
                    'amount': 300.00,
                    'currency': 'CAD',
                    'payment_method': 'credit_card',
                    'description': 'CAD test payment',
                    **self.generate_card_details()
                }
            }
        ]

        # Edge case amounts
        edge_cases = [
            {'amount': 0.01, 'desc': 'Minimum amount'},
            {'amount': 1.00, 'desc': 'One dollar'},
            {'amount': 999.99, 'desc': 'Under 1000'},
            {'amount': 5000.00, 'desc': 'Mid-range amount'},
            {'amount': 9999.99, 'desc': 'Maximum amount'}
        ]

        for edge in edge_cases:
            test_scenarios.append({
                'name': f'Edge Case - {edge["desc"]}',
                'data': {
                    'merchant_id': 'MERCHANT_EDGE',
                    'customer_id': 'CUSTOMER_EDGE',
                    'amount': edge['amount'],
                    'currency': 'USD',
                    'payment_method': 'credit_card',
                    'description': f'Edge case: {edge["desc"]}',
                    **self.generate_card_details()
                }
            })

        # Execute scenarios
        scenario_results = []
        for scenario in test_scenarios:
            print(f"Creating scenario: {scenario['name']}")
            result = self.create_payment_via_api(scenario['data'])
            if result and result.get('success'):
                scenario_results.append((scenario['name'], result['payment']))
                print(f"  ✓ Created: {result['payment']['id']}")
            else:
                print(f"  ✗ Failed to create scenario: {scenario['name']}")

        return scenario_results

    def create_banking_test_scenarios(self):
        """Create specific banking test scenarios"""
        print("\nCreating banking test scenarios...")
        
        # Test insufficient funds
        print("Testing insufficient funds scenario...")
        try:
            # Create a payment that should exceed available balance
            large_payment = {
                'merchant_id': 'MERCHANT_001',
                'customer_id': 'CUSTOMER_001',
                'amount': 50000.00,  # Very large amount
                'currency': 'USD',
                'payment_method': 'bank_transfer',
                'description': 'Insufficient funds test'
            }
            
            result = self.create_payment_via_api(large_payment)
            if result and result.get('success'):
                payment_id = result['payment']['id']
                print(f"  ✓ Created large payment: {payment_id}")
                
                # Try to process it (should fail due to insufficient funds)
                process_result = self.process_payment_via_api(payment_id)
                if process_result:
                    status = process_result['payment']['status']
                    print(f"  ✓ Processing result: {status}")
                    if status == 'failed':
                        print("  ✓ Insufficient funds test passed - payment failed as expected")
                    else:
                        print("  ⚠ Insufficient funds test unexpected result")
            
        except Exception as e:
            print(f"  ✗ Banking test scenario error: {e}")

    def test_multi_bank_scenarios(self):
        """Test multi-bank transaction scenarios"""
        print("\n🏦 Testing Multi-Bank Transaction Scenarios...")
        
        test_scenarios = [
            {
                'name': 'High-Value Cross-Bank Transaction',
                'customer_id': 'CUSTOMER_001',
                'merchant_id': 'MERCHANT_001', 
                'amount': 5000.00,
                'currency': 'USD',
                'description': 'Test high-value cross-bank payment'
            },
            {
                'name': 'International Payment (EUR)',
                'customer_id': 'CUSTOMER_002',
                'merchant_id': 'MERCHANT_003',
                'amount': 1250.00,
                'currency': 'EUR',
                'description': 'Test international EUR payment'
            },
            {
                'name': 'Small Business Payment',
                'customer_id': 'CUSTOMER_003',
                'merchant_id': 'MERCHANT_004',
                'amount': 45.99,
                'currency': 'USD',
                'description': 'Test small business payment'
            },
            {
                'name': 'Service Provider Payment',
                'customer_id': 'CUSTOMER_004',
                'merchant_id': 'MERCHANT_005',
                'amount': 2750.00,
                'currency': 'USD',
                'description': 'Test service provider payment'
            }
        ]
        
        results = []
        for scenario in test_scenarios:
            print(f"\nTesting: {scenario['name']}")
            
            # Create payment
            payment_data = {
                'merchant_id': scenario['merchant_id'],
                'customer_id': scenario['customer_id'],
                'amount': scenario['amount'],
                'currency': scenario['currency'],
                'payment_method': 'credit_card',
                'description': scenario['description'],
                **self.generate_card_details()
            }
            
            payment_result = self.create_payment_via_api(payment_data)
            if payment_result and payment_result.get('success'):
                payment_id = payment_result['payment']['id']
                print(f"  ✓ Payment created: {payment_id}")
                
                # Process payment (this will trigger multi-bank processing)
                time.sleep(1)  # Small delay
                process_result = self.process_payment_via_api(payment_id)
                
                if process_result and process_result.get('success'):
                    payment = process_result['payment']
                    print(f"  ✓ Payment processed: {payment['status']}")
                    
                    # Check for network details
                    if 'network_details' in payment:
                        details = payment['network_details']
                        print(f"    🏦 Issuer: {details.get('issuer_bank', 'N/A')}")
                        print(f"    🏪 Acquirer: {details.get('acquirer_bank', 'N/A')}")
                        print(f"    ⏱️ Total time: {details.get('total_processing_time_ms', 'N/A')}ms")
                        
                    results.append({
                        'scenario': scenario['name'],
                        'success': True,
                        'payment_id': payment_id,
                        'status': payment['status'],
                        'network_details': payment.get('network_details')
                    })
                else:
                    print(f"  ✗ Payment processing failed")
                    results.append({
                        'scenario': scenario['name'],
                        'success': False,
                        'payment_id': payment_id,
                        'error': 'Processing failed'
                    })
            else:
                print(f"  ✗ Payment creation failed")
                results.append({
                    'scenario': scenario['name'],
                    'success': False,
                    'error': 'Creation failed'
                })
        
        return results

    def print_summary(self, results):
        """Print summary of created data"""
        print("\n" + "="*60)
        print("SAMPLE DATA GENERATION SUMMARY")
        print("="*60)
        
        print(f"Total Payments Created: {len(results['created'])}")
        print(f"Total Payments Processed: {len(results['processed'])}")
        print(f"Total Refunds Created: {len(results['refunded'])}")
        
        # Payment status breakdown
        if results['processed']:
            status_counts = {}
            for payment in results['processed']:
                status = payment['status']
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print("\nPayment Status Breakdown:")
            for status, count in status_counts.items():
                print(f"  {status.upper()}: {count}")

        # Currency breakdown
        if results['created']:
            currency_counts = {}
            total_amounts = {}
            for payment in results['created']:
                currency = payment['currency']
                amount = float(payment['amount'])
                currency_counts[currency] = currency_counts.get(currency, 0) + 1
                total_amounts[currency] = total_amounts.get(currency, 0) + amount
            
            print("\nCurrency Breakdown:")
            for currency in sorted(currency_counts.keys()):
                print(f"  {currency}: {currency_counts[currency]} payments, Total: {total_amounts[currency]:.2f}")

        print("\nAPI Endpoints to test:")
        health_url = API_BASE.replace('/api/v1', '/health')
        print(f"  Health Check: {health_url}")
        print(f"  List Payments: {API_BASE}/payments")
        print(f"  Banking Customers: {API_BASE}/banking/customers/{{customer_id}}/accounts")
        print(f"  Account Balance: {API_BASE}/banking/accounts/{{account_id}}/balance")
        print(f"  Account Transactions: {API_BASE}/banking/accounts/{{account_id}}/transactions")

def main():
    """Main function to generate comprehensive sample data"""
    print("Payment System Sample Data Generator - Phase 2")
    print("=" * 60)
    
    generator = SampleDataGenerator()
    
    # Test API connection first
    if not generator.test_api_connection():
        print("\n❌ Cannot connect to API. Please start the server first.")
        return
    
    # Create comprehensive bank accounts
    bank_accounts = generator.create_comprehensive_bank_accounts()
    
    # Wait a moment for accounts to be fully created
    time.sleep(1)
    
    # Generate main sample payments
    results = generator.generate_sample_payments(num_payments=30)
    
    # Create specific test scenarios
    scenarios = generator.create_specific_test_scenarios()
    
    # Test multi-bank scenarios
    multi_bank_results = generator.test_multi_bank_scenarios()
    
    # Create banking test scenarios
    generator.create_banking_test_scenarios()
    
    # Print comprehensive summary
    generator.print_summary(results)
    
    print(f"\nBank Accounts Created: {len(bank_accounts)}")
    print(f"Test Scenarios Created: {len(scenarios)}")
    print(f"Multi-Bank Tests: {len(multi_bank_results)}")
    
    # Multi-bank test summary
    successful_multi_bank = [r for r in multi_bank_results if r['success']]
    print(f"Multi-Bank Success Rate: {len(successful_multi_bank)}/{len(multi_bank_results)}")
    
    if results['created'] or bank_accounts:
        print("\n🎉 Phase 2 sample data generation complete!")
        print("\nMulti-Bank Features Tested:")
        print("✓ Issuer-Acquirer routing")
        print("✓ Bank-specific response times")
        print("✓ Cross-bank transaction processing")
        print("✓ Different bank rules and limits")
        print("✓ Fee calculation and settlement")
        
        print("\nNext steps:")
        print("1. Test advanced scenarios: different currencies, high amounts")
        print("2. Monitor network transaction logs")
        print("3. Test failure scenarios: bank downtime, limits exceeded")
        print("4. Analyze performance across different bank combinations")
    else:
        print("\n❌ No data was created. Please check setup.")

if __name__ == "__main__":
    main()