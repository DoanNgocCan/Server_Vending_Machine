from flask import jsonify
from db.db import db_handler
from datetime import datetime, timezone

def getSystemStats():
    """
    Get system statistics
    
    Returns:
        System statistics
    """
    try:
        devices = db_handler.getAllDevices()
        
        # Get total data count for each device
        device_stats = []
        for device in devices:
            data_count = len(db_handler.getDeviceData(device['device_id'], limit=10000))
            latest_data = db_handler.getLatestDeviceData(device['device_id'])
            
            device_stats.append({
                'device_id': device['device_id'],
                'device_name': device['device_name'],
                'device_type': device['device_type'],
                'data_count': data_count,
                'last_seen': latest_data['timestamp'] if latest_data else None
            })
        
        return jsonify({
            'status': 'success',
            'total_devices': len(devices),
            'device_stats': device_stats
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Define the route for system statistics
@app.route('/api/stats', methods=['GET'])
def stats():
    return getSystemStats()