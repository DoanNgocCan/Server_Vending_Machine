from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import sqlite3
from db import db_handler

cart_bp = Blueprint('cart', __name__)

@cart_bp.route('/api/cart/add', methods=['POST'])
def addToCart():
    try:
        data = request.get_json()
        
        requiredFields = ['user_id', 'product_id', 'quantity']
        for field in requiredFields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        userId = data['user_id']
        productId = data['product_id']
        quantity = int(data['quantity'])
        
        if quantity <= 0:
            return jsonify({
                'success': False,
                'error': 'Quantity must be greater than 0'
            }), 400
        
        conn = db_handler.getDatabaseConnection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name, price, stock
            FROM products 
            WHERE product_id = ? AND is_active = 1
        """, (productId,))
        
        product = cursor.fetchone()
        conn.close()
        
        if not product:
            return jsonify({
                'success': False,
                'error': 'Product not found or not available'
            }), 404
        
        if product['stock'] < quantity:
            return jsonify({
                'success': False,
                'error': f'Insufficient stock. Available: {product["stock"]}'
            }), 400
        
        # Logic to add to cart would go here (e.g., updating a session or database)
        
        return jsonify({
            'success': True,
            'message': f'Added {quantity}x {product["name"]} to cart',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cart_bp.route('/api/cart/<user_id>', methods=['GET'])
def getCart(user_id):
    try:
        # Logic to retrieve cart contents would go here
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'cart_items': [],  # Replace with actual cart items
            'total_items': 0,  # Replace with actual total items
            'total_amount': 0.0,  # Replace with actual total amount
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Register the blueprint in the main app file (app.py) as follows:
# from central_server.api.cart.routes import cart_bp
# app.register_blueprint(cart_bp)