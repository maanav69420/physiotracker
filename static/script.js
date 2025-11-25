document.addEventListener('DOMContentLoaded', function() {
    // Profile dropdown with smooth animation
    const profileBtn = document.querySelector('.profile-btn');
    const profileDropdown = document.querySelector('.profile-dropdown');
    
    if (profileBtn && profileDropdown) {
        profileBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            const menu = profileDropdown.querySelector('.dropdown-menu');
            if (menu) {
                menu.classList.toggle('hidden');
            }
        });
        
        document.addEventListener('click', function() {
            const menu = profileDropdown.querySelector('.dropdown-menu');
            if (menu) {
                menu.classList.add('hidden');
            }
        });
    }

    // API Base
    const API_BASE = '/api';

    // API Helper Functions
    async function apiGet(path) {
        const r = await fetch(`${API_BASE}${path}`);
        if (!r.ok) throw new Error(`${r.status} ${path}`);
        return r.json();
    }

    async function apiPost(path, body) {
        const r = await fetch(`${API_BASE}${path}`, {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify(body)
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.message || `POST failed ${path}`);
        return data;
    }

    async function apiPut(path, body) {
        const r = await fetch(`${API_BASE}${path}`, {
            method:'PUT',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify(body)
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.message || `PUT failed ${path}`);
        return data;
    }

    async function apiDelete(path) {
        const r = await fetch(`${API_BASE}${path}`, { method:'DELETE' });
        const data = await r.json();
        if (!r.ok) throw new Error(data.message || `DELETE failed ${path}`);
        return data;
    }

    // Enhanced search with debouncing and API call
    const searchInput = document.getElementById('global-search-input');
    let debounceTimer;
    
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(async () => {
                const searchTerm = this.value.trim();
                
                if (searchTerm === '') {
                    await reloadItems();
                    return;
                }

                try {
                    const results = await apiGet(`/utils/search?q=${encodeURIComponent(searchTerm)}`);
                    renderInventoryTable(results);
                } catch(e) {
                    console.error('Search error:', e);
                    showNotification('Search failed');
                }
            }, 300);
        });
    }

    // Active navigation highlighting
    const navLinks = document.querySelectorAll('nav a');
    const currentPath = window.location.pathname;
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath || 
            (currentPath === '/' && link.textContent.trim() === 'Dashboard')) {
            link.classList.add('active');
        }
    });

    // Filter by department with API
    window.filterByDept = async function(dept) {
        try {
            if (dept === 'all') {
                await reloadItems();
            } else {
                const items = await apiGet('/items');
                const filtered = items.filter(i => 
                    (i.department || i.lab_name || '').toLowerCase().includes(dept.toLowerCase())
                );
                renderInventoryTable(filtered);
            }
        } catch(e) {
            console.error('Filter error:', e);
            showNotification('Filter failed');
        }
    };

    // Filter by status with API
    window.filterByStatus = async function(status) {
        try {
            let items;
            if (status === 'all' || status === 'total') {
                items = await apiGet('/items');
            } else if (status === 'available') {
                items = await apiGet('/items/available');
            } else if (status === 'reserved') {
                // Use dedicated reserved endpoint
                items = await apiGet('/items/reserved');
            } else if (status === 'low-stock') {
                const allItems = await apiGet('/items');
                items = allItems.filter(i => {
                    const qty = Number(i.quantity ?? i.current_stock ?? 0);
                    const min = Number(i.min_stock_level ?? 5);
                    return qty <= min;
                });
            } else {
                const allItems = await apiGet('/items');
                items = allItems.filter(i => 
                    (i.operational_status || i.status) === status
                );
            }
            renderInventoryTable(items);
        } catch(e) {
            console.error('Status filter error:', e);
            showNotification('Filter failed');
        }
    };

    // Load dashboard with live stats from API
    async function loadDashboard() {
        try {
            const stats = await apiGet('/utils/stats');
            
            // Update stat cards
            const totalEl = document.getElementById('total-items');
            const reservedEl = document.getElementById('reserved-count');
            
            if (totalEl) totalEl.textContent = stats.total_items || 0;
            
            // Fetch reserved items count from dedicated endpoint
            try {
                const reservedItems = await apiGet('/items/reserved');
                if (reservedEl) reservedEl.textContent = reservedItems.length || 0;
            } catch(e) {
                console.warn('Failed to fetch reserved items:', e);
                // Fallback: count from stats
                if (reservedEl) reservedEl.textContent = stats.reserved_items || 0;
            }

            const items = await apiGet('/items');
            renderInventoryTable(items);
            loadDeptFilter(items);
        } catch(e) {
            console.error('Dashboard load error:', e);
            showNotification('Failed to load dashboard');
        }
    }

    // Load departments into filter dropdown
    async function loadDepartments() {
        try {
            const depts = await apiGet('/utils/departments');
            const sel = document.getElementById('dept-filter');
            if (!sel) return;
            
            // Clear existing options except "All Departments"
            sel.innerHTML = '<option value="all">All Departments</option>';
            
            depts.forEach(d => {
                const opt = document.createElement('option');
                opt.value = d;
                opt.textContent = d;
                sel.appendChild(opt);
            });
        } catch(e) {
            console.warn('Failed to load departments:', e);
        }
    }

    function loadDeptFilter(items) {
        const unique = [...new Set(items.map(i => i.department || i.lab_name).filter(Boolean))];
        const sel = document.getElementById('dept-filter');
        if (!sel) return;
        
        // Only add if not already present
        unique.forEach(d => {
            if ([...sel.options].some(o => o.value === d)) return;
            const opt = document.createElement('option');
            opt.value = d;
            opt.textContent = d;
            sel.appendChild(opt);
        });
    }

    // Group cache for action lookups
    let ITEM_GROUPS = [];
    let GROUP_LOOKUP = {};

    /**
     * Group items by (name, department, location)
     */
    function groupItems(items) {
        GROUP_LOOKUP = {};
        ITEM_GROUPS = [];
        items.forEach(it => {
            const name = (it.name || it.equipment_name || 'Unnamed').trim();
            const dept = it.department || it.lab_name || '';
            const loc = it.location || it.room_no || '';
            const key = `${name}||${dept}||${loc}`;
            if (!GROUP_LOOKUP[key]) {
                GROUP_LOOKUP[key] = {
                    key,
                    name,
                    dept,
                    loc,
                    items: [],
                    totalQty: 0
                };
                ITEM_GROUPS.push(GROUP_LOOKUP[key]);
            }
            const qty = Number(it.quantity ?? it.current_stock ?? 1);
            GROUP_LOOKUP[key].items.push(it);
            GROUP_LOOKUP[key].totalQty += qty;
        });
        return ITEM_GROUPS;
    }

    /**
     * Derive a representative status for a group
     */
    function deriveGroupStatus(group) {
        const statuses = group.items.map(i => i.operational_status || i.status || 'unknown');
        if (statuses.some(s => s === 'in_use')) return 'in_use';
        if (statuses.some(s => s === 'reserved')) return 'reserved';
        if (statuses.some(s => s === 'scheduled')) return 'reserved'; // Map scheduled -> reserved
        if (statuses.some(s => s === 'maintenance')) return 'maintenance';
        if (statuses.every(s => s === 'available')) return 'available';
        return statuses[0] || 'unknown';
    }

    /**
     * Pick one item id from group for an action (prefers available)
     */
    function pickItemIdForAction(group) {
        const preferred = group.items.find(i => (i.operational_status || i.status) === 'available')
            || group.items[0];
        return preferred.id;
    }

    // Inject/extend styles for centered ID and icon buttons
    (function ensureStyles(){
        if (document.getElementById('inventory-style')) return;
        const s = document.createElement('style');
        s.id = 'inventory-style';
        s.textContent = `
          .inventory-table td.row-number {
            width:60px;
            text-align:center;
            font-weight:600;
            color:#475569;
            letter-spacing:.5px;
          }
          .inventory-table td.actions {
            white-space:nowrap;
          }
          .action-icon {
            background:#fff;
            border:1px solid #e2e8f0;
            border-radius:8px;
            padding:6px 10px;
            margin:0 4px;
            cursor:pointer;
            font-size:18px;
            line-height:1;
            display:inline-flex;
            align-items:center;
            justify-content:center;
            position:relative;
            transition:background .15s,color .15s,transform .15s;
          }
          .action-icon:hover {
            background:#059669;
            color:#fff;
            transform:translateY(-2px);
          }
          .action-icon[data-tip]:hover:after {
            content:attr(data-tip);
            position:absolute;
            bottom:-32px;
            left:50%;
            transform:translateX(-50%);
            background:#334155;
            color:#fff;
            font-size:12px;
            padding:4px 8px;
            border-radius:6px;
            white-space:nowrap;
            box-shadow:0 4px 12px rgba(0,0,0,.15);
            z-index:10;
          }
          #reservation-modal {
            display:none;
            position:fixed;
            inset:0;
            background:rgba(0,0,0,.45);
            backdrop-filter:saturate(180%) blur(4px);
            z-index:1000;
            align-items:center;
            justify-content:center;
          }
          #reservation-modal .box {
            background:#ffffff;
            width:420px;
            max-width:94%;
            border-radius:16px;
            padding:22px 26px 20px;
            box-shadow:0 20px 40px -10px rgba(0,0,0,.25);
            animation:fadeInScale .25s ease;
            font-family:system-ui,-apple-system,Segoe UI,Roboto;
          }
          #reservation-modal h3 {
            margin:0 0 10px;
            font-size:20px;
            font-weight:600;
            color:#0f172a;
            letter-spacing:.3px;
          }
          #reservation-modal form {
            display:grid;
            gap:14px;
            margin-top:6px;
          }
          #reservation-modal label {
            font-size:13px;
            font-weight:600;
            text-transform:uppercase;
            letter-spacing:.5px;
            color:#475569;
          }
          #reservation-modal input[type="text"],
          #reservation-modal input[type="number"],
          #reservation-modal input[type="datetime-local"] {
            width:100%;
            padding:10px 12px;
            border:1px solid #cbd5e1;
            border-radius:10px;
            font-size:14px;
            outline:none;
            background:#f8fafc;
            transition:border-color .15s,background .15s;
          }
          #reservation-modal input:focus {
            border-color:#059669;
            background:#ffffff;
          }
          #reservation-modal .actions {
            display:flex;
            gap:10px;
            margin-top:4px;
          }
          #reservation-modal button {
            flex:1;
            border:none;
            border-radius:10px;
            padding:11px 14px;
            font-size:14px;
            font-weight:600;
            cursor:pointer;
            transition:background .18s,transform .18s;
          }
          #reservation-modal button.submit {
            background:#059669;
            color:#fff;
          }
          #reservation-modal button.submit:hover {
            background:#047857;
            transform:translateY(-2px);
          }
          #reservation-modal button.cancel {
            background:#e2e8f0;
            color:#334155;
          }
          #reservation-modal button.cancel:hover {
            background:#cbd5e1;
            transform:translateY(-2px);
          }
          @keyframes fadeInScale {
            from {opacity:0; transform:scale(.9);}
            to {opacity:1; transform:scale(1);}
          }
        `;
        document.head.appendChild(s);
    })();

    /**
     * Render grouped table with row numbers and icons
     */
    function renderInventoryTable(items) {
        const tbody = document.getElementById('inventory-table-body') || document.getElementById('inventory-tbody');
        const loadingRow = document.getElementById('loading-row');
        if (!tbody) return;
        
        if (loadingRow) loadingRow.style.display = 'none';
        
        tbody.innerHTML = '';

        const groups = groupItems(items).sort((a,b)=>a.name.localeCompare(b.name));
        let rowNum = 1;
        groups.forEach(g=>{
            const status = deriveGroupStatus(g);
            const displayStatus = status === 'scheduled' ? 'reserved' : status; // Display reserved instead of scheduled
            const anyId = pickItemIdForAction(g);
            const tr = document.createElement('tr');
            tr.dataset.groupKey = g.key;
            tr.dataset.status = status;
            tr.innerHTML = `
              <td class="row-number">${rowNum}</td>
              <td>${g.name}</td>
              <td>${g.dept}</td>
              <td style="text-align:center;font-weight:600;">${g.totalQty}</td>
              <td>${g.loc}</td>
              <td><span class="status ${status}">${displayStatus}</span></td>
              <td class="actions">
                 <button class="action-icon" data-tip="Reserve / Schedule" onclick="openUnifiedReservation('${anyId}','${g.name.replace(/'/g,'&#39;')}')">🕒</button>
                 <button class="action-icon" data-tip="Return Item" onclick="returnItem('${anyId}')">🔄</button>
              </td>`;
            tbody.appendChild(tr);
            rowNum++;
        });
    }

    /**
     * Reload items then render as groups
     */
    async function reloadItems() {
        try {
            const items = await apiGet('/items');
            renderInventoryTable(items);
        } catch(e) {
            console.error('Reload error:', e);
            showNotification('Failed to reload items');
        }
    }

    /**
     * Unified reservation modal
     */
    function ensureReservationModal() {
        if (document.getElementById('reservation-modal')) return;
        const modal = document.createElement('div');
        modal.id = 'reservation-modal';
        modal.innerHTML = `
          <div class="box">
            <h3 id="resv-title">Reserve Item</h3>
            <form id="resv-form">
              <div>
                <label for="resv-user-id">User ID</label>
                <input type="text" id="resv-user-id" required placeholder="e.g. 1001">
              </div>
              <div>
                <label for="resv-user-name">Your Name</label>
                <input type="text" id="resv-user-name" required placeholder="e.g. Jane Doe">
              </div>
              <div>
                <label for="resv-qty">Quantity</label>
                <input type="number" id="resv-qty" min="1" value="1" required>
              </div>
              <div>
                <label for="resv-start">Start Date & Time</label>
                <input type="datetime-local" id="resv-start" required>
              </div>
              <div>
                <label for="resv-end">End Date & Time</label>
                <input type="datetime-local" id="resv-end" required>
              </div>
            </form>
            <div class="actions">
              <button class="cancel" type="button" id="resv-cancel-btn">Cancel</button>
              <button class="submit" type="button" id="resv-submit-btn">Reserve</button>
            </div>
          </div>`;
        document.body.appendChild(modal);
        modal.addEventListener('click', e=>{
            if(e.target===modal) closeReservationModal();
        });
        document.getElementById('resv-cancel-btn').onclick = closeReservationModal;
        document.getElementById('resv-submit-btn').onclick = submitUnifiedReservation;
    }

    let CURRENT_RESERVATION_ITEM = null;

    window.openUnifiedReservation = function(itemId, itemName) {
        ensureReservationModal();
        CURRENT_RESERVATION_ITEM = itemId;
        const now = new Date();
        const pad = n=>String(n).padStart(2,'0');
        const isoLocal = (d)=>`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
        const startVal = isoLocal(now);
        const endVal = isoLocal(new Date(now.getTime()+60*60*1000)); // +1h
        document.getElementById('resv-title').textContent = `Reserve: ${itemName}`;
        document.getElementById('resv-start').value = startVal;
        document.getElementById('resv-end').value = endVal;
        document.getElementById('reservation-modal').style.display='flex';
    };

    function closeReservationModal() {
        const m = document.getElementById('reservation-modal');
        if (m) m.style.display='none';
        CURRENT_RESERVATION_ITEM = null;
    }

    async function submitUnifiedReservation() {
        try {
            if(!CURRENT_RESERVATION_ITEM) return;
            const userId = document.getElementById('resv-user-id').value.trim();
            const userName = document.getElementById('resv-user-name').value.trim();
            const qty = parseInt(document.getElementById('resv-qty').value, 10);
            const start = document.getElementById('resv-start').value;
            const end = document.getElementById('resv-end').value;
            
            if(!userId || !userName || !start || !end) {
                showNotification('All fields required');
                return;
            }
            if(isNaN(qty) || qty < 1){
                showNotification('Quantity must be ≥ 1');
                return;
            }
            
            const res = await apiPost(`/items/${CURRENT_RESERVATION_ITEM}/schedule`, {
                user_id: parseInt(userId,10),
                user_name: userName,
                quantity: qty,
                start_datetime: start + ':00',
                end_datetime: end + ':00'
            });
            showNotification(res.message || 'Reservation saved');
            closeReservationModal();
            await reloadItems();
        } catch(e) {
            showNotification(e.message);
        }
    }

    // Return item (POST /api/items/{id}/return)
    window.returnItem = async function(itemId) {
        try {
            const needsCleaning = confirm('Mark cleaning required? OK = Yes / Cancel = No');
            const needsMaintenance = !needsCleaning && confirm('Mark maintenance required? OK = Yes / Cancel = No');
            const res = await apiPost(`/items/${itemId}/return`, {
                needs_cleaning: needsCleaning || false,
                needs_maintenance: needsMaintenance || false
            });
            showNotification(res.message || 'Item returned');
            await reloadItems();
        } catch (e) {
            showNotification(e.message);
        }
    };

    // Notification system
    function showNotification(message) {
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #059669, #10b981);
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(5, 150, 105, 0.3);
            z-index: 1001;
            animation: slideInRight 0.3s ease-out;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }

    // Add Item Modal Functions
    window.openAddItemModal = function() {
        const modal = document.getElementById('add-item-modal');
        if (modal) {
            modal.classList.remove('hidden');
            // Populate department dropdown
            populateAddItemDepartments();
        }
    };

    window.closeAddItemModal = function() {
        const modal = document.getElementById('add-item-modal');
        if (modal) {
            modal.classList.add('hidden');
            document.getElementById('add-item-form').reset();
        }
    };

    async function populateAddItemDepartments() {
        try {
            const depts = await apiGet('/utils/departments');
            const sel = document.getElementById('item-department');
            if (!sel) return;
            
            sel.innerHTML = '<option value="">Select Department</option>';
            depts.forEach(d => {
                const opt = document.createElement('option');
                opt.value = d;
                opt.textContent = d;
                sel.appendChild(opt);
            });
        } catch(e) {
            console.warn('Failed to load departments for modal:', e);
        }
    }

    window.handleDepartmentChange = function() {
        const deptSelect = document.getElementById('item-department');
        const locSelect = document.getElementById('item-location');
        if (!deptSelect || !locSelect) return;
        
        const dept = deptSelect.value;
        
        // Department -> Location mapping
        const locationMap = {
            'Anatomy Lab': ['303'],
            'Exercise Therapy Lab': ['304'],
            'Exercise Tolerance and Fitness Lab': ['305'],
            'Functional Diagnostics Lab': ['306'],
            'Electrotherapy Lab': ['302'],
            'Biomechanics and kinesiology lab': ['301']
        };
        
        locSelect.innerHTML = '<option value="">Select Location</option>';
        
        if (dept && locationMap[dept]) {
            locationMap[dept].forEach(loc => {
                const opt = document.createElement('option');
                opt.value = loc;
                opt.textContent = loc;
                locSelect.appendChild(opt);
            });
        }
    };

    window.addItem = async function() {
        const form = document.getElementById('add-item-form');
        
        const payload = {
            id: document.getElementById('item-id').value.trim(),
            name: document.getElementById('item-name').value.trim(),
            description: document.getElementById('item-description').value.trim(),
            department: document.getElementById('item-department').value,
            quantity: parseInt(document.getElementById('item-quantity').value, 10),
            location: document.getElementById('item-location').value,
            supplier: document.getElementById('item-supplier').value.trim(),
            min_stock_level: parseInt(document.getElementById('min-stock-level').value || '1', 10)
        };
        
        // Validation
        if (!payload.id || !payload.name || !payload.department || !payload.location) {
            showNotification('Please fill in all required fields');
            return;
        }
        
        try {
            const res = await apiPost('/items', payload);
            showNotification(res.message || 'Item added successfully');
            closeAddItemModal();
            await reloadItems();
            // Refresh stats
            if (document.getElementById('total-items')) {
                loadDashboard();
            }
        } catch(e) {
            showNotification(e.message || 'Failed to add item');
        }
    };

    // Expose functions globally
    window.reloadItems = reloadItems;
    window.showNotification = showNotification;

    // Auto-refresh every 60s
    if (!window.inventoryAutoRefreshed) {
        window.inventoryAutoRefreshed = true;
        setInterval(async () => {
            const tbody = document.getElementById('inventory-tbody') || document.getElementById('inventory-table-body');
            if (tbody) {
                try { await reloadItems(); } catch(e){}
            }
        }, 60000);
    }

    // Initial page logic
    if (document.getElementById('total-items')) {
        loadDashboard();
    } else if (document.getElementById('inventory-tbody') || document.getElementById('inventory-table-body')) {
        reloadItems();
        loadDepartments();
    }
});