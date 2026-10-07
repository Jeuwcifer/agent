/**
 * smart_effects.js - Visual cursor and click feedback.
 * Injected into the browser DOM to render smooth pointer movements and click ripples.
 * NOTE: On-screen textbars and floating windows are strictly disabled to ensure
 * clean, unoccluded application UI recordings.
 */

(function () {
  window.__vidya = window.__vidya || {};

  // ---------------------------------------------------------------------------
  // 1. Animated SVG Cursor Pointer
  // ---------------------------------------------------------------------------
  window.__vidya.ensureCursor = function () {
    let cursor = document.getElementById('vidya-fake-cursor');
    if (!cursor) {
      cursor = document.createElement('div');
      cursor.id = 'vidya-fake-cursor';
      cursor.style.position = 'fixed';
      cursor.style.left = (window.innerWidth / 2) + 'px';
      cursor.style.top = (window.innerHeight / 2) + 'px';
      cursor.style.width = '26px';
      cursor.style.height = '26px';
      cursor.style.backgroundImage = 'url("data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2226%22 height=%2226%22 viewBox=%220 0 24 24%22 fill=%22white%22 stroke=%22%230f172a%22 stroke-width=%221.75%22 stroke-linejoin=%22round%22%3E%3Cpath d=%22M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z%22/%3E%3C/svg%3E")';
      cursor.style.backgroundSize = 'contain';
      cursor.style.backgroundRepeat = 'no-repeat';
      cursor.style.pointerEvents = 'none';
      cursor.style.zIndex = '2147483647';
      cursor.style.filter = 'drop-shadow(0px 3px 6px rgba(0, 0, 0, 0.5))';
      cursor.style.transition = 'left 0.45s cubic-bezier(0.25, 0.1, 0.25, 1), top 0.45s cubic-bezier(0.25, 0.1, 0.25, 1)';
      document.body.appendChild(cursor);
    }
    return cursor;
  };

  window.__vidya.moveTo = function (x, y) {
    const cursor = window.__vidya.ensureCursor();
    cursor.style.transition = 'left 0.45s cubic-bezier(0.25, 0.1, 0.25, 1), top 0.45s cubic-bezier(0.25, 0.1, 0.25, 1)';
    cursor.style.left = x + 'px';
    cursor.style.top = y + 'px';
  };

  // Zero-latency tracking during native mouse movements / active dragging
  if (!window._vidyaMouseTracking) {
    window._vidyaMouseTracking = true;
    window.addEventListener('mousemove', (e) => {
      const cursor = window.__vidya && window.__vidya.ensureCursor ? window.__vidya.ensureCursor() : document.getElementById('vidya-fake-cursor');
      if (cursor) {
        cursor.style.transition = 'none';
        cursor.style.left = e.clientX + 'px';
        cursor.style.top = e.clientY + 'px';
      }
    }, true);
  }

  // ---------------------------------------------------------------------------
  // 2. Click Ripple Feedback
  // ---------------------------------------------------------------------------
  window.__vidya.clickRipple = function (x, y, color) {
    const rippleColor = color || 'rgba(56, 189, 248, 0.55)';
    const borderColor = color ? color.replace('0.55', '0.95') : 'rgba(14, 165, 233, 0.95)';

    const ripple = document.createElement('div');
    ripple.className = 'vidya-click-ripple';
    ripple.style.position = 'fixed';
    ripple.style.left = (x - 18) + 'px';
    ripple.style.top = (y - 18) + 'px';
    ripple.style.width = '36px';
    ripple.style.height = '36px';
    ripple.style.borderRadius = '50%';
    ripple.style.backgroundColor = rippleColor;
    ripple.style.border = '2.5px solid ' + borderColor;
    ripple.style.pointerEvents = 'none';
    ripple.style.zIndex = '2147483646';
    ripple.style.boxShadow = '0 0 16px ' + rippleColor;
    ripple.style.transform = 'scale(0.7)';
    ripple.style.opacity = '1';
    ripple.style.transition = 'transform 0.45s cubic-bezier(0.1, 0.9, 0.2, 1), opacity 0.45s ease-out';
    document.body.appendChild(ripple);

    requestAnimationFrame(() => {
      ripple.style.transform = 'scale(2.4)';
      ripple.style.opacity = '0';
    });

    setTimeout(() => {
      ripple.remove();
    }, 500);
  };

  window.__vidya.highlightElement = function (selectorOrEl) {
    let el = typeof selectorOrEl === 'string' ? document.querySelector(selectorOrEl) : selectorOrEl;
    if (!el) return;
    const origOutline = el.style.outline;
    const origTransition = el.style.transition;
    el.style.transition = 'outline 0.3s ease';
    el.style.outline = '3px solid rgba(56, 189, 248, 0.85)';
    setTimeout(() => {
      el.style.outline = origOutline;
      el.style.transition = origTransition;
    }, 1500);
  };

  // ---------------------------------------------------------------------------
  // 3. On-Screen Floating Textbars / Caption Bars (Permanently Disabled)
  // ---------------------------------------------------------------------------
  window.__vidya.showBanner = function () {
    const existing = document.getElementById('vidya-instruction-banner');
    if (existing) existing.remove();
  };

  window.__vidya.hideBanner = function () {
    const existing = document.getElementById('vidya-instruction-banner');
    if (existing) existing.remove();
  };

  // ---------------------------------------------------------------------------
  // 4. Floating Instructional Windows (Permanently Disabled)
  // ---------------------------------------------------------------------------
  window.__vidya.showWindow = function () {
    const existing = document.getElementById('vidya-instruction-window');
    if (existing) existing.remove();
  };

  window.__vidya.hideWindow = function () {
    const existing = document.getElementById('vidya-instruction-window');
    if (existing) existing.remove();
  };
})();
