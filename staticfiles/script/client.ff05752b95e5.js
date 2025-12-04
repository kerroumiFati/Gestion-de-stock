// Client page simple CRUD list + add
(function($){
  const API_BASE = '/API/clients/';
  const API_SECTEURS = '/API/secteurs/';
  const DEBUG = true; function dbg(...a){ if(DEBUG) try{ console.log('[Client]', ...a);}catch(e){} }

  function getCookie(name){
    const m = document.cookie.split('; ').find(r=>r.startsWith(name+'='));
    return m ? decodeURIComponent(m.split('=')[1]) : null;
  }
  function getCSRFToken(){
    let t = getCookie('csrftoken');
    if(!t){ const el = document.querySelector('input[name="csrfmiddlewaretoken"]'); if(el) t = el.value; }
    return t;
  }
  $.ajaxSetup({
    beforeSend: function(xhr, settings){
      if(!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type)){
        const t = getCSRFToken(); if(t) xhr.setRequestHeader('X-CSRFToken', t);
      }
    }
  });

  function els(){
    return {
      $id: $('#id'),
      $nom: $('#nom'),
      $prenom: $('#prenom'),
      $email: $('#email'),
      $adresse: $('#adresse'),
      $telephone: $('#telephone'),
      $secteur: $('#secteur'),
      $nif: $('#nif'),
      $nis: $('#nis'),
      $ai: $('#ai'),
      $rc: $('#rc'),
      $btn: $('#btnClient'),
      $tableBody: $('#table-content')
    };
  }

  function resetForm(){
    const { $id, $nom, $prenom, $email, $adresse, $telephone, $secteur, $nif, $nis, $ai, $rc, $btn } = els();
    $id.val('');
    $nom.val('');
    $prenom.val('');
    $email.val('');
    $adresse.val('');
    $telephone.val('');
    // Reset secteur select to first option (empty value)
    $secteur.prop('selectedIndex', 0);
    $nif.val('');
    $nis.val('');
    $ai.val('');
    $rc.val('');
    $btn.html('<i class="fa fa-plus"></i> Ajouter');
  }

  function asList(data){
    if(Array.isArray(data)) return data;
    if(data && Array.isArray(data.results)) return data.results;
    if(data && typeof data === 'object') return Object.values(data);
    return [];
  }

  // Load secteurs into select
  function loadSecteurs(){
    return $.ajax({ url: API_SECTEURS + '?is_active=true', method: 'GET', dataType: 'json' })
      .done(function(data){
        const list = asList(data);
        dbg('loadSecteurs: list size =', list.length);
        const $secteur = $('#secteur');
        $secteur.find('option:not(:first)').remove();
        list.forEach(function(s){
          const colorDot = s.couleur ? `<span style="display:inline-block;width:10px;height:10px;background:${s.couleur};border-radius:50%;margin-right:5px;"></span>` : '';
          $secteur.append(`<option value="${s.id}" data-couleur="${s.couleur || ''}">${s.code} - ${s.nom}</option>`);
        });
      })
      .fail(function(xhr){
        dbg('loadSecteurs: fail', xhr.status);
      });
  }

  function loadClients(){
    return $.ajax({ url: API_BASE + '?page_size=1000', method: 'GET', dataType: 'json' })
      .done(function(data){
        const list = asList(data);
        dbg('loadClients: list size =', list.length, list);
        const { $tableBody } = els();
        $tableBody.empty();
        if(!list || !list.length){
          $tableBody.append('<tr><td colspan="12" class="text-center text-muted">Aucun client</td></tr>');
          return;
        }
        list.forEach(function(c){
          const $tr = $('<tr>');
          $tr.append(`<td>${c.id}</td>`);
          $tr.append(`<td>${c.nom || ''}</td>`);
          $tr.append(`<td>${c.prenom || ''}</td>`);
          $tr.append(`<td>${c.email || ''}</td>`);
          $tr.append(`<td>${c.telephone || ''}</td>`);
          $tr.append(`<td>${c.adresse || ''}</td>`);
          // Secteur avec badge coloré
          const secteurHtml = c.secteur_nom
            ? `<span class="badge" style="background-color: ${c.secteur_couleur || '#6c757d'}; color: white;">${c.secteur_code || ''} - ${c.secteur_nom}</span>`
            : '<span class="text-muted">-</span>';
          $tr.append(`<td>${secteurHtml}</td>`);
          // Champs fiscaux
          $tr.append(`<td>${c.nif || '<span class="text-muted">-</span>'}</td>`);
          $tr.append(`<td>${c.nis || '<span class="text-muted">-</span>'}</td>`);
          $tr.append(`<td>${c.ai || '<span class="text-muted">-</span>'}</td>`);
          $tr.append(`<td>${c.rc || '<span class="text-muted">-</span>'}</td>`);
          $tr.append(`<td>
            <button type="button" class="action-btn action-btn-edit btn-edit" data-id="${c.id}"><i class="fas fa-edit"></i></button>
            <button type="button" class="action-btn action-btn-delete btn-delete" data-id="${c.id}"><i class="fas fa-trash"></i></button>
          </td>`);
          $tableBody.append($tr);
        });
      })
      .fail(function(xhr){
        const { $tableBody } = els();
        $tableBody.empty().append('<tr><td colspan="12" class="text-center text-danger">Erreur de chargement</td></tr>');
        dbg('loadClients: fail', xhr.status, xhr.responseText || xhr.statusText);
      });
  }

  function payloadFromForm(){
    const { $nom, $prenom, $email, $adresse, $telephone, $secteur, $nif, $nis, $ai, $rc } = els();
    const secteurVal = $secteur.val();
    return {
      nom: ($nom.val()||'').trim(),
      prenom: ($prenom.val()||'').trim(),
      email: ($email.val()||'').trim(),
      adresse: ($adresse.val()||'').trim(),
      telephone: ($telephone.val()||'').trim(),
      secteur: secteurVal ? parseInt(secteurVal, 10) : null,
      nif: ($nif.val()||'').trim(),
      nis: ($nis.val()||'').trim(),
      ai: ($ai.val()||'').trim(),
      rc: ($rc.val()||'').trim()
    };
  }

  function validate(data){
    if(!data.nom){ alert('Le nom est obligatoire'); return false; }
    if(!data.prenom){ alert('Le prenom est obligatoire'); return false; }
    if(!data.email){ alert('L\'email est obligatoire'); return false; }
    if(!data.adresse){ alert('L\'adresse est obligatoire'); return false; }
    if(!data.telephone){ alert('Le téléphone est obligatoire'); return false; }
    return true;
  }

  function createClient(){
    const data = payloadFromForm();
    if(!validate(data)) return;
    dbg('createClient payload', data);
    $.ajax({ url: API_BASE, method: 'POST', contentType: 'application/json', data: JSON.stringify(data) })
      .done(function(resp){ dbg('createClient success', resp); resetForm(); loadClients(); })
      .fail(function(xhr){
        dbg('createClient fail', xhr.status, xhr.responseText || xhr.statusText, xhr.responseJSON);
        let msg = 'Erreur lors de la création du client';
        const j = xhr.responseJSON; if(j){
          if(j.detail) msg = j.detail; else if(j.error) msg = j.error;
          else if(j.nom && Array.isArray(j.nom) && j.nom.length) msg = j.nom[0];
        }
        alert(msg);
      });
  }

  function updateClient(id){
    const data = payloadFromForm();
    if(!validate(data)) return;
    dbg('updateClient payload', id, data);
    $.ajax({ url: API_BASE + id + '/', method: 'PATCH', contentType: 'application/json', data: JSON.stringify(data) })
      .done(function(resp){ dbg('updateClient success', resp); resetForm(); loadClients(); })
      .fail(function(xhr){
        dbg('updateClient fail', xhr.status, xhr.responseText || xhr.statusText, xhr.responseJSON);
        let msg = 'Erreur lors de la modification du client';
        const j = xhr.responseJSON; if(j){
          if(j.detail) msg = j.detail; else if(j.error) msg = j.error;
        }
        alert(msg);
      });
  }

  function editClient(id){
    $.ajax({ url: API_BASE + id + '/', method: 'GET', dataType: 'json' })
      .done(function(c){
        dbg('editClient loaded', c);
        const { $id, $nom, $prenom, $email, $adresse, $telephone, $secteur, $nif, $nis, $ai, $rc, $btn } = els();
        $id.val(c.id);
        $nom.val(c.nom || '');
        $prenom.val(c.prenom || '');
        $email.val(c.email || '');
        $adresse.val(c.adresse || '');
        $telephone.val(c.telephone || '');
        // Set secteur value - use the ID from the client object
        if(c.secteur){
          $secteur.val(c.secteur);
          // If the value didn't set (option doesn't exist yet), wait a bit and try again
          if(!$secteur.val()){
            setTimeout(function(){ $secteur.val(c.secteur); }, 100);
          }
        } else {
          $secteur.prop('selectedIndex', 0);
        }
        $nif.val(c.nif || '');
        $nis.val(c.nis || '');
        $ai.val(c.ai || '');
        $rc.val(c.rc || '');
        $btn.html('<i class="fa fa-save"></i> Modifier');
        // Scroll to form
        $('html, body').animate({ scrollTop: $('#nom').offset().top - 100 }, 300);
      })
      .fail(function(xhr){
        dbg('editClient fail', xhr.status);
        alert('Impossible de charger le client');
      });
  }

  function deleteClient(id){
    if(!confirm('Supprimer ce client ?')) return;
    $.ajax({ url: API_BASE + id + '/', method: 'DELETE' })
      .done(function(){ loadClients(); })
      .fail(function(xhr){
        let msg = (xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Suppression impossible';
        alert(msg);
      });
  }

  function bind(){
    $(document).off('click', '#btnClient').on('click', '#btnClient', function(){
      const { $id } = els();
      const id = $id.val();
      if(id){
        updateClient(id);
      } else {
        createClient();
      }
    });
    $(document).off('click', '#table-content .btn-delete').on('click', '#table-content .btn-delete', function(){
      const id = $(this).data('id'); deleteClient(id);
    });
    $(document).off('click', '#table-content .btn-edit').on('click', '#table-content .btn-edit', function(){
      const id = $(this).data('id'); editClient(id);
    });
  }

  function init(){
    if(!document.getElementById('tclient')){ dbg('init client: table not found, skip'); return; }
    bind();
    loadSecteurs();
    loadClients();
  }

  $(document).ready(init);
})(jQuery);
