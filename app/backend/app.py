import os
import math
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
DB_USER = os.environ.get('DB_USER', 'cloudmart')
DB_PASS = os.environ.get('DB_PASS', 'cloudmart_password')
DB_PORT = os.environ.get('DB_PORT', '5432')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
GEOFENCE_RADIUS_METERS = 50.0

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT,
        cursor_factory=RealDictCursor
    )

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi, delta_lambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)

def send_sms_notification(phone_number, message_text):
    print(f"\n[AWS SNS SMS DISPATCH]\nRecipient: {phone_number}\nMessage:   {message_text}\n")
    if not phone_number:
        return {"status": "skipped"}
    try:
        if os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY'):
            sns = boto3.client('sns', region_name=AWS_REGION)
            res = sns.publish(PhoneNumber=phone_number, Message=message_text)
            return {"status": "sent", "message_id": res.get('MessageId')}
        return {"status": "logged_locally"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authorization token missing"}), 401
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, name, email, phone_number, role FROM users WHERE id = %s", (payload['user_id'],))
            current_user = cur.fetchone()
            cur.close()
            conn.close()
            if not current_user:
                return jsonify({"error": "User does not exist"}), 401
        except Exception:
            return jsonify({"error": "Invalid or expired token"}), 401
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

# ----------------- AUTHENTICATION WITH ROLES -----------------
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    phone = data.get('phone_number', '').strip()
    role = data.get('role', 'customer').strip().lower()
    if role not in ['customer', 'seller']:
        role = 'customer'

    if not name or not email or not password:
        return jsonify({"error": "All fields are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"error": "Email is already registered"}), 409

        cur.execute("""
            INSERT INTO users (name, email, password_hash, phone_number, role)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, name, email, phone_number, role
        """, (name, email, hashed_pw, phone, role))
        user = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        token = jwt.encode({'user_id': user['id'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)}, JWT_SECRET, algorithm='HS256')
        return jsonify({"message": "Registration successful", "token": token, "user": user}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, email, password_hash, phone_number, role FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return jsonify({"error": "Invalid email or password"}), 401

        token = jwt.encode({'user_id': user['id'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)}, JWT_SECRET, algorithm='HS256')
        del user['password_hash']
        return jsonify({"message": "Login successful", "token": token, "user": user}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    return jsonify({"user": current_user}), 200

# ----------------- SELLER CENTRAL (VENDOR INVENTORY & ADD/REMOVE) -----------------
@app.route('/api/seller/products', methods=['POST'])
@token_required
def seller_add_product(current_user):
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    price = data.get('price', type=float) if 'price' in data else None
    stock = data.get('stock', type=int) if 'stock' in data else None
    category = data.get('category', 'Electronics').strip()
    image_url = data.get('image_url', '').strip() or 'https://images.unsplash.com/photo-1543512214-318c7553f230?w=600'

    if not name or price is None or stock is None:
        return jsonify({"error": "Product name, valid price, and stock are required"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO products (name, description, price, stock, category, image_url, rating, rating_count)
            VALUES (%s, %s, %s, %s, %s, %s, 4.8, 1)
            RETURNING id, name, price, stock, category, image_url
        """, (name, description, price, stock, category, image_url))
        new_prod = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Product published to CloudMart catalog", "product": new_prod}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/seller/products/<int:prod_id>', methods=['DELETE'])
@token_required
def seller_delete_product(current_user, prod_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id = %s RETURNING id, name", (prod_id,))
        deleted = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if not deleted:
            return jsonify({"error": "Product not found"}), 404
        return jsonify({"message": f"Product '{deleted['name']}' removed from catalog", "id": prod_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/seller/products/<int:prod_id>/stock', methods=['PUT'])
@token_required
def seller_update_stock(current_user, prod_id):
    data = request.get_json() or {}
    new_stock = data.get('stock', type=int)
    new_price = data.get('price', type=float)
    if new_stock is None and new_price is None:
        return jsonify({"error": "Provide new stock count or price"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if new_stock is not None and new_price is not None:
            cur.execute("UPDATE products SET stock = %s, price = %s WHERE id = %s RETURNING id, name, stock, price", (new_stock, new_price, prod_id))
        elif new_stock is not None:
            cur.execute("UPDATE products SET stock = %s WHERE id = %s RETURNING id, name, stock, price", (new_stock, prod_id))
        else:
            cur.execute("UPDATE products SET price = %s WHERE id = %s RETURNING id, name, stock, price", (new_price, prod_id))
        updated = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Inventory updated", "product": updated}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------- CUSTOMER CATALOG & SEARCH -----------------
@app.route('/api/categories', methods=['GET'])
def get_categories():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT category, COUNT(*) as count FROM products GROUP BY category ORDER BY category ASC")
        categories = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({"categories": categories}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        search = request.args.get('search', '').strip()
        cat = request.args.get('category', '').strip()
        sort_by = request.args.get('sort', 'newest')
        conds = ["1=1"]
        params = []
        if search:
            conds.append("(name ILIKE %s OR description ILIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])
        if cat and cat != 'All':
            conds.append("category = %s")
            params.append(cat)

        sort_map = {'price_asc': 'price ASC', 'price_desc': 'price DESC', 'rating': 'rating DESC'}
        order = sort_map.get(sort_by, 'created_at DESC')

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM products WHERE {' AND '.join(conds)} ORDER BY {order}", tuple(params))
        products = cur.fetchall()
        cur.close()
        conn.close()

        for p in products:
            p['price'] = float(p['price'])
            p['rating'] = float(p['rating'])
        return jsonify({"products": products}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
        product = cur.fetchone()
        cur.close()
        conn.close()
        if not product:
            return jsonify({"error": "Product not found"}), 404
        product['price'] = float(product['price'])
        product['rating'] = float(product['rating'])
        return jsonify({"product": product}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------- CART, CHECKOUT & ORDERS -----------------
@app.route('/api/cart/validate', methods=['POST'])
def validate_cart():
    data = request.get_json() or {}
    items = data.get('items', [])
    product_ids = [it['product_id'] for it in items if 'product_id' in it]
    if not product_ids:
        return jsonify({"valid": True, "total": 0.0}), 200

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, price, stock, image_url FROM products WHERE id = ANY(%s)", (product_ids,))
    db_prods = {p['id']: p for p in cur.fetchall()}
    cur.close()
    conn.close()

    total = 0.0
    for it in items:
        p = db_prods.get(it['product_id'])
        if p:
            total += float(p['price']) * it.get('quantity', 1)
    return jsonify({"valid": True, "total": round(total, 2)}), 200

@app.route('/api/orders', methods=['POST'])
@token_required
def create_order(current_user):
    data = request.get_json() or {}
    items = data.get('items', [])
    address = data.get('shipping_address', 'Katpadi, Vellore').strip()
    idempotency_key = data.get('idempotency_key') or secrets.token_hex(16)
    target_lat = 12.9716
    target_lng = 79.1585

    conn = get_db_connection()
    conn.autocommit = False
    cur = conn.cursor()

    try:
        cur.execute("SELECT id, total_amount, status FROM orders WHERE idempotency_key = %s", (idempotency_key,))
        existing = cur.fetchone()
        if existing:
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({"order_id": existing['id'], "status": existing['status']}), 200

        product_ids = [it['product_id'] for it in items]
        cur.execute("SELECT id, name, price, stock FROM products WHERE id = ANY(%s) FOR UPDATE", (product_ids,))
        db_prods = {p['id']: p for p in cur.fetchall()}

        calculated_total = 0.0
        for it in items:
            p = db_prods.get(it['product_id'])
            if not p or p['stock'] < it['quantity']:
                conn.rollback()
                return jsonify({"error": f"Insufficient stock for {p['name'] if p else 'item'}"}), 409
            calculated_total += float(p['price']) * it['quantity']

        cur.execute("""
            INSERT INTO orders (user_id, total_amount, shipping_address, shipping_city, shipping_postal_code, status, idempotency_key)
            VALUES (%s, %s, %s, 'Vellore', '632014', 'CONFIRMED', %s) RETURNING id
        """, (current_user['id'], calculated_total, address, idempotency_key))
        order_id = cur.fetchone()['id']

        for it in items:
            cur.execute("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (%s, %s, %s, %s)",
                        (order_id, it['product_id'], it['quantity'], db_prods[it['product_id']]['price']))
            cur.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (it['quantity'], it['product_id']))

        cur.execute("""
            INSERT INTO shipments (order_id, current_status, warehouse_name, current_location, latitude, longitude)
            VALUES (%s, 'ORDERED', 'Tamil Nadu Regional Hub', 'Warehouse Dispatch Bay', %s, %s)
        """, (order_id, target_lat, target_lng))

        plain_otp = f"{secrets.randbelow(900000) + 100000}"
        otp_hash = hashlib.sha256(plain_otp.encode('utf-8')).hexdigest()
        phone = current_user.get('phone_number') or "+919876543210"

        cur.execute("INSERT INTO delivery_otps (order_id, otp_code_hash, phone_number) VALUES (%s, %s, %s)",
                    (order_id, otp_hash, phone))
        conn.commit()
        cur.close()
        conn.close()

        send_sms_notification(phone, f"CloudMart: Order #{order_id} confirmed. Secret Doorstep OTP generated. Track at /orders/{order_id}")

        return jsonify({
            "order_id": order_id,
            "total_amount": round(calculated_total, 2),
            "status": "CONFIRMED",
            "demo_otp_secret": plain_otp
        }), 201
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

@app.route('/api/orders', methods=['GET'])
@token_required
def get_user_orders(current_user):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT o.id, o.total_amount, o.status, o.created_at, s.current_status as shipment_status, s.current_location
            FROM orders o
            LEFT JOIN shipments s ON o.id = s.order_id
            WHERE o.user_id = %s
            ORDER BY o.created_at DESC
        """, (current_user['id'],))
        orders = cur.fetchall()
        cur.close()
        conn.close()
        for o in orders:
            o['total_amount'] = float(o['total_amount'])
            o['created_at'] = o['created_at'].isoformat()
        return jsonify({"orders": orders}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------- GEOFENCED LOGISTICS HANDSHAKE -----------------
@app.route('/api/orders/<int:order_id>/tracking', methods=['GET'])
@token_required
def get_order_tracking(current_user, order_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT o.id as order_id, o.status as order_status, o.shipping_address,
                   s.current_status, s.warehouse_name, s.current_location, s.latitude as target_lat, s.longitude as target_lng,
                   otp.is_verified as otp_verified, otp.phone_number
            FROM orders o
            JOIN shipments s ON o.id = s.order_id
            LEFT JOIN delivery_otps otp ON o.id = otp.order_id
            WHERE o.id = %s
        """, (order_id,))
        tracking = cur.fetchone()
        cur.close()
        conn.close()
        if not tracking:
            return jsonify({"error": "Tracking record not found"}), 404

        all_steps = ["ORDERED", "PACKED", "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED"]
        curr_idx = all_steps.index(tracking['current_status']) if tracking['current_status'] in all_steps else 0
        timeline = [
            {"step": 1, "title": "Order Confirmed", "desc": "Package allocated at fulfillment center", "completed": curr_idx >= 0, "current": curr_idx == 0},
            {"step": 2, "title": "Packed & Sealed", "desc": "Tamper-evident packaging applied", "completed": curr_idx >= 1, "current": curr_idx == 1},
            {"step": 3, "title": "In Transit", "desc": "Departed regional hub", "completed": curr_idx >= 2, "current": curr_idx == 2},
            {"step": 4, "title": "Out for Delivery", "desc": "Courier en route to customer doorstep", "completed": curr_idx >= 3, "current": curr_idx == 3},
            {"step": 5, "title": "Delivered", "desc": "Unlocked upon 50m geofence & OTP verification", "completed": curr_idx >= 4, "current": curr_idx == 4}
        ]
        tracking['timeline'] = timeline
        return jsonify({"tracking": tracking}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/orders/<int:order_id>/advance-status', methods=['POST'])
@token_required
def advance_shipment_status(current_user, order_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT current_status FROM shipments WHERE order_id = %s", (order_id,))
        shipment = cur.fetchone()
        transitions = {
            'ORDERED': ('PACKED', 'Warehouse Processing Bay 2'),
            'PACKED': ('IN_TRANSIT', 'Vellore Regional Logistics Hub'),
            'IN_TRANSIT': ('OUT_FOR_DELIVERY', 'Out with Courier - Delivery Van #TN-23-9081'),
            'OUT_FOR_DELIVERY': ('DELIVERED', 'Delivered at Doorstep')
        }
        curr = shipment['current_status']
        if curr not in transitions:
            cur.close()
            conn.close()
            return jsonify({"message": f"Terminal state: {curr}"}), 200

        nxt_status, nxt_loc = transitions[curr]
        cur.execute("UPDATE shipments SET current_status = %s, current_location = %s WHERE order_id = %s", (nxt_status, nxt_loc, order_id))
        if nxt_status == 'DELIVERED':
            cur.execute("UPDATE orders SET status = 'DELIVERED' WHERE id = %s", (order_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"new_status": nxt_status, "current_location": nxt_loc}), 200
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

@app.route('/api/orders/<int:order_id>/otp/verify', methods=['POST'])
@token_required
def verify_geofenced_delivery_otp(current_user, order_id):
    data = request.get_json() or {}
    submitted_otp = str(data.get('otp', '')).strip()
    driver_lat = float(data.get('driver_lat', 0.0))
    driver_lng = float(data.get('driver_lng', 0.0))

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT s.latitude as target_lat, s.longitude as target_lng,
                   otp.id as otp_id, otp.otp_code_hash, otp.phone_number, otp.is_verified, otp.attempts
            FROM shipments s
            JOIN delivery_otps otp ON s.order_id = otp.order_id
            WHERE s.order_id = %s
        """, (order_id,))
        rec = cur.fetchone()
        if not rec:
            cur.close()
            conn.close()
            return jsonify({"error": "Order or OTP record not found"}), 404

        proximity_meters = calculate_haversine_distance(driver_lat, driver_lng, float(rec['target_lat']), float(rec['target_lng']))

        # Spatial Barrier
        if proximity_meters > GEOFENCE_RADIUS_METERS:
            cur.execute("UPDATE delivery_otps SET attempts = attempts + 1 WHERE id = %s", (rec['otp_id'],))
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({
                "error": f"GEOFENCE_VIOLATION: Courier is {proximity_meters}m away. Anti-Fraud Policy requires proximity within {GEOFENCE_RADIUS_METERS}m of customer doorstep.",
                "code": "GEOFENCE_BREACH",
                "proximity_meters": proximity_meters
            }), 403

        # Cryptographic Hash Match
        submitted_hash = hashlib.sha256(submitted_otp.encode('utf-8')).hexdigest()
        if rec['otp_code_hash'] != submitted_hash:
            cur.execute("UPDATE delivery_otps SET attempts = attempts + 1 WHERE id = %s", (rec['otp_id'],))
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({"error": "Invalid OTP code"}), 400

        # Success Handshake
        cur.execute("UPDATE delivery_otps SET is_verified = TRUE WHERE id = %s", (rec['otp_id'],))
        cur.execute("UPDATE shipments SET current_status = 'DELIVERED', current_location = 'Delivered at Doorstep', updated_at = CURRENT_TIMESTAMP WHERE order_id = %s", (order_id,))
        cur.execute("UPDATE orders SET status = 'DELIVERED' WHERE id = %s", (order_id,))
        conn.commit()
        cur.close()
        conn.close()

        send_sms_notification(rec['phone_number'], f"CloudMart: Order #{order_id} DELIVERED! Proximity verified at {proximity_meters}m.")

        return jsonify({
            "success": True,
            "message": f"Handshake Complete! Proximity: {proximity_meters}m (Within {GEOFENCE_RADIUS_METERS}m perimeter).",
            "status": "DELIVERED"
        }), 200
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
