// HackVeda Crawler Dashboard JavaScript - FIXED VERSION
// Modern, responsive dashboard functionality

// Initialize Socket.IO with explicit configuration
const socket = io({
    transports: ['websocket', 'polling'],
    timeout: 5000,
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000
});

// Global variables
let isConnected = false;
let currentCrawlSession = null;

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Dashboard initializing...');
    
    // Debug: Check if all required elements exist
    const requiredElements = [
        'start-crawl-btn', 'crawl-progress', 'progress-bar', 
        'progress-text', 'current-keyword', 'keywords', 
        'max-results', 'session-name'
    ];
    
    requiredElements.forEach(id => {
        const element = document.getElementById(id);
        if (!element) {
            console.error(`❌ Missing element: ${id}`);
        } else {
            console.log(`✅ Found element: ${id}`);
        }
    });
    
    initializeDashboard();
    setupEventListeners();
    setupSocketListeners();
});

// Initialize dashboard
function initializeDashboard() {
    console.log('🚀 Initializing HackVeda Crawler Dashboard...');
    
    // Set initial status
    updateSystemStatus('warning', 'Connecting...');
    
    // Load initial data
    checkSystemHealth();
    loadDatabaseStats();
    loadSessions();
    
    // Set up auto-refresh
    setInterval(() => {
        if (!currentCrawlSession) {
            checkSystemHealth();
            loadDatabaseStats();
            loadSessions();
        }
    }, 15000);
}

// Setup event listeners
function setupEventListeners() {
    // Crawl form submission
    const crawlForm = document.getElementById('crawl-form');
    if (crawlForm) {
        crawlForm.addEventListener('submit', function(e) {
            e.preventDefault();
            startCrawling();
        });
    }
    
    // Email form submission
    const emailForm = document.getElementById('email-form');
    if (emailForm) {
        emailForm.addEventListener('submit', function(e) {
            e.preventDefault();
            sendEmail();
        });
    }
}

// Setup Socket.IO listeners
function setupSocketListeners() {
    socket.on('connect', function() {
        isConnected = true;
        console.log('✅ Socket.IO Connected successfully');
        console.log('Socket ID:', socket.id);
        updateSystemStatus('healthy', 'Connected');
        
        // Force refresh data after connection
        setTimeout(() => {
            checkSystemHealth();
            loadDatabaseStats();
            loadSessions();
        }, 1000);
    });
    
    socket.on('disconnect', function() {
        isConnected = false;
        console.log('❌ Disconnected from server');
        updateSystemStatus('error', 'Disconnected');
    });
    
    socket.on('connect_error', function(error) {
        console.error('❌ Socket connection error:', error);
        updateSystemStatus('error', 'Connection Failed');
    });
    
    socket.on('crawl_progress', function(data) {
        updateCrawlProgress(data);
    });
    
    socket.on('crawl_complete', function(data) {
        handleCrawlComplete(data);
    });
    
    socket.on('crawl_error', function(data) {
        handleCrawlError(data);
    });
    
    socket.on('email_sent', function(data) {
        handleEmailSent(data);
    });
}

// System health check
async function checkSystemHealth() {
    try {
        console.log('🔍 Checking system health...');
        const response = await fetch('/api/health');
        const data = await response.json();
        
        console.log('Health check response:', data);
        
        if (data.status === 'healthy') {
            if (isConnected) {
                updateSystemStatus('healthy', 'All Systems Operational');
            } else {
                updateSystemStatus('warning', 'API OK, Socket Connecting...');
            }
            
            const emailServices = data.components.email_services || {};
            updateEmailServiceStatus(emailServices);
        } else {
            updateSystemStatus('error', 'System Issues Detected');
        }
    } catch (error) {
        console.error('Health check failed:', error);
        updateSystemStatus('error', 'API Connection Failed');
    }
}

// Load database statistics
async function loadDatabaseStats() {
    try {
        const response = await fetch('/api/database/stats');
        const data = await response.json();
        
        if (data.status === 'success') {
            updateStatsCards(data.stats);
        }
    } catch (error) {
        console.error('Failed to load database stats:', error);
    }
}

// Load recent sessions
async function loadSessions() {
    try {
        const response = await fetch('/api/sessions');
        const data = await response.json();
        
        if (data.status === 'success') {
            renderSessionsTable(data.sessions);
        }
    } catch (error) {
        console.error('Failed to load sessions:', error);
        const tableContainer = document.getElementById('sessions-table');
        if (tableContainer) {
            tableContainer.innerHTML = `
                <div class="text-center py-8 text-red-500">
                    <i class="fas fa-exclamation-triangle text-2xl mb-2"></i>
                    <p>Failed to load sessions</p>
                </div>
            `;
        }
    }
}

// Start crawling
async function startCrawling() {
    console.log('🔍 Starting crawl function...');
    
    try {
        const keywordsElement = document.getElementById('keywords');
        const maxResultsElement = document.getElementById('max-results');
        const sessionNameElement = document.getElementById('session-name');
        
        if (!keywordsElement) {
            console.error('❌ Keywords element not found');
            showToast('error', 'Error', 'Keywords input not found');
            return;
        }
        
        const keywordsText = keywordsElement.value.trim();
        const maxResults = maxResultsElement ? parseInt(maxResultsElement.value) : 10;
        const sessionName = sessionNameElement ? sessionNameElement.value.trim() : '';
        
        if (!keywordsText) {
            showToast('error', 'Error', 'Please enter at least one keyword');
            return;
        }
        
        const keywords = keywordsText.split('\n').map(k => k.trim()).filter(k => k);
        
        // Update UI
        const startBtn = document.getElementById('start-crawl-btn');
        if (startBtn) {
            startBtn.disabled = true;
            startBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Starting...';
        }
        
        // Show progress bar
        const progressDiv = document.getElementById('crawl-progress');
        if (progressDiv) {
            progressDiv.classList.remove('hidden');
        }
        
        const response = await fetch('/api/crawl', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                keywords: keywords,
                max_results: maxResults,
                session_name: sessionName || undefined
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentCrawlSession = data.session_name;
            showToast('success', 'Crawling Started', `Session: ${data.session_name}`);
        } else {
            throw new Error(data.error || 'Failed to start crawling');
        }
        
    } catch (error) {
        console.error('❌ Crawling failed:', error);
        showToast('error', 'Crawling Failed', error.message);
        resetCrawlUI();
    }
}

// Send email
async function sendEmail() {
    const toEmailElement = document.getElementById('to-email');
    const subjectElement = document.getElementById('email-subject');
    const bodyElement = document.getElementById('email-body');
    
    if (!toEmailElement || !subjectElement || !bodyElement) {
        showToast('error', 'Error', 'Email form elements not found');
        return;
    }
    
    const toEmail = toEmailElement.value.trim();
    const subject = subjectElement.value.trim();
    const body = bodyElement.value.trim();
    
    if (!toEmail || !subject || !body) {
        showToast('error', 'Error', 'Please fill in all email fields');
        return;
    }
    
    try {
        const response = await fetch('/api/email/send', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                to_email: toEmail,
                subject: subject,
                body: body
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('success', 'Email Sent', `Successfully sent to ${toEmail}`);
            document.getElementById('email-form').reset();
        } else {
            throw new Error(data.error || 'Failed to send email');
        }
        
    } catch (error) {
        console.error('Email sending failed:', error);
        showToast('error', 'Email Failed', error.message);
    }
}

// Test email service
async function testEmailService() {
    try {
        showToast('info', 'Testing', 'Testing email service...');
        
        const response = await fetch('/api/email/test', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            updateEmailServiceStatus(data.results);
            showToast('success', 'Test Complete', 'Email service test completed');
        } else {
            throw new Error(data.error || 'Test failed');
        }
        
    } catch (error) {
        console.error('Email test failed:', error);
        showToast('error', 'Test Failed', error.message);
    }
}

// Update system status
function updateSystemStatus(status, message) {
    const statusElement = document.getElementById('system-status');
    if (!statusElement) return;
    
    const indicator = statusElement.querySelector('.status-indicator');
    const text = statusElement.querySelector('span:last-child');
    
    if (!indicator || !text) return;
    
    // Remove existing classes
    indicator.classList.remove('status-healthy', 'status-warning', 'status-error', 'pulse-animation');
    
    // Add new status
    switch (status) {
        case 'healthy':
            indicator.classList.add('status-healthy');
            break;
        case 'warning':
            indicator.classList.add('status-warning', 'pulse-animation');
            break;
        case 'error':
            indicator.classList.add('status-error', 'pulse-animation');
            break;
    }
    
    text.textContent = message;
}

// Update email service status
function updateEmailServiceStatus(services) {
    const statusElement = document.getElementById('sendgrid-status');
    if (!statusElement) return;
    
    if (services.sendgrid) {
        const isWorking = services.sendgrid.working;
        const statusClass = isWorking ? 'status-healthy' : 'status-error';
        const statusText = isWorking ? 'Working' : 'Error';
        
        statusElement.innerHTML = `
            <span class="status-indicator ${statusClass}"></span>${statusText}
        `;
    }
}

// Update stats cards
function updateStatsCards(stats) {
    const elements = {
        'total-sessions': stats.crawl_sessions || 0,
        'total-results': stats.search_results || 0,
        'emails-sent': stats.email_logs || 0,
        'total-domains': stats.domains || 0
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
}

// Update crawl progress
function updateCrawlProgress(data) {
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const currentKeyword = document.getElementById('current-keyword');
    
    if (data.status === 'started') {
        if (progressBar) progressBar.style.width = '0%';
        if (progressText) progressText.textContent = '0%';
        if (currentKeyword) currentKeyword.textContent = `Starting crawl session: ${data.session_name}`;
    } else if (data.status === 'crawling') {
        const progress = Math.round(data.progress || 0);
        if (progressBar) progressBar.style.width = `${progress}%`;
        if (progressText) progressText.textContent = `${progress}%`;
        if (currentKeyword) currentKeyword.textContent = `Crawling: ${data.current_keyword}`;
    }
}

// Handle crawl completion
function handleCrawlComplete(data) {
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const currentKeyword = document.getElementById('current-keyword');
    
    // Complete progress
    if (progressBar) progressBar.style.width = '100%';
    if (progressText) progressText.textContent = '100%';
    if (currentKeyword) currentKeyword.textContent = `Completed! Found ${data.total_results} results`;
    
    // Show success message
    showToast('success', 'Crawling Complete', `Found ${data.total_results} results in session: ${data.session_name}`);
    
    // Reset UI after delay
    setTimeout(() => {
        resetCrawlUI();
        loadDatabaseStats();
        loadSessions();
    }, 3000);
    
    currentCrawlSession = null;
}

// Handle crawl error
function handleCrawlError(data) {
    showToast('error', 'Crawling Error', data.error);
    resetCrawlUI();
    currentCrawlSession = null;
}

// Reset crawl UI
function resetCrawlUI() {
    const startBtn = document.getElementById('start-crawl-btn');
    if (startBtn) {
        startBtn.disabled = false;
        startBtn.innerHTML = '<i class="fas fa-play mr-2"></i>Start Crawling';
    }
    
    const progressDiv = document.getElementById('crawl-progress');
    if (progressDiv) {
        progressDiv.classList.add('hidden');
    }
}

// Render sessions table
function renderSessionsTable(sessions) {
    const tableContainer = document.getElementById('sessions-table');
    if (!tableContainer) return;
    
    if (sessions.length === 0) {
        tableContainer.innerHTML = `
            <div class="text-center py-8 text-gray-500">
                <i class="fas fa-inbox text-2xl mb-2"></i>
                <p>No crawl sessions found</p>
            </div>
        `;
        return;
    }
    
    const tableHTML = `
        <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
                <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Session</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Keywords</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Results</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
                ${sessions.map(session => `
                    <tr class="hover:bg-gray-50">
                        <td class="px-6 py-4 whitespace-nowrap">
                            <div class="text-sm font-medium text-gray-900">${session.session_name}</div>
                        </td>
                        <td class="px-6 py-4">
                            <div class="text-sm text-gray-900">
                                ${Array.isArray(session.keywords) ? session.keywords.slice(0, 3).join(', ') : 'N/A'}
                                ${Array.isArray(session.keywords) && session.keywords.length > 3 ? '...' : ''}
                            </div>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                            <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(session.status)}">
                                ${session.status}
                            </span>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            ${session.total_results || 0}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            ${session.start_time ? new Date(session.start_time).toLocaleDateString() : 'N/A'}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            <button onclick="sendCrawlReport(${session.id})" class="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-xs">
                                <i class="fas fa-envelope mr-1"></i>Email Report
                            </button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    tableContainer.innerHTML = tableHTML;
}

// Get status color classes
function getStatusColor(status) {
    switch (status) {
        case 'completed':
            return 'bg-green-100 text-green-800';
        case 'running':
            return 'bg-blue-100 text-blue-800';
        case 'failed':
            return 'bg-red-100 text-red-800';
        default:
            return 'bg-gray-100 text-gray-800';
    }
}

// Show toast notification
function showToast(type, title, message) {
    const toast = document.getElementById('toast');
    const icon = document.getElementById('toast-icon');
    const titleEl = document.getElementById('toast-title');
    const messageEl = document.getElementById('toast-message');
    
    if (!toast || !icon || !titleEl || !messageEl) return;
    
    // Set content
    titleEl.textContent = title;
    messageEl.textContent = message;
    
    // Set icon and colors
    toast.className = 'fixed top-4 right-4 bg-white rounded-lg shadow-lg p-4 transform transition-transform duration-300 z-50';
    
    switch (type) {
        case 'success':
            toast.classList.add('border-l-4', 'border-green-500');
            icon.className = 'fas fa-check-circle text-green-500 mr-3';
            break;
        case 'error':
            toast.classList.add('border-l-4', 'border-red-500');
            icon.className = 'fas fa-exclamation-circle text-red-500 mr-3';
            break;
        case 'warning':
            toast.classList.add('border-l-4', 'border-yellow-500');
            icon.className = 'fas fa-exclamation-triangle text-yellow-500 mr-3';
            break;
        case 'info':
        default:
            toast.classList.add('border-l-4', 'border-blue-500');
            icon.className = 'fas fa-info-circle text-blue-500 mr-3';
            break;
    }
    
    // Show toast
    toast.style.transform = 'translateX(0)';
    
    // Hide after 5 seconds
    setTimeout(() => {
        toast.style.transform = 'translateX(100%)';
    }, 5000);
}

// Refresh dashboard
function refreshDashboard() {
    checkSystemHealth();
    loadDatabaseStats();
    loadSessions();
    showToast('info', 'Refreshed', 'Dashboard data updated');
}

// Send crawl report via email
async function sendCrawlReport(sessionId) {
    const email = prompt('Enter email address to send the crawl report:');
    if (!email) return;
    
    // Validate email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showToast('error', 'Invalid Email', 'Please enter a valid email address');
        return;
    }
    
    try {
        showToast('info', 'Sending Report', 'Generating and sending crawl report...');
        
        const response = await fetch('/api/email/report', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                to_email: email,
                session_id: sessionId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('success', 'Report Sent!', 
                `Beautiful crawl report with ${data.total_results} results sent to ${email}`);
        } else {
            throw new Error(data.error || 'Failed to send report');
        }
        
    } catch (error) {
        console.error('Failed to send crawl report:', error);
        showToast('error', 'Send Failed', error.message);
    }
}

// Handle email sent event
function handleEmailSent(data) {
    // Update email activity panel
    addEmailActivity(data);
    
    // Update stats
    loadDatabaseStats();
    
    // Show notification
    showToast('success', 'Email Sent!', 
        `Report sent to ${data.to_email} with ${data.total_results} results`);
    
    // Pulse email status indicator
    const indicator = document.getElementById('email-status-indicator');
    if (indicator) {
        indicator.classList.add('pulse-animation');
        setTimeout(() => {
            indicator.classList.remove('pulse-animation');
        }, 2000);
    }
}

// Add email activity to the panel
function addEmailActivity(data) {
    const activityPanel = document.getElementById('email-activity');
    if (!activityPanel) return;
    
    // Remove "no activity" message if it exists
    const noActivity = activityPanel.querySelector('.text-center');
    if (noActivity) {
        noActivity.remove();
    }
    
    // Create activity item
    const activityItem = document.createElement('div');
    activityItem.className = 'bg-green-50 border-l-4 border-green-400 p-4 rounded-r-lg animate-pulse';
    activityItem.innerHTML = `
        <div class="flex items-center justify-between">
            <div class="flex items-center">
                <i class="fas fa-envelope text-green-600 mr-3"></i>
                <div>
                    <p class="text-sm font-medium text-green-800">Crawl Report Sent</p>
                    <p class="text-xs text-green-600">To: ${data.to_email}</p>
                </div>
            </div>
            <div class="text-right">
                <p class="text-xs text-green-600">${data.total_results} results</p>
                <p class="text-xs text-gray-500">${new Date(data.timestamp).toLocaleTimeString()}</p>
            </div>
        </div>
        <div class="mt-2">
            <p class="text-xs text-gray-600 truncate">${data.subject}</p>
            <p class="text-xs text-gray-500">Message ID: ${data.message_id}</p>
        </div>
    `;
    
    // Add to top of activity panel
    activityPanel.insertBefore(activityItem, activityPanel.firstChild);
    
    // Remove animation after 3 seconds
    setTimeout(() => {
        activityItem.classList.remove('animate-pulse');
        activityItem.classList.add('bg-gray-50');
        activityItem.classList.remove('bg-green-50');
    }, 3000);
    
    // Keep only last 10 activities
    const activities = activityPanel.children;
    if (activities.length > 10) {
        for (let i = 10; i < activities.length; i++) {
            activities[i].remove();
        }
    }
}

// Utility functions
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
}

function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return num.toLocaleString();
}
