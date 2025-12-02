(function(){
  const API_BASE = '/API';
  const $ = window.jQuery;
  let facturesDataTable = null;

  function asList(resp){
    if(Array.isArray(resp)) return resp;
    if(resp && Array.isArray(resp.results)) return resp.results;
    return [];
  }

  function getCSRFToken(){
    const match = document.cookie.match(/csrftoken=([^;]+)/); return match ? match[1] : '';
  }

  function loadClients(){
    // Les clients sont maintenant chargés par le custom select dans facture.html
    // Cette fonction est gardée pour compatibilité mais ne fait plus rien
    console.log('[Facture.js] loadClients - skipped (handled by custom select)');
    return $.Deferred().resolve().promise();
  }

  function loadBLs(){
    // Les BLs sont maintenant chargés par le custom select dans facture.html
    // Cette fonction est gardée pour compatibilité mais ne fait plus rien
    console.log('[Facture.js] loadBLs - skipped (handled by custom select)');
    return $.Deferred().resolve().promise();
  }

  function getStatutBadge(statut) {
    if(statut === 'draft') return '<span class="badge badge-secondary">Brouillon</span>';
    if(statut === 'issued') return '<span class="badge badge-primary">Émise</span>';
    if(statut === 'paid') return '<span class="badge badge-success">Payée</span>';
    if(statut === 'canceled') return '<span class="badge badge-danger">Annulée</span>';
    return statut || '';
  }

  function getActions(f) {
    const actions = [
      '<a class="btn btn-sm btn-outline-primary" target="_blank" href="'+ API_BASE +'/factures/'+ f.id +'/printable/"><i class="fas fa-print"></i></a>'
    ];
    if(f.statut === 'draft'){
      actions.push('<button class="btn btn-sm btn-success act-issue" data-id="'+f.id+'" title="Émettre"><i class="fas fa-check"></i></button>');
    }
    if(f.statut === 'issued'){
      actions.push('<button class="btn btn-sm btn-warning act-pay" data-id="'+f.id+'" title="Marquer payée"><i class="fas fa-money-bill"></i></button>');
    }
    return actions.join(' ');
  }

  function renderFacturesList(){
    const $table = $('#tfacture');
    if(!$table.length){
      console.warn('[Facture.js] #tfacture not found');
      return;
    }
    console.log('[Facture.js] Loading factures list...');

    $.ajax({ url: API_BASE + '/factures/?page_size=100', method: 'GET', dataType: 'json' })
      .done(function(data){
        console.log('[Facture.js] API response:', data);
        const rows = asList(data);
        console.log('[Facture.js] Factures count:', rows.length);

        // Préparer les données pour DataTables
        const tableData = rows.map(function(f){
          return [
            f.id,
            f.numero || '',
            (f.date_emission || '').toString().replace('T',' ').slice(0,10),
            ((f.client_nom||'') + ' ' + (f.client_prenom||'')).trim(),
            getStatutBadge(f.statut),
            (typeof f.total_ttc !== 'undefined' ? parseFloat(f.total_ttc).toFixed(2) + ' DA' : ''),
            getActions(f)
          ];
        });

        // Détruire l'ancienne instance DataTables si elle existe
        if(facturesDataTable){
          facturesDataTable.destroy();
          facturesDataTable = null;
        }

        // Vider le tbody
        $('#fact_table').empty();

        // Initialiser DataTables avec les nouvelles données
        facturesDataTable = $table.DataTable({
          data: tableData,
          destroy: true,
          language: {
            url: '//cdn.datatables.net/plug-ins/1.13.7/i18n/fr-FR.json',
            emptyTable: 'Aucune facture'
          },
          order: [[0, 'desc']],
          columnDefs: [
            { targets: [4, 6], orderable: false },
            { targets: 5, className: 'text-right' },
            { targets: 6, className: 'text-center' }
          ],
          pageLength: 25
        });

        updateTotalsSummary(rows);
      })
      .fail(function(xhr){
        console.error('[Facture.js] factures list fail', xhr.status, xhr.responseText || xhr.statusText);
        $('#fact_table').html('<tr><td colspan="7" class="text-center text-danger">Erreur de chargement</td></tr>');
      });
  }

  function updateTotalsSummary(rows){
    rows = Array.isArray(rows) ? rows : [];
    let totalHT = 0, totalTVA = 0, totalTTC = 0;
    rows.forEach(function(f){
      totalHT += parseFloat(f.total_ht || 0) || 0;
      totalTVA += parseFloat(f.total_tva || 0) || 0;
      totalTTC += parseFloat(f.total_ttc || 0) || 0;
    });
    $('#total-ht-display').text((totalHT).toFixed(2) + ' €');
    $('#total-tva-display').text((totalTVA).toFixed(2) + ' €');
    $('#total-ttc-display').text((totalTTC).toFixed(2) + ' €');
    $('#total-factures-count').text(rows.length);
  }

  function createFactureFromBL(){
    const bl = $('#fact_bl').val();
    console.log('[Facture.js] Creating facture from BL:', bl);
    const tva = parseFloat($('#fact_tva').val()||'20') || 0;
    const numero = ($('#fact_num').val()||'').trim();
    if(!bl){ alert('Veuillez sélectionner un bon de livraison validé'); return; }
    const payload = { bon_livraison: parseInt(bl,10), tva_rate: tva };
    if(numero) payload.numero = numero;
    $.ajax({ url: API_BASE + '/factures/from_bl/', method: 'POST', contentType: 'application/json', headers:{ 'X-CSRFToken': getCSRFToken() }, data: JSON.stringify(payload) })
      .done(function(resp){
        console.log('[Facture.js] Facture created successfully:', resp);
        renderFacturesList();
        $('#fact_bl').val('');
        $('#fact_num').val('');
        // Reset custom select BL if function exists
        if(typeof window.resetFactureBLCustomSelect === 'function'){
          window.resetFactureBLCustomSelect();
        }
        alert('Facture créée avec succès!');
      })
      .fail(function(xhr){
        console.error('[Facture.js] Error creating facture:', xhr.status, xhr.responseText);
        alert('Erreur création facture: ' + (xhr.responseText || xhr.statusText));
      });
  }

  function bindActions(){
    $(document).off('change', '#fact_client').on('change', '#fact_client', loadBLs);
    $(document).off('click', '#btn_create_from_bl').on('click', '#btn_create_from_bl', function(e){ e.preventDefault(); createFactureFromBL(); });
    $(document).off('click', '#btn_refresh_factures').on('click', '#btn_refresh_factures', function(e){
      e.preventDefault();
      console.log('[Facture.js] Refreshing...');
      renderFacturesList();
      // Aussi rafraîchir les custom selects
      if(typeof window.resetFactureBLCustomSelect === 'function'){
        window.resetFactureBLCustomSelect();
      }
    });
    $(document).off('click', '.act-issue').on('click', '.act-issue', function(){
      const id = $(this).data('id');
      $.ajax({ url: API_BASE + '/factures/'+id+'/issue/', method: 'POST', headers:{ 'X-CSRFToken': getCSRFToken() } })
        .done(function(){ renderFacturesList(); })
        .fail(function(xhr){ alert('Erreur émission: ' + (xhr.responseText || xhr.statusText)); });
    });
    $(document).off('click', '.act-pay').on('click', '.act-pay', function(){
      const id = $(this).data('id');
      $.ajax({ url: API_BASE + '/factures/'+id+'/pay/', method: 'POST', headers:{ 'X-CSRFToken': getCSRFToken() } })
        .done(function(){ renderFacturesList(); })
        .fail(function(xhr){ alert('Erreur paiement: ' + (xhr.responseText || xhr.statusText)); });
    });
  }

  function init(){
    // Vérifier si on est sur la page des factures (chercher le tableau ou le custom select)
    if(!$('#fact_table').length && !$('#customSelectFactClient').length) {
      console.log('[Facture.js] Not on facture page, skipping init');
      return;
    }
    console.log('[Facture.js] Initializing...');
    bindActions();
    renderFacturesList();
  }

  $(init);

  // Aussi initialiser quand le fragment est chargé dynamiquement
  $(document).on('fragment:loaded', function(e, data){
    if(data && data.name === 'facture'){
      console.log('[Facture.js] Fragment loaded, reinitializing...');
      init();
    }
  });
})();