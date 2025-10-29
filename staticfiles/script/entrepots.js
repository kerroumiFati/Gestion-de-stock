(function(){
  const apiBase = '/API';
  const $ = window.jQuery;

  function getCookie(name){
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }
  function notify(type, msg){
    const cls = type === 'success' ? 'modern-alert-success' : type === 'warning' ? 'modern-alert-warning' : 'modern-alert-danger';
    const icon = type === 'success' ? 'check-circle' : type === 'warning' ? 'exclamation-triangle' : 'times-circle';
    const box = $('<div>').addClass('modern-alert '+cls+' alert-dismissible fade show');
    box.html('<i class="fa fa-'+icon+'"></i> ' + msg + '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>');
    $('#wh_alerts').empty().append(box);
    setTimeout(function(){ box.fadeOut(function(){ box.remove(); }); }, 5000);
  }
  function ajaxJSON(opts){
    const csrftoken = getCookie('csrftoken');
    opts.headers = opts.headers || {};
    if (csrftoken) opts.headers['X-CSRFToken'] = csrftoken;
    if (!opts.contentType) opts.contentType = 'application/json';
    return $.ajax(opts);
  }

  function resetForm(){
    $('#wh_id').val('');
    $('#wh_name').val('');
    $('#wh_code').val('');
    $('#wh_active').val('true');
  }

  function loadList(){
    const include_inactive = $('#wh_show_inactive').is(':checked');
    return $.get(apiBase + '/entrepots/', include_inactive ? {include_inactive: 1} : {}).then(function(items){
      const tbody = $('#twh tbody');
      tbody.empty();

      if(!items || items.length === 0){
        tbody.append('<tr><td colspan="6" class="text-center text-muted">Aucun entrepôt</td></tr>');
        return;
      }

      items.forEach(function(w){
        const tr = $('<tr>');
        tr.append($('<td>').html('<strong>' + w.id + '</strong>'));
        tr.append($('<td>').html('<code style="background: #eff6ff; padding: 3px 8px; border-radius: 4px; color: #1e40af; font-weight: 600;">' + w.code + '</code>'));
        tr.append($('<td>').text(w.name));

        // Badge de statut avec le nouveau design
        const statusBadge = w.is_active ?
          '<span class="status-badge status-badge-active"><i class="fa fa-check-circle"></i> Actif</span>' :
          '<span class="status-badge status-badge-inactive"><i class="fa fa-times-circle"></i> Inactif</span>';
        tr.append($('<td>').html(statusBadge));

        tr.append($('<td>').html('<span class="modern-badge modern-badge-info">' + (w.stocks_count || 0) + ' lignes</span> / <span class="modern-badge modern-badge-default">' + (w.stocks_total || 0) + '</span>'));

        // Boutons avec le nouveau design
        const btnEdit = $('<button type="button" class="btn-edit-warehouse"><i class="fa fa-edit"></i> Modifier</button>').on('click', function(){
          $('#wh_id').val(w.id);
          $('#wh_name').val(w.name);
          $('#wh_code').val(w.code);
          $('#wh_active').val(String(!!w.is_active));
          $('html,body').animate({scrollTop:0}, 200);
        });

        const btnDel = $('<button type="button" class="btn-delete-warehouse ml-2"><i class="fa fa-trash"></i> Supprimer</button>').on('click', function(){
          if (!confirm('Supprimer cet entrepôt ?')) return;
          ajaxJSON({ url: apiBase + '/entrepots/'+w.id+'/', method:'DELETE' })
            .then(function(){ notify('success', 'Entrepôt supprimé'); loadList(); })
            .catch(function(xhr){ notify('error', (xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur suppression'); });
        });

        tr.append($('<td>').append(btnEdit).append(btnDel));
        tbody.append(tr);
      });
    });
  }

  function save(){
    const id = $('#wh_id').val();
    const name = $('#wh_name').val().trim();
    const code = $('#wh_code').val().trim();
    const is_active = $('#wh_active').val() === 'true';
    if (!name || !code) return notify('error', 'Nom et code sont requis');
    const data = JSON.stringify({ name, code, is_active });

    if (id){
      ajaxJSON({ url: apiBase + '/entrepots/'+id+'/', method:'PATCH', data })
        .then(function(){ notify('success', 'Entrepôt mis à jour'); resetForm(); loadList(); })
        .catch(function(xhr){ notify('error', (xhr.responseJSON && JSON.stringify(xhr.responseJSON)) || 'Erreur mise à jour'); });
    } else {
      ajaxJSON({ url: apiBase + '/entrepots/', method:'POST', data })
        .then(function(){ notify('success', 'Entrepôt créé'); resetForm(); loadList(); })
        .catch(function(xhr){ notify('error', (xhr.responseJSON && JSON.stringify(xhr.responseJSON)) || 'Erreur création'); });
    }
  }

  function init(){
    if (!$('#twh').length) return;

    // Détruire DataTable si elle existe déjà
    if ($.fn.DataTable && $.fn.DataTable.isDataTable('#twh')) {
      $('#twh').DataTable().destroy();
    }

    resetForm();
    loadList();
    $('#wh_save').on('click', save);
    $('#wh_reset').on('click', resetForm);
    $('#wh_show_inactive').on('change', loadList);
  }

  $(document).ready(init);

  // Support pour le système de chargement de fragments
  document.addEventListener('fragment:loaded', function(e){
    if(e && e.detail && e.detail.name === 'entrepots'){
      init();
    }
  });
})();