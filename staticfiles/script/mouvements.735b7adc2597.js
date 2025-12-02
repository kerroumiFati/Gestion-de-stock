/* Mouvements UI logic: load products, handle filter, and submit movement forms */
(function(){
  const apiBase = '/API';
  const $ = window.jQuery;
  let mouvementsDataTable = null;

  function notify(type, msg){
    const cls = type === 'success' ? 'alert-success' : type === 'warning' ? 'alert-warning' : 'alert-danger';
    const box = $('<div>').addClass('alert '+cls+' alert-dismissible fade show').text(msg);
    box.append('<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>');
    $('#results-count').closest('.container-fluid, .card-body').find('#mv_messages').remove();
    const container = $('<div id="mv_messages" class="my-2"></div>').append(box);
    $('.card-body').first().prepend(container);
  }

  function loadProducts(selectors){
    return $.get(apiBase + '/produits/').then(function(items){
      const opts = ['<option value="">Sélectionner</option>'];
      const mvOpts = ['<option value="">Tous</option>'];
      items.forEach(p => {
        const label = `${p.reference} - ${p.designation}`;
        opts.push(`<option value="${p.id}">${label}</option>`);
        mvOpts.push(`<option value="${p.id}">${label}</option>`);
      });
      // mouvement filter select
      if ($('#mv_prod').length){ $('#mv_prod').html(mvOpts.join('')); }
      // form selects
      (selectors || []).forEach(sel => { $(sel).html(opts.join('')); });
    });
  }

  function loadWarehouses(selectors){
    return $.get(apiBase + '/entrepots/').then(function(items){
      const opts = ['<option value="">Sélectionner</option>'];
      items.forEach(w => { opts.push(`<option value="${w.id}">${w.code} - ${w.name}</option>`); });
      (selectors || []).forEach(sel => { $(sel).html(opts.join('')); });
    });
  }

  function loadFournisseurs(selectors){
    return $.get(apiBase + '/fournisseurs/').then(function(items){
      const opts = ['<option value="">Sélectionner un fournisseur</option>'];
      items.forEach(f => { opts.push(`<option value="${f.id}">${f.libelle}</option>`); });
      (selectors || []).forEach(sel => { $(sel).html(opts.join('')); });
    });
  }

  function getDeltaBadge(delta) {
    if (delta > 0) {
      return `<span class="badge badge-success">+${delta}</span>`;
    } else if (delta < 0) {
      return `<span class="badge badge-danger">${delta}</span>`;
    }
    return `<span class="badge badge-secondary">${delta}</span>`;
  }

  function getSourceBadge(source) {
    const colors = {
      'BL': 'primary', 'BC': 'info', 'ACHAT': 'success', 'INV': 'warning',
      'CORR': 'secondary', 'TRANS': 'info', 'PERTE': 'danger', 'CASSE': 'danger',
      'EXP': 'warning', 'SAMPLE': 'purple', 'DON': 'pink', 'CONS': 'orange',
      'VENTE': 'primary', 'RETOUR': 'danger'
    };
    const color = colors[source] || 'secondary';
    return `<span class="badge badge-${color}">${source || ''}</span>`;
  }

  function reloadJournal(){
    const params = {};
    const prod = $('#mv_prod').val();
    const src = $('#mv_src').val();
    const after = $('#mv_after').val();
    const before = $('#mv_before').val();
    const wh = $('#mv_wh').val();
    if (prod) params.produit = prod;
    if (src) params.source = src;
    if (wh) params.warehouse = wh;
    if (after) params.date_after = new Date(after).toISOString();
    if (before) params.date_before = new Date(before).toISOString();

    console.log('[Mouvements.js] Loading journal with params:', params);

    return $.get(apiBase + '/mouvements/', params).then(function(rows){
      console.log('[Mouvements.js] Loaded rows:', rows.length);

      let totalIn = 0, totalOut = 0;

      // Préparer les données pour DataTables
      const tableData = rows.map(r => {
        const d = new Date(r.date);
        const delta = Number(r.delta);
        if (delta > 0) totalIn += delta; else totalOut += Math.abs(delta);

        return [
          d.toLocaleString('fr-FR'),
          r.produit_reference ? `${r.produit_reference} - ${r.produit_designation || ''}` : r.produit,
          r.warehouse_code ? `${r.warehouse_code} - ${r.warehouse_name||''}` : '',
          getDeltaBadge(delta),
          getSourceBadge(r.source),
          r.ref_id || '',
          r.note || ''
        ];
      });

      // Détruire l'ancienne instance DataTables si elle existe
      if (mouvementsDataTable) {
        mouvementsDataTable.destroy();
        mouvementsDataTable = null;
      }

      // Vider le tbody
      $('#tmouv tbody').empty();

      // Initialiser DataTables avec les nouvelles données
      mouvementsDataTable = $('#tmouv').DataTable({
        data: tableData,
        destroy: true,
        language: {
          url: '//cdn.datatables.net/plug-ins/1.13.7/i18n/fr-FR.json',
          emptyTable: 'Aucun mouvement trouvé'
        },
        order: [[0, 'desc']],
        columnDefs: [
          { targets: [3, 4], className: 'text-center' }
        ],
        pageLength: 25,
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "Tous"]]
      });

      $('#results-count').text(`${rows.length} lignes`);
      $('#total-entrees').text(totalIn);
      $('#total-sorties').text(totalOut);
      $('#solde').text(totalIn - totalOut);

    }).catch(function(err){
      notify('error', 'Erreur lors du chargement du journal');
      console.error('[Mouvements.js] Error:', err);
    });
  }

  function setupFilter(){
    $('#mv_filter').on('click', function(){ reloadJournal(); });
    $('#mv_refresh').on('click', function(){
      // Animation de rotation de l'icône pendant le rechargement
      const btn = $(this);
      const icon = btn.find('i');
      icon.addClass('fa-spin');
      reloadJournal().finally(function(){
        icon.removeClass('fa-spin');
      });
    });
    $('#mv_reset').on('click', function(){
      // Reset hidden selects
      $('#mv_prod').val('');
      $('#mv_src').val('');
      $('#mv_after').val('');
      $('#mv_before').val('');
      $('#mv_wh').val('');

      // Reset custom selects triggers text
      resetCustomSelectTrigger('customSelectMvProd', 'Tous');
      resetCustomSelectTrigger('customSelectMvWh', 'Tous');

      reloadJournal();
    });
    $('#mv_export').on('click', function(){
      // Export CSV depuis DataTables
      if (mouvementsDataTable) {
        const headers = [];
        $('#tmouv thead tr th').each(function(){ headers.push($(this).text()); });
        let csv = headers.join(',') + '\n';

        // Utiliser les données de DataTables
        mouvementsDataTable.rows().every(function(){
          const data = this.data();
          const cols = data.map(function(cell){
            // Retirer les balises HTML pour l'export
            let t = $('<div>').html(cell).text().replace(/"/g,'""');
            if (t.indexOf(',')>=0) t = '"'+t+'"';
            return t;
          });
          csv += cols.join(',') + '\n';
        });

        const blob = new Blob([csv], {type:'text/csv;charset=utf-8;'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = 'mouvements.csv'; a.click();
        URL.revokeObjectURL(url);
      }
    });
  }

  function resetCustomSelectTrigger(containerId, defaultText) {
    const container = document.getElementById(containerId);
    if (container) {
      const trigger = container.querySelector('.custom-select-trigger');
      if (trigger) {
        const selectedText = trigger.querySelector('.selected-text');
        if (selectedText) {
          selectedText.textContent = defaultText;
          selectedText.classList.add('placeholder');
        }
      }
      // Reset selected state in options
      const options = container.querySelectorAll('.custom-select-option');
      options.forEach(function(opt) {
        opt.classList.toggle('selected', opt.getAttribute('data-value') === '');
      });
    }
  }

  function getCookie(name){
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }
  function postJSON(url, data){
    const csrftoken = getCookie('csrftoken');
    return $.ajax({
      url,
      method:'POST',
      data: JSON.stringify(data),
      contentType:'application/json',
      headers: csrftoken ? {'X-CSRFToken': csrftoken} : {}
    });
  }

  function setupTransfer(){
    $('#mv_transfer_submit').on('click', function(){
      const produit = $('#mv_transfer_produit').val();
      const quantite = parseFloat($('#mv_transfer_qty').val() || '0');
      const from_warehouse = $('#mv_transfer_from').val();
      const to_warehouse = $('#mv_transfer_to').val();
      const note = $('#mv_transfer_note').val();
      if (!produit || quantite <= 0 || !from_warehouse || !to_warehouse){ return notify('error', 'Sélectionnez produit, quantité > 0 et les deux entrepôts'); }
      postJSON(apiBase + '/mouvements/transfer/', { produit, quantite, from_warehouse, to_warehouse, note })
        .then(function(){ notify('success', 'Transfert enregistré'); reloadJournal(); })
        .catch(function(xhr){
          const msg = (xhr && xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur transfert';
          notify('error', msg);
        });
    });
  }

  function setupLoss(){
    $('#mv_loss_submit').on('click', function(){
      const produit = $('#mv_loss_produit').val();
      const quantite = parseFloat($('#mv_loss_qty').val() || '0');
      const type = $('#mv_loss_type').val();
      const note = $('#mv_loss_note').val();
      const warehouse = $('#mv_loss_warehouse').val();
      if (!produit || quantite <= 0 || !warehouse){ return notify('error', 'Sélectionnez produit, quantité > 0 et entrepôt'); }
      postJSON(apiBase + '/mouvements/loss/', { produit, quantite, type, note, warehouse })
        .then(function(){ notify('success', 'Sortie (perte/casse/exp) enregistrée'); reloadJournal(); })
        .catch(function(xhr){
          const msg = (xhr && xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur enregistrement';
          notify('error', msg);
        });
    });
  }

  function setupOutflow(){
    $('#mv_outflow_submit').on('click', function(){
      const produit = $('#mv_outflow_produit').val();
      const quantite = parseFloat($('#mv_outflow_qty').val() || '0');
      const type = $('#mv_outflow_type').val();
      const note = $('#mv_outflow_note').val();
      const warehouse = $('#mv_outflow_warehouse').val();
      if (!produit || quantite <= 0 || !warehouse){ return notify('error', 'Sélectionnez produit, quantité > 0 et entrepôt'); }
      postJSON(apiBase + '/mouvements/outflow/', { produit, quantite, type, note, warehouse })
        .then(function(){ notify('success', 'Sortie (échantillon/don/consommation) enregistrée'); reloadJournal(); })
        .catch(function(xhr){
          const msg = (xhr && xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur enregistrement';
          notify('error', msg);
        });
    });
  }

  function setupReturn(){
    // Définir la date par défaut à aujourd'hui
    const today = new Date().toISOString().split('T')[0];
    $('#mv_return_date').val(today);

    $('#mv_return_submit').on('click', function(){
      const produit = $('#mv_return_produit').val();
      const quantite = parseFloat($('#mv_return_qty').val() || '0');
      const fournisseur = $('#mv_return_fournisseur').val();
      const warehouse = $('#mv_return_warehouse').val();
      const reason = $('#mv_return_reason').val();
      const note = $('#mv_return_note').val();
      const date = $('#mv_return_date').val();

      // Validations
      if (!produit){ return notify('error', 'Veuillez sélectionner un produit'); }
      if (quantite <= 0){ return notify('error', 'La quantité doit être supérieure à 0'); }
      if (!fournisseur){ return notify('error', 'Veuillez sélectionner un fournisseur'); }
      if (!warehouse){ return notify('error', 'Veuillez sélectionner un entrepôt'); }
      if (!reason){ return notify('error', 'Veuillez sélectionner un motif de retour'); }

      // Construire la note complète avec le motif
      const reasonText = $('#mv_return_reason option:selected').text();
      const fullNote = `RETOUR FOURNISSEUR - ${reasonText}${note ? ': ' + note : ''}`;

      const data = {
        produit: produit,
        quantite: quantite,
        fournisseur: fournisseur,
        warehouse: warehouse,
        reason: reason,
        note: fullNote,
        date: date
      };

      postJSON(apiBase + '/mouvements/return_supplier/', data)
        .then(function(){
          notify('success', 'Retour fournisseur enregistré avec succès');
          // Réinitialiser le formulaire
          $('#mv_return_produit').val('');
          $('#mv_return_qty').val('');
          $('#mv_return_fournisseur').val('');
          $('#mv_return_reason').val('');
          $('#mv_return_note').val('');
          $('#mv_return_date').val(today);
          reloadJournal();
        })
        .catch(function(xhr){
          const msg = (xhr && xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur lors de l\'enregistrement du retour';
          notify('error', msg);
        });
    });
  }

  function init(){
    if (!$('#tmouv').length) return; // not on mouvements page
    // Ensure selects exist before loading
    Promise.all([
      loadProducts(['#mv_transfer_produit', '#mv_loss_produit', '#mv_outflow_produit', '#mv_return_produit']),
      loadWarehouses(['#mv_transfer_from', '#mv_transfer_to', '#mv_loss_warehouse', '#mv_outflow_warehouse', '#mv_return_warehouse', '#mv_wh']),
      loadFournisseurs(['#mv_return_fournisseur'])
    ]).then(reloadJournal);
    setupFilter();
    setupTransfer();
    setupLoss();
    setupOutflow();
    setupReturn();
  }

  $(document).ready(init);
})();
