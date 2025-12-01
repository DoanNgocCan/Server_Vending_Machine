from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import logging

# Initialize logger
logger = logging.getLogger(__name__)

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/api/payment/confirm', methods=['POST'])
def confirm_payment():
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        
        if not transaction_id:
            return jsonify({
                'success': False,
                'error': 'transaction_id is required'
            }), 400
        
        # Get transaction details
        with dbLock:
            conn = getDatabaseConnection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT transaction_id, user_id, items, total_amount, payment_status
                FROM transactions 
                WHERE transaction_id = ?
            """, (transaction_id,))
            
            transaction = cursor.fetchone()
            
            if not transaction:
                conn.close()
                return jsonify({
                    'success': False,
                    'error': 'Transaction not found'
                }), 404
            
            if transaction['payment_status'] != 'pending':
                conn.close()
                return jsonify({
                    'success': False,
                    'error': f'Transaction already {transaction["payment_status"]}'
                }), 400
            
            # Update transaction status
            cursor.execute("""
                UPDATE transactions 
                SET payment_status = 'completed', paid_at = ?
                WHERE transaction_id = ?
            """, (datetime.now(timezone.utc).isoformat(), transaction_id))
            
            # Update stock for each item
            items = json.loads(transaction['items'])
            for item in items:
                cursor.execute("""
                    UPDATE products 
                    SET stock = stock - ?,
                        updated_at = ?
                    WHERE product_id = ?
                """, (item['quantity'], datetime.now(timezone.utc).isoformat(), item['product_id']))
            
            conn.commit()
            conn.close()
        
        # Clear user's cart
        with cartLock:
            if transaction['user_id'] in userCarts:
                del userCarts[transaction['user_id']]
        
        # Send dispense command via MQTT
        if mqttHandler:
            mqttHandler.publishDispenseCommand(transaction_id, items)
        
        # Update statistics
        appStats['successful_transactions'] += 1
        
        # Log event
        logSystemEvent('payment_confirmed', f'Payment confirmed for transaction: {transaction_id}', 'INFO', {
            'transaction_id': transaction_id,
            'user_id': transaction['user_id'],
            'total_amount': float(transaction['total_amount'])
        })
        
        return jsonify({
            'success': True,
            'transaction_id': transaction_id,
            'message': 'Payment confirmed successfully',
            'dispensing': True,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error confirming payment: {str(e)}")
        appStats['failed_transactions'] += 1
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500