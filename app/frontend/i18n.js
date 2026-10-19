/* CloudMart i18n: EN / HI / TA — persisted in localStorage, zero deps */
const I18N = {
  en: { search: "Search CloudMart products...", cart: "Cart", orders: "Orders", signout: "Sign Out", tagline: "Protected by Dual-Factor Geofenced Delivery Logistics Handshake." },
  hi: { search: "CloudMart उत्पाद खोजें...", cart: "कार्ट", orders: "ऑर्डर", signout: "साइन आउट", tagline: "डुअल-फैक्टर जियोफेंस्ड डिलीवरी द्वारा सुरक्षित।" },
  ta: { search: "CloudMart தயாரிப்புகளைத் தேடுக...", cart: "கூடை", orders: "ஆர்டர்கள்", signout: "வெளியேறு", tagline: "இரட்டை-காரணி புவிவேலி டெலிவரி பாதுகாப்பு।" },
};
function getLang() { return localStorage.getItem("cm_lang") || "en"; }
function setLang(l) { localStorage.setItem("cm_lang", l); location.reload(); }
function t(k) { return (I18N[getLang()] || I18N.en)[k] || I18N.en[k] || k; }
function langPickerHTML() {
  const l = getLang();
  return `<select onchange="setLang(this.value)" style="background:#232f3e;color:#fff;border:1px solid #555;border-radius:4px;padding:4px 8px;font-size:12px;font-weight:700;">
    <option value="en"${l === "en" ? " selected" : ""}>English</option>
    <option value="hi"${l === "hi" ? " selected" : ""}>हिन्दी</option>
    <option value="ta"${l === "ta" ? " selected" : ""}>தமிழ்</option></select>`;
}
