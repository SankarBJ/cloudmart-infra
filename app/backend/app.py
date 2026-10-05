from flask import Flask, jsonify
import os
import psycopg2

app = Flask(__name__)

DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "cloudmart")
DB_USER = os.getenv("DB_USER", "cloudmart")
DB_PASSWORD = os.getenv("DB_PASSWORD", "cloudmart123")


def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


@app.route("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "cloudmart-backend"
    })


@app.route("/api/products")
def products():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, name, price, description FROM products ORDER BY id"
    )

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    products = [
        {
            "id": row[0],
            "name": row[1],
            "price": float(row[2]),
            "description": row[3]
        }
        for row in rows
    ]

    return jsonify(products)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
