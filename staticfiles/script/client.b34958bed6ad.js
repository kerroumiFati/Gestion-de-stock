// Client page simple CRUD list + add
(function($){
  const API_BASE = '/API/clients/';
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
      $btn: $('#btnClient'),
      $tableBody: $('#table-content')
    };
  }

  function resetForm(){
    const { $id, $nom, $prenom, $email, $adresse, $telephone } = els();
    $id.val(''); $nom.val(''); $prenom.val(''); $email.val(''); $adresse.val(''); $telephone.val('');
  }

  function asList(data){
    if(Array.isArray(data)) return data;
    if(data && Array.isArray(data.results)) return data.results;
    if(data && typeof data === 'object') return Object.values(data);
    return [];
  }

  function loadClients(){
    return $.ajax({ url: API_BASE + '?page_size=1000', method: 'GET', dataType: 'json' })
      .done(function(data){
        const list = asList(data);
        dbg('loadClients: list size =', list.length, list);
        const { $tableBody } = els();
        $tableBody.empty();
        if(!list || !list.length){
          $tableBody.append('<tr><td colspan="8" class="text-center text-muted">Aucun client</td></tr>');
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
          $tr.append(`<td><button type="button" class="btn btn-sm btn-outline-danger btn-delete" data-id="${c.id}"><i class="fas fa-trash"></i></button></td>`);
          $tr.append(`<td><button type="button" class="btn btn-sm btn-outline-primary btn-edit" data-id="${c.id}"><i class="fas fa-edit"></i></button></td>`);
          $tableBody.append($tr);
        });
      })
      .fail(function(xhr){
        const { $tableBody } = els();
        $tableBody.empty().append('<tr><td colspan="8" class="text-center text-danger">Erreur de chargement</td></tr>');
        dbg('loadClients: fail', xhr.status, xhr.responseText || xhr.statusText);
      });
  }

  function payloadFromForm(){
    const { $nom, $prenom, $email, $adresse, $telephone } = els();
    return {
      nom: ($nom.val()||'').trim(),
      prenom: ($prenom.val()||'').trim(),
      email: ($email.val()||'').trim(),
      adresse: ($adresse.val()||'').trim(),
      telephone: ($telephone.val()||'').trim()
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
    $(document).off('click', '#btnClient').on('click', '#btnClient', function(){ createClient(); });
    $(document).off('click', '#table-content .btn-delete').on('click', '#table-content .btn-delete', function(){
      const id = $(this).data('id'); deleteClient(id);
    });
  }

  function init(){
    if(!document.getElementById('tclient')){ dbg('init client: table not found, skip'); return; }
    bind();
    loadClients();
    // Safe delegated handler for add/update if needed later
    $(document).off('click', '#tclient .btn-edit');
  }

  $(document).ready(init);
})(jQuery);
