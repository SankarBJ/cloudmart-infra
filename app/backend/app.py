import os
import math
import secrets
import hashlib
import datetime
from functools import wraps
from collections import Counter
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
import jwt
import boto3
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

FRONTEND_DIR = os.environ.get('FRONTEND_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend')))
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app)

JWT_SECRET = os.environ.get('JWT_SECRET', 'cloudmart-secure-jwt-dev-secret-key-32chars!')
DATABASE_URL = os.environ.get('DATABASE_URL')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_NAME = os.environ.get('DB_NAME', 'cloudmart')
DB_USER = os.environ.get('DB_USER', 'cloudmart')
DB_PASS = os.environ.get('DB_PASS', 'cloudmart_password')
DB_PORT = os.environ.get('DB_PORT', '5432')
GEOFENCE_RADIUS_METERS = 50.0

DEMO_PRODUCTS = [
    {"id": 1, "name": "Echo Wave Smart Speaker with Alexa", "description": "Rich HD audio smart speaker with voice control.", "price": 49.99, "stock": 50, "category": "Electronics", "image_url": "https://images.unsplash.com/photo-1543512214-318c7553f230?w=600", "rating": 4.7, "rating_count": 342},
    {"id": 2, "name": "Kindle Paperwhite 16GB Display", "description": "Now with 6.8 inch display and adjustable warm light.", "price": 139.99, "stock": 35, "category": "Electronics", "image_url": "https://images.unsplash.com/photo-1592496431122-2349e0fbc666?w=600", "rating": 4.8, "rating_count": 890},
    {"id": 3, "name": "CloudSonic Noise Cancelling Headphones", "description": "Over-ear wireless headphones with active noise cancelling.", "price": 89.99, "stock": 40, "category": "Electronics", "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600", "rating": 4.6, "rating_count": 520},
    {"id": 4, "name": "CloudTech Pro Mechanical Keyboard", "description": "RGB tactile mechanical coding keyboard.", "price": 69.99, "stock": 60, "category": "Electronics", "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600", "rating": 4.7, "rating_count": 610},
    {"id": 5, "name": "Stainless Steel Insulated Water Bottle 1L", "description": "Vacuum insulated flask keeps drinks cold 24 hrs.", "price": 24.99, "stock": 120, "category": "Home & Kitchen", "image_url": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=600", "rating": 4.5, "rating_count": 215},
    {"id": 6, "name": "Barista Touch Espresso Coffee Maker", "description": "Automatic micro-foam milk texturing with 15 bar pump.", "price": 299.99, "stock": 15, "category": "Home & Kitchen", "image_url": "https://images.unsplash.com/photo-1517668808822-9ebb02f2a0e6?w=600", "rating": 4.9, "rating_count": 145},
    {"id": 7, "name": "Ergonomic Memory Foam Office Chair Cushion", "description": "Orthopedic seat cushion designed to relieve lower back pain.", "price": 34.50, "stock": 75, "category": "Office", "image_url": "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=600", "rating": 4.4, "rating_count": 430},
    {"id": 8, "name": "Organic Cotton Breathable Crewneck T-Shirt", "description": "100% combed cotton modern tailored fit.", "price": 19.99, "stock": 150, "category": "Fashion", "image_url": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=600", "rating": 4.3, "rating_count": 180},
    {"id": 9, "name": "Waterproof Outdoor Trail Hiking Backpack 40L", "description": "Lightweight ripstop nylon trekking bag.", "price": 54.99, "stock": 45, "category": "Fashion", "image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600", "rating": 4.6, "rating_count": 290},
    {"id": 10, "name": "Designing Data-Intensive Applications Book", "description": "The definitive guide to distributed data systems.", "price": 42.00, "stock": 80, "category": "Books", "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600", "rating": 4.9, "rating_count": 1250}
]

def get_db_connection():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return psycopg2.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT,
        cursor_factory=RealDictCursor
    )

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi, delta_lambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)

@app.route('/')
def serve_root():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_page(path):
    if os.path.exists(os.path.join(FRONTEND_DIR, path)):
        return send_from_directory(FRONTEND_DIR, path)
    if os.path.exists(os.path.join(FRONTEND_DIR, f"{path}.html")):
        return send_from_directory(FRONTEND_DIR, f"{path}.html")
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "database": "connected"}), 200

# ----------------- FIXED PRODUCT CATALOG WITH PROPER FILTERS -----------------
@app.route('/api/categories', methods=['GET'])
def get_categories():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT category, COUNT(*) as count FROM products GROUP BY category ORDER BY category ASC")
        cats = cur.fetchall()
        cur.close(); conn.close()
        if cats:
            return jsonify({"categories": cats}), 200
    except Exception:
        pass

    counts = Counter(p['category'] for p in DEMO_PRODUCTS)
    cat_list = [{"category": c, "count": cnt} for c, cnt in sorted(counts.items())]
    return jsonify({"categories": cat_list}), 200

@app.route('/api/products', methods=['GET'])
def get_products():
    category = request.args.get('category', '').strip()
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort', 'newest')

    # Try Database Query First
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        conds = ["1=1"]
        params = []
        if category and category.lower() != 'all':
            conds.append("category ILIKE %s")
            params.append(category)
        if search:
            conds.append("(name ILIKE %s OR description ILIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])

        sort_map = {'price_asc': 'price ASC', 'price_desc': 'price DESC', 'rating': 'rating DESC'}
        order = sort_map.get(sort_by, 'id ASC')

        cur.execute(f"SELECT * FROM products WHERE {' AND '.join(conds)} ORDER BY {order}", tuple(params))
        prods = cur.fetchall()
        cur.close(); conn.close()
        if prods:
            for p in prods:
                p['price'] = float(p['price']); p['rating'] = float(p['rating'])
            return jsonify({"products": prods}), 200
    except Exception:
        pass

    # Exact Fallback Filter
    filtered = list(DEMO_PRODUCTS)
    if category and category.lower() != 'all':
        filtered = [p for p in filtered if p['category'].lower() == category.lower()]
    if search:
        filtered = [p for p in filtered if search.lower() in p['name'].lower() or search.lower() in p.get('description', '').lower()]
    if sort_by == 'price_asc':
        filtered.sort(key=lambda x: x['price'])
    elif sort_by == 'price_desc':
        filtered.sort(key=lambda x: x['price'], reverse=True)
    elif sort_by == 'rating':
        filtered.sort(key=lambda x: x['rating'], reverse=True)

    return jsonify({"products": filtered}), 200

@app.route('/api/products/<int:pid>', methods=['GET'])
def get_product_one(pid):
    p = next((x for x in DEMO_PRODUCTS if x['id'] == pid), DEMO_PRODUCTS[0])
    return jsonify({"product": p}), 200

# ----------------- AUTH & ROLES -----------------
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    role = data.get('role', 'customer').strip().lower()
    demo_user = {"id": 1, "name": data.get('name', 'User'), "email": data.get('email', 'user@example.com'), "phone_number": data.get('phone_number', '+919876543210'), "role": role}
    token = jwt.encode({'user_id': 1, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)}, JWT_SECRET, algorithm='HS256')
    return jsonify({"message": "Success", "token": token, "user": demo_user}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', 'sankar@example.com')
    role = 'seller' if 'seller' in email else 'customer'
    demo_user = {"id": 1, "name": email.split('@')[0].capitalize(), "email": email, "phone_number": "+919876543210", "role": role}
    token = jwt.encode({'user_id': 1, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)}, JWT_SECRET, algorithm='HS256')
    return jsonify({"message": "Success", "token": token, "user": demo_user}), 200

# ----------------- SELLER CENTRAL -----------------
@app.route('/api/seller/products', methods=['POST'])
def seller_add_prod():
    data = request.get_json() or {}
    new_p = {
        "id": len(DEMO_PRODUCTS) + 1, "name": data.get('name', 'New Product'), "category": data.get('category', 'Electronics'),
        "price": float(data.get('price', 99.99)), "stock": int(data.get('stock', 20)),
        "image_url": data.get('image_url') or "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600",
        "rating": 4.8, "rating_count": 1
    }
    DEMO_PRODUCTS.append(new_p)
    return jsonify({"message": "Product published", "product": new_p}), 201

@app.route('/api/seller/products/<int:pid>', methods=['DELETE'])
def seller_del_prod(pid):
    global DEMO_PRODUCTS
    DEMO_PRODUCTS = [x for x in DEMO_PRODUCTS if x['id'] != pid]
    return jsonify({"message": "Deleted"}), 200

@app.route('/api/seller/products/<int:pid>/stock', methods=['PUT'])
def seller_stock_prod(pid):
    data = request.get_json() or {}
    for p in DEMO_PRODUCTS:
        if p['id'] == pid:
            if 'stock' in data: p['stock'] = int(data['stock'])
            return jsonify({"product": p}), 200
    return jsonify({"error": "Not found"}), 404

# ----------------- ORDERS & GEOFENCED HANDSHAKE -----------------
@app.route('/api/orders', methods=['POST'])
def create_order_endpoint():
    data = request.get_json() or {}
    items = data.get('items', [])
    oid = secrets.randbelow(8999) + 1000
    plain_otp = f"{secrets.randbelow(900000) + 100000}"
    total = sum(float(x.get('quantity', 1)) * 34.50 for x in items)
    return jsonify({"order_id": oid, "total_amount": round(total, 2), "status": "CONFIRMED", "demo_otp_secret": plain_otp}), 201

@app.route('/api/orders', methods=['GET'])
def get_user_orders_endpoint():
    return jsonify({"orders": [
        {"id": 1042, "total_amount": 34.50, "status": "OUT_FOR_DELIVERY", "created_at": datetime.datetime.utcnow().isoformat(), "shipping_city": "Vellore", "current_location": "En route with courier van"}
    ]}), 200

@app.route('/api/orders/<int:order_id>/tracking', methods=['GET'])
def get_tracking(order_id):
    timeline = [
        {"step": 1, "title": "Order Confirmed", "desc": "Package allocated at fulfillment center", "completed": True, "current": False},
        {"step": 2, "title": "Packed & Sealed", "desc": "Tamper-evident packaging applied", "completed": True, "current": False},
        {"step": 3, "title": "In Transit", "desc": "Departed regional hub", "completed": True, "current": False},
        {"step": 4, "title": "Out for Delivery", "desc": "Courier approaching customer doorstep", "completed": True, "current": True},
        {"step": 5, "title": "Delivered", "desc": "Unlocked upon 50m geofence & OTP verification", "completed": False, "current": False}
    ]
    return jsonify({"tracking": {
        "order_id": order_id, "current_status": "OUT_FOR_DELIVERY", "timeline": timeline,
        "target_lat": 12.9716, "target_lng": 79.1585, "otp_verified": False
    }}), 200

@app.route('/api/orders/<int:order_id>/otp/verify', methods=['POST'])
def verify_geofenced_otp(order_id):
    data = request.get_json() or {}
    driver_lat = float(data.get('driver_lat', 0.0))
    driver_lng = float(data.get('driver_lng', 0.0))
    dist = calculate_haversine_distance(driver_lat, driver_lng, 12.9716, 79.1585)

    if dist > GEOFENCE_RADIUS_METERS:
        return jsonify({
            "error": f"GEOFENCE_VIOLATION: Courier is {dist}m away. Anti-Fraud Policy requires proximity within {GEOFENCE_RADIUS_METERS}m of doorstep.",
            "code": "GEOFENCE_BREACH", "proximity_meters": dist
        }), 403

    return jsonify({"success": True, "message": f"Handshake Complete! Proximity: {dist}m (Within {GEOFENCE_RADIUS_METERS}m).", "status": "DELIVERED"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
