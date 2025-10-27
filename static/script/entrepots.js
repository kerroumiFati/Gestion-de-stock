(function(){
  const apiBase = '/API';
  const $ = window.jQuery;

  function getCookie(name){
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }
  function notify(type, msg){
    const cls = type === 'success' ? 'alert-success' : type === 'warning' ? 'alert-warning' : 'alert-danger';
    const box = $('<div>').addClass('alert '+cls+' alert-dismissible fade show').text(msg);
    box.append('<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>');
    $('#wh_alerts').empty().append(box);
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
      items.forEach(function(w){
        const tr = $('<tr>');
        tr.append($('<td>').text(w.id));
        tr.append($('<td>').text(w.code));
        tr.append($('<td>').text(w.name));
        tr.append($('<td>').text(w.is_active ? 'Oui' : 'Non'));
        tr.append($('<td>').text((w.stocks_count || 0) + ' lignes / ' + (w.stocks_total || 0)));
        const btnToggle = $('<button class=\"btn btn-sm btn-outline-secondary mr-2\"></button>')
          .text(w.is_active ? 'Désactiver' : 'Activer')
          .on('click', function(){
            ajaxJSON({ url: apiBase + '/entrepots/'+w.id+'/', method:'PATCH', data: JSON.stringify({is_active: !w.is_active}) })
              .then(function(){ notify('success', 'Statut mis à jour'); loadList(); })
              .catch(function(xhr){ notify('error', (xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur mise à jour'); });
          });
        const btnEdit = $('<button class="btn btn-sm btn-outline-primary">Modifier</button>').on('click', function(){
          $('#wh_id').val(w.id);
          $('#wh_name').val(w.name);
          $('#wh_code').val(w.code);
          $('#wh_active').val(String(!!w.is_active));
          $('html,body').animate({scrollTop:0}, 200);
        });
        const btnDel = $('<button class="btn btn-sm btn-outline-danger">Supprimer</button>').on('click', function(){
          if (!confirm('Supprimer cet entrepôt ?')) return;
          ajaxJSON({ url: apiBase + '/entrepots/'+w.id+'/', method:'DELETE' })
            .then(function(){ notify('success', 'Entrepôt supprimé'); loadList(); })
            .catch(function(xhr){ notify('error', (xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur suppression'); });
        });
        tr.append($('<td>').append(btnToggle).append(btnEdit));
        tr.append($('<td>').append(btnDel));
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
    resetForm();
    loadList();
    $('#wh_save').on('click', save);
    $('#wh_reset').on('click', resetForm);
    $('#wh_show_inactive').on('change', loadList);
  }

  $(document).ready(init);
})();