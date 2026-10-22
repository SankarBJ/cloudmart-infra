// CloudMart Universal Navigation, Voice Assistant & Resilient API Connector
(function() {
  // Determine best API endpoint automatically
  window.getApiBase = function() {
    if (window.location.protocol === 'file:') return 'http://localhost:5000/api';
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      if (window.location.port === '5000') return '/api';
      return '/api';
    }
    return '/api';
  };

  // Robust fetch with automatic backend fallback
  window.cloudmartFetch = async function(endpoint, options = {}) {
    const path = endpoint.startsWith('/') ? endpoint : '/' + endpoint;
    const candidates = [
      window.getApiBase() + path,
      'http://localhost:5000/api' + path,
      'https://cloudmart-infra-2.onrender.com/api' + path
    ];

    let lastError = null;
    for (const url of candidates) {
      try {
        const res = await fetch(url, options);
        if (res.ok || res.status === 400 || res.status === 401 || res.status === 403 || res.status === 404 || res.status === 409) {
          return res;
        }
      } catch (err) {
        lastError = err;
      }
    }
    throw lastError || new Error("Failed to connect to any backend service.");
  };

  function getCartCount() {
    try {
      const cart = JSON.parse(localStorage.getItem("cloudmart_cart") || "[]");
      return cart.reduce((sum, item) => sum + (item.quantity || 1), 0);
    } catch(e) { return 0; }
  }

  function getUser() {
    try { return JSON.parse(localStorage.getItem("cloudmart_user") || "null"); }
    catch(e) { return null; }
  }

  function renderHeader() {
    const headerContainer = document.getElementById("cloudmart-header");
    if (!headerContainer) return;

    const user = getUser();
    const cartCount = getCartCount();
    const role = localStorage.getItem("cloudmart_role") || "customer";

    headerContainer.innerHTML = `
      <header class="navbar">
        <div class="nav-left">
          <a href="/" class="nav-logo">
            <span class="logo-bold">cloud</span><span class="logo-orange">mart</span><span class="logo-domain">.in</span>
          </a>
          <div class="nav-deliver-to">
            <span class="nav-line-1">Deliver to</span>
            <span class="nav-line-2">📍 ${user ? (user.city || "Chennai 600028") : "India"}</span>
          </div>
        </div>

        <div class="nav-center">
          <form class="nav-search-form" onsubmit="event.preventDefault(); window.triggerHeaderSearch();">
            <select class="nav-search-dropdown" id="nav-search-category">
              <option value="All">All</option>
              <option value="Electronics">Electronics</option>
              <option value="Mobiles">Mobiles</option>
              <option value="Fashion">Fashion</option>
              <option value="Home">Home</option>
            </select>
            <input type="text" id="twotabsearchtextbox" class="nav-search-input" placeholder="Search CloudMart or tap mic..." autocomplete="off">
            
            <div class="voice-lang-pill" id="voice-lang-pill" title="Current Voice Language">
              <select id="voice-lang-select" onchange="window.currentVoiceLang = this.value">
                <option value="en-IN" selected>EN</option>
                <option value="hi-IN">HI</option>
                <option value="ta-IN">TA</option>
              </select>
            </div>

            <button type="button" id="nav-mic-btn" class="nav-mic-btn" title="Tap to speak" onclick="window.startVoiceSearch()">
              🎙️
            </button>
            <button type="submit" class="nav-search-btn" title="Search">
              🔍
            </button>
          </form>
        </div>

        <div class="nav-right">
          <div class="nav-account-dropdown">
            <a href="${user ? '/orders' : '/login'}" class="nav-link">
              <span class="nav-line-1">Hello, ${user ? user.name.split(' ')[0] : 'Sign In'}</span>
              <span class="nav-line-2">Account & Lists ▾</span>
            </a>
          </div>

          <a href="/orders" class="nav-link">
            <span class="nav-line-1">Returns</span>
            <span class="nav-line-2">& Orders</span>
          </a>

          <a href="/cart" class="nav-link nav-cart-link">
            <span class="nav-cart-icon">🛒</span>
            <span class="nav-cart-count" id="nav-cart-count">${cartCount}</span>
            <span class="nav-line-2 cart-text">Cart</span>
          </a>

          ${user ? `
            <button class="nav-btn-logout" onclick="window.logoutUser()">Sign Out</button>
          ` : `
            <a href="/login" class="nav-btn-signin">Sign In</a>
          `}
        </div>
      </header>

      <nav class="subnav">
        <a href="/" class="subnav-link">🏠 All Products</a>
        <a href="/?cat=Mobiles" class="subnav-link">Mobiles</a>
        <a href="/?cat=Electronics" class="subnav-link">Electronics</a>
        <a href="/?cat=Fashion" class="subnav-link">Fashion</a>
        <a href="/?cat=Home" class="subnav-link">Home & Kitchen</a>
        <a href="/ai-chat" class="subnav-link nav-highlight">✨ Marti AI & Voice Assistant</a>
        <span class="subnav-spacer"></span>
        <a href="${role === 'seller' ? '/?view=seller' : '/?view=customer'}" class="subnav-link seller-switch">
          ${role === 'seller' ? 'Switch to Customer View' : 'Sell on CloudMart (Seller Central)'}
        </a>
      </nav>

      <!-- Floating Marti AI Quick Launcher -->
      <a href="/ai-chat" class="marti-float-btn" title="Talk to Marti AI Assistant">
        <span class="float-icon">🤖</span>
        <span class="float-text">Ask Marti AI</span>
      </a>
    `;
  }

  window.currentVoiceLang = 'en-IN';

  window.startVoiceSearch = function() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Voice recognition is supported in Google Chrome and Microsoft Edge.");
      return;
    }

    const micBtn = document.getElementById("nav-mic-btn");
    const searchInput = document.getElementById("twotabsearchtextbox");

    if (window.activeVoiceRecognition) {
      try { window.activeVoiceRecognition.stop(); } catch(e){}
      window.activeVoiceRecognition = null;
      if (micBtn) micBtn.classList.remove("listening");
      if (searchInput) searchInput.placeholder = "Search CloudMart or tap mic...";
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = window.currentVoiceLang || 'en-IN';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    if (micBtn) micBtn.classList.add("listening");
    if (searchInput) searchInput.placeholder = "🎙️ Listening... Speak now";

    recognition.onresult = function(event) {
      let query = (event.results[0][0].transcript || "").trim();
      let clean = query.toLowerCase();

      // Clean conversational prefixes
      const fillers = [
        "search for", "search", "show me", "can you show", "show",
        "find me", "find", "looking for", "i want to buy", "buy", "order",
        "price of", "parungoa", "kaattu", "dikhaiye"
      ];
      for (const f of fillers) {
        if (clean.startsWith(f + " ")) {
          clean = clean.slice(f.length + 1).trim();
          break;
        }
      }

      const finalQuery = clean || query;
      if (searchInput) {
        searchInput.value = finalQuery;
        searchInput.placeholder = "Search CloudMart or tap mic...";
      }

      if (typeof window.executeSearchFilter === 'function') {
        window.executeSearchFilter(finalQuery);
      } else {
        window.location.href = "/?search=" + encodeURIComponent(finalQuery);
      }
    };

    recognition.onerror = function(event) {
      console.warn("Speech recognition error:", event.error);
      if (micBtn) micBtn.classList.remove("listening");
      if (searchInput) searchInput.placeholder = "Search CloudMart or tap mic...";
      if (event.error === 'not-allowed') {
        alert("Microphone permission was denied. Please allow microphone access in your browser bar.");
      }
    };

    recognition.onend = function() {
      if (micBtn) micBtn.classList.remove("listening");
      if (searchInput && searchInput.placeholder.includes("Listening")) {
        searchInput.placeholder = "Search CloudMart or tap mic...";
      }
      window.activeVoiceRecognition = null;
    };

    window.activeVoiceRecognition = recognition;
    recognition.start();
  };

  window.triggerHeaderSearch = function() {
    const input = document.getElementById("twotabsearchtextbox");
    const query = input ? input.value.trim() : "";
    if (typeof window.executeSearchFilter === 'function') {
      window.executeSearchFilter(query);
    } else {
      window.location.href = "/?search=" + encodeURIComponent(query);
    }
  };

  window.logoutUser = function() {
    localStorage.removeItem("cloudmart_token");
    localStorage.removeItem("cloudmart_user");
    window.location.href = "/login";
  };

  window.addEventListener("DOMContentLoaded", renderHeader);
  window.updateCartBadge = function() {
    const badge = document.getElementById("nav-cart-count");
    if (badge) badge.innerText = getCartCount();
  };
})();
