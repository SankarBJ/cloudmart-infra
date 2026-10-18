const API = '/api';

function getAuthToken() { return localStorage.getItem('cloudmart_jwt'); }
function getCurrentUser() { return JSON.parse(localStorage.getItem('cloudmart_user') || 'null'); }
function getCart() { return JSON.parse(localStorage.getItem('cloudmart_cart') || '[]'); }

function saveCart(cart) {
    localStorage.setItem('cloudmart_cart', JSON.stringify(cart));
    updateCartCount();
}

function updateCartCount() {
    const countEl = document.getElementById('navCartCount');
    if (countEl) {
        const cart = getCart();
        const total = cart.reduce((acc, it) => acc + (it.quantity || 1), 0);
        countEl.innerText = total;
    }
}

function renderAmazonHeader(activePage = '') {
    const user = getCurrentUser();
    const userGreeting = user ? `Hello, ${user.name.split(' ')[0]}` : 'Hello, Sign In';

    const headerHTML = `
    <header class="amz-header">
        <div class="amz-nav-top">
            <a href="/" class="amz-logo">CloudMart<span>.in</span></a>
            
            <div class="amz-deliver-box" onclick="location.href='/checkout'">
                <span style="font-size:11px; color:#ccc;">Deliver to ${user ? user.name.split(' ')[0] : 'Guest'}</span>
                <strong style="font-size:13px; color:#fff;">Vellore 632014</strong>
            </div>

            <div class="amz-search-bar">
                <input type="text" id="globalSearchInput" placeholder="Search CloudMart (e.g. Echo, Kindle, Backpack)..." 
                       onkeyup="if(event.key==='Enter') executeSearch()">
                <button onclick="executeSearch()">🔍</button>
            </div>

            <div class="amz-nav-actions">
                <a href="${user ? '#' : '/login'}" class="amz-nav-link" id="navAccountBtn" onclick="${user ? 'handleLogout()' : ''}">
                    <span style="font-size:11px;">${userGreeting}</span>
                    <strong style="font-size:13px;">${user ? 'Account (Sign Out)' : 'Account & Lists'}</strong>
                </a>

                <a href="/orders" class="amz-nav-link">
                    <span style="font-size:11px;">Returns</span>
                    <strong style="font-size:13px;">& Orders</strong>
                </a>

                <a href="/cart" class="amz-cart-btn">
                    <span style="font-size:22px;">🛒</span>
                    <span id="navCartCount" class="amz-cart-badge">0</span>
                    <strong style="color:#fff; font-size:13px;">Cart</strong>
                </a>
            </div>
        </div>

        <div class="amz-subnav">
            <a href="/" class="${activePage === 'home' ? 'active' : ''}">All Departments</a>
            <a href="/?cat=Electronics">Electronics</a>
            <a href="/?cat=Home%20%26%20Kitchen">Home & Kitchen</a>
            <a href="/?cat=Books">Books</a>
            <a href="/orders">Past Orders</a>
            <a href="/tracking">Logistics Handshake Demo</a>
        </div>
    </header>
    `;

    document.body.insertAdjacentHTML('afterbegin', headerHTML);
    updateCartCount();
}

function executeSearch() {
    const q = document.getElementById('globalSearchInput').value.trim();
    if (q) location.href = `/?search=${encodeURIComponent(q)}`;
}

function handleLogout() {
    if (confirm("Do you want to log out of your CloudMart account?")) {
        localStorage.removeItem('cloudmart_jwt');
        localStorage.removeItem('cloudmart_user');
        location.href = '/login';
    }
}
