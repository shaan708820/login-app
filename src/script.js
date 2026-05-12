// Toggle between Login and Signup forms
function toggleForms() {
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

// Handle Signup
document.getElementById('signupForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('signup-email').value;
    const password = document.getElementById('signup-password').value;

    const res = await fetch('/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });

    const data = await res.json();
    alert(data.message);

    if (res.ok) {
        document.getElementById('login-email').value = email;
        toggleForms(); // Switch to login form
    }
});

// Handle Login
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    const res = await fetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });

    if (res.ok) {
        loadGallery();
    } else {
        showErrorPage();
    }
});

// Render the Gallery
async function loadGallery() {
    const res = await fetch('/gallery-data');
    if (!res.ok) return showErrorPage();
    
    const data = await res.json();
    
    document.body.innerHTML = `
        <div class="gallery-wrapper">
            <h2>Random Photo Gallery</h2>
            <div class="gallery-grid">
                ${data.images.map((src, index) => `<img src="${src}" class="gallery-img" style="animation-delay: ${index * 0.1}s">`).join('')}
            </div>
            <button onclick="window.location.reload()" class="btn" style="margin-top: 30px; max-width: 200px;">Logout</button>
        </div>
    `;
    document.body.style.alignItems = 'flex-start';
}

// Render the Oops Page
function showErrorPage() {
    document.body.innerHTML = `
        <div class="error-box">
            <h1>OOps, Sign in first.</h1>
            <p style="margin-bottom: 20px;">You entered invalid credentials or do not have an account.</p>
            <button onclick="window.location.reload()" class="btn">Go to Signup / Login</button>
        </div>
    `;
}