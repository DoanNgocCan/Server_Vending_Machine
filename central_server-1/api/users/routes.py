from flask import Blueprint, request, jsonify
import json
import uuid
from datetime import datetime, timezone
from db.db import db_handler
import logging

logger = logging.getLogger(__name__)

users_bp = Blueprint('users', __name__)

@users_bp.route('/api/user/register', methods=['POST'])
def registerUser():
    try:
        data = request.get_json()
        
        requiredFields = ['full_name', 'phone_number', 'birthday', 'password']
        for field in requiredFields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        userId = f"user_{uuid.uuid4().hex[:8]}"
        
        conn = db_handler.getDatabaseConnection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO users (user_id, full_name, phone_number, birthday, password, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            userId,
            data['full_name'],
            data['phone_number'],
            data['birthday'],
            data['password'],
            'active',
            datetime.now(timezone.utc).isoformat(),
            datetime.now(timezone.utc).isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f'New user registered: {userId}')
        
        return jsonify({
            'success': True,
            'user_id': userId,
            'message': 'User registered successfully',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@users_bp.route('/api/user/<user_id>', methods=['GET'])
def getUser(user_id):
    try:
        conn = db_handler.getDatabaseConnection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, full_name, phone_number, email, status, created_at, updated_at
            FROM users 
            WHERE user_id = ?
        """, (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        return jsonify({
            'success': True,
            'user': dict(user),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500