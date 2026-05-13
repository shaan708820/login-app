let currentUserEmail = '';
// ==========================================
// GLOBAL VARIABLES
// ==========================================
let chartInstance = null;
let currentActiveStock = 'SUZLON'; // Default stock on login

// ==========================================
// 1. UI TOGGLES & MODALS
// ==========================================
function toggleForms(e) {
    if(e) e.preventDefault();
    const loginForm = document.getElementById('loginForm');
    const signupForm = document.getElementById('signupForm');
    
    if (loginForm.style.display === 'none') {
        loginForm.style.display = 'block';
        signupForm.style.display = 'none';
    } else {
        loginForm.style.display = 'none';
        signupForm.style.display = 'block';
    }
}

function closeModal() {
    document.getElementById('successModal').classList.remove('active');
    toggleForms(); // Switch back to login form after success
}

// ==========================================
// 2. CRASH-PROOF AUTHENTICATION
// ==========================================

// Handle Signup
document.getElementById('signupForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('signup-email').value;
    const password = document.getElementById('signup-password').value;
    const btn = e.target.querySelector('button');

    btn.textContent = 'Registering...';
    btn.disabled = true;

    try {
        const res = await fetch('/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await res.json();
        
        btn.textContent = 'Sign Up';
        btn.disabled = false;

        if (res.ok) {
            document.getElementById('modal-message').textContent = data.message;
            document.getElementById('successModal').classList.add('active');
            
            document.getElementById('login-email').value = email;
            document.getElementById('signupForm').reset();
        } else {
            alert(data.message);
        }
    } catch (error) {
        btn.textContent = 'Sign Up';
        btn.disabled = false;
        alert("🚨 Server Crash! Please check your Python terminal to see the error. (Did you delete the old database.db?)");
        console.error("Signup Error:", error);
    }
});

// Handle Login
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const btn = e.target.querySelector('button');

    btn.textContent = 'Logging in...';
    btn.disabled = true;

    try {
        const res = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        if (!res.ok && res.status === 500) {
            throw new Error("Server 500 Error");
        }

        const data = await res.json();

        btn.textContent = 'Login';
        btn.disabled = false;

        if (res.ok) {
            // Hide Auth, Show Dashboard
            currentUserEmail = email;
            document.getElementById('user-email-display').innerText = currentUserEmail;
            document.getElementById('auth-container').style.display = 'none';
            document.getElementById('dashboard').style.display = 'block';
            document.body.style.alignItems = 'flex-start';
            
            // Initialize Dashboard Data
            loadDashboard();
            loadChart(currentActiveStock);
        } else {
            alert(data.message || "Invalid credentials");
        }
    } catch (error) {
        btn.textContent = 'Login';
        btn.disabled = false;
        alert("🚨 Server Crash! Please check your Python terminal to see the error. (Did you delete the old database.db?)");
        console.error("Login Error:", error);
    }
});


// ==========================================
// 3. TRADING DASHBOARD LOGIC
// ==========================================

// Load Portfolio & Wallet
async function loadDashboard() {
    const res = await fetch('/api/portfolio');
    if (!res.ok) {
        alert("Session expired. Please log in again.");
        window.location.reload();
        return;
    }
    const data = await res.json();
    
    // Update Wallet Balance
    document.getElementById('wallet-balance').innerText = data.balance.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2});
    
    // Render Holdings
    const container = document.getElementById('holdings-container');
    container.innerHTML = '';
    let totalPnl = 0;

    if (data.holdings.length === 0) {
        container.innerHTML = '<p style="color:#64748b; text-align:center; padding: 20px 0;">No active positions.</p>';
    }

    data.holdings.forEach(item => {
        const invested = item.shares * item.avg_price;
        const currentValue = item.shares * item.current_price;
        const pnl = currentValue - invested;
        totalPnl += pnl;

        const pnlClass = pnl >= 0 ? 'profit' : 'loss';
        
        container.innerHTML += `
            <div class="holding-item" onclick="loadChart('${item.symbol}')">
                <div>
                    <div class="holding-symbol">${item.symbol}</div>
                    <div class="holding-details">${item.shares} Qty | Avg ₹${item.avg_price.toFixed(2)}</div>
                </div>
                <div>
                    <div class="price-tag">₹${item.current_price.toFixed(2)}</div>
                    <div class="${pnlClass}" style="text-align: right; font-size: 0.85rem; margin-top: 4px;">
                        ${pnl >= 0 ? '+' : ''}₹${pnl.toFixed(2)}
                    </div>
                </div>
            </div>
        `;
    });

    // Update Total P&L
    const pnlEl = document.getElementById('total-pnl');
    pnlEl.innerText = `${totalPnl >= 0 ? '+' : ''}₹${totalPnl.toFixed(2)}`;
    pnlEl.className = totalPnl >= 0 ? 'profit' : 'loss';

    // Refresh Watchlist Sidebar
    loadWatchlist();
}

// Load Default Watchlist
async function loadWatchlist() {
    const res = await fetch('/api/watchlist');
    const stocks = await res.json();
    const container = document.getElementById('watchlist-container');
    container.innerHTML = '';

    stocks.forEach(stock => {
        container.innerHTML += `
            <div class="holding-item" onclick="loadChart('${stock.symbol}')" style="cursor: pointer;">
                <div class="holding-symbol">${stock.symbol}</div>
                <div class="price-tag">₹${stock.price.toFixed(2)}</div>
            </div>
        `;
    });
}

// Search Bar Logic
function searchStock() {
    const query = document.getElementById('stock-search').value.toUpperCase().trim();
    if (!query) return;
    loadChart(query);
    document.getElementById('stock-search').value = ''; // Clear search bar
}

// Fetch and Render Chart Data
async function loadChart(symbol) {
    document.getElementById('current-stock-name').innerText = "Fetching real-time data...";
    
    const res = await fetch(`/api/chart/${symbol}`);
    const data = await res.json();
    
    if (!res.ok) {
        alert("Stock not found on NSE. Make sure you use the correct symbol (e.g., WIPRO, TCS).");
        document.getElementById('current-stock-name').innerText = currentActiveStock + " (NSE)";
        return;
    }
    
    currentActiveStock = symbol;
    document.getElementById('current-stock-name').innerText = symbol + " (NSE)";
    document.getElementById('current-stock-price').innerText = `₹${data.current.toFixed(2)}`;
    document.getElementById('trade-symbol').innerText = symbol;

    renderChart(data.prices, data.dates);
}

// Draw Chart.js Graph
function renderChart(priceHistory, dates) {
    const ctx = document.getElementById('stockChart').getContext('2d');
    const isProfit = priceHistory[priceHistory.length - 1] >= priceHistory[0];
    const lineColor = isProfit ? '#10b981' : '#ef4444'; // Green if up, Red if down

    if (chartInstance) {
        chartInstance.destroy(); // Destroy old chart before drawing new one
    }

    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: 'Close Price',
                data: priceHistory,
                borderColor: lineColor,
                backgroundColor: isProfit ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.1,
                pointRadius: 0,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false, // Allows chart to stretch to container height
            plugins: { 
                legend: { display: false } 
            },
            scales: {
                x: { display: false },
                y: { display: true, position: 'right' }
            },
            interaction: { 
                mode: 'index', 
                intersect: false 
            }
        }
    });
}

// Buy and Sell Logic
async function executeTrade(action) {
    const qty = document.getElementById('trade-qty').value;
    const btn = event.target;
    
    if (qty <= 0) {
        alert("Please enter a valid quantity greater than 0.");
        return;
    }

    btn.disabled = true; // Prevent double clicking
    const originalText = btn.textContent;
    btn.textContent = 'Processing...';
    
    try {
        const res = await fetch('/api/trade', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol: currentActiveStock, qty: qty, action: action })
        });

        const data = await res.json();
        alert(data.message);
        
        if (res.ok) {
            loadDashboard(); // Refresh portfolio numbers and wallet after successful trade
        }
    } catch(error) {
        alert("Transaction failed due to server error.");
        console.error(error);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}
// Profile Menu Logic
function toggleProfileMenu() {
    document.getElementById('profileMenu').classList.toggle('active');
}

function openPasswordModal() {
    alert("Change password functionality coming soon!");
    toggleProfileMenu(); // Close the menu
}

function logoutUser() {
    // In a real app, you'd send a fetch request to a /logout backend route to clear the session
    window.location.reload(); 
}

// Close the dropdown if the user clicks anywhere outside of it
window.onclick = function(event) {
    if (!event.target.matches('.profile-icon')) {
        const menu = document.getElementById('profileMenu');
        if (menu && menu.classList.contains('active')) {
            menu.classList.remove('active');
        }
    }
}