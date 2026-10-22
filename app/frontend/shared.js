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

function renderAmazonHeaderInto(containerId, activePage = '') {
    const container = document.getElementById(containerId);
    if (!container) return;

    const user = getCurrentUser();
    const userGreeting = user ? `Hello, ${user.name.split(' ')[0]}` : 'Hello, Sign In';

    container.innerHTML = `
    <header class="amz-header">
        <div class="amz-nav-top">
            <a href="/" class="amz-logo">CloudMart<span>.in</span></a>
            
            <div class="amz-deliver-box" onclick="location.href='/checkout'">
                <span style="font-size:11px; color:#ccc;">Deliver to ${user ? user.name.split(' ')[0] : 'Guest'}</span>
                <strong style="font-size:13px; color:#fff;">Vellore 632014</strong>
            </div>

            <!-- Amazon Search Bar with Integrated Regional Voice Search -->
            <div class="amz-search-bar">
                <input type="text" id="globalSearchInput" placeholder="Search products or tap mic to speak..." 
                       onkeyup="if(event.key==='Enter') executeSearch()">
                <button type="button" class="btn-mic" id="navMicBtn" title="Speak in Tamil, Hindi, or English" onclick="openVoiceSearchModal()">🎙️</button>
                <button type="button" onclick="executeSearch()">🔍</button>
            </div>

            <div class="amz-nav-actions">
                <a href="#" class="amz-nav-link" onclick="handleLogout()">
                    <span style="font-size:11px;">${userGreeting}</span>
                    <strong style="font-size:13px;">Sign Out</strong>
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
            <a href="/?cat=Office">Office</a>
            <a href="/?cat=Fashion">Fashion</a>
            <a href="/?cat=Books">Books</a>
            <a href="/orders">Order History</a>
            <a href="/tracking">Logistics Handshake</a>
        </div>
    </header>

    <!-- Regional Voice Search Modal -->
    <div id="voiceModal" class="voice-modal-overlay">
        <div class="voice-card">
            <span class="voice-close-btn" onclick="closeVoiceSearchModal()">✕</span>
            <div class="voice-pulse-circle" id="voicePulseRing">
                <span style="font-size:36px;">🎙️</span>
            </div>
            <h3 id="voiceStatusTitle" style="font-size:18px; font-weight:700; margin-top:15px;">Listening...</h3>
            <p id="voiceLiveTranscript" style="font-size:14px; color:#007185; min-height:45px; margin:10px 0; font-weight:600;">
                Speak into your microphone...
            </p>

            <div style="margin-top:10px; border-top:1px solid #eee; padding-top:12px;">
                <label style="font-size:12px; font-weight:700; color:#555;">Choose Voice Language:</label>
                <div style="display:flex; justify-content:center; gap:8px; margin-top:8px;">
                    <button class="voice-lang-btn active" id="btnLangTa" onclick="setVoiceLang('ta-IN', this)">தமிழ் (Tamil)</button>
                    <button class="voice-lang-btn" id="btnLangHi" onclick="setVoiceLang('hi-IN', this)">हिन्दी (Hindi)</button>
                    <button class="voice-lang-btn" id="btnLangEn" onclick="setVoiceLang('en-IN', this)">English (India)</button>
                </div>
            </div>
        </div>
    </div>
    `;

    updateCartCount();
}

// ----------------- WEB SPEECH API RECOGNITION -----------------
let activeVoiceLang = 'ta-IN';
let speechRecognizer = null;

function setVoiceLang(langCode, btnEl) {
    activeVoiceLang = langCode;
    document.querySelectorAll('.voice-lang-btn').forEach(b => b.classList.remove('active'));
    if (btnEl) btnEl.classList.add('active');
    if (speechRecognizer) {
        speechRecognizer.abort();
        startListeningSession();
    }
}

function openVoiceSearchModal() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert("Speech Recognition is not supported by your current browser. Please open in Google Chrome or Microsoft Edge.");
        return;
    }
    const modal = document.getElementById('voiceModal');
    if (modal) modal.style.display = 'flex';
    startListeningSession();
}

function closeVoiceSearchModal() {
    if (speechRecognizer) speechRecognizer.abort();
    const modal = document.getElementById('voiceModal');
    if (modal) modal.style.display = 'none';
}

function startListeningSession() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    speechRecognizer = new SpeechRecognition();
    speechRecognizer.lang = activeVoiceLang;
    speechRecognizer.interimResults = true;
    speechRecognizer.maxAlternatives = 1;

    const transcriptEl = document.getElementById('voiceLiveTranscript');
    const titleEl = document.getElementById('voiceStatusTitle');

    titleEl.innerText = activeVoiceLang === 'ta-IN' ? 'பேசுங்கள்... (Listening in Tamil)' : 
                       activeVoiceLang === 'hi-IN' ? 'बोलिए... (Listening in Hindi)' : 'Listening in English...';

    speechRecognizer.onresult = (event) => {
        let currentTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            currentTranscript += event.results[i][0].transcript;
        }
        transcriptEl.innerText = `"${currentTranscript}"`;

        if (event.results[0].isFinal) {
            processVoiceTranscript(currentTranscript);
        }
    };

    speechRecognizer.onerror = (event) => {
        titleEl.innerText = "Could not hear audio";
        transcriptEl.innerText = `Error: ${event.error}. Please allow microphone permissions and try again.`;
    };

    speechRecognizer.start();
}

async function processVoiceTranscript(rawText) {
    try {
        const res = await fetch(`${API}/voice-search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ transcript: rawText, lang: activeVoiceLang })
        });
        const data = await res.json();
        const searchKeyword = data.normalized_query || rawText;

        document.getElementById('globalSearchInput').value = searchKeyword;
        setTimeout(() => {
            closeVoiceSearchModal();
            location.href = `/?search=${encodeURIComponent(searchKeyword)}`;
        }, 800);
    } catch(e) {
        closeVoiceSearchModal();
        location.href = `/?search=${encodeURIComponent(rawText)}`;
    }
}

function executeSearch() {
    const q = document.getElementById('globalSearchInput').value.trim();
    if (q) location.href = `/?search=${encodeURIComponent(q)}`;
}

function handleLogout() {
    if (confirm("Sign out of CloudMart?")) {
        localStorage.removeItem('cloudmart_jwt');
        localStorage.removeItem('cloudmart_user');
        location.href = '/';
    }
}
