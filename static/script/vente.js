$(function(){
  let produitsCache = [];
  let currentVente = null;
  let venteLines = [];

  // === INITIALISATION ===
  function init(){
    loadClients();
    loadCurrencies();
    refreshProduits();
    loadVentesList();
    loadStats();
    
    // Event listeners
    $('#vente_ref, #vente_cb').on('keyup change', refreshProduits);
    $('#vente_remise').on('keyup change', calculateTotals);
    
    // Navigation entre onglets
    $('#liste-ventes-tab').on('click', function(){
      loadVentesList();
    });
    $('#stats-ventes-tab').on('click', function(){
      loadStats();
    });
    $('#devises-tab').on('click', function(){
      loadCurrenciesList();
      loadExchangeRates();
    });
  }

  // === GESTION DES CLIENTS ===
  function loadClients(){
    $.get('/API/clients/?format=json', function(resp){
      const sel = $('#vente_client').empty().append(`<option value="">Choisir un client...</option>`);
      resp.forEach(c => sel.append(`<option value="${c.id}">${c.nom} ${c.prenom}</option>`));
    });
  }

  // === GESTION DES PRODUITS ===
  function loadProduits(url){
    $.get(url, function(resp){
      produitsCache = resp;
      const sel = $('#vente_prod').empty().append(`<option value="">Choisir un produit...</option>`);
      resp.forEach(p => {
        const stockInfo = p.quantite > 0 ? `(stock: ${p.quantite})` : '(RUPTURE)';
        const disabled = p.quantite <= 0 ? 'disabled' : '';
        sel.append(`<option value="${p.id}" ${disabled}>${p.reference}: ${p.designation} ${stockInfo}</option>`);
      });
    });
  }
  
  function refreshProduits(){
    const ref = $('#vente_ref').val();
    const cb = $('#vente_cb').val();
    let url = '/API/produits/?format=json';
    if(ref) url += '&reference__icontains=' + encodeURIComponent(ref);
    if(cb) url += '&code_barre__icontains=' + encodeURIComponent(cb);
    loadProduits(url);
  }

  // === GESTION DES LIGNES DE VENTE ===
  function addLineToVente(){
    const pid = $('#vente_prod').val();
    const qte = parseInt($('#vente_qte').val() || '1', 10);
    
    if(!pid){ 
      showAlert('Veuillez choisir un produit', 'warning'); 
      return; 
    }
    
    const p = produitsCache.find(x => String(x.id) === String(pid));
    if(!p){ 
      showAlert('Produit introuvable', 'danger'); 
      return; 
    }
    
    if(qte > p.quantite){ 
      showAlert(`Stock insuffisant. Stock disponible: ${p.quantite}`, 'warning'); 
      return; 
    }

    // Vérifier si le produit est déjà dans la vente
    const existingIndex = venteLines.findIndex(line => line.produit.id === p.id);
    
    if(existingIndex >= 0){
      // Mettre à jour la quantité existante
      venteLines[existingIndex].quantite += qte;
      if(venteLines[existingIndex].quantite > p.quantite){
        showAlert(`Stock insuffisant. Stock disponible: ${p.quantite}`, 'warning');
        venteLines[existingIndex].quantite -= qte;
        return;
      }
    } else {
      // Ajouter nouvelle ligne
      venteLines.push({
        produit: p,
        designation: p.designation,
        quantite: qte,
        prixU_snapshot: parseFloat(p.prixU)
      });
    }
    
    // Reset des champs
    $('#vente_prod').val('');
    $('#vente_qte').val('1');
    
    refreshVenteTable();
    showAlert('Produit ajouté à la vente', 'success');
  }

  function removeLineFromVente(index){
    venteLines.splice(index, 1);
    refreshVenteTable();
  }

  function refreshVenteTable(){
    const tbody = $('#vente_body').empty();
    
    venteLines.forEach((line, index) => {
      const total = (line.quantite * line.prixU_snapshot).toFixed(2);
      const row = `
        <tr>
          <td>${line.produit.reference}</td>
          <td>${line.designation}</td>
          <td>${line.prixU_snapshot.toFixed(2)} €</td>
          <td>
            <input type="number" class="form-control form-control-sm qte-input" 
                   data-index="${index}" value="${line.quantite}" min="1" max="${line.produit.quantite}">
          </td>
          <td>${total} €</td>
          <td>
            <button class="btn btn-sm btn-outline-danger remove-line" data-index="${index}">
              <i class="fa fa-trash"></i>
            </button>
          </td>
        </tr>
      `;
      tbody.append(row);
    });
    
    calculateTotals();
  }

  function calculateTotals(){
    let totalHT = 0;
    
    venteLines.forEach(line => {
      totalHT += line.quantite * line.prixU_snapshot;
    });
    
    const remisePercent = parseFloat($('#vente_remise').val() || 0);
    const remiseMontant = totalHT * (remisePercent / 100);
    const totalTTC = totalHT - remiseMontant;
    
    $('#vente_total_ht').text(totalHT.toFixed(2) + ' €');
    $('#vente_remise_montant').text(remiseMontant.toFixed(2) + ' €');
    $('#vente_total_ttc').text(totalTTC.toFixed(2) + ' €');
  }

  // === GESTION DES VENTES ===
  function saveVente(complete = false){
    const client = $('#vente_client').val();
    if(!client){ 
      showAlert('Veuillez sélectionner un client', 'warning'); 
      return; 
    }
    
    if(venteLines.length === 0){ 
      showAlert('Veuillez ajouter au moins un produit', 'warning'); 
      return; 
    }

    const venteLignes = venteLines.map(line => ({
      produit: line.produit.id,
      designation: line.designation,
      quantite: line.quantite,
      prixU_snapshot: line.prixU_snapshot
    }));

    const payload = {
      client: parseInt(client),
      type_paiement: $('#vente_paiement').val(),
      currency: $('#vente_currency').val() ? parseInt($('#vente_currency').val()) : null,
      remise_percent: parseFloat($('#vente_remise').val() || 0),
      observations: $('#vente_obs').val(),
      lignes: venteLignes
    };

    const numero = $('#vente_num').val().trim();
    if(numero) payload.numero = numero;

    const url = currentVente ? `/API/ventes/${currentVente.id}/` : '/API/ventes/';
    const method = currentVente ? 'PUT' : 'POST';

    $.ajax({
      url: url,
      method: method,
      contentType: 'application/json',
      data: JSON.stringify(payload),
      success: function(vente){
        currentVente = vente;
        showAlert('Vente enregistrée avec succès!', 'success');
        $('#vente_status').html(`<span class="text-success">Vente ${vente.numero} - Statut: ${vente.statut_display}</span>`);
        
        if(complete){
          completeVente(vente.id);
        }
      },
      error: function(xhr){
        console.error('Erreur:', xhr.responseText);
        showAlert('Erreur lors de l\'enregistrement: ' + xhr.responseText, 'danger');
      }
    });
  }

  function completeVente(venteId){
    if(!venteId && currentVente) venteId = currentVente.id;
    if(!venteId){ 
      showAlert('Aucune vente à finaliser', 'warning'); 
      return; 
    }

    $.ajax({
      url: `/API/ventes/${venteId}/complete/`,
      method: 'POST',
      success: function(resp){
        showAlert('Vente finalisée avec succès!', 'success');
        $('#vente_status').html(`<span class="text-success">Vente finalisée - ${resp.status}</span>`);
        
        // Proposer d'imprimer le reçu
        if(confirm('Vente finalisée! Voulez-vous imprimer le reçu?')){
          window.open(`/API/ventes/${venteId}/printable/`, '_blank');
        }
        
        clearVenteForm();
        refreshProduits(); // Actualiser les stocks
      },
      error: function(xhr){
        const error = JSON.parse(xhr.responseText);
        if(error.lignes){
          let message = 'Stock insuffisant pour:\n';
          error.lignes.forEach(ligne => {
            message += `- ${ligne.reference}: demandé ${ligne.demande}, disponible ${ligne.stock}\n`;
          });
          showAlert(message, 'warning');
        } else {
          showAlert('Erreur: ' + xhr.responseText, 'danger');
        }
      }
    });
  }

  function clearVenteForm(){
    currentVente = null;
    venteLines = [];
    $('#vente_client').val('');
    $('#vente_paiement').val('cash');
    $('#vente_remise').val('0');
    $('#vente_num').val('');
    $('#vente_obs').val('');
    $('#vente_status').empty();
    refreshVenteTable();
  }

  // === GESTION DE LA LISTE DES VENTES ===
  function loadVentesList(){
    $.get('/API/ventes/?format=json', function(ventes){
      const tbody = $('#liste_ventes_body').empty();
      
      ventes.forEach(vente => {
        const date = new Date(vente.date_vente).toLocaleDateString('fr-FR');
        const statutClass = vente.statut === 'completed' ? 'success' : 
                           vente.statut === 'canceled' ? 'danger' : 'warning';
        
        const actions = `
          <button class="btn btn-sm btn-outline-primary view-vente" data-id="${vente.id}">
            <i class="fa fa-eye"></i>
          </button>
          ${vente.statut === 'draft' ? `
            <button class="btn btn-sm btn-outline-success complete-vente" data-id="${vente.id}">
              <i class="fa fa-check"></i>
            </button>
            <button class="btn btn-sm btn-outline-danger cancel-vente" data-id="${vente.id}">
              <i class="fa fa-times"></i>
            </button>
          ` : ''}
          <button class="btn btn-sm btn-outline-info print-vente" data-id="${vente.id}">
            <i class="fa fa-print"></i>
          </button>
        `;
        
        const row = `
          <tr>
            <td>${vente.numero}</td>
            <td>${date}</td>
            <td>${vente.client_nom} ${vente.client_prenom}</td>
            <td><span class="badge badge-${statutClass}">${vente.statut_display}</span></td>
            <td>${vente.type_paiement_display}</td>
            <td>${parseFloat(vente.total_ttc).toFixed(2)} €</td>
            <td>${actions}</td>
          </tr>
        `;
        tbody.append(row);
      });
    });
  }

  // === GESTION DES STATISTIQUES ===
  function loadStats(){
    $.get('/API/ventes/stats/?format=json', function(stats){
      $('#stat_ventes_today').text(stats.ventes_aujourd_hui);
      $('#stat_ventes_week').text(stats.ventes_semaine);
      $('#stat_ventes_month').text(stats.ventes_mois);
      $('#stat_ventes_total').text(stats.total_ventes);
      
      $('#stat_ca_today').text(parseFloat(stats.ca_aujourd_hui).toFixed(2) + ' €');
      $('#stat_ca_week').text(parseFloat(stats.ca_semaine).toFixed(2) + ' €');
      $('#stat_ca_month').text(parseFloat(stats.ca_mois).toFixed(2) + ' €');
      $('#stat_ca_total').text(parseFloat(stats.ca_total).toFixed(2) + ' €');
    });
  }

  // === UTILITAIRES ===
  function showAlert(message, type = 'info'){
    // Créer une alerte Bootstrap temporaire
    const alertDiv = `
      <div class="alert alert-${type} alert-dismissible fade show" role="alert" style="position: fixed; top: 20px; right: 20px; z-index: 9999;">
        ${message}
        <button type="button" class="close" data-dismiss="alert">
          <span>&times;</span>
        </button>
      </div>
    `;
    $('body').append(alertDiv);
    
    // Auto-supprimer après 5 secondes
    setTimeout(() => {
      $('.alert').alert('close');
    }, 5000);
  }

  // === EVENT LISTENERS ===
  
  // Ajouter une ligne à la vente
  $('#vente_add_line').click(addLineToVente);
  
  // Modifier quantité dans le tableau
  $('#vente_body').on('change', '.qte-input', function(){
    const index = $(this).data('index');
    const newQte = parseInt($(this).val());
    const maxQte = venteLines[index].produit.quantite;
    
    if(newQte > maxQte){
      showAlert(`Stock insuffisant. Maximum: ${maxQte}`, 'warning');
      $(this).val(venteLines[index].quantite);
      return;
    }
    
    venteLines[index].quantite = newQte;
    refreshVenteTable();
  });
  
  // Supprimer une ligne
  $('#vente_body').on('click', '.remove-line', function(){
    const index = $(this).data('index');
    removeLineFromVente(index);
  });
  
  // Actions de la vente
  $('#vente_save_draft').click(() => saveVente(false));
  $('#vente_complete').click(() => {
    if(currentVente && currentVente.statut === 'draft'){
      completeVente();
    } else {
      saveVente(true);
    }
  });
  $('#vente_clear').click(clearVenteForm);
  
  // Actions sur la liste des ventes
  $('#liste_ventes_body').on('click', '.complete-vente', function(){
    const venteId = $(this).data('id');
    if(confirm('Finaliser cette vente?')){
      completeVente(venteId);
      setTimeout(loadVentesList, 1000);
    }
  });
  
  $('#liste_ventes_body').on('click', '.cancel-vente', function(){
    const venteId = $(this).data('id');
    if(confirm('Annuler cette vente?')){
      $.post(`/API/ventes/${venteId}/cancel/`, {}, function(){
        showAlert('Vente annulée', 'success');
        loadVentesList();
      });
    }
  });
  
  $('#liste_ventes_body').on('click', '.print-vente', function(){
    const venteId = $(this).data('id');
    window.open(`/API/ventes/${venteId}/printable/`, '_blank');
  });

  // Scan de code-barres (Enter)
  $('#vente_cb').on('keypress', function(e){
    if(e.which === 13){ // Enter
      const cb = $(this).val().trim();
      if(cb){
        const produit = produitsCache.find(p => p.code_barre === cb);
        if(produit){
          $('#vente_prod').val(produit.id);
          addLineToVente();
          $(this).val('');
        } else {
          showAlert('Code-barres non trouvé', 'warning');
        }
      }
    }
  });

  // === GESTION DES DEVISES ===
  function loadCurrencies(){
    $.get('/API/currencies/?format=json', function(currencies){
      const selectors = ['#vente_currency', '#rate_from_currency', '#rate_to_currency', '#convert_from', '#convert_to'];
      
      selectors.forEach(selector => {
        const sel = $(selector).empty();
        if(selector === '#vente_currency') {
          sel.append('<option value="">Devise par défaut</option>');
        } else {
          sel.append('<option value="">Choisir...</option>');
        }
        
        currencies.forEach(c => {
          const defaultText = c.is_default ? ' (défaut)' : '';
          sel.append(`<option value="${c.id}">${c.code} - ${c.name} (${c.symbol})${defaultText}</option>`);
        });
      });
    });
  }

  function loadCurrenciesList(){
    $.get('/API/currencies/?format=json', function(currencies){
      const tbody = $('#currencies_body').empty();
      
      currencies.forEach(currency => {
        const defaultBadge = currency.is_default ? 
          '<span class="badge badge-success">Oui</span>' : 
          '<span class="badge badge-secondary">Non</span>';
        
        const actions = `
          <button class="btn btn-sm btn-outline-primary set-default-currency" data-id="${currency.id}" ${currency.is_default ? 'disabled' : ''}>
            <i class="fa fa-star"></i>
          </button>
          <button class="btn btn-sm btn-outline-danger delete-currency" data-id="${currency.id}" ${currency.is_default ? 'disabled' : ''}>
            <i class="fa fa-trash"></i>
          </button>
        `;
        
        const row = `
          <tr>
            <td><strong>${currency.code}</strong></td>
            <td>${currency.name}</td>
            <td>${currency.symbol}</td>
            <td>${defaultBadge}</td>
            <td>${actions}</td>
          </tr>
        `;
        tbody.append(row);
      });
    });
  }

  function addCurrency(){
    const code = $('#currency_code').val().trim().toUpperCase();
    const name = $('#currency_name').val().trim();
    const symbol = $('#currency_symbol').val().trim();
    
    if(!code || !name || !symbol){
      showAlert('Veuillez remplir tous les champs', 'warning');
      return;
    }
    
    if(code.length !== 3){
      showAlert('Le code devise doit faire 3 caractères', 'warning');
      return;
    }
    
    const payload = {
      code: code,
      name: name,
      symbol: symbol,
      is_active: true
    };
    
    $.ajax({
      url: '/API/currencies/',
      method: 'POST',
      contentType: 'application/json',
      data: JSON.stringify(payload),
      success: function(){
        showAlert('Devise ajoutée avec succès', 'success');
        $('#currency_code, #currency_name, #currency_symbol').val('');
        loadCurrenciesList();
        loadCurrencies();
      },
      error: function(xhr){
        showAlert('Erreur: ' + xhr.responseText, 'danger');
      }
    });
  }

  // === GESTION DES TAUX DE CHANGE ===
  function loadExchangeRates(){
    $.get('/API/exchange-rates/?format=json', function(rates){
      const tbody = $('#rates_body').empty();
      
      rates.forEach(rate => {
        const date = new Date(rate.date).toLocaleDateString('fr-FR');
        const actions = `
          <button class="btn btn-sm btn-outline-danger delete-rate" data-id="${rate.id}">
            <i class="fa fa-trash"></i>
          </button>
        `;
        
        const row = `
          <tr>
            <td><strong>${rate.from_currency_code}</strong></td>
            <td><strong>${rate.to_currency_code}</strong></td>
            <td>${parseFloat(rate.rate).toFixed(6)}</td>
            <td>${date}</td>
            <td>${actions}</td>
          </tr>
        `;
        tbody.append(row);
      });
    });
  }

  function addExchangeRate(){
    const fromCurrency = $('#rate_from_currency').val();
    const toCurrency = $('#rate_to_currency').val();
    const rateValue = $('#rate_value').val();
    
    if(!fromCurrency || !toCurrency || !rateValue){
      showAlert('Veuillez remplir tous les champs', 'warning');
      return;
    }
    
    if(fromCurrency === toCurrency){
      showAlert('Les devises source et destination doivent être différentes', 'warning');
      return;
    }
    
    const payload = {
      from_currency: parseInt(fromCurrency),
      to_currency: parseInt(toCurrency),
      rate: parseFloat(rateValue),
      is_active: true
    };
    
    $.ajax({
      url: '/API/exchange-rates/',
      method: 'POST',
      contentType: 'application/json',
      data: JSON.stringify(payload),
      success: function(response, textStatus, xhr){
        if(xhr.status === 200) {
          showAlert('Taux de change mis à jour avec succès', 'info');
        } else {
          showAlert('Taux de change ajouté avec succès', 'success');
        }
        $('#rate_from_currency, #rate_to_currency, #rate_value').val('');
        loadExchangeRates();
      },
      error: function(xhr){
        let errorMessage = 'Erreur lors de l\'ajout du taux de change';
        try {
          const errorData = JSON.parse(xhr.responseText);
          if(errorData.non_field_errors) {
            errorMessage = 'Ce taux de change existe déjà pour cette date. Il a été mis à jour.';
          } else {
            errorMessage = xhr.responseText;
          }
        } catch(e) {
          errorMessage = xhr.responseText;
        }
        showAlert(errorMessage, 'warning');
        // Recharger les taux même en cas d'erreur car il peut y avoir eu une mise à jour
        loadExchangeRates();
      }
    });
  }

  function convertCurrency(){
    const amount = $('#convert_amount').val();
    const fromCurrency = $('#convert_from').val();
    const toCurrency = $('#convert_to').val();
    
    if(!amount || !fromCurrency || !toCurrency){
      showAlert('Veuillez remplir tous les champs du convertisseur', 'warning');
      return;
    }
    
    const params = new URLSearchParams({
      amount: amount,
      from_currency: fromCurrency,
      to_currency: toCurrency
    });
    
    $.get(`/API/exchange-rates/convert/?${params}`, function(result){
      const fromSymbol = $('#convert_from option:selected').text().match(/\(([^)]+)\)/)[1];
      const toSymbol = $('#convert_to option:selected').text().match(/\(([^)]+)\)/)[1];
      
      $('#convert_result').html(`
        <strong>${parseFloat(result.original_amount).toFixed(2)} ${fromSymbol}</strong> = 
        <strong>${parseFloat(result.converted_amount).toFixed(2)} ${toSymbol}</strong>
        <br><small>Taux: 1 ${result.from_currency} = ${parseFloat(result.exchange_rate).toFixed(6)} ${result.to_currency}</small>
      `).show();
    }).fail(function(xhr){
      showAlert('Erreur de conversion: ' + xhr.responseText, 'danger');
    });
  }

  // === EVENT LISTENERS POUR DEVISES ===
  
  // Ajouter une devise
  $('#add_currency').click(addCurrency);
  
  // Ajouter un taux de change
  $('#add_rate').click(addExchangeRate);
  
  // Convertisseur
  $('#convert_btn').click(convertCurrency);
  
  // Actions sur les devises
  $('#currencies_body').on('click', '.set-default-currency', function(){
    const currencyId = $(this).data('id');
    $.post(`/API/currencies/${currencyId}/set_default/`, {}, function(){
      showAlert('Devise par défaut mise à jour', 'success');
      loadCurrenciesList();
      loadCurrencies();
    });
  });
  
  $('#currencies_body').on('click', '.delete-currency', function(){
    const currencyId = $(this).data('id');
    if(confirm('Supprimer cette devise?')){
      $.ajax({
        url: `/API/currencies/${currencyId}/`,
        method: 'DELETE',
        success: function(){
          showAlert('Devise supprimée', 'success');
          loadCurrenciesList();
          loadCurrencies();
        }
      });
    }
  });
  
  // Actions sur les taux de change
  $('#rates_body').on('click', '.delete-rate', function(){
    const rateId = $(this).data('id');
    if(confirm('Supprimer ce taux de change?')){
      $.ajax({
        url: `/API/exchange-rates/${rateId}/`,
        method: 'DELETE',
        success: function(){
          showAlert('Taux de change supprimé', 'success');
          loadExchangeRates();
        }
      });
    }
  });

  // Initialisation
  init();
});
