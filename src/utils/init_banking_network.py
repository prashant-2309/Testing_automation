"""Initialize banking network with multiple banks"""
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from src.payment_service.api import create_app
from src.models.payment_models import db
from src.models.banking_models import *
from src.models.bank_network_models import *
from src.banking_service.acquirer_service import AcquirerBankService

def create_bank_configurations():
    """Create diverse bank configurations with proper currency support"""
    banks_config = [
        # Tier 1 Issuer Banks (Customer banks)
        {
            'bank_code': 'WF',
            'bank_name': 'Wells Fargo Bank',
            'bank_type': BankType.DUAL,
            'bank_tier': BankTier.TIER_1,
            'base_response_time_ms': 300,
            'success_rate': 0.97,
            'daily_transaction_limit': 250000.00,
            'single_transaction_limit': 25000.00,
            'per_transaction_fee': 0.25,
            'percentage_fee': 0.020,
            'supported_currencies': ['USD', 'EUR', 'GBP'],
            'fraud_detection_level': 'high',
            'supports_24_7': True
        },
        {
            'bank_code': 'BOA',
            'bank_name': 'Bank of America',
            'bank_type': BankType.DUAL,
            'bank_tier': BankTier.TIER_1,
            'base_response_time_ms': 250,
            'success_rate': 0.98,
            'daily_transaction_limit': 300000.00,
            'single_transaction_limit': 30000.00,
            'per_transaction_fee': 0.20,
            'percentage_fee': 0.018,
            'supported_currencies': ['USD', 'EUR', 'GBP', 'CAD'],
            'fraud_detection_level': 'high',
            'supports_24_7': True
        },
        {
            'bank_code': 'CHASE',
            'bank_name': 'JPMorgan Chase',
            'bank_type': BankType.DUAL,
            'bank_tier': BankTier.TIER_1,
            'base_response_time_ms': 200,
            'success_rate': 0.98,
            'daily_transaction_limit': 350000.00,
            'single_transaction_limit': 35000.00,
            'per_transaction_fee': 0.22,
            'percentage_fee': 0.019,
            'supported_currencies': ['USD', 'EUR', 'GBP', 'JPY', 'CAD'],
            'fraud_detection_level': 'high',
            'supports_24_7': True
        },
        
        # Tier 2 Regional Banks
        {
            'bank_code': 'USB',
            'bank_name': 'US Bank',
            'bank_type': BankType.ISSUER,
            'bank_tier': BankTier.TIER_2,
            'base_response_time_ms': 450,
            'success_rate': 0.95,
            'daily_transaction_limit': 150000.00,
            'single_transaction_limit': 15000.00,
            'per_transaction_fee': 0.30,
            'percentage_fee': 0.025,
            'supported_currencies': ['USD', 'EUR'],
            'fraud_detection_level': 'medium',
            'supports_24_7': False,
            'business_hours_start': 8,
            'business_hours_end': 18
        },
        {
            'bank_code': 'CITI',
            'bank_name': 'Citibank',
            'bank_type': BankType.ISSUER,
            'bank_tier': BankTier.TIER_2,
            'base_response_time_ms': 400,
            'success_rate': 0.96,
            'daily_transaction_limit': 200000.00,
            'single_transaction_limit': 20000.00,
            'per_transaction_fee': 0.28,
            'percentage_fee': 0.023,
            'supported_currencies': ['USD', 'EUR', 'GBP'],
            'fraud_detection_level': 'medium',
            'supports_24_7': True
        },
        
        # Specialized Acquirer Banks - THESE MUST SUPPORT ALL CURRENCIES
        {
            'bank_code': 'FISERV',
            'bank_name': 'Fiserv Merchant Services',
            'bank_type': BankType.ACQUIRER,
            'bank_tier': BankTier.TIER_1,
            'base_response_time_ms': 150,
            'success_rate': 0.99,
            'daily_transaction_limit': 1000000.00,
            'single_transaction_limit': 50000.00,
            'per_transaction_fee': 0.15,
            'percentage_fee': 0.015,
            'supported_currencies': ['USD', 'EUR', 'GBP', 'CAD', 'JPY'],  # ALL currencies
            'fraud_detection_level': 'low',
            'supports_24_7': True
        },
        {
            'bank_code': 'FDMS',
            'bank_name': 'First Data Merchant Services',
            'bank_type': BankType.ACQUIRER,
            'bank_tier': BankTier.TIER_1,
            'base_response_time_ms': 180,
            'success_rate': 0.99,
            'daily_transaction_limit': 800000.00,
            'single_transaction_limit': 40000.00,
            'per_transaction_fee': 0.18,
            'percentage_fee': 0.017,
            'supported_currencies': ['USD', 'EUR', 'GBP', 'CAD', 'JPY'],  # ALL currencies
            'fraud_detection_level': 'low',
            'supports_24_7': True
        },
        {
            'bank_code': 'GLOBAL',
            'bank_name': 'Global Payments Acquirer',
            'bank_type': BankType.ACQUIRER,
            'bank_tier': BankTier.TIER_2,
            'base_response_time_ms': 220,
            'success_rate': 0.98,
            'daily_transaction_limit': 600000.00,
            'single_transaction_limit': 30000.00,
            'per_transaction_fee': 0.20,
            'percentage_fee': 0.020,
            'supported_currencies': ['USD', 'EUR', 'GBP', 'JPY', 'CAD'],  # ALL currencies
            'fraud_detection_level': 'medium',
            'supports_24_7': True
        }
    ]
    
    created_banks = []
    for bank_config in banks_config:
        try:
            # Check if bank already exists
            existing = BankConfiguration.query.filter_by(bank_code=bank_config['bank_code']).first()
            if existing:
                # Update existing bank with new currency support
                existing.set_supported_currencies(bank_config['supported_currencies'])
                db.session.commit()
                print(f"✓ Updated bank {bank_config['bank_code']} with currencies: {bank_config['supported_currencies']}")
                continue
            
            # Extract supported currencies before creating bank
            supported_currencies = bank_config.pop('supported_currencies')
            
            # Create bank without supported_currencies field
            bank = BankConfiguration(**bank_config)
            
            # Set supported currencies using the method
            bank.set_supported_currencies(supported_currencies)
            
            db.session.add(bank)
            created_banks.append(bank)
            
            print(f"✓ Created bank {bank.bank_code} with currencies: {supported_currencies}")
            
        except Exception as e:
            print(f"✗ Error creating bank {bank_config['bank_code']}: {e}")
    
    db.session.commit()
    print(f"✓ Created/Updated {len(created_banks)} bank configurations")
    
    # Verify currency support
    print(f"\n📊 Currency Support Verification:")
    all_banks = BankConfiguration.query.all()
    for bank in all_banks:
        currencies = bank.get_supported_currencies()
        print(f"  {bank.bank_code} ({bank.bank_type.value}): {currencies}")
    
    return created_banks

def create_merchant_accounts():
    """Create merchant accounts with different acquirers and currencies"""
    acquirer_service = AcquirerBankService()
    
    # First, clean up existing merchant accounts to avoid duplicates
    try:
        existing_accounts = MerchantAccount.query.all()
        for account in existing_accounts:
            db.session.delete(account)
        db.session.commit()
        print(f"✓ Cleaned up {len(existing_accounts)} existing merchant accounts")
    except Exception as e:
        print(f"⚠️ Could not clean existing accounts: {e}")
    
    # Create merchant accounts for each currency they need to support
    merchants_config = [
        # MERCHANT_001 - TechStore Electronics (supports all major currencies)
        {
            'merchant_id': 'MERCHANT_001',
            'acquirer_bank_code': 'FISERV',
            'business_name': 'TechStore Electronics USD',
            'business_type': 'retail',
            'mcc_code': '5732',
            'currency': 'USD',
            'daily_volume_limit': 75000.00,
            'risk_level': 'low'
        },
        {
            'merchant_id': 'MERCHANT_001',
            'acquirer_bank_code': 'FDMS',
            'business_name': 'TechStore Electronics EUR',
            'business_type': 'retail',
            'mcc_code': '5732',
            'currency': 'EUR',
            'daily_volume_limit': 65000.00,
            'risk_level': 'low'
        },
        {
            'merchant_id': 'MERCHANT_001',
            'acquirer_bank_code': 'GLOBAL',
            'business_name': 'TechStore Electronics GBP',
            'business_type': 'retail',
            'mcc_code': '5732',
            'currency': 'GBP',
            'daily_volume_limit': 55000.00,
            'risk_level': 'low'
        },
        {
            'merchant_id': 'MERCHANT_001',
            'acquirer_bank_code': 'FISERV',
            'business_name': 'TechStore Electronics CAD',
            'business_type': 'retail',
            'mcc_code': '5732',
            'currency': 'CAD',
            'daily_volume_limit': 70000.00,
            'risk_level': 'low'
        },
        {
            'merchant_id': 'MERCHANT_001',
            'acquirer_bank_code': 'GLOBAL',
            'business_name': 'TechStore Electronics JPY',
            'business_type': 'retail',
            'mcc_code': '5732',
            'currency': 'JPY',
            'daily_volume_limit': 8000000.00,  # JPY amount
            'risk_level': 'low'
        },
        
        # MERCHANT_002 - Fashion Forward Boutique (supports USD, EUR, GBP)
        {
            'merchant_id': 'MERCHANT_002', 
            'acquirer_bank_code': 'FDMS',
            'business_name': 'Fashion Forward Boutique USD',
            'business_type': 'ecommerce',
            'mcc_code': '5651',
            'currency': 'USD',
            'daily_volume_limit': 50000.00,
            'risk_level': 'medium'
        },
        {
            'merchant_id': 'MERCHANT_002',
            'acquirer_bank_code': 'GLOBAL',
            'business_name': 'Fashion Forward Boutique EUR',
            'business_type': 'ecommerce',
            'mcc_code': '5651',
            'currency': 'EUR',
            'daily_volume_limit': 45000.00,
            'risk_level': 'medium'
        },
        {
            'merchant_id': 'MERCHANT_002',
            'acquirer_bank_code': 'FISERV',
            'business_name': 'Fashion Forward Boutique GBP',
            'business_type': 'ecommerce',
            'mcc_code': '5651',
            'currency': 'GBP',
            'daily_volume_limit': 40000.00,
            'risk_level': 'medium'
        },
        
        # MERCHANT_003 - Global Services Inc (supports all currencies)
        {
            'merchant_id': 'MERCHANT_003',
            'acquirer_bank_code': 'GLOBAL',
            'business_name': 'Global Services Inc USD',
            'business_type': 'service',
            'mcc_code': '7299',
            'currency': 'USD',
            'daily_volume_limit': 100000.00,
            'risk_level': 'low'
        },
        {
            'merchant_id': 'MERCHANT_003',
            'acquirer_bank_code': 'GLOBAL',
            'business_name': 'Global Services Inc EUR',
            'business_type': 'service',
            'mcc_code': '7299',
            'currency': 'EUR',
            'daily_volume_limit': 85000.00,
            'risk_level': 'low'
        },
        {
            'merchant_id': 'MERCHANT_003',
            'acquirer_bank_code': 'FISERV',
            'business_name': 'Global Services Inc GBP',
            'business_type': 'service',
            'mcc_code': '7299',
            'currency': 'GBP',
            'daily_volume_limit': 75000.00,
            'risk_level': 'low'
        },
        {
            'merchant_id': 'MERCHANT_003',
            'acquirer_bank_code': 'GLOBAL',
            'business_name': 'Global Services Inc JPY',
            'business_type': 'service',
            'mcc_code': '7299',
            'currency': 'JPY',
            'daily_volume_limit': 10000000.00,
            'risk_level': 'low'
        },
        {
            'merchant_id': 'MERCHANT_003',
            'acquirer_bank_code': 'FDMS',
            'business_name': 'Global Services Inc CAD',
            'business_type': 'service',
            'mcc_code': '7299',
            'currency': 'CAD',
            'daily_volume_limit': 95000.00,
            'risk_level': 'low'
        },
        
        # MERCHANT_004 - Restaurant Chain (USD, EUR)
        {
            'merchant_id': 'MERCHANT_004',
            'acquirer_bank_code': 'FISERV',
            'business_name': 'Restaurant Chain USD',
            'business_type': 'restaurant',
            'mcc_code': '5812',
            'currency': 'USD',
            'daily_volume_limit': 25000.00,
            'risk_level': 'low'
        },
        {
            'merchant_id': 'MERCHANT_004',
            'acquirer_bank_code': 'FDMS',
            'business_name': 'Restaurant Chain EUR',
            'business_type': 'restaurant',
            'mcc_code': '5812',
            'currency': 'EUR',
            'daily_volume_limit': 22000.00,
            'risk_level': 'low'
        },
        
        # MERCHANT_005 - International Consulting (supports USD, EUR, GBP, CAD)
        {
            'merchant_id': 'MERCHANT_005',
            'acquirer_bank_code': 'GLOBAL',
            'business_name': 'International Consulting USD',
            'business_type': 'service',
            'mcc_code': '7392',
            'currency': 'USD',
            'daily_volume_limit': 150000.00,
            'risk_level': 'medium'
        },
        {
            'merchant_id': 'MERCHANT_005',
            'acquirer_bank_code': 'FDMS',
            'business_name': 'International Consulting EUR',
            'business_type': 'service',
            'mcc_code': '7392',
            'currency': 'EUR',
            'daily_volume_limit': 125000.00,
            'risk_level': 'medium'
        },
        {
            'merchant_id': 'MERCHANT_005',
            'acquirer_bank_code': 'GLOBAL',
            'business_name': 'International Consulting GBP',
            'business_type': 'service',
            'mcc_code': '7392',
            'currency': 'GBP',
            'daily_volume_limit': 110000.00,
            'risk_level': 'medium'
        },
        {
            'merchant_id': 'MERCHANT_005',
            'acquirer_bank_code': 'FISERV',
            'business_name': 'International Consulting CAD',
            'business_type': 'service',
            'mcc_code': '7392',
            'currency': 'CAD',
            'daily_volume_limit': 130000.00,
            'risk_level': 'medium'
        }
    ]
    
    created_accounts = []
    currency_counts = {}
    
    for merchant_config in merchants_config:
        result = acquirer_service.create_merchant_account(merchant_config)
        if result['success']:
            created_accounts.append(result['merchant_account'])
            currency = merchant_config['currency']
            currency_counts[currency] = currency_counts.get(currency, 0) + 1
            print(f"✓ Created {merchant_config['currency']} account for {merchant_config['merchant_id']} with {merchant_config['acquirer_bank_code']}")
        else:
            print(f"✗ Failed to create {merchant_config['currency']} account for {merchant_config['merchant_id']}: {result['error']}")
    
    print(f"\n📊 Merchant Account Summary by Currency:")
    for currency, count in currency_counts.items():
        print(f"  {currency}: {count} accounts")
    
    # Verify merchant accounts
    print(f"\n🔍 Merchant Account Verification:")
    all_merchants = MerchantAccount.query.all()
    merchant_summary = {}
    for account in all_merchants:
        key = account.merchant_id
        if key not in merchant_summary:
            merchant_summary[key] = []
        merchant_summary[key].append(f"{account.currency} ({account.acquirer_bank_code})")
    
    for merchant_id, currencies in merchant_summary.items():
        print(f"  {merchant_id}: {', '.join(currencies)}")
    
    return created_accounts

def initialize_banking_network():
    """Initialize complete banking network"""
    try:
        app = create_app('development')
        
        with app.app_context():
            # Create all tables
            db.create_all()
            print("✓ Database tables created")
            
            # Create bank configurations
            banks = create_bank_configurations()
            
            # Create merchant accounts
            merchant_accounts = create_merchant_accounts()
            
            print(f"\n🏦 Banking Network Initialization Complete!")
            print(f"✓ {len(banks)} bank configurations created")
            print(f"✓ {len(merchant_accounts)} merchant accounts created")
            
            # Print summary
            print(f"\n📊 Network Summary:")
            print(f"Issuer Banks: {len([b for b in banks if b.bank_type in [BankType.ISSUER, BankType.DUAL]])}")
            print(f"Acquirer Banks: {len([b for b in banks if b.bank_type in [BankType.ACQUIRER, BankType.DUAL]])}")
            print(f"Tier 1 Banks: {len([b for b in banks if b.bank_tier == BankTier.TIER_1])}")
            print(f"Tier 2 Banks: {len([b for b in banks if b.bank_tier == BankTier.TIER_2])}")
            
            return True
            
    except Exception as e:
        print(f"✗ Error initializing banking network: {e}")
        return False

if __name__ == "__main__":
    print("🏦 Initializing Multi-Bank Payment Network")
    print("=" * 50)
    
    if initialize_banking_network():
        print("\n🎉 Banking network ready for multi-bank transactions!")
        print("\nNext steps:")
        print("1. Start server: python run_server.py")
        print("2. Generate sample data: python src\\utils\\sample_data.py")
        print("3. Test multi-bank payments!")
    else:
        print("\n❌ Failed to initialize banking network")