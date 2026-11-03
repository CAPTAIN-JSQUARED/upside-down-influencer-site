document.addEventListener('DOMContentLoaded', function () {
  // Footer year
  var yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  // Mobile nav toggle
  var navToggle = document.getElementById('navToggle');
  var nav = document.getElementById('primary-nav');
  if (navToggle && nav) {
    navToggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  // YouTube embed modal
  var modal = document.getElementById('videoModal');
  var frame = document.getElementById('videoModalFrame');

  function openVideo(embedUrl) {
    if (!embedUrl || !modal || !frame) return;
    frame.innerHTML = '<iframe src="' + embedUrl + '?autoplay=1&rel=0" ' +
      'title="Episode player" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>';
    modal.hidden = false;
    document.body.style.overflow = 'hidden';
  }

  function closeVideo() {
    if (!modal || !frame) return;
    modal.hidden = true;
    frame.innerHTML = '';
    document.body.style.overflow = '';
  }

  document.querySelectorAll('[data-embed-url]').forEach(function (el) {
    el.addEventListener('click', function () {
      var embedUrl = el.getAttribute('data-embed-url');
      if (embedUrl) openVideo(embedUrl);
    });
  });

  if (modal) {
    modal.querySelectorAll('[data-close]').forEach(function (el) {
      el.addEventListener('click', closeVideo);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeVideo();
    });
  }
});
