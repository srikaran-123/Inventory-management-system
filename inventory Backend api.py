# ============================================================
#  INVENTORY MANAGEMENT SYSTEM — Flask Backend API
#  Table column: Productname (matches your MySQL table)
#  Run: python app.py
#  URL: http://localhost:5000
# ============================================================

from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import traceback
from dotenv import load_dotenv
import os
load_dotenv()

app = Flask(__name__)
CORS(app)

# ============================================================
# DATABASE CONNECTION
# Change password="" to your MySQL password if you have one
# ============================================================

def get_db():
    try:
        conn = mysql.connector.connect(
            host     = os.getenv('DB_HOST'),
            database = os.getenv('DB_NAME'),
            user     = os.getenv('DB_USER'),
            password = os.getenv('DB_PASSWORD')         # ← your MySQL password here (empty if none)
        )
        return conn
    except Error as e:
        print(f"❌ DB Connection Error: {e}")
        return None


def run_query(sql, params=None, fetch=True):
    conn = get_db()
    if not conn:
        print("❌ Cannot connect to database!")
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        if fetch:
            result = cursor.fetchall()
        else:
            conn.commit()
            result = cursor.rowcount
        cursor.close()
        conn.close()
        return result
    except Error as e:
        print(f"❌ SQL Error: {e}")
        traceback.print_exc()
        conn.close()
        return None


# ============================================================
# HOME
# ============================================================

@app.route('/')
def home():
    return jsonify({
        "message"  : "Inventory Management API - Running!",
        "endpoints": {
            "products"  : "/api/products",
            "inventory" : "/api/inventory",
            "suppliers" : "/api/suppliers",
            "orders"    : "/api/orders",
            "dashboard" : "/api/dashboard"
        }
    })


# ============================================================
# PRODUCTS — /api/products
# ============================================================

# GET all products
@app.route('/api/products', methods=['GET'])
def get_all_products():
    try:
        sql    = "SELECT * FROM products ORDER BY Productname"
        result = run_query(sql)
        if result is None:
            return jsonify({"error": "Database error"}), 500
        return jsonify({"success": True, "count": len(result), "data": result})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# GET one product by ID
@app.route('/api/products/<int:id>', methods=['GET'])
def get_product(id):
    try:
        sql = """
            SELECT p.id, p.Productname AS name, p.HSNcode, p.price, p.category,
                   COALESCE(i.quantity, 0) AS stock
            FROM products p
            LEFT JOIN inventory i ON i.product_id = p.id
            WHERE p.id = %s
        """
        result = run_query(sql, (id,))
        if not result:
            return jsonify({"error": f"Product ID {id} not found"}), 404
        return jsonify({"success": True, "data": result[0]})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# GET search product by name
@app.route('/api/products/search/<string:keyword>', methods=['GET'])
def search_products(keyword):
    try:
        sql    = "SELECT * FROM products WHERE Productname LIKE %s"
        result = run_query(sql, (f"%{keyword}%",))
        return jsonify({"success": True, "count": len(result), "data": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# POST add new product
@app.route('/api/products', methods=['POST'])
def add_product():
    try:
        data = request.get_json()
        if not data.get('Productname'):
            return jsonify({"error": "'Productname' is required"}), 400
        if not data.get('HSNcode'):
            return jsonify({"error": "'HSNcode' is required"}), 400
        if not data.get('price'):
            return jsonify({"error": "'price' is required"}), 400

        sql  = "INSERT INTO products (Productname, HSNcode, price, category) VALUES (%s, %s, %s, %s)"
        rows = run_query(sql, (
            data['Productname'],
            data['HSNcode'],
            float(data['price']),
            data.get('category', '')
        ), fetch=False)

        if rows:
            # Auto create inventory row with 0 stock
            new_p = run_query("SELECT id FROM products WHERE HSNcode = %s", (data['HSNcode'],))
            if new_p:
                run_query(
                    "INSERT INTO inventory (product_id, quantity) VALUES (%s, 0)",
                    (new_p[0]['id'],), fetch=False
                )
            return jsonify({"success": True, "message": f"Product '{data['Productname']}' added!"}), 201
        else:
            return jsonify({"error": "Failed. HSNcode may already exist."}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# PUT update product
@app.route('/api/products/<int:id>', methods=['PUT'])
def update_product(id):
    try:
        data = request.get_json()
        sql  = "UPDATE products SET Productname=%s, HSNcode=%s, price=%s, category=%s WHERE id=%s"
        rows = run_query(sql, (
            data.get('Productname'),
            data.get('HSNcode'),
            data.get('price'),
            data.get('category'),
            id
        ), fetch=False)
        if rows:
            return jsonify({"success": True, "message": f"Product ID {id} updated"})
        else:
            return jsonify({"error": f"Product ID {id} not found"}), 404
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# DELETE product
@app.route('/api/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    try:
        rows = run_query("DELETE FROM products WHERE id=%s", (id,), fetch=False)
        if rows:
            return jsonify({"success": True, "message": f"Product ID {id} deleted"})
        else:
            return jsonify({"error": f"Product ID {id} not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# INVENTORY — /api/inventory
# ============================================================

# GET all inventory
@app.route('/api/inventory', methods=['GET'])
def get_all_inventory():
    try:
        sql = """
            SELECT i.id, i.product_id, p.Productname AS product_name,
                   p.HSNcode, p.category, i.quantity, i.updated_at,
                   CASE
                       WHEN i.quantity = 0  THEN 'OUT OF STOCK'
                       WHEN i.quantity < 10 THEN 'LOW STOCK'
                       ELSE 'IN STOCK'
                   END AS stock_status
            FROM inventory i
            JOIN products p ON p.id = i.product_id
            ORDER BY p.Productname
        """
        result = run_query(sql)
        if result is None:
            return jsonify({"error": "Database error"}), 500
        return jsonify({"success": True, "count": len(result), "data": result})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# GET low stock
@app.route('/api/inventory/low-stock', methods=['GET'])
def get_low_stock():
    try:
        sql = """
            SELECT p.Productname AS product_name, p.HSNcode,
                   p.category, i.quantity, i.product_id
            FROM inventory i
            JOIN products p ON p.id = i.product_id
            WHERE i.quantity < 10
            ORDER BY i.quantity ASC
        """
        result = run_query(sql)
        return jsonify({"success": True, "alert_count": len(result), "data": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# GET stock for one product
@app.route('/api/inventory/<int:product_id>', methods=['GET'])
def get_stock(product_id):
    try:
        sql = """
            SELECT p.Productname AS name, p.HSNcode, i.quantity, i.updated_at
            FROM inventory i JOIN products p ON p.id = i.product_id
            WHERE i.product_id = %s
        """
        result = run_query(sql, (product_id,))
        if not result:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"success": True, "data": result[0]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# PUT update stock
@app.route('/api/inventory/<int:product_id>', methods=['PUT'])
def update_stock(product_id):
    try:
        data = request.get_json()
        qty  = data.get('quantity')
        if qty is None:
            return jsonify({"error": "'quantity' is required"}), 400
        rows = run_query(
            "UPDATE inventory SET quantity=%s, updated_at=NOW() WHERE product_id=%s",
            (qty, product_id), fetch=False
        )
        if rows:
            return jsonify({"success": True, "message": f"Stock updated to {qty}"})
        else:
            return jsonify({"error": "Product not found in inventory"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# SUPPLIERS — /api/suppliers
# ============================================================

@app.route('/api/suppliers', methods=['GET'])
def get_all_suppliers():
    result = run_query("SELECT * FROM suppliers ORDER BY name")
    if result is None:
        return jsonify({"error": "Database error"}), 500
    return jsonify({"success": True, "count": len(result), "data": result})


@app.route('/api/suppliers/<int:id>', methods=['GET'])
def get_supplier(id):
    result = run_query("SELECT * FROM suppliers WHERE id=%s", (id,))
    if not result:
        return jsonify({"error": f"Supplier ID {id} not found"}), 404
    return jsonify({"success": True, "data": result[0]})


@app.route('/api/suppliers', methods=['POST'])
def add_supplier():
    try:
        data = request.get_json()
        if not data.get('name'):
            return jsonify({"error": "'name' is required"}), 400
        rows = run_query(
            "INSERT INTO suppliers (name, email, phone) VALUES (%s, %s, %s)",
            (data['name'], data.get('email',''), data.get('phone','')),
            fetch=False
        )
        if rows:
            return jsonify({"success": True, "message": f"Supplier '{data['name']}' added!"}), 201
        else:
            return jsonify({"error": "Failed to add supplier"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/suppliers/<int:id>', methods=['PUT'])
def update_supplier(id):
    data = request.get_json()
    rows = run_query(
        "UPDATE suppliers SET name=%s, email=%s, phone=%s WHERE id=%s",
        (data.get('name'), data.get('email'), data.get('phone'), id),
        fetch=False
    )
    if rows:
        return jsonify({"success": True, "message": f"Supplier ID {id} updated"})
    else:
        return jsonify({"error": f"Supplier ID {id} not found"}), 404


@app.route('/api/suppliers/<int:id>', methods=['DELETE'])
def delete_supplier(id):
    rows = run_query("DELETE FROM suppliers WHERE id=%s", (id,), fetch=False)
    if rows:
        return jsonify({"success": True, "message": f"Supplier ID {id} deleted"})
    else:
        return jsonify({"error": f"Supplier ID {id} not found"}), 404


# ============================================================
# ORDERS — /api/orders
# ============================================================

@app.route('/api/orders', methods=['GET'])
def get_all_orders():
    try:
        sql = """
            SELECT o.id, p.Productname AS product_name, p.HSNcode,
                   o.quantity, o.type, o.created_at
            FROM orders o JOIN products p ON p.id = o.product_id
            ORDER BY o.created_at DESC
        """
        result = run_query(sql)
        if result is None:
            return jsonify({"error": "Database error"}), 500
        return jsonify({"success": True, "count": len(result), "data": result})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/orders/type/<string:order_type>', methods=['GET'])
def get_orders_by_type(order_type):
    order_type = order_type.upper()
    if order_type not in ['IN','OUT']:
        return jsonify({"error": "Use IN or OUT"}), 400
    sql = """
        SELECT o.id, p.Productname AS product_name, p.HSNcode,
               o.quantity, o.type, o.created_at
        FROM orders o JOIN products p ON p.id = o.product_id
        WHERE o.type = %s ORDER BY o.created_at DESC
    """
    result = run_query(sql, (order_type,))
    return jsonify({"success": True, "count": len(result), "data": result})


@app.route('/api/orders/product/<int:product_id>', methods=['GET'])
def get_orders_by_product(product_id):
    sql = """
        SELECT o.id, p.Productname AS product_name,
               o.quantity, o.type, o.created_at
        FROM orders o JOIN products p ON p.id = o.product_id
        WHERE o.product_id = %s ORDER BY o.created_at DESC
    """
    result = run_query(sql, (product_id,))
    return jsonify({"success": True, "count": len(result), "data": result})


@app.route('/api/orders', methods=['POST'])
def add_order():
    try:
        data = request.get_json()
        for field in ['product_id','quantity','type']:
            if field not in data:
                return jsonify({"error": f"'{field}' is required"}), 400

        order_type = data['type'].upper()
        if order_type not in ['IN','OUT']:
            return jsonify({"error": "type must be IN or OUT"}), 400

        quantity   = int(data['quantity'])
        product_id = int(data['product_id'])

        if quantity <= 0:
            return jsonify({"error": "quantity must be greater than 0"}), 400

        # For OUT — check stock
        if order_type == 'OUT':
            stock = run_query(
                "SELECT quantity FROM inventory WHERE product_id=%s", (product_id,)
            )
            if not stock:
                return jsonify({"error": "Product not found in inventory"}), 404
            current = stock[0]['quantity']
            if current < quantity:
                return jsonify({
                    "error"        : "Not enough stock!",
                    "current_stock": current,
                    "requested"    : quantity
                }), 400

        # Insert order
        run_query(
            "INSERT INTO orders (product_id, quantity, type) VALUES (%s, %s, %s)",
            (product_id, quantity, order_type), fetch=False
        )

        # Update inventory
        if order_type == 'IN':
            run_query(
                "UPDATE inventory SET quantity=quantity+%s, updated_at=NOW() WHERE product_id=%s",
                (quantity, product_id), fetch=False
            )
        else:
            run_query(
                "UPDATE inventory SET quantity=quantity-%s, updated_at=NOW() WHERE product_id=%s",
                (quantity, product_id), fetch=False
            )

        action = "added to" if order_type == 'IN' else "removed from"
        return jsonify({
            "success": True,
            "message": f"{quantity} units {action} inventory"
        }), 201

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============================================================
# DASHBOARD — /api/dashboard
# ============================================================

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    try:
        total_products  = run_query("SELECT COUNT(*) AS c FROM products")[0]['c']
        total_suppliers = run_query("SELECT COUNT(*) AS c FROM suppliers")[0]['c']
        total_stock     = run_query("SELECT COALESCE(SUM(quantity),0) AS c FROM inventory")[0]['c']
        out_of_stock    = run_query("SELECT COUNT(*) AS c FROM inventory WHERE quantity=0")[0]['c']
        low_stock       = run_query("SELECT COUNT(*) AS c FROM inventory WHERE quantity>0 AND quantity<10")[0]['c']
        total_orders    = run_query("SELECT COUNT(*) AS c FROM orders")[0]['c']
        stock_in        = run_query("SELECT COALESCE(SUM(quantity),0) AS c FROM orders WHERE type='IN'")[0]['c']
        stock_out       = run_query("SELECT COALESCE(SUM(quantity),0) AS c FROM orders WHERE type='OUT'")[0]['c']
        total_value     = run_query("""
            SELECT COALESCE(SUM(i.quantity * p.price),0) AS c
            FROM inventory i JOIN products p ON p.id=i.product_id
        """)[0]['c']

        low_stock_list = run_query("""
            SELECT p.Productname AS name, p.HSNcode, i.quantity
            FROM inventory i JOIN products p ON p.id=i.product_id
            WHERE i.quantity < 10 ORDER BY i.quantity ASC LIMIT 5
        """)

        top_products = run_query("""
            SELECT p.Productname AS name, p.HSNcode,
                   SUM(o.quantity) AS total_sold
            FROM orders o JOIN products p ON p.id=o.product_id
            WHERE o.type='OUT'
            GROUP BY p.id, p.Productname, p.HSNcode
            ORDER BY total_sold DESC LIMIT 5
        """)

        return jsonify({
            "success": True,
            "data": {
                "total_products" : total_products,
                "total_suppliers": total_suppliers,
                "total_stock"    : int(total_stock),
                "out_of_stock"   : out_of_stock,
                "low_stock"      : low_stock,
                "total_orders"   : total_orders,
                "total_stock_in" : int(stock_in),
                "total_stock_out": int(stock_out),
                "total_value"    : float(total_value),
                "low_stock_items": low_stock_list,
                "top_products"   : top_products
            }
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Route not found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405


# ============================================================
# RUN
# ============================================================

if __name__ == '__main__':
    print("=" * 50)
    print("  INVENTORY MANAGEMENT API")
    print("  URL: http://localhost:5000")
    print("  Press Ctrl+C to stop")
    print("=" * 50)
    app.run(debug=True, port=5000)