from flask import Flask, request, jsonify, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os

# Initialize Flask to serve the 'src' folder
app = Flask(__name__, static_folder='src', static_url_path='')
app.secret_key = 'secure_wipro_session_key'

DB_FILE = 'database.db'

def init_db():
    """Forces database and table creation on startup."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Run immediately
init_db()

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    hashed_pw = generate_password_hash(password)
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, hashed_pw))
        conn.commit()
        return jsonify({"message": "Signup successful! You can now log in."}), 201
    except sqlite3.IntegrityError:
        return jsonify({"message": "This email is already registered."}), 400
    except Exception as e:
        return jsonify({"message": f"Server error: {str(e)}"}), 500
    finally:
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user[0], password):
            session['user'] = email
            return jsonify({"message": "Login success"}), 200
        else:
            return jsonify({"message": "Invalid credentials"}), 401
    finally:
        conn.close()

@app.route('/gallery-data')
def get_gallery():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Generate 12 random images
    images = [f"https://picsum.photos/400/300?random={i}" for i in range(1, 13)]
    return jsonify({"images": images})

if __name__ == '__main__':
    app.run(debug=True, port=5000)