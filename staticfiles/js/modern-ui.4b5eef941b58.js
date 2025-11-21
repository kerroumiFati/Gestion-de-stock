/**
 * Modern UI - Gestion du sidebar et interactions
 */
(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        const sidebar = document.getElementById('sidebar');
        const body = document.body;

        // Fonction pour toggle le sidebar
        function toggleSidebar() {
            if (sidebar) {
                const isDesktop = window.innerWidth >= 993;

                if (isDesktop) {
                    // Desktop: toggle collapsed state
                    sidebar.classList.toggle('sidebar-collapsed');
                    body.classList.toggle('sidebar-collapsed');

                    // Sauvegarder l'état dans localStorage
                    const isCollapsed = sidebar.classList.contains('sidebar-collapsed');
                    localStorage.setItem('sidebar-collapsed', isCollapsed);
                } else {
                    // Mobile: toggle collapsed state (logique inversée)
                    sidebar.classList.toggle('sidebar-collapsed');
                }
            }
        }

        // Restaurer l'état du sidebar depuis localStorage (desktop uniquement)
        if (window.innerWidth >= 993) {
            const savedState = localStorage.getItem('sidebar-collapsed');
            if (savedState === 'true') {
                sidebar?.classList.add('sidebar-collapsed');
                body.classList.add('sidebar-collapsed');
            }
        }

        // Bouton toggle dans le header (toujours visible)
        const headerToggle = document.getElementById('sidebar-menu-toggle');
        if (headerToggle) {
            headerToggle.addEventListener('click', toggleSidebar);
        }

        // Bouton toggle dans le sidebar (pour fermer depuis l'intérieur)
        const sidebarToggle = document.querySelector('.sidebar-toggle');
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', toggleSidebar);
        }

        // Theme Toggle
        const themeToggle = document.querySelector('.theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', function() {
                const html = document.documentElement;
                const currentTheme = html.getAttribute('data-theme');
                const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

                html.setAttribute('data-theme', newTheme);
                localStorage.setItem('theme', newTheme);

                // Update icon
                const icon = this.querySelector('i') || document.createElement('i');
                icon.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
                if (!this.querySelector('i')) {
                    this.appendChild(icon);
                }
            });

            // Set initial icon
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const icon = document.createElement('i');
            icon.className = currentTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
            themeToggle.appendChild(icon);
        }

        // Close sidebar on mobile when clicking outside
        document.addEventListener('click', function(e) {
            if (window.innerWidth < 992) { // Bootstrap lg breakpoint
                if (!sidebar?.contains(e.target) &&
                    !e.target.closest('.sidebar-menu-toggle') &&
                    !sidebar?.classList.contains('sidebar-collapsed')) {
                    toggleSidebar();
                }
            }
        });

        // Handle responsive behavior
        function handleResize() {
            if (window.innerWidth >= 993) {
                // Desktop: respect localStorage
                const savedState = localStorage.getItem('sidebar-collapsed');
                if (savedState === 'true') {
                    sidebar?.classList.add('sidebar-collapsed');
                    body.classList.add('sidebar-collapsed');
                } else {
                    sidebar?.classList.remove('sidebar-collapsed');
                    body.classList.remove('sidebar-collapsed');
                }
            } else {
                // Mobile: reset to default (caché, sans classe collapsed)
                sidebar?.classList.remove('sidebar-collapsed');
                body.classList.remove('sidebar-collapsed');
            }
        }

        window.addEventListener('resize', handleResize);
    });
})();
