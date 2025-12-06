// Fournisseur page simple CRUD list + add
(function($){
  const API_BASE = '/API/fournisseurs/';
  const DEBUG = true; function dbg(...a){ if(DEBUG) try{ console.log('[Fournisseur]', ...a);}catch(e){} }

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
      $libelle: $('#libelle'),
      $email: $('#email'),
      $adresse: $('#addresse'), // note: template uses id="addresse"
      $tel: $('#tel'),
      $btn: $('#btn'),
      $tableBody: $('#table-content')
    };
  }

  function resetForm(){
    const { $id, $libelle, $email, $adresse, $tel } = els();
    $id.val('');
    $libelle.val('');
    $email.val('');
    $adresse.val('');
    $tel.val('');
  }

  function asList(data){
    if(Array.isArray(data)) return data;
    if(data && Array.isArray(data.results)) return data.results;
    if(data && typeof data === 'object') return Object.values(data);
    return [];
  }

  function loadFournisseurs(){
    return $.ajax({ url: API_BASE + '?page_size=1000', method: 'GET', dataType: 'json' })
      .done(function(data){
        const list = asList(data);
        dbg('loadFournisseurs: list size =', list.length, list);
        const { $tableBody } = els();
        $tableBody.empty();
        if(!list || !list.length){
          $tableBody.append('<tr><td colspan="7" class="text-center text-muted">Aucun fournisseur</td></tr>');
          return;
        }
        list.forEach(function(f){
          const $tr = $('<tr>');
          $tr.append(`<td>${f.id}</td>`);
          $tr.append(`<td>${f.libelle || ''}</td>`);
          $tr.append(`<td>${f.email || ''}</td>`);
          $tr.append(`<td>${f.telephone || ''}</td>`);
          $tr.append(`<td>${f.adresse || ''}</td>`);
          $tr.append(`<td><button type="button" class="btn btn-sm btn-outline-danger btn-delete" data-id="${f.id}"><i class="fas fa-trash"></i></button></td>`);
          $tr.append(`<td><button type="button" class="btn btn-sm btn-outline-primary btn-edit" data-id="${f.id}"><i class="fas fa-edit"></i></button></td>`);
          $tableBody.append($tr);
        });
      })
      .fail(function(xhr){
        const { $tableBody } = els();
        $tableBody.empty().append('<tr><td colspan="7" class="text-center text-danger">Erreur de chargement</td></tr>');
        dbg('loadFournisseurs: fail', xhr.status, xhr.responseText || xhr.statusText);
      });
  }

  function payloadFromForm(){
    const { $libelle, $email, $adresse, $tel } = els();
    return {
      libelle: ($libelle.val()||'').trim(),
      email: ($email.val()||'').trim(),
      adresse: ($adresse.val()||'').trim(),
      telephone: ($tel.val()||'').trim()
    };
  }

  function validate(data){
    if(!data.libelle){ alert('Le libelle est obligatoire'); return false; }
    return true;
  }

  function createFournisseur(){
    const data = payloadFromForm();
    if(!validate(data)) return;
    dbg('createFournisseur payload', data);
    $.ajax({ url: API_BASE, method: 'POST', contentType: 'application/json', data: JSON.stringify(data) })
      .done(function(resp){ dbg('createFournisseur success', resp); resetForm(); loadFournisseurs(); })
      .fail(function(xhr){
        dbg('createFournisseur fail', xhr.status, xhr.responseText || xhr.statusText, xhr.responseJSON);
        let msg = 'Erreur lors de la création du fournisseur';
        const j = xhr.responseJSON; if(j){
          if(j.detail) msg = j.detail; else if(j.error) msg = j.error;
          else if(j.libelle && Array.isArray(j.libelle) && j.libelle.length) msg = j.libelle[0];
        }
        alert(msg);
      });
  }

  function deleteFournisseur(id){
    if(!confirm('Supprimer ce fournisseur ?')) return;
    $.ajax({ url: API_BASE + id + '/', method: 'DELETE' })
      .done(function(){ loadFournisseurs(); })
      .fail(function(xhr){
        let msg = (xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Suppression impossible';
        alert(msg);
      });
  }

  function bind(){
    const { $btn } = els();
    $(document).off('click', '#btn').on('click', '#btn', function(){ createFournisseur(); });
    $(document).off('click', '#table-content .btn-delete').on('click', '#table-content .btn-delete', function(){
      const id = $(this).data('id'); deleteFournisseur(id);
    });
  }

  function init(){
    // Only on fournisseur page: detect a specific element
    if(!document.getElementById('tfourni')){ dbg('init fournisseur: table not found, skip'); return; }
    bind();
    loadFournisseurs();
  }

  $(document).ready(init);
  document.addEventListener('fragment:loaded', function(e){ if(e && e.detail && e.detail.name==='fournisseur'){ init(); } });
})(jQuery);
