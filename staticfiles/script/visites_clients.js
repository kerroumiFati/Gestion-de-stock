/**
 * Visites Clients - JavaScript pour la page des visites clients dans le backoffice
 */

(function() {
    'use strict';

    console.log('[VISITES JS] Script loaded');

    let currentPage = 1;
    let totalPages = 1;
    let visitesData = [];

    // Initialisation
    function init() {
        console.log('[VISITES JS] Initializing...');

        // Mettre la date d'aujourd'hui par defaut
        const today = new Date().toISOString().split('T')[0];
        const dateFilter = document.getElementById('date-filter');
        if (dateFilter) {
            dateFilter.value = today;
        }

        // Charger les livreurs pour le filtre
        loadLivreurs();

        // Ajouter l'event listener pour la recherche de client
        const clientSearch = document.getElementById('client-search');
        if (clientSearch) {
            // Recherche en temps réel avec debounce
            let searchTimeout;
            clientSearch.addEventListener('input', function() {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    loadVisites();
                }, 500); // Attendre 500ms après la dernière frappe
            });

            // Recherche immédiate avec Enter
            clientSearch.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    clearTimeout(searchTimeout);
                    loadVisites();
                }
            });
        }

        // Charger les visites
        loadVisites();
    }

    // Charger la liste des livreurs
    async function loadLivreurs() {
        try {
            const response = await fetch('/API/distribution/livreurs/');
            if (!response.ok) throw new Error('Erreur API');
            const data = await response.json();

            const select = document.getElementById('livreur-filter');
            if (!select) return;

            // Garder l'option "Tous"
            select.innerHTML = '<option value="">Tous les livreurs</option>';

            const livreurs = data.results || data;
            livreurs.forEach(livreur => {
                const option = document.createElement('option');
                option.value = livreur.id;
                option.textContent = livreur.nom || `${livreur.matricule}`;
                select.appendChild(option);
            });

            // Initialiser Select2 sur le select livreur
            initSelect2();
        } catch (error) {
            console.error('[VISITES JS] Erreur chargement livreurs:', error);
        }
    }

    // Initialiser Select2 pour le select livreur
    function initSelect2() {
        if (typeof $ === 'undefined' || typeof $.fn.select2 === 'undefined') {
            console.warn('[VISITES JS] jQuery ou Select2 non disponible');
            return;
        }

        const $livreurSelect = $('#livreur-filter');

        if (!$livreurSelect.length) {
            console.warn('[VISITES JS] Select livreur non trouvé');
            return;
        }

        // Détruire l'instance existante si elle existe
        if ($livreurSelect.data('select2')) {
            $livreurSelect.select2('destroy');
        }

        // Initialiser Select2
        $livreurSelect.select2({
            placeholder: 'Tous les livreurs',
            allowClear: false,
            width: 'resolve',
            language: {
                noResults: function() {
                    return "Aucun livreur trouvé";
                },
                searching: function() {
                    return "Recherche...";
                }
            },
            dropdownAutoWidth: false,
            minimumResultsForSearch: 5 // Afficher la recherche seulement si plus de 5 options
        });

        console.log('[VISITES JS] Select2 initialisé sur le select livreur');
    }

    // Charger les visites
    window.loadVisites = async function(page = 1) {
        currentPage = page;

        const dateFilter = document.getElementById('date-filter');
        const livreurFilter = document.getElementById('livreur-filter');
        const resultatFilter = document.getElementById('resultat-filter');
        const clientSearch = document.getElementById('client-search');

        const date = dateFilter ? dateFilter.value : '';
        const livreur = livreurFilter ? livreurFilter.value : '';
        const resultat = resultatFilter ? resultatFilter.value : '';
        const search = clientSearch ? clientSearch.value.trim() : '';

        // Afficher le loading
        showLoading(true);

        try {
            let url = '/API/visites-clients/?';
            if (date) url += `date=${date}&`;
            if (livreur) url += `livreur=${livreur}&`;
            if (resultat) url += `resultat=${resultat}&`;
            if (search) url += `search=${encodeURIComponent(search)}&`;
            url += `page=${page}`;

            console.log('[VISITES JS] Fetching:', url);

            const response = await fetch(url);
            if (!response.ok) throw new Error('Erreur API');
            const data = await response.json();

            visitesData = data.results || data;

            // Mettre a jour les statistiques
            updateStats(data);

            // Afficher les visites
            displayVisites(visitesData);

            // Pagination
            if (data.count !== undefined) {
                totalPages = Math.ceil(data.count / 20);
                renderPagination();
            }

        } catch (error) {
            console.error('[VISITES JS] Erreur chargement visites:', error);
            showEmpty(true);
        } finally {
            showLoading(false);
        }
    };

    // Mettre a jour les statistiques
    async function updateStats(data) {
        const dateFilter = document.getElementById('date-filter');
        const date = dateFilter ? dateFilter.value : new Date().toISOString().split('T')[0];

        try {
            const statsResponse = await fetch(`/API/visites-clients/stats/?date=${date}`);
            if (statsResponse.ok) {
                const stats = await statsResponse.json();

                document.getElementById('total-visites').textContent = stats.total_visites || 0;
                document.getElementById('total-ventes').textContent = stats.ventes || 0;
                document.getElementById('total-commandes').textContent = stats.commandes || 0;
                document.getElementById('total-absents').textContent = stats.absents || 0;
                document.getElementById('total-refuses').textContent = stats.refuses || 0;
            }
        } catch (error) {
            console.error('[VISITES JS] Erreur stats:', error);
            // Calculer les stats localement
            const visites = data.results || data;
            document.getElementById('total-visites').textContent = visites.length;
            document.getElementById('total-ventes').textContent = visites.filter(v => v.resultat === 'vente').length;
            document.getElementById('total-commandes').textContent = visites.filter(v => v.resultat === 'commande').length;
            document.getElementById('total-absents').textContent = visites.filter(v => v.resultat === 'absent').length;
            document.getElementById('total-refuses').textContent = visites.filter(v => v.resultat === 'refuse').length;
        }
    }

    // Afficher les visites dans la table
    function displayVisites(visites) {
        const tbody = document.getElementById('visites-tbody');
        const table = document.getElementById('visites-table');
        const countEl = document.getElementById('visites-count');

        if (!tbody || !table) return;

        if (!visites || visites.length === 0) {
            showEmpty(true);
            table.style.display = 'none';
            if (countEl) countEl.textContent = '0 visites';
            return;
        }

        showEmpty(false);
        table.style.display = 'table';
        if (countEl) countEl.textContent = `${visites.length} visites`;

        tbody.innerHTML = visites.map(visite => {
            const heure = visite.heure_visite ? formatTime(visite.heure_visite) : '-';
            const clientNom = visite.client_nom || visite.client?.nom || 'Client inconnu';
            const clientAdresse = visite.client_adresse || visite.client?.adresse || '';
            const livreurNom = visite.livreur_nom || visite.livreur?.nom || 'Livreur inconnu';
            const livreurInitials = getInitials(livreurNom);
            const resultat = visite.resultat || 'autre';
            const notes = visite.notes || '-';

            // GPS link
            let gpsHtml = '-';
            if (visite.latitude && visite.longitude) {
                const lat = visite.latitude;
                const lng = visite.longitude;
                gpsHtml = `<a href="https://www.google.com/maps?q=${lat},${lng}" target="_blank" class="gps-link">
                    <i class="fas fa-map-marker-alt"></i> Voir
                </a>`;
            }

            return `
                <tr>
                    <td>${heure}</td>
                    <td>
                        <div class="client-info">
                            <span class="client-name">${escapeHtml(clientNom)}</span>
                            <span class="client-address">${escapeHtml(clientAdresse)}</span>
                        </div>
                    </td>
                    <td>
                        <div class="livreur-info">
                            <div class="livreur-avatar">${livreurInitials}</div>
                            <span>${escapeHtml(livreurNom)}</span>
                        </div>
                    </td>
                    <td>
                        <span class="badge badge-${resultat}">${getResultatLabel(resultat)}</span>
                    </td>
                    <td>${gpsHtml}</td>
                    <td>${escapeHtml(notes)}</td>
                </tr>
            `;
        }).join('');
    }

    // Formater l'heure
    function formatTime(datetime) {
        if (!datetime) return '-';
        const date = new Date(datetime);
        return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    }

    // Obtenir les initiales
    function getInitials(name) {
        if (!name) return '?';
        const parts = name.split(' ');
        if (parts.length >= 2) {
            return (parts[0][0] + parts[1][0]).toUpperCase();
        }
        return name.substring(0, 2).toUpperCase();
    }

    // Obtenir le label du resultat
    function getResultatLabel(resultat) {
        const labels = {
            'vente': 'Vente',
            'commande': 'Commande',
            'absent': 'Absent',
            'ferme': 'Ferme',
            'refuse': 'Refuse',
            'autre': 'Autre'
        };
        return labels[resultat] || resultat;
    }

    // Echapper le HTML
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Afficher/masquer le loading
    function showLoading(show) {
        const loading = document.getElementById('visites-loading');
        if (loading) {
            loading.style.display = show ? 'flex' : 'none';
        }
    }

    // Afficher/masquer l'etat vide
    function showEmpty(show) {
        const empty = document.getElementById('visites-empty');
        if (empty) {
            empty.style.display = show ? 'block' : 'none';
        }
    }

    // Render pagination
    function renderPagination() {
        const container = document.getElementById('pagination');
        if (!container || totalPages <= 1) {
            if (container) container.innerHTML = '';
            return;
        }

        let html = '';

        // Previous
        if (currentPage > 1) {
            html += `<button class="pagination-btn" onclick="loadVisites(${currentPage - 1})">
                <i class="fas fa-chevron-left"></i>
            </button>`;
        }

        // Pages
        for (let i = 1; i <= totalPages; i++) {
            if (i === currentPage) {
                html += `<button class="pagination-btn active">${i}</button>`;
            } else if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
                html += `<button class="pagination-btn" onclick="loadVisites(${i})">${i}</button>`;
            } else if (i === currentPage - 3 || i === currentPage + 3) {
                html += `<span style="padding: 8px;">...</span>`;
            }
        }

        // Next
        if (currentPage < totalPages) {
            html += `<button class="pagination-btn" onclick="loadVisites(${currentPage + 1})">
                <i class="fas fa-chevron-right"></i>
            </button>`;
        }

        container.innerHTML = html;
    }

    // Exporter les visites
    window.exportVisites = function() {
        const dateFilter = document.getElementById('date-filter');
        const date = dateFilter ? dateFilter.value : new Date().toISOString().split('T')[0];

        // Creer un CSV simple
        if (!visitesData || visitesData.length === 0) {
            alert('Aucune donnee a exporter');
            return;
        }

        let csv = 'Heure,Client,Adresse,Livreur,Resultat,Latitude,Longitude,Notes\n';

        visitesData.forEach(v => {
            const heure = v.heure_visite ? formatTime(v.heure_visite) : '';
            const client = v.client_nom || v.client?.nom || '';
            const adresse = (v.client_adresse || v.client?.adresse || '').replace(/"/g, '""');
            const livreur = v.livreur_nom || v.livreur?.nom || '';
            const resultat = getResultatLabel(v.resultat || 'autre');
            const lat = v.latitude || '';
            const lng = v.longitude || '';
            const notes = (v.notes || '').replace(/"/g, '""');

            csv += `"${heure}","${client}","${adresse}","${livreur}","${resultat}","${lat}","${lng}","${notes}"\n`;
        });

        // Telecharger
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `visites_${date}.csv`;
        link.click();
    };

    // Ecouter l'evenement fragment:loaded
    document.addEventListener('fragment:loaded', function(e) {
        if (e.detail && e.detail.name === 'visites_clients') {
            console.log('[VISITES JS] Fragment loaded event received');
            init();
        }
    });

    // Init si le DOM est deja charge
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        setTimeout(init, 100);
    } else {
        document.addEventListener('DOMContentLoaded', init);
    }

})();
