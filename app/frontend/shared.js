// CloudMart Unified Shared Navigation & English Voice Assistant
(function() {
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
            <input type="text" id="twotabsearchtextbox" class="nav-search-input" placeholder="Search Amazon in English or tap mic..." autocomplete="off">
            <button type="button" id="nav-mic-btn" class="nav-mic-btn" title="Click to speak in English" onclick="window.startEnglishVoiceSearch()">
              🎙️
            </button>
            <button type="submit" class="nav-search-btn" title="Search">
              🔍
            </button>
          </form>
        </div>

        <div class="nav-right">
          <div class="nav-lang-badge">
            <span class="flag-icon">🇮🇳</span> <span>EN</span>
          </div>

          <div class="nav-account-dropdown">
            <a href="${user ? '/orders' : '/login'}" class="nav-link">
              <span class="nav-line-1">Hello, ${user ? user.name.split(' ')[0] : 'sign in'}</span>
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
        <a href="${role === 'seller' ? '/?view=seller' : '/?view=customer'}" class="subnav-link seller-switch" id="role-switch-link">
          ${role === 'seller' ? 'Switch to Customer View' : 'Sell on CloudMart (Seller Central)'}
        </a>
      </nav>
    `;
  }

  // English-only Speech Recognition
  window.startEnglishVoiceSearch = function() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Voice recognition is supported in Google Chrome and Microsoft Edge. Please open this page in Chrome or Edge.");
      return;
    }

    const micBtn = document.getElementById("nav-mic-btn");
    const searchInput = document.getElementById("twotabsearchtextbox");

    if (window.activeVoiceRecognition) {
      try { window.activeVoiceRecognition.stop(); } catch(e){}
      window.activeVoiceRecognition = null;
      if (micBtn) micBtn.classList.remove("listening");
      if (searchInput) searchInput.placeholder = "Search Amazon in English...";
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-IN'; // Indian English dialect (compatible with en-US)
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    if (micBtn) {
      micBtn.classList.add("listening");
      micBtn.title = "Listening... Speak in English now";
    }
    if (searchInput) {
      searchInput.placeholder = "🎙️ Listening... Speak your search in English";
    }

    recognition.onresult = function(event) {
      let query = event.results[0][0].transcript || "";
      console.log("Spoken English text:", query);

      // Clean conversational filler words
      let clean = query.trim().toLowerCase();
      const fillers = [
        "search for", "please search for", "search",
        "show me", "can you show me", "can you show", "show",
        "find me", "can you find me", "find",
        "looking for", "i am looking for", "i'm looking for",
        "i want to buy", "i want", "buy", "order", "get me",
        "what is the price of", "price of"
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
        searchInput.placeholder = "Search Amazon in English...";
      }

      // Execute search
      if (typeof window.executeSearchFilter === 'function') {
        window.executeSearchFilter(finalQuery);
      } else {
        window.location.href = "/?search=" + encodeURIComponent(finalQuery);
      }
    };

    recognition.onerror = function(event) {
      console.warn("Speech recognition error:", event.error);
      if (micBtn) micBtn.classList.remove("listening");
      if (searchInput) searchInput.placeholder = "Search Amazon in English...";
      if (event.error === 'not-allowed') {
        alert("Microphone access was denied. Please allow microphone permissions in your browser address bar.");
      }
    };

    recognition.onend = function() {
      if (micBtn) micBtn.classList.remove("listening");
      if (searchInput && searchInput.placeholder.includes("Listening")) {
        searchInput.placeholder = "Search Amazon in English...";
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
