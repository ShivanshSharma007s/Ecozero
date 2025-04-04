// Mobile Menu Toggle
function toggleMenu() {
    const nav = document.getElementById('mobileNav');
    nav.classList.toggle('active');
    
    // Close when clicking outside
    if (nav.classList.contains('active')) {
        document.addEventListener('click', function closeMenu(e) {
            if (!nav.contains(e.target) && e.target !== document.querySelector('.mobile-menu-btn')) {
                nav.classList.remove('active');
                document.removeEventListener('click', closeMenu);
            }
        });
    }
}

// Viewport Height Adjustment (for mobile browsers)
function adjustViewport() {
    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--vh', `${vh}px`);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    adjustViewport();
    
    // Prevent form submission
    document.getElementById('calcForm').addEventListener('submit', (e) => {
        e.preventDefault();
    });
    
    // Initialize range values
    document.querySelectorAll('input[type="range"]').forEach(range => {
        updateValue(range);
    });
});

window.addEventListener('resize', adjustViewport);

// Update range input display value
function updateValue(input) {
    input.parentElement.querySelector('.range-value').textContent = input.value;
}

// Show tooltip modal
function showTip(type) {
    const tips = {
        energy: "Average office building uses ~20 kWh/sqft/year. Residential buildings typically use 10-15 kWh/sqft/year.",
        water: "Includes all building water usage including irrigation, restrooms, and HVAC systems. Average is about 20 gallons/sqft/year."
    };
    
    document.getElementById('tipContent').innerHTML = `
        <h3>${type.charAt(0).toUpperCase() + type.slice(1)} Information</h3>
        <p>${tips[type]}</p>
    `;
    
    document.getElementById('tipModal').classList.add('active');
}

// Hide tooltip modal
function hideTip() {
    document.getElementById('tipModal').classList.remove('active');
}

// Calculate emissions
async function calculateEmissions() {
    const form = document.getElementById('calcForm');
    const btn = document.querySelector('.calculate-btn');
    const spinner = btn.querySelector('.spinner');
    const resultSection = document.getElementById('resultSection');
    
    // Validate inputs
    const inputs = form.querySelectorAll('input[required], select[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value) {
            input.style.borderColor = 'red';
            isValid = false;
        } else {
            input.style.borderColor = '#ddd';
        }
    });
    
    if (!isValid) {
        showError('Please fill in all required fields');
        return;
    }
    
    // Show loading state
    btn.disabled = true;
    spinner.classList.remove('hidden');
    resultSection.classList.add('hidden');
    
    try {
        const response = await fetch('/calculate', {
            method: 'POST',
            body: new FormData(form)
        });
        
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        displayResults(data);
        
    } catch (error) {
        showError(error.message);
    } finally {
        btn.disabled = false;
        spinner.classList.add('hidden');
    }
}

// Display results
function displayResults(data) {
    const resultSection = document.getElementById('resultSection');
    
    resultSection.innerHTML = `
        <div class="result-header">
            <h2><i class="fas fa-chart-pie"></i> Your Carbon Analysis</h2>
            <div class="emission-badge">
                ${data.emissions} tons CO₂/year
                <div class="comparison">${data.comparison}</div>
            </div>
        </div>

        <div class="recommendations">
            <h3><i class="fas fa-road"></i> Net Zero Roadmap</h3>
            ${data.recommendations.map((rec, index) => `
                <div class="recommendation-card">
                    <div class="rec-header" onclick="toggleRecommendation(${index})">
                        <span>${rec.title}</span>
                        <i class="fas fa-chevron-down"></i>
                    </div>
                    <div class="rec-content">
                        <p>${rec.description}</p>
                        <div class="rec-meta">
                            <span class="impact-tag ${rec.cost.toLowerCase()}">
                                <i class="fas fa-bolt"></i> ${rec.impact} (Cost: ${rec.cost})
                            </span>
                        </div>
                    </div>
                </div>
            `).join('')}
        </div>
        
        <div class="actions">
            <button class="save-btn" onclick="saveReport()">
                <i class="fas fa-download"></i> Save Report
            </button>
            <button class="reset-btn" onclick="location.reload()">
                <i class="fas fa-redo"></i> New Analysis
            </button>
        </div>
    `;
    
    resultSection.classList.remove('hidden');
    
    // Initialize all recommendation contents as collapsed
    document.querySelectorAll('.rec-content').forEach(content => {
        content.style.maxHeight = '0';
        content.style.padding = '0 1rem';
    });
}

// Toggle recommendation details
function toggleRecommendation(index) {
    const content = document.querySelectorAll('.rec-content')[index];
    const icon = document.querySelectorAll('.rec-header i')[index];
    
    if (content.style.maxHeight === '0px' || !content.style.maxHeight) {
        content.style.maxHeight = content.scrollHeight + 'px';
        content.style.padding = '1rem';
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-up');
    } else {
        content.style.maxHeight = '0';
        content.style.padding = '0 1rem';
        icon.classList.remove('fa-chevron-up');
        icon.classList.add('fa-chevron-down');
    }
}

// Save report (placeholder)
function saveReport() {
    alert('Report saving functionality would be implemented here. Could generate a PDF or save to user account.');
}

// Show error message
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.innerHTML = `
        <i class="fas fa-exclamation-circle"></i> ${message}
    `;
    errorDiv.style.position = 'fixed';
    errorDiv.style.bottom = '20px';
    errorDiv.style.left = '50%';
    errorDiv.style.transform = 'translateX(-50%)';
    errorDiv.style.backgroundColor = '#ffebee';
    errorDiv.style.color = '#c62828';
    errorDiv.style.padding = '1rem';
    errorDiv.style.borderRadius = '8px';
    errorDiv.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)';
    errorDiv.style.zIndex = '1000';
    errorDiv.style.maxWidth = '90%';
    errorDiv.style.textAlign = 'center';
    
    document.body.appendChild(errorDiv);
    
    setTimeout(() => {
        errorDiv.style.opacity = '0';
        setTimeout(() => errorDiv.remove(), 300);
    }, 5000);
}