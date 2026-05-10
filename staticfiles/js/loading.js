/**
 * Loading — spinner global pour toutes les opérations réseau.
 *
 * - Patche window.fetch et $.ajax automatiquement.
 * - N'affiche le spinner qu'après 300 ms (évite le flash sur requêtes rapides).
 * - Gère les requêtes concurrentes avec un compteur.
 * - Expose window.Loading.show() / .hide() pour usage manuel.
 */
(function () {
    'use strict';

    let _pending = 0;
    let _showTimer = null;
    const DELAY_MS = 300;

    const overlay = document.getElementById('global-loading-overlay');

    function _show() {
        if (!overlay) return;
        overlay.classList.add('active');
        overlay.setAttribute('aria-hidden', 'false');
    }

    function _hide() {
        if (!overlay) return;
        overlay.classList.remove('active');
        overlay.setAttribute('aria-hidden', 'true');
    }

    function _increment() {
        _pending++;
        if (_pending === 1) {
            // Premier appel : délai avant affichage
            _showTimer = setTimeout(_show, DELAY_MS);
        }
    }

    function _decrement() {
        _pending = Math.max(0, _pending - 1);
        if (_pending === 0) {
            clearTimeout(_showTimer);
            _showTimer = null;
            _hide();
        }
    }

    // ── API publique ────────────────────────────────────────────────────────
    window.Loading = {
        show: function () { _pending++; _show(); },
        hide: function () { _pending = Math.max(0, _pending - 1); if (_pending === 0) _hide(); },
    };

    // ── Patch fetch ─────────────────────────────────────────────────────────
    const _nativeFetch = window.fetch;
    window.fetch = function (input, init) {
        // Ne pas spinner pour les polling silencieux (ex: alertes en arrière-plan)
        const url = (typeof input === 'string') ? input : (input && input.url) || '';
        const silent = (init && init._silent) || url.includes('/API/alerts/');
        if (!silent) _increment();
        return _nativeFetch.apply(this, arguments).finally(function () {
            if (!silent) _decrement();
        });
    };

    // ── Patch $.ajax (jQuery) ───────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', function () {
        if (window.$ && $.ajaxSetup) {
            $(document).ajaxStart(function () { _increment(); });
            $(document).ajaxStop(function ()  { _decrement(); });
        }
    });
})();
