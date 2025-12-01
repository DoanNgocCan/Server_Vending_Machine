from flask import Blueprint, jsonify
from db.db import db_handler

products_bp = Blueprint('products', __name__)

@products_bp.route('/', methods=['GET'])
def get_products():
    try:
        products = db_handler.get_all_products()
        return jsonify({
            'success': True,
            'products': products,
            'total_products': len(products)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@products_bp.route('/<product_id>', methods=['GET'])
def get_product(product_id):
    try:
        product = db_handler.get_product_by_id(product_id)
        if product:
            return jsonify({
                'success': True,
                'product': product
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Product not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500