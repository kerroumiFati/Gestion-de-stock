/**
 * Initialisation globale de Select2 pour tous les selects
 */
(function() {
    'use strict';

    // Attendre que jQuery et Select2 soient chargés
    if (typeof jQuery === 'undefined' || typeof jQuery.fn.select2 === 'undefined') {
        console.warn('jQuery ou Select2 non chargé');
        return;
    }

    jQuery(document).ready(function($) {

        // Fonction pour initialiser Select2 sur un élément
        function initSelect2(selector, config) {
            const defaultConfig = {
                theme: 'bootstrap4',
                allowClear: true,
                width: '100%',
                language: {
                    noResults: function() {
                        return "Aucun résultat trouvé";
                    },
                    searching: function() {
                        return "Recherche en cours...";
                    },
                    inputTooShort: function() {
                        return "Veuillez saisir au moins 1 caractère";
                    },
                    loadingMore: function() {
                        return "Chargement de plus de résultats...";
                    }
                }
            };

            const finalConfig = $.extend({}, defaultConfig, config);

            $(selector).each(function() {
                if (!$(this).hasClass('select2-hidden-accessible')) {
                    $(this).select2(finalConfig);
                }
            });
        }

        // Initialiser Select2 sur tous les selects de produits
        function initProductSelects() {
            // Tous les selects qui ont "produit" dans l'ID ou la classe
            $('select[id*="produit"], select[class*="produit-select"]').each(function() {
                if (!$(this).hasClass('select2-hidden-accessible')) {
                    $(this).select2({
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
                }
            });
        }

        // Initialiser Select2 sur tous les selects de clients
        function initClientSelects() {
            $('select[id*="client"], select[class*="client-select"]').each(function() {
                if (!$(this).hasClass('select2-hidden-accessible')) {
                    $(this).select2({
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
                }
            });
        }

        // Initialiser Select2 sur tous les selects de fournisseurs
        function initFournisseurSelects() {
            $('select[id*="fournisseur"], select[class*="fournisseur-select"]').each(function() {
                if (!$(this).hasClass('select2-hidden-accessible')) {
                    $(this).select2({
                        theme: 'bootstrap4',
                        placeholder: 'Rechercher un fournisseur...',
                        allowClear: true,
                        width: '100%',
                        language: {
                            noResults: function() {
                                return "Aucun fournisseur trouvé";
                            },
                            searching: function() {
                                return "Recherche en cours...";
                            }
                        }
                    });
                }
            });
        }

        // Initialiser Select2 sur tous les selects de catégories
        function initCategorieSelects() {
            $('select[id*="categorie"], select[class*="categorie-select"]').each(function() {
                if (!$(this).hasClass('select2-hidden-accessible')) {
                    $(this).select2({
                        theme: 'bootstrap4',
                        placeholder: 'Rechercher une catégorie...',
                        allowClear: true,
                        width: '100%',
                        language: {
                            noResults: function() {
                                return "Aucune catégorie trouvée";
                            },
                            searching: function() {
                                return "Recherche en cours...";
                            }
                        }
                    });
                }
            });
        }

        // Initialiser Select2 sur tous les selects d'entrepôts
        function initWarehouseSelects() {
            $('select[id*="warehouse"], select[id*="entrepot"], select[class*="warehouse-select"]').each(function() {
                if (!$(this).hasClass('select2-hidden-accessible')) {
                    $(this).select2({
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
                }
            });
        }

        // Fonction pour initialiser TOUS les selects
        function initAllSelects() {
            $('select').each(function() {
                // Ne pas réinitialiser les selects qui ont déjà Select2
                if ($(this).hasClass('select2-hidden-accessible')) {
                    return;
                }

                // Ne pas initialiser sur certains selects spéciaux
                if ($(this).hasClass('no-select2')) {
                    return;
                }

                // Configuration par défaut
                let config = {
                    theme: 'bootstrap4',
                    allowClear: true,
                    width: '100%',
                    language: {
                        noResults: function() {
                            return "Aucun résultat trouvé";
                        },
                        searching: function() {
                            return "Recherche en cours...";
                        },
                        inputTooShort: function() {
                            return "Veuillez saisir au moins 1 caractère";
                        },
                        loadingMore: function() {
                            return "Chargement...";
                        }
                    }
                };

                // Personnaliser le placeholder selon l'ID ou la classe
                const $select = $(this);
                const id = $select.attr('id') || '';
                const className = $select.attr('class') || '';

                if (id.includes('produit') || className.includes('produit')) {
                    config.placeholder = 'Rechercher un produit...';
                } else if (id.includes('client') || className.includes('client')) {
                    config.placeholder = 'Rechercher un client...';
                } else if (id.includes('fournisseur') || className.includes('fournisseur')) {
                    config.placeholder = 'Rechercher un fournisseur...';
                } else if (id.includes('categorie') || className.includes('categorie')) {
                    config.placeholder = 'Rechercher une catégorie...';
                } else if (id.includes('warehouse') || id.includes('entrepot') || className.includes('warehouse') || className.includes('entrepot')) {
                    config.placeholder = 'Rechercher un entrepôt...';
                } else if (id.includes('user') || id.includes('utilisateur') || className.includes('user')) {
                    config.placeholder = 'Rechercher un utilisateur...';
                } else if (id.includes('group') || id.includes('role') || className.includes('group') || className.includes('role')) {
                    config.placeholder = 'Rechercher un rôle...';
                } else if (id.includes('currency') || id.includes('devise') || className.includes('currency') || className.includes('devise')) {
                    config.placeholder = 'Rechercher une devise...';
                } else if (id.includes('paiement') || id.includes('payment') || className.includes('paiement')) {
                    config.placeholder = 'Choisir un mode de paiement...';
                } else if (id.includes('statut') || id.includes('status') || className.includes('statut')) {
                    config.placeholder = 'Choisir un statut...';
                } else {
                    // Essayer de récupérer le placeholder existant ou le premier option
                    const placeholder = $select.attr('placeholder') ||
                                      $select.data('placeholder') ||
                                      $select.find('option:first').text() ||
                                      'Sélectionner...';
                    config.placeholder = placeholder;
                }

                // Initialiser Select2
                $select.select2(config);
            });
        }

        // Fonction pour réinitialiser tous les Select2
        window.reinitSelect2 = function() {
            initAllSelects();
        };

        // Initialisation au chargement de la page
        // Attendre un peu pour laisser le temps aux autres scripts de charger les options
        setTimeout(function() {
            initAllSelects();
        }, 500);

        // Observer les changements DOM pour initialiser les nouveaux selects
        const observer = new MutationObserver(function(mutations) {
            let shouldReinit = false;

            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length) {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === 1) { // Element node
                            const $node = $(node);
                            // Vérifier si le noeud ajouté est un select ou contient des selects
                            if ($node.is('select') || $node.find('select').length) {
                                shouldReinit = true;
                            }
                        }
                    });
                }
            });

            if (shouldReinit) {
                // Utiliser un debounce pour éviter trop d'appels
                clearTimeout(window.select2ReinitTimer);
                window.select2ReinitTimer = setTimeout(function() {
                    initAllSelects();
                }, 200);
            }
        });

        // Observer le body pour les changements
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // Fonction globale pour forcer la réinitialisation
        window.forceReinitSelect2 = function() {
            // Détruire tous les Select2 existants
            $('.select2-hidden-accessible').each(function() {
                try {
                    $(this).select2('destroy');
                } catch(e) {
                    // Ignorer les erreurs
                }
            });

            // Réinitialiser tous les selects
            initAllSelects();
        };
    });
})();
