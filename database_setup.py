import sqlite3
import random
from datetime import datetime, timedelta

def init_database(db_path='devops_guardian.db'):
    """Initialize DevOps Guardian database with extended schema"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Drop tables in dependency order
    cursor.execute('DROP TABLE IF EXISTS audit_log')
    cursor.execute('DROP TABLE IF EXISTS admin_sessions')
    cursor.execute('DROP TABLE IF EXISTS admins')
    cursor.execute('DROP TABLE IF EXISTS refund_requests')
    cursor.execute('DROP TABLE IF EXISTS order_items')
    cursor.execute('DROP TABLE IF EXISTS orders')
    cursor.execute('DROP TABLE IF EXISTS customers')
    cursor.execute('DROP TABLE IF EXISTS products')
    
    # Original tables (preserved)
    cursor.execute('''
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT,
            stock INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            total_amount REAL DEFAULT 0.0,
            shipping_address TEXT,
            tracking_number TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE order_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            unit_price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE refund_requests (
            refund_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            approved_by INTEGER,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (approved_by) REFERENCES admins(admin_id)
        )
    ''')
    
    # NEW: Admins table
    cursor.execute('''
        CREATE TABLE admins (
            admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL,
            otp_secret TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # NEW: Admin sessions
    cursor.execute('''
        CREATE TABLE admin_sessions (
            session_id TEXT PRIMARY KEY,
            admin_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            ip_address TEXT,
            FOREIGN KEY (admin_id) REFERENCES admins(admin_id)
        )
    ''')
    
    # NEW: Audit log
    cursor.execute('''
        CREATE TABLE audit_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT,
            status TEXT NOT NULL,
            risk_level TEXT,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES admins(admin_id)
        )
    ''')
    
    # Indexes for performance
    cursor.execute('CREATE INDEX idx_audit_admin ON audit_log(admin_id)')
    cursor.execute('CREATE INDEX idx_audit_timestamp ON audit_log(timestamp)')
    cursor.execute('CREATE INDEX idx_audit_action ON audit_log(action)')
    cursor.execute('CREATE INDEX idx_sessions_admin ON admin_sessions(admin_id)')
    cursor.execute('CREATE INDEX idx_sessions_expires ON admin_sessions(expires_at)')
    
    conn.commit()
    print("✓ Database schema created")
    
    # Seed data
    seed_original_data(cursor)
    seed_admin_data(cursor)
    
    conn.commit()
    conn.close()
    print("✓ Database initialized successfully")


def seed_original_data(cursor):
    """Seed original business data"""
    # Customers
    customers = [
        ('Alice Johnson', 'alice@example.com', '555-0101'),
        ('Bob Smith', 'bob@example.com', '555-0102'),
        ('Charlie Brown', 'charlie@example.com', '555-0103'),
        ('Diana Prince', 'diana@example.com', '555-0104'),
        ('Eve Adams', 'eve@example.com', '555-0105'),
    ]
    cursor.executemany('INSERT INTO customers (name, email, phone) VALUES (?, ?, ?)', customers)
    
    # Products
    products = [
        ('Laptop', 999.99, 'Electronics', 50),
        ('Mouse', 29.99, 'Electronics', 200),
        ('Keyboard', 79.99, 'Electronics', 150),
        ('Monitor', 299.99, 'Electronics', 75),
        ('Desk Chair', 199.99, 'Furniture', 30),
        ('Desk Lamp', 39.99, 'Furniture', 100),
        ('Notebook', 4.99, 'Stationery', 500),
        ('Pen Set', 14.99, 'Stationery', 300),
        ('Backpack', 59.99, 'Accessories', 80),
        ('Water Bottle', 19.99, 'Accessories', 150),
    ]
    cursor.executemany('INSERT INTO products (name, price, category, stock) VALUES (?, ?, ?, ?)', products)
    
    # Orders and items
    statuses = ['pending', 'shipped', 'delivered', 'cancelled']
    addresses = [
        '123 Main St, City A',
        '456 Oak Ave, City B',
        '789 Pine Rd, City C',
        '321 Elm St, City D',
        '654 Maple Dr, City E',
    ]
    
    for customer_id in range(1, 6):
        num_orders = random.randint(1, 3)
        for _ in range(num_orders):
            status = random.choice(statuses)
            tracking = f'TRK{random.randint(100000, 999999)}' if status in ['shipped', 'delivered'] else None
            
            cursor.execute('''
                INSERT INTO orders (customer_id, status, shipping_address, tracking_number)
                VALUES (?, ?, ?, ?)
            ''', (customer_id, status, addresses[customer_id - 1], tracking))
            
            order_id = cursor.lastrowid
            
            # Add 1-3 items per order
            num_items = random.randint(1, 3)
            total = 0.0
            for _ in range(num_items):
                product_id = random.randint(1, 10)
                quantity = random.randint(1, 2)
                cursor.execute('SELECT price FROM products WHERE product_id = ?', (product_id,))
                price = cursor.fetchone()[0]
                
                cursor.execute('''
                    INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                    VALUES (?, ?, ?, ?)
                ''', (order_id, product_id, quantity, price))
                
                total += price * quantity
            
            cursor.execute('UPDATE orders SET total_amount = ? WHERE order_id = ?', (total, order_id))
    
    # One refund request
    cursor.execute('''
        INSERT INTO refund_requests (order_id, amount, reason, status)
        VALUES (1, 29.99, 'Product arrived damaged', 'pending')
    ''')
    
    print("✓ Original business data seeded")


def seed_admin_data(cursor):
    """Seed admin users with TOTP secrets"""
    import pyotp
    
    admins = [
        ('admin', 'supervisor', pyotp.random_base32(), 'admin@devops.local'),
        ('devops1', 'engineer', pyotp.random_base32(), 'devops1@devops.local'),
        ('devops2', 'engineer', pyotp.random_base32(), 'devops2@devops.local'),
        ('readonly', 'viewer', pyotp.random_base32(), 'readonly@devops.local'),
    ]
    
    cursor.executemany('''
        INSERT INTO admins (username, role, otp_secret, email)
        VALUES (?, ?, ?, ?)
    ''', admins)
    
    # Sample audit entries
    cursor.execute('''
        INSERT INTO audit_log (admin_id, action, resource_type, resource_id, status, risk_level, details)
        VALUES (1, 'pod_restart', 'kubernetes', 'nginx-deployment-abc123', 'success', 'medium', '{"namespace": "production", "pod": "nginx-deployment-abc123"}')
    ''')
    
    cursor.execute('''
        INSERT INTO audit_log (admin_id, action, resource_type, resource_id, status, risk_level, details)
        VALUES (2, 'sync_application', 'argocd', 'payment-service', 'success', 'low', '{"application": "payment-service", "revision": "v1.2.3"}')
    ''')
    
    print("✓ Admin data seeded")
    print("\nAdmin credentials (TOTP secrets for testing):")
    cursor.execute('SELECT username, role, otp_secret FROM admins')
    for row in cursor.fetchall():
        print(f"  {row[0]:12} [{row[1]:10}] Secret: {row[2]}")


if __name__ == '__main__':
    init_database()
