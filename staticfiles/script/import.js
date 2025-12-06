(function() {
    const DEBUG = true;
    function dbg() { if (DEBUG) console.log.apply(console, ['[Import]'].concat([].slice.call(arguments))); }

    let currentTab = 'products';
    let uploadedFile = null;
    let previewData = null;

    // Gérer les onglets
    window.switchTab = function(tab) {
        currentTab = tab;

        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        document.getElementById(tab + '-tab').classList.add('active');
    };

    // Drag & Drop
    ['products', 'categories'].forEach(type => {
        const zone = document.getElementById('uploadZone' + capitalize(type));
        if (!zone) return;

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            zone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            zone.addEventListener(eventName, () => zone.classList.add('dragover'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            zone.addEventListener(eventName, () => zone.classList.remove('dragover'), false);
        });

        zone.addEventListener('drop', handleDrop, false);

        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                document.getElementById('fileInput' + capitalize(type)).files = files;
                handleFileSelect({files: files}, type);
            }
        }
    });

    // Sélection de fichier
    window.handleFileSelect = function(input, type) {
        const file = input.files[0];
        if (!file) return;

        // Vérifier la taille (10 MB max)
        const maxSize = 10 * 1024 * 1024;
        if (file.size > maxSize) {
            alert('Le fichier est trop volumineux. Taille maximale: 10 MB');
            return;
        }

        // Vérifier l'extension
        const validExtensions = ['.xlsx', '.xls', '.csv'];
        const fileName = file.name.toLowerCase();
        const isValid = validExtensions.some(ext => fileName.endsWith(ext));

        if (!isValid) {
            alert('Format de fichier non supporté. Utilisez .xlsx, .xls ou .csv');
            return;
        }

        uploadedFile = file;

        // Afficher les infos du fichier
        document.getElementById('fileName' + capitalize(type)).textContent = file.name;
        document.getElementById('fileSize' + capitalize(type)).textContent = formatFileSize(file.size);
        document.getElementById('fileInfo' + capitalize(type)).style.display = 'block';

        // Parser et prévisualiser
        parseFile(file, type);
    };

    // Parser le fichier
    function parseFile(file, type) {
        const reader = new FileReader();

        reader.onload = function(e) {
            try {
                let data;

                if (file.name.endsWith('.csv')) {
                    data = parseCSV(e.target.result);
                } else {
                    // Pour Excel, on envoie au serveur pour traitement
                    previewFromServer(file, type);
                    return;
                }

                displayPreview(data, type);
            } catch (error) {
                console.error('Erreur de parsing:', error);
                alert('Erreur lors de la lecture du fichier: ' + error.message);
            }
        };

        if (file.name.endsWith('.csv')) {
            reader.readAsText(file);
        } else {
            reader.readAsArrayBuffer(file);
        }
    }

    // Parser CSV
    function parseCSV(text) {
        const lines = text.split('\n').filter(line => line.trim());
        if (lines.length === 0) return { headers: [], rows: [] };

        const headers = lines[0].split(',').map(h => h.trim().replace(/['"]/g, ''));
        const rows = lines.slice(1).map(line => {
            const values = line.split(',').map(v => v.trim().replace(/['"]/g, ''));
            const obj = {};
            headers.forEach((header, i) => {
                obj[header] = values[i] || '';
            });
            return obj;
        });

        return { headers, rows };
    }

    // Obtenir la prévisualisation depuis le serveur (pour Excel)
    function previewFromServer(file, type) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('type', type);

        fetch('/API/import/preview/', {
            method: 'POST',
            body: formData,
            credentials: 'same-origin'
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                alert('Erreur: ' + data.error);
                return;
            }
            displayPreview(data, type);
        })
        .catch(err => {
            console.error('Erreur preview:', err);
            alert('Erreur lors de la prévisualisation du fichier');
        });
    }

    // Afficher la prévisualisation
    function displayPreview(data, type) {
        previewData = data;
        const rows = data.rows || [];
        const headers = data.headers || [];

        if (rows.length === 0) {
            alert('Le fichier est vide ou mal formaté');
            return;
        }

        document.getElementById('previewCount' + capitalize(type)).textContent = rows.length;

        // Créer le tableau
        let html = '<table class="table table-bordered table-hover table-sm">';
        html += '<thead><tr>';
        headers.forEach(header => {
            html += '<th>' + escapeHtml(header) + '</th>';
        });
        html += '<th>Status</th></tr></thead><tbody>';

        // Afficher max 10 lignes en preview
        const previewRows = rows.slice(0, 10);
        previewRows.forEach((row, idx) => {
            html += '<tr>';
            headers.forEach(header => {
                html += '<td>' + escapeHtml(row[header] || '') + '</td>';
            });

            // Valider la ligne
            const validation = validateRow(row, type);
            const statusClass = validation.valid ? 'status-success' : 'status-error';
            const statusText = validation.valid ? 'Valide' : validation.error;
            html += '<td><span class="status-badge ' + statusClass + '">' + statusText + '</span></td>';

            html += '</tr>';
        });

        if (rows.length > 10) {
            html += '<tr><td colspan="' + (headers.length + 1) + '" class="text-center text-muted">';
            html += '... et ' + (rows.length - 10) + ' lignes supplémentaires';
            html += '</td></tr>';
        }

        html += '</tbody></table>';

        document.getElementById('previewTable' + capitalize(type)).innerHTML = html;
        document.getElementById('preview' + capitalize(type)).style.display = 'block';
    }

    // Valider une ligne
    function validateRow(row, type) {
        if (type === 'products') {
            if (!row.reference || !row.reference.trim()) {
                return { valid: false, error: 'Référence manquante' };
            }
            if (!row.designation || !row.designation.trim()) {
                return { valid: false, error: 'Désignation manquante' };
            }
            if (!row.prixU || isNaN(parseFloat(row.prixU)) || parseFloat(row.prixU) <= 0) {
                return { valid: false, error: 'Prix invalide' };
            }
            return { valid: true };
        } else if (type === 'categories') {
            if (!row.nom || !row.nom.trim()) {
                return { valid: false, error: 'Nom manquant' };
            }
            return { valid: true };
        }
        return { valid: false, error: 'Type inconnu' };
    }

    // Confirmer l'import
    window.confirmImport = function(type) {
        if (!uploadedFile || !previewData) {
            alert('Aucun fichier sélectionné');
            return;
        }

        if (!confirm('Êtes-vous sûr de vouloir importer ces données ?')) {
            return;
        }

        // Masquer la preview, afficher la progression
        document.getElementById('preview' + capitalize(type)).style.display = 'none';
        document.getElementById('progress' + capitalize(type)).style.display = 'block';

        const formData = new FormData();
        formData.append('file', uploadedFile);
        formData.append('type', type);

        fetch('/API/import/execute/', {
            method: 'POST',
            body: formData,
            credentials: 'same-origin'
        })
        .then(res => res.json())
        .then(data => {
            document.getElementById('progress' + capitalize(type)).style.display = 'none';
            displayResults(data, type);
        })
        .catch(err => {
            console.error('Erreur import:', err);
            document.getElementById('progress' + capitalize(type)).style.display = 'none';
            alert('Erreur lors de l\'import: ' + err.message);
        });
    };

    // Afficher les résultats
    function displayResults(data, type) {
        const stats = data.stats || {};
        const errors = data.errors || [];

        let html = '';

        if (stats.created > 0) {
            html += '<div class="result-card success">';
            html += '<i class="fas fa-check-circle fa-2x mb-2" style="color: #22c55e;"></i>';
            html += '<h3>' + stats.created + '</h3>';
            html += '<p>Créés avec succès</p>';
            html += '</div>';
        }

        if (stats.updated > 0) {
            html += '<div class="result-card warning">';
            html += '<i class="fas fa-edit fa-2x mb-2" style="color: #f59e0b;"></i>';
            html += '<h3>' + stats.updated + '</h3>';
            html += '<p>Mis à jour</p>';
            html += '</div>';
        }

        if (stats.skipped > 0 || errors.length > 0) {
            html += '<div class="result-card error">';
            html += '<i class="fas fa-exclamation-triangle fa-2x mb-2" style="color: #ef4444;"></i>';
            html += '<h3>' + (stats.skipped + errors.length) + '</h3>';
            html += '<p>Erreurs</p>';
            html += '</div>';
        }

        document.getElementById('resultsStats' + capitalize(type)).innerHTML = html;

        // Afficher les erreurs si présentes
        if (errors.length > 0) {
            let errorsHtml = '<h6 class="font-weight-bold mb-3">Détails des erreurs:</h6>';
            errorsHtml += '<div id="errorsList">';
            errors.forEach((error, idx) => {
                errorsHtml += '<div class="error-item">';
                errorsHtml += '<strong>Ligne ' + (error.row || idx + 2) + ':</strong> ' + escapeHtml(error.message);
                errorsHtml += '</div>';
            });
            errorsHtml += '</div>';
            document.getElementById('errorsList' + capitalize(type)).innerHTML = errorsHtml;
            document.getElementById('errorsList' + capitalize(type)).style.display = 'block';
        }

        document.getElementById('results' + capitalize(type)).style.display = 'block';

        // Rafraîchir la liste après quelques secondes
        setTimeout(() => {
            if (type === 'products') {
                show('produit');
            } else if (type === 'categories') {
                show('categorie');
            }
        }, 3000);
    }

    // Annuler l'import
    window.cancelImport = function(type) {
        document.getElementById('fileInput' + capitalize(type)).value = '';
        document.getElementById('fileInfo' + capitalize(type)).style.display = 'none';
        document.getElementById('preview' + capitalize(type)).style.display = 'none';
        document.getElementById('results' + capitalize(type)).style.display = 'none';
        uploadedFile = null;
        previewData = null;
    };

    // Télécharger un template
    window.downloadTemplate = function(type, format) {
        const url = '/API/import/template/?type=' + type + '&format=' + format;
        window.location.href = url;
    };

    // Utilitaires
    function capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return String(text).replace(/[&<>"']/g, m => map[m]);
    }

    dbg('Import module initialized');
})();
