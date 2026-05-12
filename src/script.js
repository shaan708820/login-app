document.getElementById('loginForm').addEventListener('submit', function(e) {
    e.preventDefault();

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const button = document.querySelector('.login-btn');

    // Simple visual feedback
    button.textContent = 'Authenticating...';
    button.style.opacity = '0.7';
    button.disabled = true;

    // Simulate API Call
    setTimeout(() => {
        console.log('Login Attempt:', { email, password });
        
        // Final state (Mock)
        alert('Login successful!');
        button.textContent = 'Sign In';
        button.style.opacity = '1';
        button.disabled = false;
    }, 1500);
});