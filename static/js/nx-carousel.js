/* Carrousel léger, sans dépendance, basé sur le défilement natif (scroll-snap).
 *
 * <div data-nx-carousel                     les enfants directs sont les éléments
 *      data-nx-label="Captures de l'app"    nom accessible du carrousel
 *      data-nx-item="Écran"                 nom d'un élément (« Écran 2 sur 6 »)
 *      data-nx-max="700">                   facultatif : carrousel seulement sous cette largeur (px),
 *   ...                                      au-dessus la mise en page d'origine est conservée
 * </div>
 *
 * Le glissement tactile et la molette sont ceux du navigateur ; le script ajoute les boutons,
 * la pagination, le clavier, l'état courant (.is-current) et l'événement « nx-carousel:change ».
 * Styles : static/css/nx-carousel.css.
 */
(function () {
  'use strict';
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');

  function make(tag, cls, attrs) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    for (var k in attrs || {}) e.setAttribute(k, attrs[k]);
    return e;
  }

  function arrow(dir) {
    return '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="' +
      (dir < 0 ? 'M15 5l-7 7 7 7' : 'M9 5l7 7-7 7') +
      '" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  }

  function Carousel(track) {
    this.track = track;
    this.slides = Array.prototype.slice.call(track.children);
    this.item = track.getAttribute('data-nx-item') || 'Élément';
    this.index = -1;
    this.active = false;
    var max = parseInt(track.getAttribute('data-nx-max'), 10);
    this.mq = max ? window.matchMedia('(max-width: ' + max + 'px)') : null;

    this.handleBrokenImages();
    if (this.slides.length < 2) return;          // rien à faire défiler : pas de commandes

    this.build();
    var self = this, raf = 0, settle = 0;
    track.addEventListener('scroll', function () {
      if (!raf) raf = requestAnimationFrame(function () { raf = 0; self.sync(false); });
      clearTimeout(settle);
      settle = setTimeout(function () { self.sync(true); }, 160);
    }, { passive: true });
    track.addEventListener('keydown', function (e) { self.onKey(e); });
    window.addEventListener('resize', function () { self.sync(false); });
    if (this.mq) {
      var onChange = function () { self.setActive(self.mq.matches); };
      if (this.mq.addEventListener) this.mq.addEventListener('change', onChange); else this.mq.addListener(onChange);
    }
    this.setActive(this.mq ? this.mq.matches : true);
  }

  Carousel.prototype.build = function () {
    var self = this, n = this.slides.length;
    this.controls = make('div', 'nxc-controls');
    this.prev = make('button', 'nxc-btn nxc-prev', { type: 'button', 'aria-label': this.item + ' précédent' });
    this.next = make('button', 'nxc-btn nxc-next', { type: 'button', 'aria-label': this.item + ' suivant' });
    this.prev.innerHTML = arrow(-1);
    this.next.innerHTML = arrow(1);
    this.dots = make('div', 'nxc-dots');
    this.dotEls = this.slides.map(function (s, i) {
      var d = make('button', 'nxc-dot', { type: 'button', 'aria-label': self.item + ' ' + (i + 1) + ' sur ' + n });
      d.addEventListener('click', function () { self.go(i); });
      self.dots.appendChild(d);
      return d;
    });
    this.count = make('span', 'nxc-count', { 'aria-hidden': 'true' });
    this.status = make('span', 'nxc-sr', { 'aria-live': 'polite' });
    this.prev.addEventListener('click', function () { self.go(self.index - 1); });
    this.next.addEventListener('click', function () { self.go(self.index + 1); });
    this.controls.appendChild(this.prev);
    this.controls.appendChild(this.dots);
    this.controls.appendChild(this.count);
    this.controls.appendChild(this.next);
    this.controls.appendChild(this.status);
    this.track.parentNode.insertBefore(this.controls, this.track.nextSibling);
  };

  Carousel.prototype.setActive = function (on) {
    var t = this.track;
    this.active = on;
    t.classList.toggle('nxc', on);
    this.controls.hidden = !on;
    if (on) {
      t.setAttribute('role', 'region');
      t.setAttribute('aria-roledescription', 'carrousel');
      t.setAttribute('aria-label', t.getAttribute('data-nx-label') || 'Carrousel');
      t.setAttribute('tabindex', '0');
      this.index = -1;
      this.sync(false);
    } else {
      ['role', 'aria-roledescription', 'aria-label', 'tabindex'].forEach(function (a) { t.removeAttribute(a); });
      this.slides.forEach(function (s) { s.classList.remove('is-current'); });
    }
  };

  // centre d'un élément dans le repère de défilement de la piste (le centre ne bouge pas avec l'effet d'échelle)
  Carousel.prototype.center = function (s) {
    var r = s.getBoundingClientRect();
    return r.left + r.width / 2 - this.track.getBoundingClientRect().left + this.track.scrollLeft;
  };

  // élément le plus proche du centre de la zone visible
  Carousel.prototype.current = function () {
    var self = this, t = this.track, mid = t.scrollLeft + t.clientWidth / 2, best = 0, bestD = Infinity;
    if (t.scrollLeft <= 2) return 0;
    if (t.scrollLeft + t.clientWidth >= t.scrollWidth - 2) return this.slides.length - 1;
    this.slides.forEach(function (s, i) {
      var d = Math.abs(self.center(s) - mid);
      if (d < bestD) { bestD = d; best = i; }
    });
    return best;
  };

  Carousel.prototype.sync = function (announce) {
    if (!this.active) return;
    var i = this.current(), n = this.slides.length;
    if (i !== this.index) {
      this.index = i;
      this.slides.forEach(function (s, k) { s.classList.toggle('is-current', k === i); });
      this.dotEls.forEach(function (d, k) { if (k === i) d.setAttribute('aria-current', 'true'); else d.removeAttribute('aria-current'); });
      this.prev.disabled = i === 0;
      this.next.disabled = i === n - 1;
      this.count.textContent = (i + 1) + ' / ' + n;
      this.track.dispatchEvent(new CustomEvent('nx-carousel:change', { detail: { index: i, total: n } }));
    }
    if (announce) this.status.textContent = this.item + ' ' + (i + 1) + ' sur ' + n;
  };

  Carousel.prototype.go = function (i) {
    i = Math.max(0, Math.min(this.slides.length - 1, i));
    var t = this.track, left = this.center(this.slides[i]) - t.clientWidth / 2;
    t.scrollTo({ left: left, behavior: reduce.matches ? 'auto' : 'smooth' });
  };

  Carousel.prototype.onKey = function (e) {
    if (!this.active || e.target !== this.track) return;
    var map = { ArrowLeft: this.index - 1, ArrowRight: this.index + 1, Home: 0, End: this.slides.length - 1 };
    if (!(e.key in map)) return;
    e.preventDefault();
    this.go(map[e.key]);
  };

  // une capture qui ne se charge pas laisse un cadre lisible au lieu d'une icône cassée
  Carousel.prototype.handleBrokenImages = function () {
    this.track.querySelectorAll('img').forEach(function (img) {
      var fail = function () {
        if (img.dataset.nxBroken) return;
        img.dataset.nxBroken = '1';
        var ph = make('div', 'nxc-missing', { role: 'img', 'aria-label': img.alt || 'Image indisponible' });
        ph.textContent = 'Capture indisponible';
        img.replaceWith(ph);
      };
      if (img.complete && img.naturalWidth === 0 && img.getAttribute('src')) fail();
      else img.addEventListener('error', fail);
    });
  };

  function init(root) {
    (root || document).querySelectorAll('[data-nx-carousel]').forEach(function (t) {
      if (!t.nxCarousel) t.nxCarousel = new Carousel(t);
    });
  }

  window.NxCarousel = { init: init };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { init(); });
  else init();
})();
