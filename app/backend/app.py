import os
import secrets
import hashlib
import datetime
from functools import wraps
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
import jwt
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Configuration & Secrets
JWT_SECRET = os.environ.get('JWT_SECRET', 'cloudmart-secure-jwt-dev-secret-key-32chars!')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_NAME = os.environ.get('DB_NAME', 'cloudmart')
DB_USER = os.environ.get('DB_USER', 'cloudmart_user')
DB_PASS = os.environ.get('DB_PASS', 'cloudmart_password')
DB_PORT = os.environ.get('DB_PORT', '5432')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT,
        cursor_factory=RealDictCursor
    )

def send_sms_notification(phone_number, message_text):
    print(f"\n[SMS NOTIFICATION DISPATCH]")
    print(f"Recipient: {phone_number}")
    print(f"Message:   {message_text}\n")
    if not phone_number:
        return {"status": "skipped", "reason": "No phone number provided"}

    try:
        if os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY'):
            sns_client = boto3.client('sns', region_name=AWS_REGION)
            response = sns_client.publish(
                PhoneNumber=phone_number,
                Message=message_text
            )
            return {"status": "sent", "message_id": response.get('MessageId')}
        else:
            return {"status": "logged_locally", "detail": "AWS keys not set; logged to console"}
    except (BotoCoreError, ClientError) as e:
        print(f"[AWS SNS Warning] Could not dispatch SMS: {str(e)}")
        return {"status": "failed", "error": str(e)}

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

        if not token:
            return jsonify({"error": "Authorization token is missing"}), 401

        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            current_user_id = payload['user_id']
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email, phone_number, role FROM users WHERE id = %s", (current_user_id,))
            current_user = cursor.fetchone()
            cursor.close()
            conn.close()

            if not current_user:
                return jsonify({"error": "User no longer exists"}), 401

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired, please log in again"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/health', methods=['GET'])
def health():
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    phone = data.get('phone_number', '').strip()

    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Email is already registered"}), 409

        cursor.execute("""
            INSERT INTO users (name, email, password_hash, phone_number)
            VALUES (%s, %s, %s, %s)
            RETURNING id, name, email, phone_number, role, created_at
        """, (name, email, hashed_pw, phone))
        user = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()

        token = jwt.encode({
            'user_id': user['id'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, JWT_SECRET, algorithm='HS256')

        return jsonify({
            "message": "User registered successfully",
            "token": token,
            "user": {
                "id": user['id'],
                "name": user['name'],
                "email": user['email'],
                "phone_number": user['phone_number'],
                "role": user['role']
            }
        }), 201
    except Exception as e:
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, password_hash, phone_number, role FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return jsonify({"error": "Invalid email or password"}), 401

        token = jwt.encode({
            'user_id': user['id'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, JWT_SECRET, algorithm='HS256')

        return jsonify({
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user['id'],
                "name": user['name'],
                "email": user['email'],
                "phone_number": user['phone_number'],
                "role": user['role']
            }
        }), 200
    except Exception as e:
        return jsonify({"error": f"Login failed: {str(e)}"}), 500

@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    return jsonify({"user": current_user}), 200

@app.route('/api/categories', methods=['GET'])
def get_categories():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT category, COUNT(*) as count FROM products GROUP BY category ORDER BY category ASC")
        categories = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"categories": categories}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve categories: {str(e)}"}), 500

@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        search_term = request.args.get('search', '').strip()
        category = request.args.get('category', '').strip()
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        sort_by = request.args.get('sort', 'newest')
        page = max(1, request.args.get('page', default=1, type=int))
        limit = max(1, min(50, request.args.get('limit', default=12, type=int)))
        offset = (page - 1) * limit

        query_conditions = ["1=1"]
        params = []

        if search_term:
            query_conditions.append("(name ILIKE %s OR description ILIKE %s)")
            wildcard = f"%{search_term}%"
            params.extend([wildcard, wildcard])

        if category and category.lower() != 'all':
            query_conditions.append("category = %s")
            params.append(category)

        if min_price is not None:
            query_conditions.append("price >= %s")
            params.append(min_price)

        if max_price is not None:
            query_conditions.append("price <= %s")
            params.append(max_price)

        where_clause = " AND ".join(query_conditions)
        sort_clauses = {
            'price_asc': 'price ASC',
            'price_desc': 'price DESC',
            'rating': 'rating DESC',
            'newest': 'created_at DESC'
        }
        order_clause = sort_clauses.get(sort_by, 'created_at DESC')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) as total FROM products WHERE {where_clause}", tuple(params))
        total_items = cursor.fetchone()['total']

        query = f"""
            SELECT id, name, description, price, stock, category, image_url, rating, rating_count, created_at
            FROM products
            WHERE {where_clause}
            ORDER BY {order_clause}
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        cursor.execute(query, tuple(params))
        products = cursor.fetchall()

        for p in products:
            p['price'] = float(p['price'])
            p['rating'] = float(p['rating'])

        cursor.close()
        conn.close()

        return jsonify({
            "products": products,
            "pagination": {
                "total": total_items,
                "page": page,
                "limit": limit,
                "pages": (total_items + limit - 1) // limit
            }
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve products: {str(e)}"}), 500

@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, description, price, stock, category, image_url, rating, rating_count, created_at FROM products WHERE id = %s", (product_id,))
        product = cursor.fetchone()
        cursor.close()
        conn.close()

        if not product:
            return jsonify({"error": "Product not found"}), 404

        product['price'] = float(product['price'])
        product['rating'] = float(product['rating'])
        return jsonify({"product": product}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve product: {str(e)}"}), 500

@app.route('/api/cart/validate', methods=['POST'])
def validate_cart():
    data = request.get_json() or {}
    items = data.get('items', [])
    if not items or not isinstance(items, list):
        return jsonify({"valid": True, "items": [], "total": 0.0, "item_count": 0}), 200

    product_ids = [item.get('product_id') for item in items if item.get('product_id')]
    if not product_ids:
        return jsonify({"error": "Invalid cart items"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price, stock, image_url FROM products WHERE id = ANY(%s)", (product_ids,))
        catalog_products = {p['id']: p for p in cursor.fetchall()}
        cursor.close()
        conn.close()

        validated_items = []
        total_amount = 0.0
        total_count = 0
        has_stock_error = False

        for item in items:
            p_id = item.get('product_id')
            qty = max(1, item.get('quantity', 1))
            product = catalog_products.get(p_id)

            if not product:
                validated_items.append({"product_id": p_id, "error": "Product no longer available", "valid": False})
                has_stock_error = True
                continue

            available_stock = product['stock']
            unit_price = float(product['price'])
            item_valid = (qty <= available_stock)
            if not item_valid:
                has_stock_error = True

            subtotal = round(unit_price * qty, 2)
            total_amount += subtotal
            total_count += qty

            validated_items.append({
                "product_id": p_id,
                "name": product['name'],
                "image_url": product['image_url'],
                "unit_price": unit_price,
                "quantity": qty,
                "stock": available_stock,
                "subtotal": subtotal,
                "valid": item_valid,
                "message": "In Stock" if item_valid else f"Only {available_stock} available"
            })

        return jsonify({
            "valid": not has_stock_error,
            "items": validated_items,
            "total": round(total_amount, 2),
            "item_count": total_count
        }), 200

    except Exception as e:
        return jsonify({"error": f"Cart validation failed: {str(e)}"}), 500

@app.route('/api/orders', methods=['POST'])
@token_required
def create_order(current_user):
    data = request.get_json() or {}
    items = data.get('items', [])
    shipping_address = data.get('shipping_address', '').strip()
    shipping_city = data.get('shipping_city', 'Chennai').strip()
    shipping_postal_code = data.get('shipping_postal_code', '600001').strip()
    payment_method = data.get('payment_method', 'SIMULATED_CARD')
    idempotency_key = data.get('idempotency_key', '').strip() or secrets.token_hex(16)

    if not items or not isinstance(items, list):
        return jsonify({"error": "Cart items cannot be empty"}), 400
    if not shipping_address:
        return jsonify({"error": "Shipping address is required"}), 400

    conn = get_db_connection()
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, total_amount, status, created_at FROM orders WHERE idempotency_key = %s", (idempotency_key,))
        existing_order = cursor.fetchone()
        if existing_order:
            conn.rollback()
            cursor.close()
            conn.close()
            return jsonify({
                "message": "Order already processed (idempotent replay)",
                "order_id": existing_order['id'],
                "total_amount": float(existing_order['total_amount']),
                "status": existing_order['status']
            }), 200

        product_ids = [item['product_id'] for item in items if 'product_id' in item]
        if not product_ids:
            conn.rollback()
            return jsonify({"error": "Invalid item payload"}), 400

        cursor.execute("SELECT id, name, price, stock FROM products WHERE id = ANY(%s) FOR UPDATE", (product_ids,))
        db_products = {p['id']: p for p in cursor.fetchall()}

        calculated_total = 0.0
        verified_order_items = []

        for item in items:
            p_id = item.get('product_id')
            qty = item.get('quantity', 0)
            if qty <= 0:
                conn.rollback()
                return jsonify({"error": f"Invalid quantity {qty} for product {p_id}"}), 400

            product = db_products.get(p_id)
            if not product:
                conn.rollback()
                return jsonify({"error": f"Product {p_id} not found in catalog"}), 404

            if product['stock'] < qty:
                conn.rollback()
                return jsonify({"error": f"Insufficient stock for '{product['name']}'. Requested: {qty}, Available: {product['stock']}"}), 409

            item_price = float(product['price'])
            item_subtotal = round(item_price * qty, 2)
            calculated_total += item_subtotal
            verified_order_items.append({
                "product_id": p_id,
                "name": product['name'],
                "quantity": qty,
                "unit_price": item_price
            })

        calculated_total = round(calculated_total, 2)

        cursor.execute("""
            INSERT INTO orders (user_id, total_amount, shipping_address, shipping_city, shipping_postal_code, status, payment_method, idempotency_key)
            VALUES (%s, %s, %s, %s, %s, 'CONFIRMED', %s, %s)
            RETURNING id, created_at
        """, (current_user['id'], calculated_total, shipping_address, shipping_city, shipping_postal_code, payment_method, idempotency_key))
        new_order = cursor.fetchone()
        order_id = new_order['id']

        for item in verified_order_items:
            cursor.execute("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (%s, %s, %s, %s)",
                           (order_id, item['product_id'], item['quantity'], item['unit_price']))
            cursor.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (item['quantity'], item['product_id']))

        cursor.execute("""
            INSERT INTO shipments (order_id, current_status, warehouse_name, current_location, latitude, longitude)
            VALUES (%s, 'ORDERED', 'Chennai Central Fulfillment Center', 'Warehouse Processing Bay 4', 13.0827, 80.2707)
            RETURNING id, current_status, warehouse_name, current_location, estimated_delivery
        """, (order_id,))
        shipment = cursor.fetchone()

        plain_otp = f"{secrets.randbelow(900000) + 100000}"
        otp_hash = hashlib.sha256(plain_otp.encode('utf-8')).hexdigest()
        customer_phone = current_user.get('phone_number') or "+919876543210"

        cursor.execute("INSERT INTO delivery_otps (order_id, otp_code_hash, phone_number) VALUES (%s, %s, %s)",
                       (order_id, otp_hash, customer_phone))

        conn.commit()
        cursor.close()
        conn.close()

        sms_body = f"CloudMart: Order #{order_id} confirmed! Total: ${calculated_total:.2f}. Expected delivery in 2 days. Track at /orders/{order_id}/tracking"
        send_sms_notification(customer_phone, sms_body)

        return jsonify({
            "message": "Order created successfully",
            "order_id": order_id,
            "total_amount": calculated_total,
            "status": "CONFIRMED",
            "shipment": {
                "status": shipment['current_status'],
                "warehouse": shipment['warehouse_name'],
                "location": shipment['current_location'],
                "estimated_delivery": shipment['estimated_delivery'].isoformat()
            },
            "demo_otp_secret": plain_otp
        }), 201

    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": f"Failed to create order: {str(e)}"}), 500

@app.route('/api/orders', methods=['GET'])
@token_required
def get_user_orders(current_user):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.id, o.total_amount, o.status, o.payment_method, o.shipping_address, o.shipping_city, o.created_at,
                   s.current_status as shipment_status, s.current_location,
                   COALESCE(json_agg(
                       json_build_object(
                           'product_id', oi.product_id,
                           'product_name', p.name,
                           'image_url', p.image_url,
                           'quantity', oi.quantity,
                           'unit_price', oi.unit_price
                       )
                   ) FILTER (WHERE oi.id IS NOT NULL), '[]') as items
            FROM orders o
            LEFT JOIN shipments s ON o.id = s.order_id
            LEFT JOIN order_items oi ON o.id = oi.order_id
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE o.user_id = %s
            GROUP BY o.id, s.current_status, s.current_location
            ORDER BY o.created_at DESC
        """, (current_user['id'],))
        orders = cursor.fetchall()
        cursor.close()
        conn.close()

        for o in orders:
            o['total_amount'] = float(o['total_amount'])
            o['created_at'] = o['created_at'].isoformat()

        return jsonify({"orders": orders}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve orders: {str(e)}"}), 500

@app.route('/api/orders/<int:order_id>', methods=['GET'])
@token_required
def get_order_details(current_user, order_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.id, o.user_id, o.total_amount, o.status, o.payment_method, o.shipping_address, o.shipping_city, o.created_at,
                   s.current_status as shipment_status, s.current_location, s.latitude, s.longitude, s.estimated_delivery
            FROM orders o
            LEFT JOIN shipments s ON o.id = s.order_id
            WHERE o.id = %s AND o.user_id = %s
        """, (order_id, current_user['id']))
        order = cursor.fetchone()

        if not order:
            cursor.close()
            conn.close()
            return jsonify({"error": "Order not found or access denied"}), 404

        cursor.execute("""
            SELECT oi.product_id, p.name as product_name, p.image_url, oi.quantity, oi.unit_price
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s
        """, (order_id,))
        order['items'] = cursor.fetchall()
        order['total_amount'] = float(order['total_amount'])
        for it in order['items']:
            it['unit_price'] = float(it['unit_price'])

        cursor.close()
        conn.close()
        return jsonify({"order": order}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve order: {str(e)}"}), 500

@app.route('/api/orders/<int:order_id>/tracking', methods=['GET'])
@token_required
def get_order_tracking(current_user, order_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.id as order_id, o.status as order_status, o.shipping_address, o.shipping_city,
                   s.current_status, s.warehouse_name, s.current_location, s.latitude, s.longitude,
                   s.estimated_delivery, s.updated_at,
                   otp.is_verified as otp_verified, otp.phone_number as delivery_phone
            FROM orders o
            JOIN shipments s ON o.id = s.order_id
            LEFT JOIN delivery_otps otp ON o.id = otp.order_id
            WHERE o.id = %s AND o.user_id = %s
        """, (order_id, current_user['id']))
        tracking = cursor.fetchone()
        cursor.close()
        conn.close()

        if not tracking:
            return jsonify({"error": "Tracking details not found"}), 404

        all_checkpoints = [
            {"step": 1, "status": "ORDERED", "title": "Order Placed", "desc": "Order received and confirmed by seller"},
            {"step": 2, "status": "PACKED", "title": "Packed in Warehouse", "desc": f"Packed at {tracking['warehouse_name']}"},
            {"step": 3, "status": "IN_TRANSIT", "title": "In Transit", "desc": "Departed regional sorting hub"},
            {"step": 4, "status": "OUT_FOR_DELIVERY", "title": "Out for Delivery", "desc": "Delivery agent is arriving at your doorstep with package"},
            {"step": 5, "status": "DELIVERED", "title": "Delivered", "desc": "Package handed over upon OTP verification"}
        ]

        status_order = ["ORDERED", "PACKED", "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED"]
        current_idx = status_order.index(tracking['current_status']) if tracking['current_status'] in status_order else 0

        for cp in all_checkpoints:
            cp_idx = status_order.index(cp['status'])
            cp['completed'] = cp_idx <= current_idx
            cp['current'] = cp_idx == current_idx

        tracking['latitude'] = float(tracking['latitude']) if tracking['latitude'] else 13.0827
        tracking['longitude'] = float(tracking['longitude']) if tracking['longitude'] else 80.2707
        tracking['timeline'] = all_checkpoints

        return jsonify({"tracking": tracking}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve tracking: {str(e)}"}), 500

@app.route('/api/orders/<int:order_id>/advance-status', methods=['POST'])
@token_required
def advance_shipment_status(current_user, order_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT current_status FROM shipments WHERE order_id = %s", (order_id,))
        shipment = cursor.fetchone()
        if not shipment:
            cursor.close()
            conn.close()
            return jsonify({"error": "Shipment not found"}), 404

        current_status = shipment['current_status']
        transitions = {
            'ORDERED': ('PACKED', 'Chennai Central Warehouse Bay 12', 13.0835, 80.2715),
            'PACKED': ('IN_TRANSIT', 'Koyambedu Logistics Sorting Facility', 13.0694, 80.1948),
            'IN_TRANSIT': ('OUT_FOR_DELIVERY', 'Out with Courier - Delivery Vehicle #TN-09-8831', 13.0850, 80.2150),
            'OUT_FOR_DELIVERY': ('DELIVERED', 'Delivered at Doorstep', 13.0827, 80.2707)
        }

        if current_status not in transitions:
            cursor.close()
            conn.close()
            return jsonify({"message": f"Shipment is already at terminal state: {current_status}"}), 200

        next_status, next_loc, next_lat, next_lng = transitions[current_status]

        cursor.execute("""
            UPDATE shipments 
            SET current_status = %s, current_location = %s, latitude = %s, longitude = %s, updated_at = CURRENT_TIMESTAMP
            WHERE order_id = %s
        """, (next_status, next_loc, next_lat, next_lng, order_id))

        if next_status == 'DELIVERED':
            cursor.execute("UPDATE orders SET status = 'DELIVERED' WHERE id = %s", (order_id,))

        cursor.execute("SELECT phone_number, otp_code_hash FROM delivery_otps WHERE order_id = %s", (order_id,))
        otp_rec = cursor.fetchone()

        conn.commit()
        cursor.close()
        conn.close()

        if next_status == 'OUT_FOR_DELIVERY' and otp_rec:
            sms_text = f"CloudMart: Your package for Order #{order_id} is OUT FOR DELIVERY! Please share your secret delivery OTP with the delivery agent upon arrival."
            send_sms_notification(otp_rec['phone_number'], sms_text)

        return jsonify({
            "order_id": order_id,
            "previous_status": current_status,
            "new_status": next_status,
            "current_location": next_loc,
            "coordinates": {"lat": next_lat, "lng": next_lng}
        }), 200

    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": f"Failed to advance shipment: {str(e)}"}), 500

@app.route('/api/orders/<int:order_id>/otp/verify', methods=['POST'])
@token_required
def verify_delivery_otp(current_user, order_id):
    data = request.get_json() or {}
    submitted_otp = str(data.get('otp', '')).strip()

    if not submitted_otp or len(submitted_otp) != 6:
        return jsonify({"error": "A valid 6-digit OTP is required"}), 400

    submitted_hash = hashlib.sha256(submitted_otp.encode('utf-8')).hexdigest()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, otp_code_hash, phone_number, is_verified, attempts, expires_at FROM delivery_otps WHERE order_id = %s", (order_id,))
        otp_rec = cursor.fetchone()

        if not otp_rec:
            cursor.close()
            conn.close()
            return jsonify({"error": "No OTP generated for this order"}), 404

        if otp_rec['is_verified']:
            cursor.close()
            conn.close()
            return jsonify({"message": "Order is already verified and delivered", "status": "DELIVERED"}), 200

        if otp_rec['attempts'] >= 5:
            cursor.close()
            conn.close()
            return jsonify({"error": "Max OTP attempts exceeded. Please contact customer support."}), 403

        if otp_rec['otp_code_hash'] != submitted_hash:
            cursor.execute("UPDATE delivery_otps SET attempts = attempts + 1 WHERE id = %s", (otp_rec['id'],))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"error": "Invalid OTP code", "remaining_attempts": 5 - (otp_rec['attempts'] + 1)}), 400

        cursor.execute("UPDATE delivery_otps SET is_verified = TRUE WHERE id = %s", (otp_rec['id'],))
        cursor.execute("UPDATE shipments SET current_status = 'DELIVERED', current_location = 'Delivered at Doorstep', updated_at = CURRENT_TIMESTAMP WHERE order_id = %s", (order_id,))
        cursor.execute("UPDATE orders SET status = 'DELIVERED' WHERE id = %s", (order_id,))

        conn.commit()
        cursor.close()
        conn.close()

        send_sms_notification(otp_rec['phone_number'], f"CloudMart: Order #{order_id} has been DELIVERED! Thank you for shopping with us.")

        return jsonify({
            "success": True,
            "message": "OTP verified successfully. Order marked as DELIVERED.",
            "order_id": order_id,
            "status": "DELIVERED"
        }), 200

    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": f"Failed to verify OTP: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
