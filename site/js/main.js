// ROI Calculator
function calculateROI() {
    // Get input values
    const numControllers = parseInt(document.getElementById('num-controllers').value) || 0;
    const hourlyRate = parseInt(document.getElementById('hourly-rate').value) || 100;

    // Constants
    const MINUTES_PER_CONTROLLER_MANUAL = 20; // Average time to write tests manually
    const MINUTES_PER_CONTROLLER_AI = 0.18; // 8 min / 44 controllers
    const COST_PER_CONTROLLER = 0.05; // $2.23 / 44 controllers

    // Calculate times
    const manualTimeMinutes = numControllers * MINUTES_PER_CONTROLLER_MANUAL;
    const automatedTimeMinutes = numControllers * MINUTES_PER_CONTROLLER_AI;
    const timeSavedMinutes = manualTimeMinutes - automatedTimeMinutes;

    // Calculate costs
    const manualCostDollars = (manualTimeMinutes / 60) * hourlyRate;
    const toolCostDollars = numControllers * COST_PER_CONTROLLER;
    const costSavedDollars = manualCostDollars - toolCostDollars;
    const netROI = costSavedDollars - toolCostDollars;

    // Format times
    function formatTime(minutes) {
        if (minutes < 60) {
            return `${Math.round(minutes)} min`;
        } else {
            const hours = Math.floor(minutes / 60);
            const mins = Math.round(minutes % 60);
            return `${hours}h ${mins}m`;
        }
    }

    // Update results
    document.getElementById('manual-time').textContent = formatTime(manualTimeMinutes);
    document.getElementById('automated-time').textContent = formatTime(automatedTimeMinutes);
    document.getElementById('time-saved').textContent = formatTime(timeSavedMinutes);
    document.getElementById('cost-saved').textContent = `$${manualCostDollars.toFixed(2)}`;
    document.getElementById('tool-cost').textContent = `$${toolCostDollars.toFixed(2)}`;
    document.getElementById('net-roi').textContent = `$${costSavedDollars.toFixed(2)}`;
}

// Contact Form Handler
document.getElementById('contact-form').addEventListener('submit', function(e) {
    e.preventDefault();

    // Get form values
    const formData = {
        name: document.getElementById('name').value,
        email: document.getElementById('email').value,
        company: document.getElementById('company').value,
        interest: document.getElementById('interest').value,
        message: document.getElementById('message').value
    };

    // Create mailto link
    const subject = encodeURIComponent(`.NET Test Generator: ${formData.interest}`);
    const body = encodeURIComponent(
        `Name: ${formData.name}\n` +
        `Email: ${formData.email}\n` +
        `Company: ${formData.company}\n` +
        `Interest: ${formData.interest}\n\n` +
        `Message:\n${formData.message}`
    );

    // Open email client
    window.location.href = `mailto:ted@servicevision.ai?subject=${subject}&body=${body}`;

    // Show success message
    alert('Opening your email client... If it doesn\'t open automatically, please email ted@servicevision.ai');
});

// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Initialize ROI Calculator with default values
window.addEventListener('DOMContentLoaded', function() {
    calculateROI();
});

// Auto-calculate on input change
document.getElementById('num-controllers').addEventListener('input', calculateROI);
document.getElementById('hourly-rate').addEventListener('input', calculateROI);
