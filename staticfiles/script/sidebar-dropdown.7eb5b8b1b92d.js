/**
 * Sidebar Dropdown Menu Handler
 * Gère l'ouverture et la fermeture des sous-menus dans le sidebar
 */
(function() {
  'use strict';

  console.log('[Sidebar Dropdown] Script loaded');

  // Fonction d'initialisation
  function initSidebarDropdowns() {
    console.log('[Sidebar Dropdown] Initializing...');

    // Sélectionner tous les éléments dropdown toggle
    const dropdownToggles = document.querySelectorAll('.sidebar-dropdown > .dropdown-toggle');
    console.log('[Sidebar Dropdown] Found ' + dropdownToggles.length + ' dropdown toggles');

    dropdownToggles.forEach(function(toggle, index) {
      console.log('[Sidebar Dropdown] Setting up toggle #' + index);

      toggle.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();

        console.log('[Sidebar Dropdown] Toggle clicked');

        const parentDropdown = this.parentElement;
        const isActive = parentDropdown.classList.contains('active');

        // Fermer tous les autres dropdowns (comportement accordion)
        closeAllDropdowns();

        // Toggle le dropdown courant
        if (!isActive) {
          parentDropdown.classList.add('active');
          console.log('[Sidebar Dropdown] Opened dropdown');
        } else {
          console.log('[Sidebar Dropdown] Closed dropdown');
        }

        return false;
      });
    });

    // Empêcher la fermeture lors du clic sur un lien du sous-menu
    const submenuLinks = document.querySelectorAll('.sidebar-submenu a');
    console.log('[Sidebar Dropdown] Found ' + submenuLinks.length + ' submenu links');

    submenuLinks.forEach(function(link) {
      link.addEventListener('click', function(e) {
        e.stopPropagation();
        // Le lien fonctionne normalement
      });
    });

    console.log('[Sidebar Dropdown] Initialization complete');
  }

  function closeAllDropdowns() {
    const activeDropdowns = document.querySelectorAll('.sidebar-dropdown.active');
    activeDropdowns.forEach(function(dropdown) {
      dropdown.classList.remove('active');
    });
  }

  // Attendre que le DOM et jQuery soient chargés
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSidebarDropdowns);
  } else {
    // DOM déjà chargé
    initSidebarDropdowns();
  }

  // Alternative avec jQuery si disponible
  if (typeof jQuery !== 'undefined') {
    jQuery(document).ready(function() {
      console.log('[Sidebar Dropdown] jQuery ready, reinitializing if needed');
      // Vérifier si déjà initialisé
      if (document.querySelectorAll('.sidebar-dropdown > .dropdown-toggle').length > 0) {
        const hasListeners = document.querySelector('.sidebar-dropdown > .dropdown-toggle').__listeners__;
        if (!hasListeners) {
          initSidebarDropdowns();
        }
      }
    });
  }

  // Exposer les fonctions globalement
  window.sidebarDropdown = {
    init: initSidebarDropdowns,
    closeAll: closeAllDropdowns
  };

  console.log('[Sidebar Dropdown] Script setup complete');
})();
