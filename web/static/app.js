const API = '';
let currentPage = 1;
let map = null;
let markerLayer = null;

// ── TAB NAVIGATION ──

document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    const tab = document.getElementById(`tab-${btn.dataset.tab}`);
    tab.classList.add('active');
    if (btn.dataset.tab === 'map' && !map) initMap();
  });
});

// ── DASHBOARD ──

let dashMap = null;

async function loadDashboard() {
  try {
    const res = await fetch(`${API}/api/stats`);
    const data = await res.json();

    document.getElementById('stat-total').textContent = data.total_stores.toLocaleString();
    document.getElementById('stat-states').textContent = data.total_states;
    document.getElementById('stat-open').textContent = (data.total_stores - data.temporarily_closed).toLocaleString();
    document.getElementById('stat-states-inline').textContent = data.total_states;
    document.getElementById('state-count-badge').textContent = `${data.total_states} states`;

    renderStateChart(data.stores_per_state);
    renderFlavorList(data.top_flavors);
    populateStateFilter(data.states);
    initDashMap();
  } catch (err) {
    console.error('Failed to load dashboard:', err);
  }
}

async function initDashMap() {
  if (dashMap) return;
  const el = document.getElementById('dash-map');
  if (!el) return;

  dashMap = L.map('dash-map', {
    zoomControl: false,
    attributionControl: false,
    dragging: false,
    scrollWheelZoom: false,
    doubleClickZoom: false,
    touchZoom: false,
  }).setView([39.5, -98.5], 4);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
  }).addTo(dashMap);

  setTimeout(() => dashMap.invalidateSize(), 150);

  try {
    const res = await fetch(`${API}/api/map-data`);
    const points = await res.json();
    const layer = L.layerGroup().addTo(dashMap);
    const icon = L.divIcon({
      className: 'custom-marker',
      html: '<div style="width:6px;height:6px;background:#58a6ff;border-radius:50%;opacity:0.7;"></div>',
      iconSize: [6, 6],
      iconAnchor: [3, 3],
    });
    points.forEach(p => L.marker([p.lat, p.lng], { icon, interactive: false }).addTo(layer));
  } catch (e) {}
}

function renderStateChart(storesPerState) {
  const container = document.getElementById('state-chart');
  const sorted = Object.entries(storesPerState).sort((a, b) => b[1] - a[1]);
  const max = sorted.length > 0 ? sorted[0][1] : 1;

  container.innerHTML = sorted.map(([state, count]) => `
    <div class="bar-row">
      <span class="bar-label">${state}</span>
      <div class="bar-track">
        <div class="bar-fill" style="width: ${(count / max * 100).toFixed(1)}%"></div>
      </div>
      <span class="bar-count">${count}</span>
    </div>
  `).join('');
}

function renderFlavorList(flavors) {
  const container = document.getElementById('flavor-list');
  const entries = Object.entries(flavors);

  if (entries.length === 0) {
    container.innerHTML = '<div class="loading">No flavor data available</div>';
    return;
  }

  container.innerHTML = entries.map(([name, count], i) => `
    <div class="flavor-item">
      <span class="flavor-rank">${i + 1}.</span>
      <span class="flavor-name">${name}</span>
      <span class="flavor-count">${count}</span>
    </div>
  `).join('');
}

function populateStateFilter(states) {
  const select = document.getElementById('state-filter');
  states.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s;
    opt.textContent = s;
    select.appendChild(opt);
  });
}

// ── MAP ──

async function initMap() {
  map = L.map('map', {
    zoomControl: true,
    attributionControl: true,
  }).setView([39.8, -98.5], 4);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    maxZoom: 19,
  }).addTo(map);

  setTimeout(() => map.invalidateSize(), 100);

  try {
    const res = await fetch(`${API}/api/map-data`);
    const points = await res.json();

    markerLayer = L.layerGroup().addTo(map);

    const icon = L.divIcon({
      className: 'custom-marker',
      html: '<div style="width:10px;height:10px;background:#58a6ff;border-radius:50%;border:2px solid #161b22;box-shadow:0 0 6px rgba(88,166,255,0.5);"></div>',
      iconSize: [14, 14],
      iconAnchor: [7, 7],
    });

    points.forEach(p => {
      const marker = L.marker([p.lat, p.lng], { icon }).addTo(markerLayer);
      const popup = `
        <div class="popup-title">${escapeHtml(p.name)}</div>
        <div class="popup-detail">${escapeHtml(p.city)}, ${escapeHtml(p.state)}</div>
        ${p.telephone ? `<div class="popup-detail">${escapeHtml(p.telephone)}</div>` : ''}
        ${p.flavor ? `<div class="popup-flavor">Today: ${escapeHtml(p.flavor)}</div>` : ''}
        <div class="popup-actions">
          <button class="popup-btn" onclick="openDetail(${p.oloId})">Store Info</button>
          <button class="popup-btn popup-btn-menu" onclick="openMenuBrowser(${p.oloId}, '${escapeJs(p.name)}')">Menu</button>
        </div>
      `;
      marker.bindPopup(popup, { minWidth: 200 });
    });
  } catch (err) {
    console.error('Failed to load map data:', err);
  }
}

// ── STORES TABLE ──

async function loadStores(page = 1) {
  const search = document.getElementById('search-input').value;
  const state = document.getElementById('state-filter').value;
  const openOnly = document.getElementById('open-only').checked;

  const params = new URLSearchParams({ page, per_page: 50 });
  if (search) params.set('search', search);
  if (state) params.set('state', state);
  if (openOnly) params.set('open_only', 'true');

  const tbody = document.getElementById('store-tbody');
  tbody.innerHTML = '<tr><td colspan="7"><div class="loading"><div class="spinner"></div></div></td></tr>';

  try {
    const res = await fetch(`${API}/api/stores?${params}`);
    const data = await res.json();
    currentPage = data.page;

    tbody.innerHTML = data.stores.map(store => {
      const name = store.name || store.description || '--';
      const isClosed = store.isTemporarilyClosed === 'True' || store.isTemporarilyClosed === true;
      return `
        <tr>
          <td title="${escapeHtml(name)}">${escapeHtml(name)}</td>
          <td>${escapeHtml(store.city || '--')}</td>
          <td>${escapeHtml(store.state || '--')}</td>
          <td>${escapeHtml(store.telephone || '--')}</td>
          <td title="${escapeHtml(store.flavorOfDayName || '')}">${escapeHtml(store.flavorOfDayName || '--')}</td>
          <td><span class="status-badge ${isClosed ? 'status-closed' : 'status-open'}">${isClosed ? 'Closed' : 'Open'}</span></td>
          <td>
            <button class="detail-btn" onclick="openDetail(${store.oloId})">View</button>
            <button class="detail-btn menu-btn" onclick="openMenuBrowser(${store.oloId}, '${escapeJs(name)}')">Menu</button>
          </td>
        </tr>
      `;
    }).join('');

    renderPagination(data.page, data.pages, data.total);
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="7"><div class="loading">Failed to load stores</div></td></tr>';
    console.error('Failed to load stores:', err);
  }
}

function renderPagination(page, pages, total) {
  const container = document.getElementById('pagination');
  if (pages <= 1) { container.innerHTML = ''; return; }

  let html = `<button class="page-btn" onclick="loadStores(${page - 1})" ${page <= 1 ? 'disabled' : ''}>Prev</button>`;

  const range = getPageRange(page, pages);
  range.forEach(p => {
    if (p === '...') {
      html += `<span class="page-info">...</span>`;
    } else {
      html += `<button class="page-btn ${p === page ? 'active' : ''}" onclick="loadStores(${p})">${p}</button>`;
    }
  });

  html += `<button class="page-btn" onclick="loadStores(${page + 1})" ${page >= pages ? 'disabled' : ''}>Next</button>`;
  html += `<span class="page-info">${total.toLocaleString()} stores</span>`;

  container.innerHTML = html;
}

function getPageRange(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages = [];
  pages.push(1);
  if (current > 3) pages.push('...');
  for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) pages.push(i);
  if (current < total - 2) pages.push('...');
  pages.push(total);
  return pages;
}

// ── STORE DETAIL MODAL ──

async function openDetail(oloId) {
  const overlay = document.getElementById('modal-overlay');
  const body = document.getElementById('modal-body');
  overlay.classList.add('open');
  body.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

  try {
    const res = await fetch(`${API}/api/stores/${oloId}`);
    const store = await res.json();

    const name = store.name || store.description || 'Store';
    const subtitle = [store.street, store.city, store.state, store.postalCode].filter(Boolean).join(', ');

    let hoursHtml = '';
    const dineIn = store.dineInHours;
    if (dineIn && typeof dineIn === 'object') {
      const dayMap = { Mo: 'Mon', Tu: 'Tue', We: 'Wed', Th: 'Thu', Fr: 'Fri', Sa: 'Sat', Su: 'Sun' };
      hoursHtml = '<div class="hours-grid">';
      for (const [abbr, label] of Object.entries(dayMap)) {
        const open = dineIn[`${abbr}O`];
        const close = dineIn[`${abbr}C`];
        if (open && close) {
          hoursHtml += `<div class="hours-day"><strong>${label}</strong> ${open} - ${close}</div>`;
        }
      }
      hoursHtml += '</div>';
    }

    body.innerHTML = `
      <h2>${escapeHtml(name)}</h2>
      <div class="modal-subtitle">${escapeHtml(subtitle)}</div>
      <div class="modal-actions">
        <button class="action-btn action-btn-menu" onclick="openMenuBrowser(${oloId}, '${escapeJs(name)}')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h12"/></svg>
          Browse Menu
        </button>
      </div>
      <div class="detail-grid">
        ${detailItem('OLO ID', store.oloId)}
        ${detailItem('Restaurant #', store.restaurantNumber)}
        ${detailItem('Phone', store.telephone)}
        ${detailItem('Owner', store.ownerFriendlyName)}
        ${detailItem('Flavor of the Day', store.flavorOfDayName, true)}
        ${store.flavorOfTheDayDescription ? detailItem('Flavor Description', store.flavorOfTheDayDescription, true) : ''}
        ${detailItem('Coordinates', store.latitude && store.longitude ? `${store.latitude}, ${store.longitude}` : null)}
        ${detailItem('Online Order Status', store.onlineOrderStatus === '1' || store.onlineOrderStatus === 1 ? 'Active' : 'Inactive')}
        ${detailItem('Handoff Options', store.handoffOptions)}
        ${store.ownerMessage ? detailItem('Owner Message', store.ownerMessage, true) : ''}
        ${hoursHtml ? `<div class="detail-item full-width"><div class="detail-key">Dine-In Hours</div><div class="detail-val">${hoursHtml}</div></div>` : ''}
      </div>
    `;
  } catch (err) {
    body.innerHTML = '<div class="loading">Failed to load store details</div>';
    console.error(err);
  }
}

function detailItem(label, value, fullWidth = false) {
  if (value === null || value === undefined || value === 'None') return '';
  return `
    <div class="detail-item ${fullWidth ? 'full-width' : ''}">
      <div class="detail-key">${label}</div>
      <div class="detail-val">${escapeHtml(String(value))}</div>
    </div>
  `;
}

document.getElementById('modal-close').addEventListener('click', () => {
  document.getElementById('modal-overlay').classList.remove('open');
});

document.getElementById('modal-overlay').addEventListener('click', (e) => {
  if (e.target === e.currentTarget) {
    e.currentTarget.classList.remove('open');
  }
});

// ── MENU BROWSER ──

let menuOloId = null;
let menuStoreName = '';

async function openMenuBrowser(oloId, storeName) {
  menuOloId = oloId;
  menuStoreName = storeName;
  const overlay = document.getElementById('menu-overlay');
  const body = document.getElementById('menu-body');
  document.getElementById('menu-store-name').textContent = storeName;
  overlay.classList.add('open');
  body.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

  try {
    const res = await fetch(`${API}/api/menu/${oloId}/categories`);
    if (!res.ok) throw new Error('Failed to load');
    const categories = await res.json();

    body.innerHTML = `
      <div class="menu-categories">
        ${categories.map(c => `
          <button class="menu-cat-btn" onclick="loadCategoryItems(${oloId}, '${escapeJs(c.categorySlug)}', '${escapeJs(c.categoryName)}')">
            <span class="menu-cat-name">${escapeHtml(c.categoryName)}</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
          </button>
        `).join('')}
      </div>
    `;
  } catch (err) {
    body.innerHTML = '<div class="loading">Could not load menu. The store may not have online ordering.</div>';
    console.error(err);
  }
}

async function loadCategoryItems(oloId, categorySlug, categoryName) {
  const body = document.getElementById('menu-body');
  body.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

  try {
    const res = await fetch(`${API}/api/menu/${oloId}/category/${categorySlug}`);
    if (!res.ok) throw new Error('Failed to load');
    const items = await res.json();

    body.innerHTML = `
      <button class="menu-back-btn" onclick="openMenuBrowser(${oloId}, '${escapeJs(menuStoreName)}')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
        All Categories
      </button>
      <h3 class="menu-section-title">${escapeHtml(categoryName)}</h3>
      <div class="menu-items-grid">
        ${items.map(item => {
          const info = item.info || item;
          const cost = info.base_cost != null ? formatCost(info.base_cost) : '';
          const cal = info.base_calories != null ? `${info.base_calories} cal` : '';
          const slug = info.slug || '';
          const img = info.image || '';
          return `
            <div class="menu-item-card" onclick="loadItemDetail(${oloId}, '${escapeJs(categorySlug)}', '${escapeJs(slug)}')">
              ${img ? `<div class="menu-item-img"><img src="${escapeHtml(img)}" alt="" loading="lazy" onerror="this.parentElement.style.display='none'"></div>` : ''}
              <div class="menu-item-body">
                <div class="menu-item-name">${escapeHtml(info.name || '')}</div>
                <div class="menu-item-meta">
                  ${cost ? `<span class="menu-item-price">${cost}</span>` : ''}
                  ${cal ? `<span class="menu-item-cal">${cal}</span>` : ''}
                </div>
                ${info.description ? `<div class="menu-item-desc">${escapeHtml(info.description)}</div>` : ''}
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  } catch (err) {
    body.innerHTML = `
      <button class="menu-back-btn" onclick="openMenuBrowser(${oloId}, '${escapeJs(menuStoreName)}')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
        Back
      </button>
      <div class="loading">Failed to load items</div>
    `;
    console.error(err);
  }
}

async function loadItemDetail(oloId, categorySlug, itemSlug) {
  const body = document.getElementById('menu-body');
  const prevHtml = body.innerHTML;
  body.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

  try {
    const res = await fetch(`${API}/api/menu/${oloId}/item/${categorySlug}/${itemSlug}`);
    if (!res.ok) throw new Error('Failed to load');
    const item = await res.json();
    const info = item.info || {};
    const customizations = item.customizations || {};
    const nutrition = item.nutrition || {};

    const cost = info.base_cost != null ? formatCost(info.base_cost) : 'N/A';
    const cal = info.base_calories != null ? `${info.base_calories} cal` : '';

    let modifiersHtml = '';

    if (customizations.primary) {
      modifiersHtml += renderModifierGroup(customizations.primary);
    }

    if (customizations.additional) {
      customizations.additional.forEach(mod => {
        if (mod) modifiersHtml += renderModifierGroup(mod);
      });
    }

    body.innerHTML = `
      <button class="menu-back-btn" onclick="loadCategoryItems(${oloId}, '${escapeJs(categorySlug)}', '${escapeJs(info.category || categorySlug)}')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
        Back to Items
      </button>

      <div class="item-detail-header">
        ${info.image ? `<div class="item-detail-img"><img src="${escapeHtml(info.image)}" alt="" onerror="this.parentElement.style.display='none'"></div>` : ''}
        <div class="item-detail-info">
          <h3 class="item-detail-name">${escapeHtml(info.name || '')}</h3>
          <div class="item-detail-meta">
            <span class="item-detail-price">${cost}</span>
            ${cal ? `<span class="item-detail-cal">${cal}</span>` : ''}
          </div>
          ${info.description ? `<p class="item-detail-desc">${escapeHtml(info.description)}</p>` : ''}
          ${nutrition.main_nutrition_url ? `<a href="${escapeHtml(nutrition.main_nutrition_url)}" target="_blank" class="nutrition-link">View Full Nutrition Info</a>` : ''}
        </div>
      </div>

      ${modifiersHtml ? `
        <div class="modifiers-section">
          <h4 class="modifiers-title">Customizations &amp; Options</h4>
          ${modifiersHtml}
        </div>
      ` : ''}
    `;
  } catch (err) {
    body.innerHTML = `
      <button class="menu-back-btn" onclick="loadCategoryItems(${oloId}, '${escapeJs(categorySlug)}', '${escapeJs(categorySlug)}')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
        Back
      </button>
      <div class="loading">Failed to load item details</div>
    `;
    console.error(err);
  }
}

function renderModifierGroup(mod) {
  if (!mod || !mod.options || mod.options.length === 0) return '';

  const mandatory = mod.isMandatory ? '<span class="mod-required">Required</span>' : '';
  const limits = [];
  if (mod.minQuantity != null && mod.minQuantity > 0) limits.push(`Min: ${mod.minQuantity}`);
  if (mod.maxQuantity != null) limits.push(`Max: ${mod.maxQuantity}`);
  const limitsStr = limits.length ? `<span class="mod-limits">${limits.join(' / ')}</span>` : '';

  return `
    <div class="modifier-group">
      <div class="mod-group-header">
        <span class="mod-group-title">${escapeHtml(mod.title || 'Options')}</span>
        ${mandatory}
        ${limitsStr}
      </div>
      ${mod.description ? `<div class="mod-group-desc">${escapeHtml(mod.description)}</div>` : ''}
      <div class="mod-options">
        ${mod.options.map(opt => {
          const optCost = opt.cost != null && opt.cost > 0 ? `+${formatCost(opt.cost)}` : opt.cost === 0 ? '' : '';
          const optCal = opt.calories != null ? `${opt.calories} cal` : '';
          const tags = [];
          if (opt.isDefault) tags.push('default');
          if (opt.isRemoval) tags.push('removal');

          let sizeHtml = '';
          if (opt.nested_size_options && opt.nested_size_options.length > 0) {
            sizeHtml = `<div class="size-options">${opt.nested_size_options.map(s => {
              const sCost = s.cost != null && s.cost > 0 ? formatCost(s.cost) : '';
              const sCal = s.calories != null ? `${s.calories} cal` : '';
              return `<span class="size-chip">${escapeHtml(s.name || '')}${sCost ? ` ${sCost}` : ''}${sCal ? ` / ${sCal}` : ''}</span>`;
            }).join('')}</div>`;
          }

          return `
            <div class="mod-option ${opt.isDefault ? 'mod-option-default' : ''}">
              <div class="mod-option-main">
                <span class="mod-option-name">${escapeHtml(opt.name || '')}</span>
                <div class="mod-option-right">
                  ${tags.map(t => `<span class="mod-tag mod-tag-${t}">${t}</span>`).join('')}
                  ${optCal ? `<span class="mod-option-cal">${optCal}</span>` : ''}
                  ${optCost ? `<span class="mod-option-cost">${optCost}</span>` : ''}
                </div>
              </div>
              ${sizeHtml}
            </div>
          `;
        }).join('')}
      </div>
    </div>
  `;
}

function formatCost(value) {
  if (value == null) return '';
  const num = parseFloat(value);
  if (isNaN(num) || num === 0) return '';
  return `$${num.toFixed(2)}`;
}

document.getElementById('menu-close').addEventListener('click', () => {
  document.getElementById('menu-overlay').classList.remove('open');
});

document.getElementById('menu-overlay').addEventListener('click', (e) => {
  if (e.target === e.currentTarget) {
    e.currentTarget.classList.remove('open');
  }
});

// ── EVENT LISTENERS ──

let searchTimeout;
document.getElementById('search-input').addEventListener('input', () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => loadStores(1), 300);
});

document.getElementById('state-filter').addEventListener('change', () => loadStores(1));
document.getElementById('open-only').addEventListener('change', () => loadStores(1));

// ── UTILS ──

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function escapeJs(str) {
  if (!str) return '';
  return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"');
}

// ── INIT ──

loadDashboard();
loadStores(1);
