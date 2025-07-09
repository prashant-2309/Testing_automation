import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from src.models.payment_models import db, Payment, Refund, Transaction
from src.payment_service.payment_processor import PaymentProcessor
from config.config import config
from src.banking_service.banking_processor import BankingService

def create_app(config_name=None):
    app = Flask(__name__)
    CORS(app)
    
    # Configuration
    config_name = config_name or os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Create tables
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully")
        except Exception as e:
            print(f"Error creating database tables: {e}")
    
    # Initialize payment processor
    payment_processor = PaymentProcessor()
    banking_service = BankingService()
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        try:
            # Test database connection
            db.session.execute(db.text('SELECT 1'))
            db_status = 'connected'
        except Exception as e:
            db_status = f'error: {str(e)}'
        
        return jsonify({
            'status': 'healthy',
            'service': 'payment-api',
            'database': db_status,
            'version': '1.0.0'
        })
    
    @app.route('/api/v1/payments', methods=['POST'])
    def create_payment():
        """Create a new payment"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'errors': ['No data provided']}), 400
            
            result = payment_processor.create_payment(data)
            
            if result['success']:
                return jsonify(result), 201
            else:
                return jsonify(result), 400
        
        except Exception as e:
            return jsonify({'success': False, 'errors': [str(e)]}), 500
    
    @app.route('/api/v1/payments/<payment_id>/process', methods=['POST'])
    def process_payment(payment_id):
        """Process a pending payment"""
        try:
            result = payment_processor.process_payment(payment_id)
            
            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 400
        
        except Exception as e:
            return jsonify({'success': False, 'errors': [str(e)]}), 500
    
    @app.route('/api/v1/payments/<payment_id>', methods=['GET'])
    def get_payment(payment_id):
        """Get payment details"""
        try:
            result = payment_processor.get_payment(payment_id)
            
            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 404
        
        except Exception as e:
            return jsonify({'success': False, 'errors': [str(e)]}), 500
    
    @app.route('/api/v1/payments/<payment_id>/refund', methods=['POST'])
    def refund_payment(payment_id):
        """Refund a payment"""
        try:
            data = request.get_json() or {}
            result = payment_processor.refund_payment(payment_id, data)
            
            if result['success']:
                return jsonify(result), 201
            else:
                return jsonify(result), 400
        
        except Exception as e:
            return jsonify({'success': False, 'errors': [str(e)]}), 500
    
    @app.route('/api/v1/payments/<payment_id>/transactions', methods=['GET'])
    def get_payment_transactions(payment_id):
        """Get all transactions for a payment"""
        try:
            result = payment_processor.get_payment_transactions(payment_id)
            
            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 404
        
        except Exception as e:
            return jsonify({'success': False, 'errors': [str(e)]}), 500
    
    @app.route('/api/v1/payments', methods=['GET'])
    def list_payments():
        """List all payments with optional filtering"""
        try:
            # Get query parameters
            merchant_id = request.args.get('merchant_id')
            customer_id = request.args.get('customer_id')
            status = request.args.get('status')
            limit = min(int(request.args.get('limit', 50)), 100)
            offset = int(request.args.get('offset', 0))
            
            # Build query
            query = Payment.query
            
            if merchant_id:
                query = query.filter(Payment.merchant_id == merchant_id)
            if customer_id:
                query = query.filter(Payment.customer_id == customer_id)
            if status:
                query = query.filter(Payment.status == status)
            
            # Execute query with pagination
            payments = query.offset(offset).limit(limit).all()
            total = query.count()
            
            return jsonify({
                'success': True,
                'payments': [p.to_dict() for p in payments],
                'total': total,
                'offset': offset,
                'limit': limit
            }), 200
        
        except Exception as e:
            return jsonify({'success': False, 'errors': [str(e)]}), 500

    @app.route('/api/v1/banking/accounts', methods=['POST'])
    def create_bank_account():
        """Create a new bank account"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'errors': ['No data provided']}), 400
            
            result = banking_service.create_bank_account(data)
            
            if result['success']:
                return jsonify(result), 201
            else:
                return jsonify(result), 400
        
        except Exception as e:
            return jsonify({'success': False, 'errors': [str(e)]}), 500
    
    @app.route('/api/v1/banking/accounts/<account_id>', methods=['GET'])
    def get_bank_account(account_id):
        """Get bank account details"""
        try:
            from src.models.banking_models import BankAccount
            account = BankAccount.query.get(account_id)
            
            if not account:
                return jsonify({'success': False, 'errors': ['Account not found']}), 404
            
            return jsonify({
                'success': True,
                'account': account.to_dict()
            }), 200
        
        except Exception as e:
            return jsonify({'success': False, 'errors': [str(e)]}), 500
    
    @app.route('/api/v1/banking/accounts/<account_id>/balance', methods=['GET'])
    def get_account_balance(account_id):
        """Get account balance"""
        try:
            result = banking_service.get_account_balance(account_id)
            
            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 404
        
        except Exception as e:
            return jsonify({'success': False, 'errors': [str(e)]}), 500
    
    @app.route('/api/v1/banking/accounts/<account_id>/transactions', methods=['GET'])
    def get_account_transactions(account_id):
        """Get account transaction history"""
        try:
            limit = min(int(request.args.get('limit', 50)), 100)
            offset = int(request.args.get('offset', 0))
            
            result = banking_service.get_account_transactions(account_id, limit, offset)
            
            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 404
        
        except Exception as e:
            return jsonify({'success': False, 'errors': [str(e)]}), 500
    
    @app.route('/api/v1/banking/accounts/<account_id>/status', methods=['PUT'])
    def update_account_status(account_id):
        """Update account status (freeze/activate)"""
        try:
            data = request.get_json()
            if not data or 'status' not in data:
                return jsonify({'success': False, 'errors': ['Status is required']}), 400
            
            result = banking_service.update_account_status(
                account_id,
                data['status'],
                data.get('reason')
            )
            
            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 400
        
        except Exception as e:
            return jsonify({'success': False, 'errors': [str(e)]}), 500
    
    @app.route('/api/v1/banking/customers/<customer_id>/accounts', methods=['GET'])
    def get_customer_accounts(customer_id):
        """Get all accounts for a customer"""
        try:
            result = banking_service.find_customer_accounts(customer_id)
            
            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 404
        
        except Exception as e:
            return jsonify({'success': False, 'errors': [str(e)]}), 500
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'success': False, 'errors': ['Resource not found']}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'success': False, 'errors': ['Internal server error']}), 500
    
    return app

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    
    app = create_app()
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', 5000))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    
    print(f"Starting Payment API on {host}:{port}")
    app.run(debug=debug, host=host, port=port)