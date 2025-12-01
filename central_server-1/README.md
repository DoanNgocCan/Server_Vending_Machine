# Central Server Flask Application

This project is a Central Server application built using Flask, designed to manage IoT devices, user registrations, product management, and payment processing. 

## Project Structure

```
central_server
├── app.py                     # Main entry point of the Flask application
├── api                        # API package containing all endpoints
│   ├── __init__.py           # Initializes the API package
│   ├── devices                # Device management endpoints
│   │   ├── __init__.py       # Initializes the devices module
│   │   ├── routes.py         # Routes for device management
│   ├── device_data           # Device data endpoints
│   │   ├── __init__.py       # Initializes the device_data module
│   │   ├── routes.py         # Routes for receiving and retrieving device data
│   ├── users                  # User management endpoints
│   │   ├── __init__.py       # Initializes the users module
│   │   ├── routes.py         # Routes for user registration and info
│   ├── products               # Product management endpoints
│   │   ├── __init__.py       # Initializes the products module
│   │   ├── routes.py         # Routes for retrieving products
│   ├── cart                   # Cart management endpoints
│   │   ├── __init__.py       # Initializes the cart module
│   │   ├── routes.py         # Routes for cart operations
│   ├── checkout               # Checkout processing endpoints
│   │   ├── __init__.py       # Initializes the checkout module
│   │   ├── routes.py         # Routes for checkout and payment QR codes
│   ├── payment                # Payment processing endpoints
│   │   ├── __init__.py       # Initializes the payment module
│   │   ├── routes.py         # Routes for confirming payments
│   ├── stats                  # System statistics endpoints
│   │   ├── __init__.py       # Initializes the stats module
│   │   ├── routes.py         # Route for system statistics
├── db                         # Database module
│   ├── __init__.py           # Initializes the database module
│   ├── db.py                 # Database handler functions
├── central_server.db          # SQLite database file
├── requirements.txt           # Project dependencies
└── README.md                  # Project documentation
```

## Setup Instructions

1. **Clone the repository**:
   ```
   git clone <repository-url>
   cd central_server
   ```

2. **Install dependencies**:
   It is recommended to use a virtual environment. You can create one using:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
   Then install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. **Run the application**:
   Start the Flask application by running:
   ```
   python app.py
   ```

4. **Access the API**:
   The API will be available at `http://localhost:5000`. You can use tools like Postman or curl to interact with the endpoints.

## Usage

- **Health Check**: `GET /`
- **Device Management**: Endpoints under `/api/devices`
- **Device Data**: Endpoints under `/api/device_data`
- **User Management**: Endpoints under `/api/users`
- **Product Management**: Endpoints under `/api/products`
- **Cart Management**: Endpoints under `/api/cart`
- **Checkout**: Endpoints under `/api/checkout`
- **Payment**: Endpoints under `/api/payment`
- **System Statistics**: Endpoints under `/api/stats`

## License

This project is licensed under the MIT License. See the LICENSE file for details.