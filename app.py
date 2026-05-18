from flask import Flask, request, jsonify, session
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import yfinance as yf
import traceback

app = Flask(__name__, static_folder='src', static_url_path='')
app.secret_key = 'secure_wipro_session_key'
DB_FILE = 'database.db'

# Default Watchlist Stocks
DEFAULT_STOCKS = ['SUZLON', 'RELIANCE', 'TATAMOTORS', 'HDFCBANK', 'ZOMATO']

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, balance REAL DEFAULT 100000.0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS holdings (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT NOT NULL, symbol TEXT NOT NULL, shares INTEGER NOT NULL, avg_price REAL NOT NULL)''')
    conn.commit()
    conn.close()

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
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (email, password) VALUES (?, ?)', (data['email'], hashed_pw))
        conn.commit()
        return jsonify({"message": "Signup successful! You can now log in."}), 201
    except sqlite3.IntegrityError:
        return jsonify({"message": "This email is already registered."}), 400
    finally: conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT password FROM users WHERE email = ?', (data['email'],))
    user = cursor.fetchone()
    conn.close()
    if user and check_password_hash(user[0], data['password']):
        session['user'] = data['email']
        return jsonify({"message": "Login success"}), 200
    return jsonify({"message": "Invalid credentials"}), 401

@app.route('/api/watchlist')
def watchlist():
    if 'user' not in session: return jsonify({"error": "Unauthorized"}), 401
    # Fetch live prices for default stocks
    watchlist_data = []
    for sym in DEFAULT_STOCKS:
        price = get_live_data(sym)
        if price: watchlist_data.append({"symbol": sym, "price": price})
    return jsonify(watchlist_data)

@app.route('/api/portfolio')
def portfolio():
    if 'user' not in session: return jsonify({"error": "Unauthorized"}), 401
    email = session['user']
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE email = ?', (email,))
    balance = cursor.fetchone()[0]
    cursor.execute('SELECT symbol, shares, avg_price FROM holdings WHERE user_email = ?', (email,))
    
    holdings = []
    for row in cursor.fetchall():
        live_price = get_live_data(row[0]) or row[2] # Fallback to avg price if API fails
        holdings.append({"symbol": row[0], "shares": row[1], "avg_price": row[2], "current_price": live_price})
    conn.close()
    return jsonify({"balance": balance, "holdings": holdings})

@app.route('/api/chart/<symbol>')
def get_chart(symbol):
    try:
        ticker = f"{symbol.upper()}.NS"
        stock = yf.Ticker(ticker)
        # Fetch 1 month of historical data
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
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE email = ?', (email,))
    balance = cursor.fetchone()[0]
    cursor.execute('SELECT shares, avg_price FROM holdings WHERE user_email = ? AND symbol = ?', (email, symbol))
    holding = cursor.fetchone()
    current_shares = holding[0] if holding else 0
    avg_price = holding[1] if holding else 0
    
    if action == 'buy':
        if balance < total_cost: return jsonify({"message": "Insufficient funds"}), 400
        new_balance = balance - total_cost
        new_shares = current_shares + qty
        new_avg = ((current_shares * avg_price) + total_cost) / new_shares
        cursor.execute('UPDATE users SET balance = ? WHERE email = ?', (new_balance, email))
        if holding: cursor.execute('UPDATE holdings SET shares = ?, avg_price = ? WHERE user_email = ? AND symbol = ?', (new_shares, new_avg, email, symbol))
        else: cursor.execute('INSERT INTO holdings (user_email, symbol, shares, avg_price) VALUES (?, ?, ?, ?)', (email, symbol, qty, price))
            
    elif action == 'sell':
        if current_shares < qty: return jsonify({"message": "Not enough shares"}), 400
        new_balance = balance + total_cost
        new_shares = current_shares - qty
        cursor.execute('UPDATE users SET balance = ? WHERE email = ?', (new_balance, email))
        if new_shares == 0: cursor.execute('DELETE FROM holdings WHERE user_email = ? AND symbol = ?', (email, symbol))
        else: cursor.execute('UPDATE holdings SET shares = ? WHERE user_email = ? AND symbol = ?', (new_shares, email, symbol))

    conn.commit()
    conn.close()
    return jsonify({"message": f"Successfully {action}ed {qty} shares of {symbol} at ₹{price}!"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5005'))
    app.run(debug=True, host='0.0.0.0', port=port)