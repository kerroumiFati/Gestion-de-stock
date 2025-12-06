(function() {
    // Attendre que jQuery soit disponible
    if (typeof jQuery === 'undefined') {
        console.error('jQuery is not loaded. Caisse.js requires jQuery.');
        return;
    }

    jQuery(document).ready(function($){
        // Variables globales
        let produitsData = [];
        let clientsData = [];
        let warehousesData = [];
        let currencyData = null;
        let systemConfig = null;
        let panier = []; // Articles dans le panier

    // Configuration CSRF pour Django
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Configurer le CSRF token pour toutes les requêtes AJAX
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!(/^(GET|HEAD|OPTIONS|TRACE)$/.test(settings.type)) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
            }
        }
    });

    // Fonction pour afficher un message amélioré
    function setStatus(selector, msg, isError) {
        const icon = isError ? 'fa-exclamation-triangle' : 'fa-check-circle';
        const cls = isError ? 'alert alert-danger' : 'alert alert-success';
        const title = isError ? 'Erreur' : 'Succès';

        $(selector).html(`
            <div class="${cls} alert-dismissible fade show" role="alert">
                <strong><i class="fa ${icon}"></i> ${title}:</strong> ${msg}
                <button type="button" class="close" data-dismiss="alert">
                    <span>&times;</span>
                </button>
            </div>
        `);

        setTimeout(() => {
            $(selector).find('.alert').fadeOut(400, function() {
                $(this).remove();
            });
        }, 5000);
    }

    // Charger les données initiales
    function loadInitialData() {
        // Charger les produits
        $.get('/API/produits/', function(data) {
            produitsData = data;
            const $sel = $('#caisse_produit');
            $sel.empty().append('<option value="">Choisir un produit...</option>');
            data.forEach(p => {
                if (p.is_active && p.quantite > 0) {
                    $sel.append(`<option value="${p.id}"
                        data-ref="${p.reference}"
                        data-cb="${p.code_barre || ''}"
                        data-prix="${p.prixU}"
                        data-stock="${p.quantite}"
                        data-designation="${p.designation}">${p.designation} (${p.reference}) - Stock: ${p.quantite}</option>`);
                }
            });

            // Activer Select2 sur le select de produits
            $sel.select2({
                theme: 'bootstrap4',
                placeholder: 'Rechercher un produit...',
                allowClear: true,
                width: '100%',
                language: {
                    noResults: function() {
                        return "Aucun produit trouvé";
                    },
                    searching: function() {
                        return "Recherche en cours...";
                    }
                }
            });
        }).fail(function() {
            setStatus('#caisse_status', 'Erreur lors du chargement des produits', true);
        });

        // Charger les clients
        $.get('/API/clients/', function(data) {
            clientsData = data;
            const $sel = $('#caisse_client');
            $sel.empty().append('<option value="">Sélectionner un client...</option>');
            data.forEach(c => {
                $sel.append(`<option value="${c.id}">${c.nom} ${c.prenom || ''}</option>`);
            });

            // Activer Select2 sur le select de clients
            $sel.select2({
                theme: 'bootstrap4',
                placeholder: 'Rechercher un client...',
                allowClear: true,
                width: '100%',
                language: {
                    noResults: function() {
                        return "Aucun client trouvé";
                    },
                    searching: function() {
                        return "Recherche en cours...";
                    }
                }
            });
        });

        // Charger les entrepôts
        $.get('/API/entrepots/', function(data) {
            warehousesData = data;
            const $sel = $('#caisse_warehouse');
            $sel.empty().append('<option value="">Sélectionner un entrepôt...</option>');
            data.forEach(w => {
                if (w.is_active) {
                    $sel.append(`<option value="${w.id}">${w.name} (${w.code})</option>`);
                }
            });

            // Activer Select2 sur le select d'entrepôts
            $sel.select2({
                theme: 'bootstrap4',
                placeholder: 'Rechercher un entrepôt...',
                allowClear: true,
                width: '100%',
                language: {
                    noResults: function() {
                        return "Aucun entrepôt trouvé";
                    },
                    searching: function() {
                        return "Recherche en cours...";
                    }
                }
            });
        });

        // Charger la configuration système
        $.get('/API/system-config/', function(cfg) {
            systemConfig = cfg;
            // Pré-sélectionner l'entrepôt par défaut
            if (cfg.default_warehouse) {
                $('#caisse_warehouse').val(cfg.default_warehouse);
            }
            // Charger la devise par défaut
            if (cfg.default_currency) {
                $.get(`/API/currencies/${cfg.default_currency}/`, function(currency) {
                    currencyData = currency;
                    $('#caisse_currency_symbol, #caisse_currency_symbol2').text(currency.symbol);
                });
            }
        });

        // Charger les dernières ventes
        loadRecentSales();
    }

    // Charger les dernières ventes
    function loadRecentSales() {
        $.get('/API/ventes/?ordering=-date_vente&limit=5', function(data) {
            const $container = $('#caisse_recent_sales');
            $container.empty();
            if (data && data.length > 0) {
                data.forEach(v => {
                    const date = new Date(v.date_vente).toLocaleString('fr-FR', {
                        day: '2-digit',
                        month: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit'
                    });
                    $container.append(`
                        <div class="border-bottom pb-1 mb-1">
                            <strong>${v.numero}</strong> - ${v.client_nom || 'N/A'}<br>
                            <small>${date} - ${v.total_formatted}</small>
                        </div>
                    `);
                });
            } else {
                $container.html('<p class="text-muted">Aucune vente récente</p>');
            }
        });
    }

    // Rechercher un produit par code-barres ou référence
    function searchProduct(query) {
        query = query.trim().toLowerCase();
        if (!query) return null;

        // Chercher par code-barres d'abord
        let produit = produitsData.find(p =>
            p.code_barre && p.code_barre.toLowerCase() === query && p.is_active && p.quantite > 0
        );

        // Si pas trouvé, chercher par référence
        if (!produit) {
            produit = produitsData.find(p =>
                p.reference && p.reference.toLowerCase() === query && p.is_active && p.quantite > 0
            );
        }

        return produit;
    }

    // Ajouter un article au panier
    function ajouterAuPanier(produit, quantite) {
        quantite = parseInt(quantite) || 1;

        // Vérifier le stock disponible
        const qteEnPanier = panier
            .filter(item => item.produit.id === produit.id)
            .reduce((sum, item) => sum + item.quantite, 0);

        if (qteEnPanier + quantite > produit.quantite) {
            setStatus('#caisse_status', `Stock insuffisant pour ${produit.designation} (disponible: ${produit.quantite})`, true);
            return;
        }

        // Chercher si le produit existe déjà dans le panier
        const existant = panier.find(item => item.produit.id === produit.id);
        if (existant) {
            existant.quantite += quantite;
        } else {
            panier.push({
                produit: produit,
                quantite: quantite,
                prixU: parseFloat(produit.prixU) || 0
            });
        }

        afficherPanier();
        $('#caisse_search').val('').focus();
        $('#caisse_qte').val(1);
    }

    // Afficher le contenu du panier
    function afficherPanier() {
        const $tbody = $('#caisse_items');
        const $emptyRow = $('#caisse_empty_row');

        if (panier.length === 0) {
            $emptyRow.show();
            $tbody.find('tr:not(#caisse_empty_row)').remove();
            $('#caisse_nb_articles').text(0);
            calculerTotaux();
            return;
        }

        $emptyRow.hide();
        $tbody.find('tr:not(#caisse_empty_row)').remove();

        let totalArticles = 0;
        panier.forEach((item, index) => {
            const prixU = parseFloat(item.prixU) || 0;
            const quantite = parseInt(item.quantite) || 0;
            const total = quantite * prixU;
            totalArticles += quantite;

            const currSymbol = currencyData ? currencyData.symbol : '€';
            $tbody.append(`
                <tr>
                    <td>
                        <strong>${item.produit.designation}</strong><br>
                        <small class="text-muted">${item.produit.reference}</small>
                    </td>
                    <td class="text-right">${prixU.toFixed(2)} ${currSymbol}</td>
                    <td class="text-center">
                        <input type="number" class="form-control form-control-sm qte-input text-center"
                               data-index="${index}" value="${quantite}"
                               min="1" max="${item.produit.quantite}" style="width: 70px;">
                    </td>
                    <td class="text-right"><strong>${total.toFixed(2)} ${currSymbol}</strong></td>
                    <td class="text-center">
                        <button class="btn btn-sm btn-danger remove-item" data-index="${index}">
                            <i class="fa fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `);
        });

        $('#caisse_nb_articles').text(totalArticles);
        calculerTotaux();
    }

    // Calculer les totaux
    function calculerTotaux() {
        let subtotal = 0;
        panier.forEach(item => {
            const prix = parseFloat(item.prixU) || 0;
            const qte = parseInt(item.quantite) || 0;
            subtotal += qte * prix;
        });

        const remise = parseFloat($('#caisse_remise').val()) || 0;
        const montantRemise = subtotal * (remise / 100);
        const total = subtotal - montantRemise;

        $('#caisse_subtotal').text(subtotal.toFixed(2));
        $('#caisse_total').text(total.toFixed(2));
    }

    // Vider le panier
    function viderPanier() {
        panier = [];
        afficherPanier();
    }

    // Valider la vente
    function validerVente() {
        // Validation
        if (panier.length === 0) {
            setStatus('#caisse_status', 'Le panier est vide', true);
            return;
        }

        const clientId = $('#caisse_client').val();
        if (!clientId) {
            setStatus('#caisse_status', 'Veuillez sélectionner un client', true);
            return;
        }

        const warehouseId = $('#caisse_warehouse').val();
        if (!warehouseId) {
            setStatus('#caisse_status', 'Veuillez sélectionner un entrepôt', true);
            return;
        }

        const typePaiement = $('#caisse_paiement').val();
        const remise = parseFloat($('#caisse_remise').val()) || 0;

        // Préparer les données de la vente
        const lignes = panier.map(item => ({
            produit: item.produit.id,
            quantite: item.quantite,
            prixU_snapshot: item.prixU,
            designation: item.produit.designation,
            currency: currencyData ? currencyData.id : null
        }));

        const venteData = {
            client: parseInt(clientId),
            warehouse: parseInt(warehouseId),
            type_paiement: typePaiement,
            remise_percent: remise,
            currency: currencyData ? currencyData.id : null,
            lignes: lignes
        };

        // Désactiver le bouton pendant le traitement
        const $btn = $('#caisse_validate');
        $btn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Traitement...');

        // Créer la vente
        $.ajax({
            url: '/API/ventes/',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(venteData),
            success: function(vente) {
                console.log('Vente créée:', vente);
                console.log('ID de la vente:', vente.id);

                setStatus('#caisse_status', `Vente ${vente.numero} créée avec succès !`, false);

                // Vider le panier
                viderPanier();

                // Recharger les produits pour mettre à jour les stocks
                loadInitialData();

                // Générer le ticket si configuré
                if (systemConfig && systemConfig.auto_print_ticket) {
                    genererTicket(vente.id);
                }
            },
            error: function(xhr) {
                let errorMsg = 'Erreur lors de la création de la vente';
                if (xhr.responseJSON && xhr.responseJSON.detail) {
                    errorMsg = xhr.responseJSON.detail;
                } else if (xhr.responseJSON && xhr.responseJSON.lignes) {
                    errorMsg = 'Stock insuffisant pour certains produits';
                }
                setStatus('#caisse_status', errorMsg, true);
            },
            complete: function() {
                $btn.prop('disabled', false).html('<i class="fa fa-check"></i> Valider');
            }
        });
    }

    // Générer et afficher le ticket de caisse
    function genererTicket(venteId) {
        $.get(`/API/ventes/${venteId}/ticket/`, function(html) {
            $('#ticket_content').html(html);
            $('#ticketModal').modal('show');
        }).fail(function() {
            setStatus('#caisse_status', 'Erreur lors de la génération du ticket', true);
        });
    }

    // Event handlers
    // Recherche par code-barres/référence (Enter ou bouton)
    $('#caisse_search').on('keypress', function(e) {
        if (e.which === 13) { // Enter
            e.preventDefault();
            $('#caisse_add_btn').click();
        }
    });

    $('#caisse_add_btn').on('click', function() {
        const query = $('#caisse_search').val();
        const produit = searchProduct(query);

        if (produit) {
            ajouterAuPanier(produit, 1);
        } else {
            setStatus('#caisse_status', 'Produit non trouvé ou stock épuisé', true);
        }
    });

    // Ajout manuel de produit
    $('#caisse_add_manual').on('click', function() {
        const produitId = $('#caisse_produit').val();
        const quantite = parseInt($('#caisse_qte').val()) || 1;

        if (!produitId) {
            setStatus('#caisse_status', 'Veuillez sélectionner un produit', true);
            return;
        }

        const produit = produitsData.find(p => p.id == produitId);
        if (produit) {
            ajouterAuPanier(produit, quantite);
        }
    });

    // Modifier la quantité d'un article
    $(document).on('change', '.qte-input', function() {
        const index = $(this).data('index');
        const newQte = parseInt($(this).val()) || 1;

        if (panier[index]) {
            const maxQte = panier[index].produit.quantite;
            if (newQte > maxQte) {
                setStatus('#caisse_status', `Stock insuffisant (max: ${maxQte})`, true);
                $(this).val(panier[index].quantite);
                return;
            }
            panier[index].quantite = newQte;
            afficherPanier();
        }
    });

    // Supprimer un article du panier
    $(document).on('click', '.remove-item', function() {
        const index = $(this).data('index');
        panier.splice(index, 1);
        afficherPanier();
    });

    // Recalculer lors du changement de remise
    $('#caisse_remise').on('input', function() {
        calculerTotaux();
    });

    // Vider le panier
    $('#caisse_clear').on('click', function() {
        if (panier.length > 0 && confirm('Voulez-vous vraiment vider le panier ?')) {
            viderPanier();
        }
    });

    // Valider la vente
    $('#caisse_validate').on('click', function() {
        validerVente();
    });

    // ========== PAVÉ NUMÉRIQUE ==========
    let numpadValue = '0';

    // Fonction pour mettre à jour l'affichage du pavé
    function updateNumpadDisplay() {
        $('#numpad_display').val(numpadValue);
    }

    // Toggle pour masquer/afficher le pavé numérique
    $('#toggle_numpad').on('click', function() {
        const $body = $('#numpad_body');
        const $icon = $(this).find('i');

        $body.slideToggle(300, function() {
            // Changer l'icône selon l'état
            if ($body.is(':visible')) {
                $icon.removeClass('fa-plus').addClass('fa-minus');
            } else {
                $icon.removeClass('fa-minus').addClass('fa-plus');
            }
        });
    });

    // Boutons numériques
    $('.numpad-btn').on('click', function() {
        const value = $(this).data('value').toString();

        if (numpadValue === '0' && value !== '.') {
            numpadValue = value;
        } else {
            // Empêcher plusieurs points décimaux
            if (value === '.' && numpadValue.includes('.')) {
                return;
            }
            numpadValue += value;
        }

        updateNumpadDisplay();
    });

    // Bouton effacer
    $('#numpad_clear').on('click', function() {
        if (numpadValue.length > 1) {
            numpadValue = numpadValue.slice(0, -1);
        } else {
            numpadValue = '0';
        }
        updateNumpadDisplay();
    });

    // Bouton valider (appliquer au champ cible)
    $('#numpad_enter').on('click', function() {
        const target = $('#numpad_target').val();
        const value = parseFloat(numpadValue) || 0;

        if (target === 'caisse_qte') {
            $('#caisse_qte').val(Math.max(1, Math.floor(value)));
        } else if (target === 'caisse_remise') {
            $('#caisse_remise').val(Math.min(100, Math.max(0, value)));
            calculerTotaux();
        }

        // Réinitialiser le pavé
        numpadValue = '0';
        updateNumpadDisplay();

        // Feedback visuel
        $(this).addClass('btn-success').removeClass('btn-primary');
        setTimeout(() => {
            $(this).removeClass('btn-success').addClass('btn-primary');
        }, 200);
    });

    // Support du clavier physique sur le pavé numérique
    $(document).on('keydown', function(e) {
        // Si un input normal est focus, ne pas intercepter
        if ($('input:not(#numpad_display), textarea, select').is(':focus')) {
            return;
        }

        const key = e.key;

        // Chiffres 0-9
        if (/^[0-9]$/.test(key)) {
            e.preventDefault();
            if (numpadValue === '0') {
                numpadValue = key;
            } else {
                numpadValue += key;
            }
            updateNumpadDisplay();
        }
        // Point décimal
        else if (key === '.' || key === ',') {
            e.preventDefault();
            if (!numpadValue.includes('.')) {
                numpadValue += '.';
                updateNumpadDisplay();
            }
        }
        // Backspace
        else if (key === 'Backspace') {
            e.preventDefault();
            if (numpadValue.length > 1) {
                numpadValue = numpadValue.slice(0, -1);
            } else {
                numpadValue = '0';
            }
            updateNumpadDisplay();
        }
        // Enter
        else if (key === 'Enter') {
            e.preventDefault();
            $('#numpad_enter').click();
        }
    });

        // Initialisation
        loadInitialData();
    });
})();
