from flask import Flask, jsonify, request
from decimal import Decimal
import os
import re
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "cloudmart")
DB_USER = os.getenv("DB_USER", "cloudmart")
DB_PASSWORD = os.getenv("DB_PASSWORD")


def get_db_connection():
    if not DB_PASSWORD:
        raise RuntimeError("Database password is not configured")

    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=5,
    )


def ensure_schema():
    """Create order tables if they do not already exist."""
    statements = [
        """
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            customer_name VARCHAR(120) NOT NULL,
            email VARCHAR(160) NOT NULL,
            phone VARCHAR(20) NOT NULL,
            address TEXT NOT NULL,
            city VARCHAR(80) NOT NULL,
            pincode VARCHAR(12) NOT NULL,
            payment_method VARCHAR(40) NOT NULL,
            payment_status VARCHAR(40) NOT NULL,
            total NUMERIC(10,2) NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS order_items (
            id SERIAL PRIMARY KEY,
            order_id INTEGER NOT NULL REFERENCES orders(id),
            product_id INTEGER NOT NULL,
            name VARCHAR(100) NOT NULL,
            price NUMERIC(10,2) NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0)
        )
        """,
    ]

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)


@app.get("/api/health")
def health():
    return jsonify({
        "service": "cloudmart-backend",
        "status": "healthy",
    })


@app.get("/api/products")
def products():
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT id, name, price, description
                    FROM products
                    ORDER BY id
                    """
                )
                rows = cursor.fetchall()

        result = [
            {
                **dict(row),
                "price": float(row["price"]),
            }
            for row in rows
        ]
        return jsonify(result)

    except psycopg2.Error:
        app.logger.exception("Unable to retrieve products")
        return jsonify({"error": "Unable to retrieve products"}), 503


@app.post("/api/orders")
def create_order():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Send a JSON request body"}), 400

    required = [
        "customer_name", "email", "phone", "address",
        "city", "pincode", "payment_method", "items",
    ]

    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    for field in required[:-1]:
        if not isinstance(data[field], str) or not data[field].strip():
            return jsonify({"error": f"{field} must be a non-empty string"}), 400

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", data["email"]):
        return jsonify({"error": "Enter a valid email address"}), 400

    if not isinstance(data["items"], list) or not data["items"]:
        return jsonify({"error": "The cart must contain at least one item"}), 400

    if data["payment_method"] not in ("Cash on Delivery", "Demo Payment"):
        return jsonify({"error": "Unsupported demo payment method"}), 400

    quantities = {}

    for item in data["items"]:
        if not isinstance(item, dict):
            return jsonify({"error": "Each cart item must be an object"}), 400

        product_id = item.get("product_id")
        quantity = item.get("quantity")

        if (
            isinstance(product_id, bool)
            or not isinstance(product_id, int)
            or product_id < 1
            or isinstance(quantity, bool)
            or not isinstance(quantity, int)
            or quantity < 1
            or quantity > 20
        ):
            return jsonify({
                "error": "Product IDs must be positive integers and quantities must be 1–20"
            }), 400

        quantities[product_id] = quantities.get(product_id, 0) + quantity

        if quantities[product_id] > 20:
            return jsonify({"error": "Maximum quantity per product is 20"}), 400

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                product_ids = list(quantities)

                cursor.execute(
                    """
                    SELECT id, name, price
                    FROM products
                    WHERE id = ANY(%s)
                    ORDER BY id
                    """,
                    (product_ids,),
                )
                found = {row["id"]: row for row in cursor.fetchall()}

                if set(found) != set(product_ids):
                    return jsonify({
                        "error": "One or more products do not exist"
                    }), 400

                total = sum(
                    (Decimal(found[pid]["price"]) * qty
                     for pid, qty in quantities.items()),
                    Decimal("0.00"),
                )

                if total <= 0 or total > Decimal("99999999.99"):
                    return jsonify({"error": "Order total is outside the allowed range"}), 400

                # This is a demonstration checkout, not real payment processing.
                payment_status = (
                    "PENDING_COD"
                    if data["payment_method"] == "Cash on Delivery"
                    else "SIMULATED"
                )

                cursor.execute(
                    """
                    INSERT INTO orders (
                        customer_name, email, phone, address, city,
                        pincode, payment_method, payment_status, total
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, created_at, total, payment_status
                    """,
                    (
                        data["customer_name"].strip(),
                        data["email"].strip().lower(),
                        data["phone"].strip(),
                        data["address"].strip(),
                        data["city"].strip(),
                        data["pincode"].strip(),
                        data["payment_method"],
                        payment_status,
                        total,
                    ),
                )
                order = cursor.fetchone()

                for product_id, quantity in quantities.items():
                    product = found[product_id]
                    cursor.execute(
                        """
                        INSERT INTO order_items (
                            order_id, product_id, name, price, quantity
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            order["id"],
                            product_id,
                            product["name"],
                            product["price"],
                            quantity,
                        ),
                    )

        return jsonify({
            "message": "Order placed successfully",
            "order": {
                "id": order["id"],
                "created_at": order["created_at"].isoformat(),
                "total": float(order["total"]),
                "payment_method": data["payment_method"],
                "payment_status": order["payment_status"],
            },
        }), 201

    except psycopg2.Error:
        app.logger.exception("Unable to create order")
        return jsonify({"error": "Order could not be saved"}), 503


@app.get("/api/orders/<int:order_id>")
def get_order(order_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT id, created_at, customer_name, email, total,
                           payment_method, payment_status
                    FROM orders
                    WHERE id = %s
                    """,
                    (order_id,),
                )
                order = cursor.fetchone()

                if order is None:
                    return jsonify({"error": "Order not found"}), 404

                cursor.execute(
                    """
                    SELECT product_id, name, price, quantity
                    FROM order_items
                    WHERE order_id = %s
                    ORDER BY id
                    """,
                    (order_id,),
                )
                items = cursor.fetchall()

        return jsonify({
            "order": {
                **{
                    key: value.isoformat() if key == "created_at"
                    else float(value) if key == "total"
                    else value
                    for key, value in dict(order).items()
                },
                "items": [
                    {
                        **dict(item),
                        "price": float(item["price"]),
                    }
                    for item in items
                ],
            }
        })

    except psycopg2.Error:
        app.logger.exception("Unable to retrieve order")
        return jsonify({"error": "Unable to retrieve order"}), 503


if __name__ == "__main__":
    try:
        ensure_schema()
    except psycopg2.Error:
        app.logger.exception("Database initialization failed")
        raise

    app.run(host="0.0.0.0", port=5000)
