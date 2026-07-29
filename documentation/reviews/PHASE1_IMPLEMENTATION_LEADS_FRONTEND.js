/**
 * PHASE 1 FRONTEND OPTIMIZATION: Lazy Loading + Cleanup
 * File: /opt/miguel/frontend/leads-optimized.js
 * 
 * Memory-optimized version of leads page functionality
 * Replace existing inline JavaScript with this module
 */

// ─────────────────────────────────────────────────────────────
// STATE: Keep minimal, load on-demand
// ─────────────────────────────────────────────────────────────

let currentPage = 1;
const pageSize = 20;
let totalLeads = 0;
let totalPages = 0;

let currentFilters = {
    status: null,
    priority: null,
    search: null,
    assignedTo: null,
};

let currentDetailLead = null;
let eventListenerRefs = [];  // Track listeners for cleanup

// ─────────────────────────────────────────────────────────────
// CORE: Load page on demand
// ─────────────────────────────────────────────────────────────

async function loadLeadsPage(page = 1) {
    try {
        // Build query params
        const params = new URLSearchParams();
        params.append('page', page);
        params.append('page_size', pageSize);
        
        // Add active filters
        if (currentFilters.status) params.append('status', currentFilters.status);
        if (currentFilters.priority) params.append('priority', currentFilters.priority);
        if (currentFilters.search) params.append('search', currentFilters.search);
        if (currentFilters.assignedTo) params.append('assigned_to_id', currentFilters.assignedTo);
        
        // Request only needed fields (reduce response size 10x)
        params.append('fields', 'id,lead_number,name,phone,status,priority,created_at');
        
        const response = await fetch(`/api/leads?${params.toString()}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        
        // Store pagination info
        currentPage = page;
        totalLeads = data.pagination.total_count;
        totalPages = data.pagination.total_pages;
        
        // Render this page only (not all data!)
        renderLeadTable(data.data);
        renderPagination(data.pagination);
        
        return data;
    } catch (error) {
        console.error('Failed to load leads:', error);
        showError('Failed to load leads');
    }
}

// ─────────────────────────────────────────────────────────────
// RENDER: Only render visible page
// ─────────────────────────────────────────────────────────────

function renderLeadTable(leads) {
    const tbody = document.getElementById('leadsTableBody');
    if (!tbody) return;
    
    // Clear previous rows (garbage collection)
    tbody.innerHTML = '';
    
    // Render only this page (20 rows max)
    leads.forEach((lead) => {
        const row = document.createElement('tr');
        row.dataset.leadId = lead.id;
        row.className = getStatusClass(lead.status);
        
        row.innerHTML = `
            <td>${lead.lead_number}</td>
            <td>${lead.name || '-'}</td>
            <td>${lead.phone}</td>
            <td><span class="status-pill">${lead.status}</span></td>
            <td>${lead.priority || '-'}</td>
            <td>${new Date(lead.created_at).toLocaleDateString()}</td>
            <td>
                <button class="btn-icon" onclick="openLeadDetail('${lead.id}')">👁️</button>
                <button class="btn-icon" onclick="deleteLeadConfirm('${lead.id}')">🗑️</button>
            </td>
        `;
        
        tbody.appendChild(row);
    });
}

function renderPagination(pagination) {
    const container = document.getElementById('paginationControls');
    if (!container) return;
    
    container.innerHTML = `
        <div style="display: flex; gap: 8px; align-items: center;">
            <button 
                onclick="loadLeadsPage(1)" 
                ${!pagination.has_prev ? 'disabled' : ''}
            >
                « First
            </button>
            <button 
                onclick="loadLeadsPage(${pagination.prev_page})" 
                ${!pagination.has_prev ? 'disabled' : ''}
            >
                ‹ Prev
            </button>
            
            <span style="padding: 0 12px; font-weight: 500;">
                Page ${pagination.page} of ${pagination.total_pages}
                (${pagination.total_count} total)
            </span>
            
            <button 
                onclick="loadLeadsPage(${pagination.next_page})" 
                ${!pagination.has_next ? 'disabled' : ''}
            >
                Next ›
            </button>
            <button 
                onclick="loadLeadsPage(${pagination.total_pages})" 
                ${!pagination.has_next ? 'disabled' : ''}
            >
                Last »
            </button>
        </div>
    `;
}

// ─────────────────────────────────────────────────────────────
// FILTERS: Apply and reload
// ─────────────────────────────────────────────────────────────

function applyFilters() {
    // Get filter values from UI
    currentFilters.status = document.getElementById('filterStatus')?.value || null;
    currentFilters.priority = document.getElementById('filterPriority')?.value || null;
    currentFilters.search = document.getElementById('searchInput')?.value || null;
    currentFilters.assignedTo = document.getElementById('filterAssignedTo')?.value || null;
    
    // Reset to page 1 when filters change
    currentPage = 1;
    loadLeadsPage(1);
}

function clearFilters() {
    currentFilters = { status: null, priority: null, search: null, assignedTo: null };
    
    // Clear UI
    document.getElementById('filterStatus').value = '';
    document.getElementById('filterPriority').value = '';
    document.getElementById('searchInput').value = '';
    document.getElementById('filterAssignedTo').value = '';
    
    loadLeadsPage(1);
}

// ─────────────────────────────────────────────────────────────
// DETAIL VIEW: Load on demand, cleanup after
// ─────────────────────────────────────────────────────────────

async function openLeadDetail(leadId) {
    try {
        // Fetch full lead details (only when needed)
        const response = await fetch(`/api/leads/${leadId}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const lead = await response.json();
        currentDetailLead = lead;
        
        // Render detail modal
        renderLeadDetailModal(lead);
        
        // Add event listeners
        attachDetailListeners(leadId);
        
    } catch (error) {
        console.error('Failed to load lead detail:', error);
        showError('Failed to load lead details');
    }
}

function renderLeadDetailModal(lead) {
    const modal = document.getElementById('detailPanel');
    if (!modal) return;
    
    modal.innerHTML = `
        <div class="dp-overlay" onclick="closeLeadDetail(event)"></div>
        <div class="dp-modal">
            <div class="dp-header">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <h3>${lead.lead_number}</h3>
                        <p>${lead.name}</p>
                        <p>${lead.phone}</p>
                    </div>
                    <button class="btn-close" onclick="closeLeadDetail()">✕</button>
                </div>
            </div>
            <div class="dp-body">
                <section>
                    <h4>Contact Info</h4>
                    <dl>
                        <dt>Name:</dt>
                        <dd>${lead.name}</dd>
                        <dt>Phone:</dt>
                        <dd>${lead.phone}</dd>
                        <dt>Email:</dt>
                        <dd>${lead.email || '-'}</dd>
                        <dt>Company:</dt>
                        <dd>${lead.company_name || '-'}</dd>
                    </dl>
                </section>
                
                <section>
                    <h4>Classification</h4>
                    <dl>
                        <dt>Status:</dt>
                        <dd>${lead.status}</dd>
                        <dt>Priority:</dt>
                        <dd>${lead.priority}</dd>
                        <dt>Source:</dt>
                        <dd>${lead.source || '-'}</dd>
                    </dl>
                </section>
                
                <section id="activities">
                    <h4>Activities</h4>
                    <div id="activitiesList">Loading...</div>
                </section>
            </div>
            <div class="dp-footer">
                <button onclick="closeLeadDetail()">Close</button>
                <button onclick="deleteLeadConfirm('${lead.id}')">Delete</button>
            </div>
        </div>
    `;
    
    modal.classList.add('open');
    
    // Load activities (only for detail view)
    loadLeadActivities(lead.id);
}

async function loadLeadActivities(leadId) {
    try {
        const response = await fetch(`/api/leads/${leadId}/activities?limit=20`);
        const data = await response.json();
        
        const container = document.getElementById('activitiesList');
        if (!container) return;
        
        if (data.activities.length === 0) {
            container.innerHTML = '<p>No activities yet</p>';
            return;
        }
        
        container.innerHTML = data.activities.map(activity => `
            <div class="activity-item">
                <span class="type">${activity.type}</span>
                <span class="time">${new Date(activity.created_at).toLocaleString()}</span>
                <p>${activity.note || '-'}</p>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Failed to load activities:', error);
    }
}

function attachDetailListeners(leadId) {
    // Store event handlers for cleanup
    const modal = document.getElementById('detailPanel');
    if (!modal) return;
    
    // Handler for clicking outside modal
    const overlayHandler = (e) => {
        if (e.target.classList.contains('dp-overlay')) {
            closeLeadDetail();
        }
    };
    
    modal.addEventListener('click', overlayHandler);
    eventListenerRefs.push({ element: modal, event: 'click', handler: overlayHandler });
}

function closeLeadDetail(event) {
    // Don't close if clicking inside modal
    if (event && !event.target.classList.contains('dp-overlay') && 
        !event.target.classList.contains('btn-close')) {
        return;
    }
    
    const modal = document.getElementById('detailPanel');
    if (modal) modal.classList.remove('open');
    
    // Clean up event listeners
    eventListenerRefs.forEach(({ element, event, handler }) => {
        if (element) {
            element.removeEventListener(event, handler);
        }
    });
    eventListenerRefs = [];
    
    // Clear cached lead data
    currentDetailLead = null;
}

// ─────────────────────────────────────────────────────────────
// CRUD OPERATIONS
// ─────────────────────────────────────────────────────────────

async function deleteLeadConfirm(leadId) {
    if (!confirm('Are you sure you want to delete this lead?')) return;
    
    try {
        const response = await fetch(`/api/leads/${leadId}`, { method: 'DELETE' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        // Close detail view
        closeLeadDetail();
        
        // Reload current page
        loadLeadsPage(currentPage);
        
        showSuccess('Lead deleted');
    } catch (error) {
        console.error('Delete failed:', error);
        showError('Failed to delete lead');
    }
}

// ─────────────────────────────────────────────────────────────
// UTILITY FUNCTIONS
// ─────────────────────────────────────────────────────────────

function getStatusClass(status) {
    const classMap = {
        'created': 'status-created',
        'new_lead': 'status-new',
        'contacted': 'status-contacted',
        'remind_later': 'status-remind',
        'success_won': 'status-won',
        'lost_lead': 'status-lost',
    };
    return classMap[status] || '';
}

function showError(message) {
    const container = document.getElementById('errorMessage');
    if (container) {
        container.textContent = message;
        container.style.display = 'block';
        setTimeout(() => {
            container.style.display = 'none';
        }, 5000);
    }
}

function showSuccess(message) {
    const container = document.getElementById('successMessage');
    if (container) {
        container.textContent = message;
        container.style.display = 'block';
        setTimeout(() => {
            container.style.display = 'none';
        }, 3000);
    }
}

// ─────────────────────────────────────────────────────────────
// INITIALIZATION
// ─────────────────────────────────────────────────────────────

function initializeLeadsPage() {
    // Load first page
    loadLeadsPage(1);
    
    // Attach filter listeners
    document.getElementById('filterStatus')?.addEventListener('change', applyFilters);
    document.getElementById('filterPriority')?.addEventListener('change', applyFilters);
    document.getElementById('searchInput')?.addEventListener('input', debounce(applyFilters, 500));
    document.getElementById('filterAssignedTo')?.addEventListener('change', applyFilters);
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        closeLeadDetail();
    });
}

// Debounce search input (prevent firing on every keystroke)
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Start when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeLeadsPage);
} else {
    initializeLeadsPage();
}

// ─────────────────────────────────────────────────────────────
// EXPORTS (for testing)
// ─────────────────────────────────────────────────────────────

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        loadLeadsPage,
        applyFilters,
        clearFilters,
        openLeadDetail,
        closeLeadDetail,
        deleteLeadConfirm,
    };
}
