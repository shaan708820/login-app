from flask import Flask, request, jsonify, session
import os
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
import yfinance as yf
import traceback

app = Flask(__name__, static_folder='src', static_url_path='')
app.secret_key = 'secure_wipro_session_key'

# --- 3-TIER ARCHITECTURE: AWS RDS MYSQL CONFIGURATION ---
# The DB_HOST is injected automatically by Terraform's user_data script
DB_HOST = os.environ.get('DB_HOST', 'localhost') 
DB_USER = os.environ.get('DB_USER', 'admin')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'ShaanSecurePass123!')
DB_NAME = os.environ.get('DB_NAME', 'threetierdb')

# Default Watchlist Stocks
DEFAULT_STOCKS = ['SUZLON', 'RELIANCE', 'TATAMOTORS', 'HDFCBANK', 'ZOMATO']

def get_db_connection():
    """Establishes a connection to the AWS RDS instance"""
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True # Automatically commit transactions
    )

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # MySQL syntax updates: AUTO_INCREMENT (instead of AUTOINCREMENT) and standard data types
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY, 
            email VARCHAR(255) UNIQUE NOT NULL, 
            password VARCHAR(255) NOT NULL, 
            balance DOUBLE DEFAULT 100000.0)''')
            
        cursor.execute('''CREATE TABLE IF NOT EXISTS holdings (
            id INT AUTO_INCREMENT PRIMARY KEY, 
            user_email VARCHAR(255) NOT NULL, 
            symbol VARCHAR(50) NOT NULL, 
            shares INT NOT NULL, 
            avg_price DOUBLE NOT NULL)''')
    except Exception as e:
        print(f"Database initialization failed: {e}")
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()

# Initialize tables when the container boots up
init_db()

# --- Utility to fetch live NSE data ---
def get_live_data(symbol):
    try:
        ticker = f"{symbol.upper()}.NS"
        stock = yf.Ticker(ticker)
        # Fast fetch of the last available day
        hist = stock.history(period="1d")
        if hist.empty: return None
        return round(hist['Close'].iloc[-1], 2)
    except:
        return None

@app.route('/')
def index(): 
    from flask import send_from_directory
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    hashed_pw = generate_password_hash(data['password'])
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # MySQL uses %s instead of ? for variable substitution
        cursor.execute('INSERT INTO users (email, password) VALUES (%s, %s)', (data['email'], hashed_pw))
        return jsonify({"message": "Signup successful! You can now log in."}), 201
    except pymysql.err.IntegrityError:
        return jsonify({"message": "This email is already registered."}), 400
    finally: 
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT password FROM users WHERE email = %s', (data['email'],))
    user = cursor.fetchone()
    conn.close()
    
    if user and check_password_hash(user[0], data['password']):
        session['user'] = data['email']
        return jsonify({"message": "Login success"}), 200
    return jsonify({"message": "Invalid credentials"}), 401

@app.route('/api/watchlist')
def watchlist():
    if 'user' not in session: return jsonify({"error": "Unauthorized"}), 401
    watchlist_data = []
    for sym in DEFAULT_STOCKS:
        price = get_live_data(sym)
        if price: watchlist_data.append({"symbol": sym, "price": price})
    return jsonify(watchlist_data)

@app.route('/api/portfolio')
def portfolio():
    if 'user' not in session: return jsonify({"error": "Unauthorized"}), 401
    email = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT balance FROM users WHERE email = %s', (email,))
    balance_result = cursor.fetchone()
    balance = balance_result[0] if balance_result else 0
    
    cursor.execute('SELECT symbol, shares, avg_price FROM holdings WHERE user_email = %s', (email,))
    
    holdings = []
    for row in cursor.fetchall():
        live_price = get_live_data(row[0]) or row[2] 
        holdings.append({"symbol": row[0], "shares": row[1], "avg_price": row[2], "current_price": live_price})
    conn.close()
    return jsonify({"balance": balance, "holdings": holdings})

@app.route('/api/chart/<symbol>')
def get_chart(symbol):
    try:
        ticker = f"{symbol.upper()}.NS"
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        if hist.empty: return jsonify({"error": "Not found"}), 404
        
        prices = [round(p, 2) for p in hist['Close'].tolist()]
        dates = [d.strftime('%b %d') for d in hist.index.tolist()]
        current_price = prices[-1]
        
        return jsonify({"prices": prices, "dates": dates, "current": current_price})
    except Exception as e:
        return jsonify({"error": str(e)}), 404

@app.route('/api/trade', methods=['POST'])
def trade():
    if 'user' not in session: return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    email = session['user']
    symbol = data['symbol'].upper()
    qty = int(data['qty'])
    action = data['action']
    
    price = get_live_data(symbol)
    if not price or qty <= 0: return jsonify({"message": "Invalid trade or stock not found"}), 400
    total_cost = price * qty
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT balance FROM users WHERE email = %s', (email,))
    balance = cursor.fetchone()[0]
    
    cursor.execute('SELECT shares, avg_price FROM holdings WHERE user_email = %s AND symbol = %s', (email, symbol))
    holding = cursor.fetchone()
    current_shares = holding[0] if holding else 0
    avg_price = holding[1] if holding else 0
    
    if action == 'buy':
        if balance < total_cost: return jsonify({"message": "Insufficient funds"}), 400
        new_balance = balance - total_cost
        new_shares = current_shares + qty
        new_avg = ((current_shares * avg_price) + total_cost) / new_shares
        
        cursor.execute('UPDATE users SET balance = %s WHERE email = %s', (new_balance, email))
        if holding: 
            cursor.execute('UPDATE holdings SET shares = %s, avg_price = %s WHERE user_email = %s AND symbol = %s', (new_shares, new_avg, email, symbol))
        else: 
            cursor.execute('INSERT INTO holdings (user_email, symbol, shares, avg_price) VALUES (%s, %s, %s, %s)', (email, symbol, qty, price))
            
    elif action == 'sell':
        if current_shares < qty: return jsonify({"message": "Not enough shares"}), 400
        new_balance = balance + total_cost
        new_shares = current_shares - qty
        
        cursor.execute('UPDATE users SET balance = %s WHERE email = %s', (new_balance, email))
        if new_shares == 0: 
            cursor.execute('DELETE FROM holdings WHERE user_email = %s AND symbol = %s', (email, symbol))
        else: 
            cursor.execute('UPDATE holdings SET shares = %s WHERE user_email = %s AND symbol = %s', (new_shares, email, symbol))

    conn.close()
    return jsonify({"message": f"Successfully {action}ed {qty} shares of {symbol} at ₹{price}!"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5005'))
    app.run(debug=True, host='0.0.0.0', port=port)