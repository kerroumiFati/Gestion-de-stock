(function(){
  const API_BASE = '/API';
  const $ = window.jQuery;

  function asList(resp){
    if(Array.isArray(resp)) return resp;
    if(resp && Array.isArray(resp.results)) return resp.results;
    return [];
  }

  function getCSRFToken(){
    const match = document.cookie.match(/csrftoken=([^;]+)/); return match ? match[1] : '';
  }

  function loadClients(){
    const $sel = $('#fact_client');
    if(!$sel.length) return;
    const first = $sel.find('option').first();
    $sel.empty().append(first);
    return $.ajax({ url: API_BASE + '/clients/?page_size=200', method: 'GET', dataType: 'json' })
      .done(function(data){
        const items = asList(data);
        items.forEach(function(c){
          const label = [(c.nom||'').trim(), (c.prenom||'').trim()].filter(Boolean).join(' ');
          $('<option>').val(c.id).text(label || ('Client #' + c.id)).appendTo($sel);
        });
      })
      .fail(function(xhr){
        console.warn('loadClients fail', xhr.status, xhr.responseText || xhr.statusText);
      });
  }

  function loadBLs(){
    const $sel = $('#fact_bl');
    if(!$sel.length) return;
    const clientId = $('#fact_client').val();
    const first = $sel.find('option').first();
    $sel.empty().append(first);
    if(!clientId){ return; }
    return $.ajax({ url: API_BASE + '/bons/', method: 'GET', data: { statut: 'validated', client: clientId }, dataType: 'json' })
      .done(function(data){
        const items = asList(data);
        items.forEach(function(bl){
          const label = (bl.numero ? (bl.numero + ' - ') : '') + (bl.date_creation || '');
          $('<option>').val(bl.id).text(label).appendTo($sel);
        });
      })
      .fail(function(xhr){ console.warn('loadBLs fail', xhr.status, xhr.responseText || xhr.statusText); });
  }

  function renderFacturesList(){
    const $tbody = $('#fact_table'); if(!$tbody.length) return;
    $.ajax({ url: API_BASE + '/factures/?page_size=100', method: 'GET', dataType: 'json' })
      .done(function(data){
        const rows = asList(data);
        $tbody.empty();
        if(!rows.length){ $tbody.append('<tr><td colspan="7" class="text-center text-muted">Aucune facture</td></tr>'); return; }
        rows.forEach(function(f){
          const tr = $('<tr>');
          tr.append('<td>'+ f.id +'</td>');
          tr.append('<td>'+ (f.numero || '') +'</td>');
          tr.append('<td>'+ (f.date_emission || '').toString().replace('T',' ').slice(0,16) +'</td>');
          tr.append('<td>'+ ((f.client_nom||'') + ' ' + (f.client_prenom||'')) +'</td>');
          tr.append('<td>'+ (f.statut || '') +'</td>');
          tr.append('<td>'+ (typeof f.total_ttc !== 'undefined' ? f.total_ttc : '') +'</td>');
          const actions = [
            '<a class="btn btn-sm btn-outline-primary" target="_blank" href="'+ API_BASE +'/factures/'+ f.id +'/printable/">Imprimer</a>'
          ];
          if(f.statut === 'draft'){
            actions.push('<button class="btn btn-sm btn-success act-issue" data-id="'+f.id+'">Emettre</button>');
          }
          if(f.statut === 'issued'){
            actions.push('<button class="btn btn-sm btn-warning act-pay" data-id="'+f.id+'">Payer</button>');
          }
          tr.append('<td>'+ actions.join(' ') +'</td>');
          $tbody.append(tr);
        });
        updateTotalsSummary(rows);
      })
      .fail(function(xhr){ console.warn('factures list fail', xhr.status, xhr.responseText || xhr.statusText); });
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
    const tva = parseFloat($('#fact_tva').val()||'20') || 0;
    const numero = ($('#fact_num').val()||'').trim();
    if(!bl){ alert('Veuillez sélectionner un bon de livraison validé'); return; }
    const payload = { bon_livraison: parseInt(bl,10), tva_rate: tva };
    if(numero) payload.numero = numero;
    $.ajax({ url: API_BASE + '/factures/from_bl/', method: 'POST', contentType: 'application/json', headers:{ 'X-CSRFToken': getCSRFToken() }, data: JSON.stringify(payload) })
      .done(function(){ renderFacturesList(); $('#fact_bl').val(''); $('#fact_num').val(''); })
      .fail(function(xhr){ alert('Erreur création facture: ' + (xhr.responseText || xhr.statusText)); });
  }

  function bindActions(){
    $(document).off('change', '#fact_client').on('change', '#fact_client', loadBLs);
    $(document).off('click', '#btn_create_from_bl').on('click', '#btn_create_from_bl', function(e){ e.preventDefault(); createFactureFromBL(); });
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
    if(!$('#fact_client').length) return;
    bindActions();
    loadClients().then(loadBLs);
    renderFacturesList();
  }

  $(init);
})();