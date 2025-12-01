from flask import Blueprint, request, jsonify
from db.db import db_handler
from datetime import datetime

devices_bp = Blueprint('devices', __name__)

@devices_bp.route('/', methods=['GET'])
def get_all_devices():
    try:
        devices = db_handler.getAllDevices()
        return jsonify({
            'status': 'success',
            'count': len(devices),
            'data': devices
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@devices_bp.route('/<device_id>', methods=['GET'])
def get_device_info(device_id: str):
    try:
        device = db_handler.getDeviceInfo(device_id)
        if device:
            return jsonify({
                'status': 'success',
                'data': device
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Device not found'
            }), 404
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@devices_bp.route('/', methods=['POST'])
def register_device():
    try:
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'message': 'Content-Type must be application/json'
            }), 400
        
        data = request.get_json()
        
        required_fields = ['device_id', 'device_name', 'device_type']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
        
        success = db_handler.registerDevice(
            device_id=data['device_id'],
            device_name=data['device_name'],
            device_type=data['device_type'],
            description=data.get('description', '')
        )
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Device registered successfully',
                'device_id': data['device_id']
            }), 201
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to register device'
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500