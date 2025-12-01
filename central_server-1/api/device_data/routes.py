from flask import Blueprint, request, jsonify
from db.db import db_handler
from datetime import datetime

device_data_bp = Blueprint('device_data', __name__)

@device_data_bp.route('/api/device/data', methods=['POST'])
def receive_device_data():
    try:
        if not request.is_json:
            return jsonify({'status': 'error', 'message': 'Content-Type must be application/json'}), 400
        
        data = request.get_json()
        
        required_fields = ['device_id', 'type', 'payload']
        for field in required_fields:
            if field not in data:
                return jsonify({'status': 'error', 'message': f'Missing required field: {field}'}), 400
        
        success = db_handler.insertDeviceData(
            device_id=data['device_id'],
            data_type=data['type'],
            payload=data['payload'],
            timestamp=data.get('timestamp')
        )
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Data received successfully',
                'device_id': data['device_id'],
                'timestamp': data.get('timestamp', datetime.now().isoformat())
            }), 201
        else:
            return jsonify({'status': 'error', 'message': 'Failed to store data'}), 500
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@device_data_bp.route('/api/device/<device_id>/data', methods=['GET'])
def get_device_data(device_id: str):
    try:
        limit = int(request.args.get('limit', 100))
        data_type = request.args.get('type')
        
        if limit < 1 or limit > 1000:
            return jsonify({'status': 'error', 'message': 'Limit must be between 1 and 1000'}), 400
        
        data = db_handler.getDeviceData(device_id, limit=limit, data_type=data_type)
        
        return jsonify({
            'status': 'success',
            'device_id': device_id,
            'count': len(data),
            'data': data
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@device_data_bp.route('/api/device/<device_id>/latest', methods=['GET'])
def get_latest_device_data(device_id: str):
    try:
        data_type = request.args.get('type')
        
        data = db_handler.getLatestDeviceData(device_id, data_type=data_type)
        
        if data:
            return jsonify({
                'status': 'success',
                'device_id': device_id,
                'data': data
            })
        else:
            return jsonify({'status': 'error', 'message': 'No data found for device'}), 404
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500