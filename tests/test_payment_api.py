import pytest
import json
from src.payment_service.api import create_app
from src.models.payment_models import db

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database/test_payments.db'
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'

def test_create_payment_success(client):
    """Test successful payment creation"""
    payment_data = {
        'merchant_id': 'MERCHANT_001',
        'customer_id': 'CUSTOMER_001',
        'amount': 100.50,
        'currency': 'USD',
        'payment_method': 'credit_card',
        'description': 'Test payment',
        'card_last_four': '1234',
        'card_type': 'VISA'
    }
    
    response = client.post('/api/v1/payments', 
                          data=json.dumps(payment_data),
                          content_type='application/json')
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'payment' in data
    assert data['payment']['amount'] == 100.50

def test_create_payment_invalid_amount(client):
    """Test payment creation with invalid amount"""
    payment_data = {
        'merchant_id': 'MERCHANT_001',
        'customer_id': 'CUSTOMER_001',
        'amount': -10.00,  # Invalid negative amount
        'currency': 'USD',
        'payment_method': 'credit_card'
    }
    
    response = client.post('/api/v1/payments', 
                          data=json.dumps(payment_data),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'errors' in data

def test_get_payment_not_found(client):
    """Test getting non-existent payment"""
    response = client.get('/api/v1/payments/non-existent-id')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['success'] is False