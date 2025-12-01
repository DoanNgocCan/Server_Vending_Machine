# 🌐 VENDING MACHINE API - CURL COMMANDS

**Base URL**: `http://localhost:5000` (local) hoặc `https://your-public-url.ngrok.io` (public)

## 📋 **AUTHENTICATION**
Một số endpoint cần API key. Thêm header sau:
```bash
-H "X-API-Key: your-api-key-here"
```

---

## 🏠 **1. BASIC ENDPOINTS**

### Home Page
```bash
curl -X GET http://localhost:5000/
```

### Health Check
```bash
curl -X GET http://localhost:5000/api/health
```

### System Status
```bash
curl -X GET http://localhost:5000/api/status
```

---

## 👥 **2. USER MANAGEMENT**

### Register New User
```bash
curl -X POST http://localhost:5000/api/user/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "full_name": "Nguyen Van A",
    "phone_number": "0901234567",
    "email": "nguyenvana@example.com",
    "date_of_birth": "1990-01-01",
    "face_embedding": [0.1, 0.2, 0.3, 0.4, 0.5]
  }'
```

### Get User Info
```bash
curl -X GET http://localhost:5000/api/user/USER_ID_HERE
```

### Get All Customers (Demo)
```bash
curl -X GET http://localhost:5000/api/demo/customers
```

### Get Customer Profile (Demo)
```bash
curl -X GET http://localhost:5000/api/demo/customer/USER_ID_HERE/profile
```

---

## 📦 **3. PRODUCT MANAGEMENT**

### Get All Products
```bash
curl -X GET http://localhost:5000/api/products \
  -H "X-API-Key: your-api-key"
```

### Get Inventory Status (Demo)
```bash
curl -X GET http://localhost:5000/api/demo/inventory
```

### Get Inventory Alerts (Demo)
```bash
curl -X GET http://localhost:5000/api/demo/inventory/alerts
```

---

## 🛒 **4. SHOPPING CART**

### Add Product to Cart
```bash
curl -X POST http://localhost:5000/api/cart/add \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "product_id": 1,
    "quantity": 2
  }'
```

### Get User Cart
```bash
curl -X GET http://localhost:5000/api/cart/USER_ID_HERE
```

---

## 💳 **5. CHECKOUT & PAYMENT**

### Checkout Cart
```bash
curl -X POST http://localhost:5000/api/checkout \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "user_id": "user123",
    "payment_method": "qr_code"
  }'
```

### Confirm Payment
```bash
curl -X POST http://localhost:5000/api/payment/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "txn_123",
    "payment_status": "completed"
  }'
```

---

## 📊 **6. TRANSACTION HISTORY**

### Get All Transactions (Demo)
```bash
curl -X GET "http://localhost:5000/api/demo/transactions?limit=10&status=completed"
```

### Get Transaction Details (Demo)
```bash
curl -X GET http://localhost:5000/api/demo/transaction/TRANSACTION_ID_HERE/details
```

---

## ☁️ **7. SUPABASE INTEGRATION**

### Manual Sync to Supabase
```bash
curl -X POST http://localhost:5000/api/supabase/sync \
  -H "Content-Type: application/json" \
  -d '{
    "sync_type": "full"
  }'
```

### Get Supabase Status
```bash
curl -X GET http://localhost:5000/api/supabase/status
```

---

## 📡 **8. MQTT & FACIAL RECOGNITION**

### Get MQTT Status
```bash
curl -X GET http://localhost:5000/api/mqtt/status
```

### Test Facial Recognition
```bash
curl -X POST http://localhost:5000/api/mqtt/test-recognition \
  -H "Content-Type: application/json" \
  -d '{
    "face_embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
    "test_mode": true
  }'
```

### Get Recognition Threshold
```bash
curl -X GET http://localhost:5000/api/mqtt/threshold
```

### Set Recognition Threshold
```bash
curl -X POST http://localhost:5000/api/mqtt/threshold \
  -H "Content-Type: application/json" \
  -d '{
    "threshold": 0.85
  }'
```

### Reconnect MQTT
```bash
curl -X POST http://localhost:5000/api/mqtt/reconnect
```

---

## 🔐 **9. AUTHENTICATION & SECURITY**

### Test API Authentication
```bash
curl -X GET http://localhost:5000/api/auth/test \
  -H "X-API-Key: your-api-key"
```

### Device Heartbeat
```bash
curl -X POST http://localhost:5000/api/device/heartbeat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "device_id": "vending_machine_01",
    "status": "online",
    "uptime": 3600,
    "memory_usage": 45.2
  }'
```

---

## 📋 **10. SYSTEM MONITORING**

### Get System Logs
```bash
curl -X GET "http://localhost:5000/api/system/logs?limit=20&level=INFO"
```

### Get Dashboard Data (Demo)
```bash
curl -X GET http://localhost:5000/api/demo/dashboard
```

---

## 🚀 **TESTING SCENARIOS**

### Complete User Journey
```bash
# 1. Register user
curl -X POST http://localhost:5000/api/user/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "full_name": "Test User",
    "phone_number": "0901234567",
    "email": "test@example.com",
    "date_of_birth": "1990-01-01",
    "face_embedding": [0.1, 0.2, 0.3, 0.4, 0.5]
  }' > user_response.json

# 2. Get user ID from response
USER_ID=$(cat user_response.json | grep -o '"user_id":"[^"]*' | cut -d'"' -f4)

# 3. Add products to cart
curl -X POST http://localhost:5000/api/cart/add \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "'$USER_ID'",
    "product_id": 1,
    "quantity": 2
  }'

# 4. Check cart
curl -X GET http://localhost:5000/api/cart/$USER_ID

# 5. Checkout
curl -X POST http://localhost:5000/api/checkout \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "user_id": "'$USER_ID'",
    "payment_method": "qr_code"
  }'
```

---

## 🔧 **BATCH TESTING SCRIPT**

```bash
#!/bin/bash
# test_all_endpoints.sh

BASE_URL="http://localhost:5000"
API_KEY="your-api-key-here"

echo "Testing Vending Machine API..."

# Basic endpoints
echo "1. Testing basic endpoints..."
curl -s $BASE_URL/ | jq .
curl -s $BASE_URL/api/health | jq .
curl -s $BASE_URL/api/status | jq .

# Product endpoints
echo "2. Testing product endpoints..."
curl -s -H "X-API-Key: $API_KEY" $BASE_URL/api/products | jq .

# Demo endpoints
echo "3. Testing demo endpoints..."
curl -s $BASE_URL/api/demo/customers | jq .
curl -s $BASE_URL/api/demo/transactions | jq .
curl -s $BASE_URL/api/demo/inventory | jq .

# System endpoints
echo "4. Testing system endpoints..."
curl -s $BASE_URL/api/mqtt/status | jq .
curl -s $BASE_URL/api/supabase/status | jq .

echo "Testing completed!"
```

---

## 📝 **RESPONSE EXAMPLES**

### Success Response
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": { ... },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error message here",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

---

## 🔍 **DEBUGGING TIPS**

### Check if server is running
```bash
curl -f http://localhost:5000/api/health || echo "Server is down"
```

### Test with verbose output
```bash
curl -v -X GET http://localhost:5000/api/status
```

### Save response to file
```bash
curl -X GET http://localhost:5000/api/products -o products.json
```

### Test with different content types
```bash
curl -X POST http://localhost:5000/api/user/register \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d @user_data.json
```

---

## 🌐 **PUBLIC URL USAGE**

Khi dùng public URL (ngrok, cloudflare, etc.), thay `localhost:5000` bằng public URL:

```bash
# Ví dụ với Ngrok
curl -X GET https://abc123.ngrok.io/api/health

# Ví dụ với Cloudflare
curl -X GET https://yourdomain.cloudflare.net/api/health

# Ví dụ với VPS
curl -X GET http://your-vps-ip:5000/api/health
```

---

**🔥 TIP**: Sử dụng `jq` để format JSON response đẹp hơn:
```bash
curl -X GET http://localhost:5000/api/status | jq .
``` 