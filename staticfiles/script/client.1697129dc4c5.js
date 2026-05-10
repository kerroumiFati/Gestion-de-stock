// Client page simple CRUD list + add
(function($){
  const API_BASE = '/API/clients/';
  const API_SECTEURS = '/API/secteurs/';
  const API_TYPES_PRIX = '/API/types-prix/';
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
      $type_prix: $('#type_prix'),
      $lat: $('#lat'),
      $lng: $('#lng'),
      $nif: $('#nif'),
      $nis: $('#nis'),
      $ai: $('#ai'),
      $rc: $('#rc'),
      $solde: $('#solde'),
      $btn: $('#btnClient'),
      $tableBody: $('#table-content')
    };
  }

  function resetForm(){
    const { $id, $nom, $prenom, $email, $adresse, $telephone, $secteur, $type_prix, $lat, $lng, $nif, $nis, $ai, $rc, $solde, $btn } = els();
    $id.val('');
    $nom.val('');
    $prenom.val('');
    $email.val('');
    $adresse.val('');
    $telephone.val('');
    // Reset secteur select to first option (empty value)
    $secteur.prop('selectedIndex', 0);
    $type_prix.prop('selectedIndex', 0);
    $lat.val('');
    $lng.val('');
    $nif.val('');
    $nis.val('');
    $ai.val('');
    $rc.val('');
    $solde.val('');
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

  // Load types de prix into select
  function loadTypesPrix(){
    return $.ajax({ url: API_TYPES_PRIX + '?is_active=true', method: 'GET', dataType: 'json' })
      .done(function(data){
        const list = asList(data);
        dbg('loadTypesPrix: list size =', list.length);
        const $type_prix = $('#type_prix');
        $type_prix.find('option:not(:first)').remove();
        list.forEach(function(tp){
          $type_prix.append(`<option value="${tp.id}">${tp.code} - ${tp.libelle}</option>`);
        });
      })
      .fail(function(xhr){
        dbg('loadTypesPrix: fail', xhr.status);
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
          $tableBody.append('<tr><td colspan="16" class="text-center text-muted">Aucun client</td></tr>');
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
          // Type de prix avec badge
          const typePrixHtml = c.type_prix_code
            ? `<span class="badge badge-info">${c.type_prix_code}</span>`
            : '<span class="text-muted">-</span>';
          $tr.append(`<td>${typePrixHtml}</td>`);
          // Coordonnées GPS
          const latDisplay = c.lat != null ? parseFloat(c.lat).toFixed(7) : '<span class="text-muted">-</span>';
          const lngDisplay = c.lng != null ? parseFloat(c.lng).toFixed(7) : '<span class="text-muted">-</span>';
          $tr.append(`<td class="text-right"><small>${latDisplay}</small></td>`);
          $tr.append(`<td class="text-right"><small>${lngDisplay}</small></td>`);
          // Champs fiscaux
          $tr.append(`<td>${c.nif || '<span class="text-muted">-</span>'}</td>`);
          $tr.append(`<td>${c.nis || '<span class="text-muted">-</span>'}</td>`);
          $tr.append(`<td>${c.ai || '<span class="text-muted">-</span>'}</td>`);
          $tr.append(`<td>${c.rc || '<span class="text-muted">-</span>'}</td>`);
          // Solde avec couleur
          const soldeVal = c.solde != null ? parseFloat(c.solde) : 0;
          const soldeClass = soldeVal > 0 ? 'text-success' : (soldeVal < 0 ? 'text-danger' : 'text-muted');
          const soldeDisplay = soldeVal !== 0 ? `<strong>${soldeVal.toFixed(2)} DA</strong>` : '<span class="text-muted">0.00 DA</span>';
          $tr.append(`<td class="${soldeClass}">${soldeDisplay}</td>`);
          $tr.append(`<td>
            <button type="button" class="action-btn action-btn-info btn-historique" data-id="${c.id}" title="Historique des paiements"><i class="fas fa-history"></i></button>
            <button type="button" class="action-btn action-btn-edit btn-edit" data-id="${c.id}"><i class="fas fa-edit"></i></button>
            <button type="button" class="action-btn action-btn-delete btn-delete" data-id="${c.id}"><i class="fas fa-trash"></i></button>
          </td>`);
          $tableBody.append($tr);
        });
      })
      .fail(function(xhr){
        const { $tableBody } = els();
        $tableBody.empty().append('<tr><td colspan="16" class="text-center text-danger">Erreur de chargement</td></tr>');
        dbg('loadClients: fail', xhr.status, xhr.responseText || xhr.statusText);
      });
  }

  function payloadFromForm(){
    const { $nom, $prenom, $email, $adresse, $telephone, $secteur, $type_prix, $lat, $lng, $nif, $nis, $ai, $rc, $solde } = els();
    const secteurVal = $secteur.val();
    const typePrixVal = $type_prix.val();
    const latVal = $lat.val();
    const lngVal = $lng.val();
    const soldeVal = $solde.val();
    return {
      nom: ($nom.val()||'').trim(),
      prenom: ($prenom.val()||'').trim(),
      email: ($email.val()||'').trim(),
      adresse: ($adresse.val()||'').trim(),
      telephone: ($telephone.val()||'').trim(),
      secteur: secteurVal ? parseInt(secteurVal, 10) : null,
      type_prix: typePrixVal ? parseInt(typePrixVal, 10) : null,
      lat: latVal ? parseFloat(latVal) : null,
      lng: lngVal ? parseFloat(lngVal) : null,
      nif: ($nif.val()||'').trim(),
      nis: ($nis.val()||'').trim(),
      ai: ($ai.val()||'').trim(),
      rc: ($rc.val()||'').trim(),
      solde: soldeVal ? parseFloat(soldeVal) : 0
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
    // Load client data
    $.ajax({ url: API_BASE + id + '/', method: 'GET', dataType: 'json' })
      .done(function(c){
        dbg('editClient loaded - FULL CLIENT DATA:', JSON.stringify(c, null, 2));
        dbg('Client secteur value:', c.secteur, 'Type:', typeof c.secteur);

        const { $id, $nom, $prenom, $email, $adresse, $telephone, $secteur, $type_prix, $lat, $lng, $nif, $nis, $ai, $rc, $solde, $btn } = els();

        // Log all select options
        dbg('Available secteur options in select:');
        $secteur.find('option').each(function(){
          dbg('  Option value:', $(this).val(), 'text:', $(this).text());
        });

        // Fill basic fields
        $id.val(c.id);
        $nom.val(c.nom || '');
        $prenom.val(c.prenom || '');
        $email.val(c.email || '');
        $adresse.val(c.adresse || '');
        $telephone.val(c.telephone || '');
        $lat.val(c.lat || '');
        $lng.val(c.lng || '');
        $nif.val(c.nif || '');
        $nis.val(c.nis || '');
        $ai.val(c.ai || '');
        $rc.val(c.rc || '');
        $solde.val(c.solde || '');
        $btn.html('<i class="fa fa-save"></i> Modifier');

        // Set secteur value
        dbg('Attempting to set secteur to:', c.secteur);
        if(c.secteur){
          // Try setting the value directly first
          $secteur.val(c.secteur);
          dbg('After first attempt, secteur value is:', $secteur.val());

          // If value is still empty or null, the option might not exist
          if(!$secteur.val() || $secteur.val() === ''){
            dbg('Value did not set, checking if option exists...');
            const optionExists = $secteur.find('option[value="' + c.secteur + '"]').length > 0;
            dbg('Option exists:', optionExists);

        // Set type_prix value
        dbg('Attempting to set type_prix to:', c.type_prix);
        if(c.type_prix){
          $type_prix.val(c.type_prix);
          dbg('After setting, type_prix value is:', $type_prix.val());
        } else {
          $type_prix.prop('selectedIndex', 0);
        }

            if(!optionExists){
              dbg('Option does not exist, reloading secteurs...');
              loadSecteurs().done(function(){
                dbg('Secteurs reloaded, trying to set value again...');
                $secteur.val(c.secteur);
                dbg('Final secteur value:', $secteur.val());
              });
            } else {
              dbg('Option exists but value not setting, trying again...');
              setTimeout(function(){
                $secteur.val(c.secteur);
                dbg('After timeout, secteur value:', $secteur.val());
              }, 200);
            }
          } else {
            dbg('Secteur value set successfully to:', $secteur.val());
          }
        } else {
          dbg('Client has no secteur, resetting to empty');
          $secteur.prop('selectedIndex', 0);
        }

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

  function showHistoriquePaiements(clientId){
    // Charger l'historique des paiements
    $.ajax({ url: API_BASE + clientId + '/historique_paiements/', method: 'GET' })
      .done(function(data){
        dbg('Historique paiements:', data);

        // Mettre à jour les infos du client
        $('#historique-client-nom').text(data.client_nom);
        const soldeClass = data.solde_actuel >= 0 ? 'text-success' : 'text-danger';
        $('#historique-solde-actuel').html(`<span class="${soldeClass}">${data.solde_actuel >= 0 ? '+' : ''}${data.solde_actuel.toFixed(2)} DA</span>`);
        $('#historique-client-info').show();

        // Construire le tableau d'historique
        let html = '';
        if(data.paiements && data.paiements.length > 0){
          html = `<div class="table-responsive">
            <table class="table table-hover">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Montant</th>
                  <th>Mode</th>
                  <th>Solde Avant</th>
                  <th>Solde Après</th>
                  <th>Enregistré par</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>`;

          data.paiements.forEach(function(p){
            const date = new Date(p.date_paiement).toLocaleString('fr-FR');
            const montantClass = 'text-success';
            const soldeAvantClass = p.solde_avant >= 0 ? 'text-success' : 'text-danger';
            const soldeApresClass = p.solde_apres >= 0 ? 'text-success' : 'text-danger';

            html += `<tr>
              <td><small>${date}</small></td>
              <td class="${montantClass}"><strong>+${p.montant.toFixed(2)} DA</strong></td>
              <td><span class="badge badge-info">${p.mode_paiement_display}</span></td>
              <td class="${soldeAvantClass}">${p.solde_avant >= 0 ? '+' : ''}${p.solde_avant.toFixed(2)} DA</td>
              <td class="${soldeApresClass}">${p.solde_apres >= 0 ? '+' : ''}${p.solde_apres.toFixed(2)} DA</td>
              <td><small>${p.enregistre_par || 'N/A'}</small></td>
              <td><small>${p.notes || '-'}</small></td>
            </tr>`;
          });

          html += `</tbody></table></div>`;
        } else {
          html = `<div class="alert alert-info text-center">
            <i class="fa fa-info-circle"></i> Aucun paiement de solde enregistré pour ce client
          </div>`;
        }

        $('#historique-content').html(html);
        $('#historiqueModal').modal('show');
      })
      .fail(function(xhr){
        dbg('showHistoriquePaiements fail', xhr);
        alert('Impossible de charger l\'historique des paiements');
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
    $(document).off('click', '#table-content .btn-historique').on('click', '#table-content .btn-historique', function(){
      const id = $(this).data('id'); showHistoriquePaiements(id);
    });
  }

  function init(){
    if(!document.getElementById('tclient')){ dbg('init client: table not found, skip'); return; }
    bind();
    loadSecteurs();
    loadTypesPrix();
    loadClients();
  }

  $(document).ready(init);
})(jQuery);
