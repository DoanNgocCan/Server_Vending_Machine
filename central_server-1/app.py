from flask import Flask
from flask_cors import CORS
import os
import sys

# Add the db directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'central_server.db'))

try:
    from db.db import db_handler
except ImportError:
    print("Error importing database handler")
    sys.exit(1)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
export FLASK_APP=app.py
export FLASK_ENV=development

# Import API routes
from api.devices.routes import devices_bp
from api.device_data.routes import device_data_bp
from api.users.routes import users_bp
from api.products.routes import products_bp
from api.cart.routes import cart_bp 
from api.checkout.routes import checkout_bp
from api.payment.routes import payment_bp
from api.stats.routes import stats_bp

# Register blueprints
app.register_blueprint(devices_bp, url_prefix='/api/devices')
app.register_blueprint(device_data_bp, url_prefix='/api/device/data')
app.register_blueprint(users_bp, url_prefix='/api/user')
app.register_blueprint(products_bp, url_prefix='/api/products')
app.register_blueprint(cart_bp, url_prefix='/api/cart')
app.register_blueprint(checkout_bp, url_prefix='/api/checkout')
app.register_blueprint(payment_bp, url_prefix='/api/payment')
app.register_blueprint(stats_bp, url_prefix='/api/stats')

@app.route('/', methods=['GET'])
def healthCheck():
    return {
        'status': 'OK',
        'message': 'Central Server is running',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    }

if __name__ == '__main__':
    print("Starting Central Server...")
    app.run(host='0.0.0.0', port=5000, debug=True)