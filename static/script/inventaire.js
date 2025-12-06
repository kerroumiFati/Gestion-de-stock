(function(){
  const API_BASE = '/API';
  const $ = window.jQuery;

  function asList(resp){ if(Array.isArray(resp)) return resp; if(resp && Array.isArray(resp.results)) return resp.results; return []; }
  function getCSRF(){ const m = document.cookie.match(/csrftoken=([^;]+)/); return m ? m[1] : ''; }

  // Populate product selector
  function loadProducts(){
    const $sel = $('#inv_add_product'); if(!$sel.length) return $.Deferred().resolve().promise();
    const first = $sel.find('option').first().clone();
    $sel.empty().append(first);
    return $.ajax({ url: API_BASE + '/produits/?page_size=1000', method: 'GET', dataType: 'json' })
      .done(function(data){
        const items = asList(data);
        items.forEach(function(p){
          const label = (p.reference ? (p.reference + ' - ') : '') + (p.designation || ('Produit #' + p.id));
          $('<option>').val(p.id).text(label).appendTo($sel);
        });
      })
      .fail(function(xhr){ console.warn('loadProducts fail', xhr.status, xhr.responseText || xhr.statusText); });
  }

  // Create inventory session
  function createSession(){
    const numero = ($('#inv_num').val()||'').trim();
    const date = ($('#inv_date').val()||'').trim();
    const note = ($('#inv_note').val()||'').trim();
    if(!numero){ alert('Veuillez saisir un numéro (ex: INV-2025-0001)'); return; }
    const payload = { numero: numero, date: date || undefined, note: note, lignes: [] };
    $.ajax({ url: API_BASE + '/inventaires/', method:'POST', contentType:'application/json', headers:{ 'X-CSRFToken': getCSRF() }, data: JSON.stringify(payload) })
      .done(function(resp){
        $('#btn_save_progress, #btn_validate_session').prop('disabled', false);
        $('#progress_section').show();
        if(resp && resp.numero){ $('#inv_num').val(resp.numero); }
        loadSessions();
        renderSessionLines(resp);
      })
      .fail(function(xhr){ alert('Erreur création session: ' + (xhr.responseText || xhr.statusText)); });
  }

  // Render session lines table
  function renderSessionLines(session){
    const $tbody = $('#inv_table'); if(!$tbody.length) return;
    $tbody.empty();
    const lignes = (session && session.lignes) ? session.lignes : [];
    if(!lignes.length){
      $tbody.append('<tr><td colspan="8" class="text-center text-muted">Aucune ligne pour le moment</td></tr>');
    } else {
      lignes.forEach(function(l){
        const tr = $('<tr>');
        tr.append('<td>'+ (l.produit_reference ? (l.produit_reference + ' - ') : '') + (l.produit_designation || '') +'</td>');
        tr.append('<td>'+ (l.snapshot_qty ?? '-') +'</td>');
        tr.append('<td>'+ (l.counted_qty ?? '-') +'</td>');
        const variance = (typeof l.variance !== 'undefined' && l.variance !== null) ? l.variance : ( (l.counted_qty!=null && l.snapshot_qty!=null) ? (l.counted_qty - l.snapshot_qty) : '-' );
        tr.append('<td>'+ variance +'</td>');
        tr.append('<td>'+ (l.is_completed ? 'Compté' : 'Non compté') +'</td>');
        tr.append('<td>'+ (l.counted_by_username || '') +'</td>');
        tr.append('<td>'+ (l.counted_at || '') +'</td>');
        tr.append('<td><!-- actions ligne à venir --></td>');
        $tbody.append(tr);
      });
    }
    // Update progress header
    $('#completed_count').text(session.completed_products || 0);
    $('#total_count').text(session.total_products || 0);
    const pct = Number(session.completion_percentage || 0);
    $('#progress_bar').css('width', pct+'%').attr('aria-valuenow', pct);
    $('#progress_text').text(pct.toFixed(0)+'%');
    $('#created_by').text(session.created_by_username || '-');
    // Store current session id
    $('#inv_table').data('session-id', session.id);
  }

  // Load sessions list (history)
  function loadSessions(){
    const $tbody = $('#inv_sessions_table'); if(!$tbody.length) return;
    $.ajax({ url: API_BASE + '/inventaires/?page_size=100', method:'GET', dataType:'json' })
      .done(function(data){
        const rows = asList(data); $tbody.empty();
        if(!rows.length){ $tbody.append('<tr><td colspan="9" class="text-center text-muted">Aucune session</td></tr>'); return; }
        rows.forEach(function(s){
          const tr = $('<tr>');
          tr.append('<td>'+s.id+'</td>');
          tr.append('<td>'+ (s.numero||'') +'</td>');
          tr.append('<td>'+ (s.date||'') +'</td>');
          tr.append('<td>'+ (s.statut||'') +'</td>');
          tr.append('<td>'+ (Number(s.completion_percentage||0).toFixed(0)) +'%</td>');
          tr.append('<td>'+ (s.created_by_username||'') +'</td>');
          tr.append('<td>'+ (s.validated_by_username||'') +'</td>');
          tr.append('<td>'+ (s.note||'') +'</td>');
          tr.append('<td><!-- actions: load/open later --></td>');
          $tbody.append(tr);
        });
      })
      .fail(function(xhr){ console.warn('loadSessions fail', xhr.status, xhr.responseText || xhr.statusText); });
  }

  function addLine(){
    const sessionId = $('#inv_table').data('session-id');
    const prod = parseInt($('#inv_add_product').val()||'0', 10);
    if(!sessionId){ alert('Veuillez créer une session avant d\'ajouter des produits.'); return; }
    if(!prod){ alert('Veuillez sélectionner un produit'); return; }
    // On doit fournir counted_qty? Non, on initialise snapshot_qty à partir du produit courant côté serveur via update_line ou côté client via API dédiée.
    // Comme l'API n'expose pas un endpoint lignes dédié ici, on passe par PUT de la session en ajoutant une ligne minimale.
    const payload = { lignes: [{ produit: prod, counted_qty: null, snapshot_qty: 0 }] };
    $.ajax({ url: API_BASE + '/inventaires/'+sessionId+'/', method:'PATCH', contentType:'application/json', headers:{ 'X-CSRFToken': getCSRF() }, data: JSON.stringify(payload) })
      .done(function(sess){ renderSessionLines(sess); })
      .fail(function(xhr){ alert('Erreur ajout ligne: ' + (xhr.responseText || xhr.statusText)); });
  }

  function bind(){
    $(document).off('click', '#btn_create_session').on('click', '#btn_create_session', function(e){ e.preventDefault(); createSession(); });
    $(document).off('click', '#btn_add_line').on('click', '#btn_add_line', function(e){ e.preventDefault(); addLine(); });
  }

  function init(){ if(!$('#btn_create_session').length) return; bind(); loadProducts(); loadSessions(); }
  $(init);
})();