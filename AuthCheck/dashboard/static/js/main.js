// Simple confirmation for sensitive actions
document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide flash messages after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
    
    // Confirm password changes
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const tokenField = form.querySelector('input[name="discord_token"]');
            if (tokenField && tokenField.value.length < 50) {
                if (!confirm('Discord token looks unusual. Continue anyway?')) {
                    e.preventDefault();
                }
            }
        });
    });
});