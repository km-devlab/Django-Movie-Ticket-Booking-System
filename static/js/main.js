(function () {
  'use strict';

  /* Navbar scroll shadow */
  const nav = document.querySelector('.cinema-nav');
  if (nav) {
    const onScroll = () => nav.classList.toggle('scrolled', window.scrollY > 8);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* Active nav link */
  const path = window.location.pathname;
  document.querySelectorAll('.cinema-nav .nav-link[href]').forEach((link) => {
    const href = link.getAttribute('href');
    if (href === path || (href !== '/' && path.startsWith(href))) {
      link.classList.add('active');
    }
  });

  /* Bootstrap form controls on auth/profile forms */
  document.querySelectorAll('.auth-card input, .auth-card select, .auth-card textarea, .panel-card-body input, .panel-card-body select, .panel-card-body textarea, .auth-card-body input, .auth-card-body select, .auth-card-body textarea').forEach((el) => {
    if (el.type === 'checkbox' || el.type === 'radio' || el.type === 'hidden') return;
    el.classList.add('form-control');
  });

  /* Password visibility toggle */
  document.querySelectorAll('[data-toggle-password]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-toggle-password');
      const input = document.getElementById(id);
      const icon = btn.querySelector('i');
      if (!input) return;
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      if (icon) {
        icon.classList.toggle('fa-eye', !show);
        icon.classList.toggle('fa-eye-slash', show);
      }
    });
  });

  /* Seat selection */
  document.querySelectorAll('.seat:not(.sold)').forEach((seatEl) => {
    const checkbox = seatEl.querySelector('input[type="checkbox"]');
    if (!checkbox) return;

    const sync = () => seatEl.classList.toggle('selected', checkbox.checked);

    seatEl.addEventListener('click', (e) => {
      if (e.target === checkbox || e.target.tagName === 'LABEL') return;
      e.preventDefault();
      checkbox.checked = !checkbox.checked;
      sync();
    });

    checkbox.addEventListener('change', sync);
    sync();
  });

  /* Client-side movie search filter */
  const searchInput = document.querySelector('[data-movie-search]');
  const movieList = document.getElementById('movieList');
  if (searchInput && movieList) {
    searchInput.addEventListener('input', () => {
      const term = searchInput.value.toLowerCase();
      movieList.querySelectorAll('[data-movie-card]').forEach((col) => {
        const title = col.querySelector('.movie-card-title')?.textContent.toLowerCase() || '';
        col.style.display = title.includes(term) ? '' : 'none';
      });
    });
  }
})();
