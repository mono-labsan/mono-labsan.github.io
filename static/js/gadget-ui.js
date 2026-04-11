/*!
 * ガジェット比較ナビ — UI Enhancement
 */
(function () {
  'use strict';

  /* 1. Reading progress bar -------------------------------- */
  function initProgressBar() {
    const bar = document.createElement('div');
    bar.className = 'reading-progress';
    document.body.prepend(bar);
    function update() {
      const h = document.documentElement.scrollHeight - window.innerHeight;
      bar.style.width = h > 0 ? (window.scrollY / h * 100) + '%' : '0%';
    }
    window.addEventListener('scroll', update, { passive: true });
  }

  /* 2. Back-to-top button ---------------------------------- */
  function initBackToTop() {
    const btn = document.createElement('button');
    btn.className = 'back-to-top';
    btn.innerHTML = '↑';
    btn.setAttribute('aria-label', 'ページトップへ');
    document.body.appendChild(btn);
    window.addEventListener('scroll', () => {
      btn.classList.toggle('visible', window.scrollY > 480);
    }, { passive: true });
    btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
  }

  /* 3. Scroll fade-in for cards ---------------------------- */
  function initFadeIn() {
    if (!('IntersectionObserver' in window)) return;
    const obs = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) { e.target.classList.add('is-visible'); obs.unobserve(e.target); }
      });
    }, { threshold: 0.07, rootMargin: '0px 0px -32px 0px' });
    document.querySelectorAll('article.post-entry, article.gh-card').forEach((el, i) => {
      el.classList.add('fade-in');
      el.style.transitionDelay = Math.min(i * 0.06, 0.36) + 's';
      obs.observe(el);
    });
  }

  /* 4. NEW badge on posts < 7 days old -------------------- */
  function addNewBadges() {
    const now = Date.now();
    document.querySelectorAll('article.post-entry').forEach(el => {
      const t = el.querySelector('time');
      if (!t) return;
      const diff = (now - new Date(t.getAttribute('datetime'))) / 86400000;
      if (diff < 7) {
        const b = document.createElement('span');
        b.className = 'new-badge';
        b.textContent = 'NEW';
        const cover = el.querySelector('.entry-cover');
        if (cover) cover.appendChild(b);
      }
    });
  }

  /* 5. Button press haptic feel --------------------------- */
  function initButtonFeedback() {
    document.addEventListener('mousedown', e => {
      const btn = e.target.closest('a[href*="amazon.co.jp"], .back-to-top, .btn');
      if (btn) btn.style.transform = 'scale(0.96)';
    });
    document.addEventListener('mouseup', e => {
      const btn = e.target.closest('a[href*="amazon.co.jp"], .back-to-top, .btn');
      if (btn) { btn.style.transform = ''; }
    });
  }

  /* 6. Homepage category filter --------------------------- */
  function initCategoryFilter() {
    const pills = document.querySelectorAll('.gh-cat-pill');
    const cards = document.querySelectorAll('.gh-card');
    if (!pills.length || !cards.length) return;

    pills.forEach(pill => {
      pill.addEventListener('click', e => {
        e.preventDefault();
        const active = pill.classList.contains('is-active');

        // Reset all
        pills.forEach(p => p.classList.remove('is-active'));
        cards.forEach(c => c.classList.remove('is-hidden'));

        if (active) return; // click again to deselect

        // Get category name from pill text (strip count)
        const cat = pill.textContent.trim().replace(/\d+$/, '').trim();
        pill.classList.add('is-active');

        cards.forEach(card => {
          const badges = card.querySelectorAll('.gh-cat-badge');
          const match = Array.from(badges).some(b => b.textContent.trim() === cat);
          if (!match) card.classList.add('is-hidden');
        });
      });
    });
  }

  /* 7. Smooth image load ---------------------------------- */
  function initImageFade() {
    document.querySelectorAll('img[loading="lazy"]').forEach(img => {
      img.style.opacity = '0';
      img.style.transition = 'opacity 0.4s ease';
      if (img.complete) {
        img.style.opacity = '1';
      } else {
        img.addEventListener('load', () => { img.style.opacity = '1'; });
      }
    });
  }

  /* Init -------------------------------------------------- */
  document.addEventListener('DOMContentLoaded', () => {
    initProgressBar();
    initBackToTop();
    initFadeIn();
    addNewBadges();
    initButtonFeedback();
    initCategoryFilter();
    initImageFade();
  });
})();
