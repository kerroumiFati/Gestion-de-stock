/* Category (Categorie) front-end logic */
// Requires jQuery. Uses Django REST API endpoints under /API/categories/

(function ($) {
  // Global console markers for debugging load/execution
  try { console.log('[Categorie] categorie.js file is executing'); } catch(e){}
  const API_LIST = '/API/categories_raw/'; // list-only (simple JSON)
  const API_REST = '/API/categories/'; // full REST (POST/PATCH/DELETE)
  const API_BASE = API_REST; // backward-compat alias used by update/delete
  const DEBUG = true;
  function dbg(...args){ if (DEBUG) { try { console.log('[Categorie]', ...args); } catch(e){} } }
  
  // Attach global error handlers to ensure we see problems
  try {
    window.addEventListener('error', function(ev){ console.log('[Categorie] window.error:', ev && (ev.message || ev.error) , ev); });
    window.addEventListener('unhandledrejection', function(ev){ console.log('[Categorie] unhandledrejection:', ev && ev.reason); });
    document.addEventListener('DOMContentLoaded', function(){ console.log('[Categorie] DOMContentLoaded fired'); });
    window.addEventListener('load', function(){ console.log('[Categorie] window load fired'); });
    if ($ && $.ajaxSetup) {
      $(document).ajaxStart(function(){ console.log('[Categorie] jQuery ajaxStart'); });
      $(document).ajaxStop(function(){ console.log('[Categorie] jQuery ajaxStop'); });
      $(document).ajaxError(function(event, jqxhr, settings, thrown){ console.log('[Categorie] jQuery ajaxError:', settings && settings.url, jqxhr && jqxhr.status, jqxhr && (jqxhr.responseText || jqxhr.statusText)); });
    }
  } catch(err) { try { console.log('[Categorie] error setting global handlers:', err); } catch(e){} }


  // Toast helper (Bootstrap 4)
  function ensureToastContainer() {
    if (!document.getElementById('toast-container')) {
      const container = document.createElement('div');
      container.id = 'toast-container';
      container.style.position = 'fixed';
      container.style.top = '1rem';
      container.style.right = '1rem';
      container.style.zIndex = '1080';
      document.body.appendChild(container);
    }
  }
  function showToast(message, type = 'success') {
    ensureToastContainer();
    const id = 't' + Math.random().toString(36).slice(2);
    const bg = type === 'success' ? 'bg-success' : type === 'warning' ? 'bg-warning' : type === 'danger' ? 'bg-danger' : 'bg-info';
    const text = type === 'warning' ? 'text-dark' : 'text-white';
    const html = `
      <div id="${id}" class="toast ${text}" role="alert" aria-live="assertive" aria-atomic="true" data-delay="2000" style="min-width:260px;">
        <div class="toast-header ${bg} ${text}">
          <i class="fas fa-check-circle mr-2"></i>
          <strong class="mr-auto">Confirmation</strong>
          <small class="text-light">Maintenant</small>
          <button type="button" class="ml-2 mb-1 close ${text}" data-dismiss="toast" aria-label="Fermer">
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <div class="toast-body ${text}">${message}</div>
      </div>`;
    $('#toast-container').append(html);
    const $t = $('#' + id);
    $t.toast('show');
    $t.on('hidden.bs.toast', function () { $(this).remove(); });
  }

  // Elements (will be resolved fresh each time)
  function els() {
    return {
      $id: $('#id'),
      $nom: $('#nom'),
      $description: $('#description'),
      $parent: $('#parent'),
      $couleur: $('#couleur'),
      $icone: $('#icone'),
      $is_active: $('#is_active'),
      $btn: $('#btn'),
      $btnCancel: $('#btnCancel'),
      $tableBody: $('#table-content'),
      $previewIcon: $('#preview-icon')
    };
  }

  // CSRF handling
  function getCookie(name) {
    const cookieValue = document.cookie
      .split('; ')
      .find((row) => row.startsWith(name + '='));
    return cookieValue ? decodeURIComponent(cookieValue.split('=')[1]) : null;
  }
  function getCSRFToken() {
    // Try cookie first
    let token = getCookie('csrftoken');
    if (!token) {
      // Fallback: hidden input rendered by {% csrf_token %}
      const el = document.querySelector('input[name="csrfmiddlewaretoken"]');
      if (el) token = el.value;
    }
    return token;
  }

  $.ajaxSetup({
    beforeSend: function (xhr, settings) {
      if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type)) {
        const token = getCSRFToken();
        if (token) xhr.setRequestHeader('X-CSRFToken', token);
      }
    },
  });

  function resetForm() {
    dbg('resetForm called');

    const { $id, $nom, $description, $parent, $couleur, $icone, $is_active, $btn, $btnCancel } = els();
    $id.val('');
    $nom.val('');
    $description.val('');
    $parent.val('');
    $couleur.val('#007bff');
    $icone.val('fa-cube');
    $is_active.prop('checked', true);
    $btn.text('Ajouter').removeClass('btn-outline-primary').addClass('btn-outline-success');
    $btn.find('i').attr('class', 'fas fa-plus mr-1');
    $btnCancel.hide();
    updatePreview();
  }

  function updatePreview() {
    const { $couleur, $previewIcon } = els();
    const color = $couleur.val();
    $previewIcon.css('color', color);
  }

  dbg('script loaded, binding events soon');
try { console.log('[Categorie] script tag executed and dbg enabled'); } catch(e){}


  // Simpler response normalizer for GET lists
  function toList(data) {
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.results)) return data.results; // DRF paginated
    return [];
  }

  // Minimal GET helper with robust fallback and clearer errors
  function getJSON(url) {
    console.log('[Categorie] GET', url);
    // If fetch exists, use it; otherwise fallback to jQuery
    if (typeof window.fetch === 'function') {
      return window.fetch(url, {
        credentials: 'same-origin',
        headers: { 'Accept': 'application/json' }
      }).then(function (res) {
        if (!res.ok) {
          return res.text().then(function (t) {
            const msg = 'HTTP ' + res.status + ' ' + res.statusText + (t ? ' - ' + t : '');
            throw new Error(msg);
          });
        }
        // Safely parse JSON and surface parsing errors
        return res.text().then(function (t) {
          try {
            return t ? JSON.parse(t) : [];
          } catch (e) {
            throw new Error('Invalid JSON response: ' + (e && e.message ? e.message : e));
          }
        });
      });
    } else if (window.$ && $.ajax) {
      // Fallback for older environments
      return $.ajax({ url: url, method: 'GET', dataType: 'json' });
    } else {
      // Ultimate fallback
      return Promise.reject(new Error('No HTTP client available (fetch/jQuery missing)'));
    }
  }

  function loadParents(currentId = null) {
    dbg('loadParents: called with currentId=', currentId);
    try { console.log('[Categorie] loadParents start - parent select present?', !!document.getElementById('parent')); } catch(e){}

    // Charger toutes les catégories pour la sélection du parent
    return getJSON(API_LIST)
      .then(function (data) {
        dbg('loadParents: raw data =', data);
        const { $parent } = els();
        const list = toList(data);
        dbg('loadParents: list size =', list.length, list);
        // Conserver la première option par défaut
        $parent.find('option').not(':first').remove();
        (list || []).forEach(function (c) {
          if (!currentId || String(c.id) !== String(currentId)) {
            $parent.append(
              $('<option>').val(c.id).text(c.nom)
            );
          }
        });
      })
      .catch(function (err) {
        console.warn('Impossible de charger les catégories parentes', err && (err.message || err));
      });
  }

  // Cache des catégories pour actions (édition/suppression) avec DataTables
  const categoriesCache = new Map(); // simple cache used only for edit/delete

  function loadCategories() {
    dbg('loadCategories: called');
    try { console.log('[Categorie] loadCategories start - table body present?', !!document.getElementById('table-content')); } catch(e){}

    // Approche simple: remplir le tbody sans DataTables
    return getJSON(API_LIST)
      .then(function (data) {
        dbg('loadCategories: raw data =', data);
        console.log('[Categorie] loadCategories: processed data =', data);
        const list = toList(data);
        dbg('loadCategories: list size =', list.length, list);
        categoriesCache.clear();
        list.forEach(function (c) { categoriesCache.set(String(c.id), c); });

        const { $tableBody } = els();
        $tableBody.empty();
        if (!list || list.length === 0) {
          $tableBody.append('<tr><td colspan="7" class="text-center text-muted">Aucune catégorie</td></tr>');
          return;
        }
        list.forEach(function (c, idx) {
          const statusBadge = c.is_active ? '<span class="badge badge-success">Active</span>' : '<span class="badge badge-secondary">Inactive</span>';
          const productsCount = c.products_count || 0;
          const $tr = $('<tr>');
          $tr.append(`<td>${idx + 1}</td>`);
          $tr.append(`<td><i class="fas ${c.icone || 'fa-cube'}" style="color:${c.couleur || '#007bff'}"></i> ${c.nom}</td>`);
          $tr.append(`<td>${c.description || ''}</td>`);
          $tr.append(`<td>${productsCount}</td>`);
          $tr.append(`<td>${statusBadge}</td>`);
          const $actions = $('<td>');
          $actions.append($(`<button type="button" class="btn btn-sm btn-outline-primary mr-2 btn-edit" data-id="${c.id}"><i class="fas fa-edit"></i></button>`));
          $actions.append($(`<button type="button" class="btn btn-sm btn-outline-danger btn-delete" data-id="${c.id}"><i class="fas fa-trash"></i></button>`));
          $tr.append($actions);
          $tr.append('<td></td>');
          $tableBody.append($tr);
        });
      })
      .catch(function (err) {
        const { $tableBody } = els();
        $tableBody.empty().append('<tr><td colspan="7" class="text-center text-danger">Erreur de chargement</td></tr>');
        console.error('Erreur GET categories:', err && (err.message || err));
      });
  }

  function startEdit(c) {
    dbg('startEdit called with', c);

    const { $id, $nom, $description, $parent, $couleur, $icone, $is_active, $btn, $btnCancel } = els();

    // S'assurer que les champs sont éditables
    $nom.prop('readonly', false).prop('disabled', false);
    $description.prop('readonly', false).prop('disabled', false);
    $parent.prop('disabled', false);

    // Pré-remplir immédiatement les champs simples
    $id.val(c.id);
    $nom.val(c.nom || '');
    $description.val(c.description || '');
    $couleur.val(c.couleur || '#007bff');
    $icone.val(c.icone || 'fa-cube');
    $is_active.prop('checked', !!c.is_active);

    // Recharger la liste des parents en excluant la catégorie actuelle, puis sélectionner le parent
    loadParents(c.id).then(function(){
      var parentId = (c && c.parent != null) ? String(c.parent) : '';
      $parent.val(parentId);
    }).catch(function(err){
      console.warn('loadParents during edit failed', err);
      var parentId = (c && c.parent != null) ? String(c.parent) : '';
      $parent.val(parentId);
    });

    $btn.text('Enregistrer').removeClass('btn-outline-success').addClass('btn-outline-primary');
    $btn.find('i').attr('class', 'fas fa-save mr-1');
    $btnCancel.show();
    updatePreview();
  }

  function payloadFromForm() {
    dbg('payloadFromForm called');

    const { $nom, $description, $parent, $couleur, $icone, $is_active } = els();
    return {
      nom: ($nom.val() || '').trim(),
      description: ($description.val() || '').trim(),
      parent: $parent.val() || null,
      couleur: $couleur.val() || '#007bff',
      icone: $icone.val() || 'fa-cube',
      is_active: $is_active.is(':checked'),
    };
  }

  function validateForm(data) {
    dbg('validateForm called with', data);

    if (!data.nom) {
      alert('Le nom de la catégorie est obligatoire');
      return false;
    }
    return true;
  }

  function createCategory() {
    dbg('createCategory called');

    const data = payloadFromForm();
    if (!validateForm(data)) return;

    // Re-resolve elements in case of navigation
    const { $tableBody } = els();

    dbg('createCategory: payload =', data);
    $.ajax({
      url: API_REST,
      method: 'POST',
      contentType: 'application/json',
      data: JSON.stringify(data),
    })
      .done(function (resp) {
        dbg('createCategory: success response =', resp);
        resetForm();
        Promise.all([loadParents(), loadCategories()]);
        showToast('Catégorie ajoutée avec succès', 'success');
      })
      .fail(function (xhr) {
        dbg('createCategory: fail status =', xhr.status, ' response =', xhr.responseText || xhr.statusText, xhr.responseJSON);
        let msg = 'Erreur lors de la création de la catégorie';
        const j = xhr.responseJSON;
        if (j) {
          if (j.detail) msg = j.detail;
          else if (j.error) msg = j.error;
          else if (j.nom && Array.isArray(j.nom) && j.nom.length) msg = j.nom[0];
          else if (typeof j === 'string') msg = j;
        }
        alert(msg);
        // Tenter de recharger la liste au cas où
        Promise.all([loadParents(), loadCategories()]);
      });
  }

  function updateCategory(id) {
    dbg('updateCategory called with id=', id);

    const data = payloadFromForm();
    if (!validateForm(data)) return;

    // Re-resolve elements in case of navigation
    const { $tableBody } = els();

    dbg('updateCategory: id=', id, ' payload=', data);
    $.ajax({
      url: API_BASE + id + '/',
      method: 'PATCH',
      contentType: 'application/json',
      data: JSON.stringify(data),
    })
      .done(function (resp) {
        dbg('updateCategory: success response =', resp);
        resetForm();
        Promise.all([loadParents(), loadCategories()]);
        showToast('Catégorie mise à jour', 'success');
      })
      .fail(function (xhr) {
        dbg('updateCategory: fail status =', xhr.status, ' response =', xhr.responseText || xhr.statusText, xhr.responseJSON);
        const msg = (xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur lors de la mise à jour de la catégorie';
        alert(msg);
      });
  }

  function deleteCategory(id) {
    dbg('deleteCategory called with id=', id);

    if (!confirm('Supprimer cette catégorie ?')) return;
    // Re-resolve elements in case of navigation
    const { $tableBody } = els();

    dbg('deleteCategory: id=', id);
    $.ajax({
      url: API_BASE + id + '/',
      method: 'DELETE',
    })
      .done(function (resp) {
        dbg('deleteCategory: success response =', resp);
        Promise.all([loadParents(), loadCategories()]);
        showToast('Catégorie supprimée', 'success');
      })
      .fail(function (xhr) {
        dbg('deleteCategory: fail status =', xhr.status, ' response =', xhr.responseText || xhr.statusText, xhr.responseJSON);
        if (xhr && xhr.status === 409) {
          alert('Suppression impossible: la catégorie est utilisée par des produits. Vous pouvez l\'archiver en la mettant Inactive.');
        } else {
          const msg = (xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Impossible de supprimer cette catégorie';
          alert(msg);
        }
      });
  }

  function bindEvents() {
    dbg('bindEvents called');
    try { console.log('[Categorie] binding events - checking buttons', { hasBtn: !!document.getElementById('btn'), hasCancel: !!document.getElementById('btnCancel')}); } catch(e){}

    const { $couleur, $icone } = els();

    // Utiliser des sélecteurs plus spécifiques pour éviter les conflits avec d'autres pages
    // Au lieu d'écouter #btn globalement, écouter uniquement dans le contexte de categoriePage
    $(document).off('click', '#categoriePage #btn').on('click', '#categoriePage #btn', function () {
      const { $id } = els();
      const currentId = $id.val();
      if (currentId) updateCategory(currentId);
      else createCategory();
    });

    $(document).off('click', '#categoriePage #btnCancel').on('click', '#categoriePage #btnCancel', function () {
      resetForm();
    });

    $(document).off('click', '#categoriePage #table-content .btn-edit').on('click', '#categoriePage #table-content .btn-edit', function (e) {
      e.preventDefault();
      const id = String($(this).data('id'));
      const c = categoriesCache.get(id);
      if (c) startEdit(c);
    });

    $(document).off('click', '#categoriePage #table-content .btn-delete').on('click', '#categoriePage #table-content .btn-delete', function (e) {
      e.preventDefault();
      const id = $(this).data('id');
      deleteCategory(id);
    });

    $couleur.off('input change').on('input change', updatePreview);
    $icone.off('change').on('change', updatePreview);
  }

  function init() {
    dbg('init called');
    try { console.log('[Categorie] init - looking for categoriePage element'); } catch(e){}

    // Ne s'initialise que sur la page catégories
    const page = document.getElementById('categoriePage');
    if (!page) { dbg('init: categorie-page not found, skipping init'); return; }
    // Si DataTables a été initialisé automatiquement, le désactiver pour cette page
    if (window.$ && $.fn && $.fn.dataTable && $.fn.dataTable.isDataTable('#tcategorie')) {
      try { $('#tcategorie').DataTable().clear().destroy(); } catch (e) { /* no-op */ }
    }
    bindEvents();
    updatePreview();
    // Initial loads
    Promise.all([loadParents(), loadCategories()]);
  }

  // Init on first full page load
  $(document).ready(function(){ console.log('[Categorie] jQuery document.ready handler running'); try{ init(); }catch(e){ console.log('[Categorie] init error in ready:', e); } });
  // Re-init when fragments are loaded via dynamic loader
  document.addEventListener('fragment:loaded', function (e) {
    console.log('[Categorie] fragment:loaded event received', e && e.detail);

    if (e && e.detail && e.detail.name === 'categorie') {
      init();
    }
  });
})(jQuery);
