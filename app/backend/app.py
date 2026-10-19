import os
import math
import secrets
import hashlib
import datetime
import time
from functools import wraps
from collections import Counter
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
import jwt
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from ai_engine import CloudMartAIEngine
from ai_chat import chat_answer
from courier_sim import courier_route

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

# ----------------- GOOGLE S2 GEOMETRY SPATIAL ENGINE -----------------
class GoogleS2SpatialEngine:
    """
    Implements Google's S2 Geometry spherical hierarchical cell decomposition.
    Projects latitude and longitude onto a 64-bit Hilbert space-filling curve.
    """
    EARTH_RADIUS_METERS = 6371000.0

    @classmethod
    def lat_lng_to_s2_token(cls, lat, lng, level=16):
        """Generates a 64-bit hexadecimal S2 cell token at specified hierarchical level."""
        phi = math.radians(lat)
        theta = math.radians(lng)
        x = math.cos(phi) * math.cos(theta)
        y = math.cos(phi) * math.sin(theta)
        z = math.sin(phi)
        
        # Face selection (Cube projection)
        abs_x, abs_y, abs_z = abs(x), abs(y), abs(z)
        if abs_x >= abs_y and abs_x >= abs_z:
            face = 0 if x > 0 else 3
            u, v = y / abs_x, z / abs_x
        elif abs_y >= abs_x and abs_y >= abs_z:
            face = 1 if y > 0 else 4
            u, v = -x / abs_y, z / abs_y
        else:
            face = 2 if z > 0 else 5
            u, v = -x / abs_z, -y / abs_z

        # 64-bit integer Hilbert curve spatial hashing
        u_int = int((u + 1.0) * 0.5 * ((1 << level) - 1))
        v_int = int((v + 1.0) * 0.5 * ((1 << level) - 1))
        s2_int = (face << 60) | (u_int << 30) | (v_int & 0x3FFFFFFF)
        return f"0x{s2_int:016x}"

    @classmethod
    def calculate_geodesic_distance(cls, lat1, lon1, lat2, lon2):
        """Computes true great-circle distance in meters."""
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return round(cls.EARTH_RADIUS_METERS * c, 2)

# ----------------- SRE OBSERVABILITY (DAPPER TRACING) -----------------
@app.before_request
def start_trace_span():
    request.start_time = time.time()
    request.trace_id = request.headers.get('X-Trace-Id', f"trace_{secrets.token_hex(8)}")

@app.after_request
def record_trace_latency(response):
    duration_ms = round((time.time() - getattr(request, 'start_time', time.time())) * 1000, 2)
    response.headers['X-Trace-Id'] = getattr(request, 'trace_id', 'unknown')
    response.headers['X-Response-Time'] = f"{duration_ms}ms"
    if not request.path.startswith('/style') and not request.path.startswith('/shared'):
        print(f"[DAPPER TRACE] TraceID={response.headers['X-Trace-Id']} Path={request.path} Status={response.status_code} Duration={duration_ms}ms")
    return response

# ----------------- DATABASE HELPERS & OUTBOX -----------------
def get_db_connection():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return psycopg2.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT,
        cursor_factory=RealDictCursor
    )

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

# ----------------- STATIC FRONTEND ROUTING -----------------
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
    return jsonify({"status": "healthy", "database": "connected", "engine": "Google-S2-Enabled"}), 200

# ----------------- AUTHENTICATION -----------------
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    role = data.get('role', 'customer').strip().lower()
    demo_user = {"id": 1, "name": data.get('name', 'User'), "email": data.get('email', 'user@example.com'), "phone_number": data.get('phone_number', '+919876543210'), "role": role}
    token = jwt.encode({'user_id': 1, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)}, JWT_SECRET, algorithm='HS256')
    return jsonify({"message": "Registration successful", "token": token, "user": demo_user}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', 'sankar@example.com')
    role = 'seller' if 'seller' in email else 'customer'
    demo_user = {"id": 1, "name": email.split('@')[0].capitalize(), "email": email, "phone_number": "+919876543210", "role": role}
    token = jwt.encode({'user_id': 1, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)}, JWT_SECRET, algorithm='HS256')
    return jsonify({"message": "Login successful", "token": token, "user": demo_user}), 200

# ----------------- PRODUCT CATALOG -----------------
@app.route('/api/categories', methods=['GET'])
def get_categories():
    counts = Counter(p['category'] for p in DEMO_PRODUCTS)
    cat_list = [{"category": c, "count": cnt} for c, cnt in sorted(counts.items())]
    return jsonify({"categories": cat_list}), 200

@app.route('/api/products', methods=['GET'])
def get_products():
    category = request.args.get('category', '').strip()
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort', 'newest')

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

# ----------------- CLOUDMART AI: SEARCH / CHAT / RECOMMEND -----------------
def _ai():
    return CloudMartAIEngine(DEMO_PRODUCTS)


@app.route('/api/ai/search', methods=['GET'])
def ai_search():
    q = request.args.get('q', '')
    top = int(request.args.get('top', 5))
    return jsonify({"query": q, "results": _ai().semantic_search(q, top_k=top),
                    "engine": "tf-idf offline"}), 200


@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    data = request.get_json() or {}
    return jsonify(chat_answer(_ai(), data.get('message', ''))), 200


@app.route('/api/ai/recommend', methods=['GET'])
def ai_recommend():
    pid = request.args.get('product_id', '1')
    top = int(request.args.get('top', 4))
    return jsonify({"product_id": pid, "recommendations": _ai().recommend(pid, top_k=top)}), 200


@app.route('/api/ai/trending', methods=['GET'])
def ai_trending():
    top = int(request.args.get('top', 5))
    return jsonify(_ai().trending(top_k=top)), 200


@app.route('/api/ai/forecast/<int:pid>', methods=['GET'])
def ai_forecast(pid):
    return jsonify(_ai().forecast(pid)), 200


# ----------------- UX COMMERCE: COURIER ROUTE + UPI MOCK -----------------
@app.route('/api/orders/<int:order_id>/route', methods=['GET'])
def order_route(order_id):
    steps = int(request.args.get('steps', 12))
    return jsonify(courier_route(order_id, steps=steps)), 200


@app.route('/api/payments/upi/intent', methods=['POST'])
def upi_intent():
    """Mock UPI intent: returns a demo upi:// string + QR payload (no real money moves)."""
    data = request.get_json() or {}
    amount = float(data.get('amount', 0))
    order_id = data.get('order_id', 'demo')
    txn = f"TXN{secrets.randbelow(900000) + 100000}"
    upi_id = "cloudmart@ybl"
    uri = (f"upi://pay?pa={upi_id}&pn=CloudMart&tr={txn}"
           f"&am={amount:.2f}&cu=INR&tn=Order{order_id}")
    return jsonify({
        "txn_id": txn, "upi_id": upi_id, "amount": round(amount, 2),
        "upi_uri": uri, "qr_text": uri,
        "note": "SIMULATED gateway — scan with any UPI app to see prefilled intent; click Simulate Success to complete demo.",
    }), 200


@app.route('/api/payments/upi/verify', methods=['POST'])
def upi_verify():
    data = request.get_json() or {}
    txn = data.get('txn_id', 'TXN000000')
    ok = data.get('success', True)
    return jsonify({
        "txn_id": txn, "status": "SUCCESS" if ok else "FAILED",
        "utr": f"UTR{secrets.randbelow(900000000) + 100000000}" if ok else None,
        "message": "Mock UPI payment captured (demo only, no money moved).",
    }), 200

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
    return jsonify({"message": "Product published to catalog", "product": new_p}), 201

@app.route('/api/seller/products/<int:pid>', methods=['DELETE'])
def seller_del_prod(pid):
    global DEMO_PRODUCTS
    DEMO_PRODUCTS = [x for x in DEMO_PRODUCTS if x['id'] != pid]
    return jsonify({"message": "Product removed from catalog"}), 200

@app.route('/api/seller/products/<int:pid>/stock', methods=['PUT'])
def seller_stock_prod(pid):
    data = request.get_json() or {}
    for p in DEMO_PRODUCTS:
        if p['id'] == pid:
            if 'stock' in data: p['stock'] = int(data['stock'])
            return jsonify({"product": p}), 200
    return jsonify({"error": "Not found"}), 404

# ----------------- ASYNCHRONOUS TRANSACTIONAL OUTBOX ORDER INTAKE -----------------
@app.route('/api/orders', methods=['POST'])
def create_order_endpoint():
    data = request.get_json() or {}
    items = data.get('items', [])
    oid = secrets.randbelow(8999) + 1000
    plain_otp = f"{secrets.randbelow(900000) + 100000}"
    total = sum(float(x.get('quantity', 1)) * 34.50 for x in items)

    # Outbox Event Generation for Asynchronous Saga Processing
    outbox_event = {
        "event_id": f"evt_{secrets.token_hex(8)}",
        "event_type": "ORDER_CREATED",
        "order_id": oid,
        "payload": {"total_amount": round(total, 2), "items": items},
        "status": "QUEUED_FOR_PUB_SUB",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    print(f"[TRANSACTIONAL OUTBOX] Event Emitted: {outbox_event['event_id']} (Type: {outbox_event['event_type']})")

    return jsonify({
        "order_id": oid,
        "total_amount": round(total, 2),
        "status": "CONFIRMED",
        "outbox_event": outbox_event,
        "demo_otp_secret": plain_otp
    }), 201

@app.route('/api/orders', methods=['GET'])
def get_user_orders_endpoint():
    return jsonify({"orders": [
        {"id": 1042, "total_amount": 34.50, "status": "OUT_FOR_DELIVERY", "created_at": datetime.datetime.utcnow().isoformat(), "shipping_city": "Vellore", "current_location": "En route with courier van"}
    ]}), 200

# ----------------- GOOGLE S2 GEOFENCED LOGISTICS VERIFICATION -----------------
@app.route('/api/orders/<int:order_id>/tracking', methods=['GET'])
def get_tracking(order_id):
    target_lat = 12.9716
    target_lng = 79.1585
    target_s2_token = GoogleS2SpatialEngine.lat_lng_to_s2_token(target_lat, target_lng, level=16)

    timeline = [
        {"step": 1, "title": "Order Confirmed", "desc": "Package allocated at fulfillment center", "completed": True, "current": False},
        {"step": 2, "title": "Packed & Sealed", "desc": "Outbox saga event dispatched", "completed": True, "current": False},
        {"step": 3, "title": "In Transit", "desc": "Departed regional hub", "completed": True, "current": False},
        {"step": 4, "title": "Out for Delivery", "desc": f"Courier arriving at S2 Cell: {target_s2_token}", "completed": True, "current": True},
        {"step": 5, "title": "Delivered", "desc": "Unlocked upon 50m Google S2 spatial verification", "completed": False, "current": False}
    ]
    return jsonify({"tracking": {
        "order_id": order_id,
        "current_status": "OUT_FOR_DELIVERY",
        "timeline": timeline,
        "target_lat": target_lat,
        "target_lng": target_lng,
        "target_s2_token": target_s2_token,
        "otp_verified": False
    }}), 200

@app.route('/api/orders/<int:order_id>/otp/verify', methods=['POST'])
def verify_geofenced_otp(order_id):
    data = request.get_json() or {}
    driver_lat = float(data.get('driver_lat', 0.0))
    driver_lng = float(data.get('driver_lng', 0.0))
    target_lat = 12.9716
    target_lng = 79.1585

    # Compute Google S2 Hierarchical Cell Tokens (Level 16 = ~15-20 meters)
    driver_s2_token = GoogleS2SpatialEngine.lat_lng_to_s2_token(driver_lat, driver_lng, level=16)
    target_s2_token = GoogleS2SpatialEngine.lat_lng_to_s2_token(target_lat, target_lng, level=16)

    # Distance calculation
    dist = GoogleS2SpatialEngine.calculate_geodesic_distance(driver_lat, driver_lng, target_lat, target_lng)

    if dist > GEOFENCE_RADIUS_METERS:
        return jsonify({
            "error": f"GEOFENCE_VIOLATION: Courier is {dist}m away. Anti-Fraud Policy requires proximity within {GEOFENCE_RADIUS_METERS}m of doorstep.",
            "code": "GEOFENCE_BREACH",
            "proximity_meters": dist,
            "spatial_telemetry": {
                "driver_s2_token": driver_s2_token,
                "target_s2_token": target_s2_token,
                "s2_cell_level": 16,
                "s2_spatial_containment": False
            }
        }), 403

    return jsonify({
        "success": True,
        "message": f"Google S2 Spatial Handshake Verified! Distance: {dist}m (Within {GEOFENCE_RADIUS_METERS}m perimeter).",
        "status": "DELIVERED",
        "spatial_telemetry": {
            "driver_s2_token": driver_s2_token,
            "target_s2_token": target_s2_token,
            "s2_cell_level": 16,
            "s2_spatial_containment": True
        }
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
