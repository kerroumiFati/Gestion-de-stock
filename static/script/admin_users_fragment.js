// Administration des Utilisateurs, Rôles et Permissions - Version fragment
(function($){
  const API_BASE = '/API';
  const DEBUG = true;
  function dbg(...args){ if(DEBUG) console.log('[AdminUsers]', ...args); }

  // Cache des données
  let USERS = [];
  let ROLES = [];
  let PERMISSIONS = [];
  let AUDIT_LOGS = [];

  // Helpers
  function getCSRFToken(){
    const cookieValue = document.cookie
      .split('; ')
      .find(row => row.startsWith('csrftoken='));
    return cookieValue ? cookieValue.split('=')[1] : '';
  }

  function asList(data){
    if(Array.isArray(data)) return data;
    if(data && Array.isArray(data.results)) return data.results;
    return [];
  }

  function showNotification(message, type = 'success'){
    const alertClass = type === 'success' ? 'alert-success' : type === 'warning' ? 'alert-warning' : 'alert-danger';
    const icon = type === 'success' ? 'check-circle' : type === 'warning' ? 'exclamation-triangle' : 'times-circle';

    const alert = $('<div>')
      .addClass('alert ' + alertClass + ' alert-dismissible fade show')
      .attr('role', 'alert')
      .html('<i class="fa fa-' + icon + '"></i> ' + message +
            '<button type="button" class="close" data-dismiss="alert"><span>&times;</span></button>');

    $('.page-container').prepend(alert);
    setTimeout(() => alert.fadeOut(() => alert.remove()), 5000);
  }

  /****************************
   * STATISTIQUES
   ****************************/
  function updateStats(){
    $('#stat_users_count').text(USERS.length);
    $('#stat_roles_count').text(ROLES.length);
    $('#stat_permissions_count').text(PERMISSIONS.length);

    const activeUsers = USERS.filter(u => u.is_active).length;
    $('#stat_active_count').text(activeUsers);
  }

  /****************************
   * GESTION DES UTILISATEURS
   ****************************/
  function loadUsers(){
    $.ajax({ url: API_BASE + '/users/', method: 'GET', dataType: 'json' })
      .done(function(data){
        USERS = asList(data);
        dbg('Utilisateurs chargés:', USERS.length);
        renderUsers(USERS);
        updateStats();
        fillAuditUserFilter(USERS);
      })
      .fail(function(xhr){
        dbg('Erreur chargement utilisateurs:', xhr);
        showNotification('Erreur de chargement des utilisateurs', 'danger');
      });
  }

  function renderUsers(users){
    const $tbody = $('#users_table_body');
    $tbody.empty();

    if(!users || users.length === 0){
      $tbody.append('<tr><td colspan="6" class="text-center text-muted">Aucun utilisateur</td></tr>');
      return;
    }

    users.forEach(function(user){
      const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ') || '-';
      const rolesHtml = (user.group_names || []).map(g =>
        '<span class="modern-badge modern-badge-info mr-1">' + g + '</span>'
      ).join('') || '-';

      const statusBadge = user.is_active ?
        '<span class="modern-badge modern-badge-success">Actif</span>' :
        '<span class="modern-badge modern-badge-default">Inactif</span>';

      const staffBadge = user.is_staff ?
        '<span class="modern-badge modern-badge-warning ml-1"><i class="fa fa-crown"></i> Admin</span>' : '';

      const tr = $('<tr>');
      tr.append('<td><strong>' + user.username + '</strong></td>');
      tr.append('<td>' + fullName + '</td>');
      tr.append('<td>' + (user.email || '-') + '</td>');
      tr.append('<td>' + rolesHtml + '</td>');
      tr.append('<td>' + statusBadge + staffBadge + '</td>');

      const actions = '<button type="button" class="action-btn action-btn-edit" data-action="edit" data-id="' + user.id + '">'+
                     '<i class="fa fa-edit"></i> Modifier</button> ' +
                     '<button type="button" class="action-btn action-btn-delete ml-1" data-action="delete" data-id="' + user.id + '">'+
                     '<i class="fa fa-trash"></i> Supprimer</button>';
      tr.append('<td>' + actions + '</td>');

      $tbody.append(tr);
    });
  }

  function openUserModal(userId = null){
    if(userId){
      // Mode édition
      const user = USERS.find(u => u.id === userId);
      if(!user) return;

      $('#user_modal_title').text('Modifier l\'utilisateur');
      $('#user_id').val(user.id);
      $('#user_username').val(user.username).prop('disabled', true);
      $('#user_email').val(user.email || '');
      $('#user_firstname').val(user.first_name || '');
      $('#user_lastname').val(user.last_name || '');
      $('#user_password').val('');
      $('#user_is_active').prop('checked', user.is_active);
      $('#user_is_staff').prop('checked', user.is_staff);

      // Sélectionner les groupes
      $('#user_groups').val(user.groups || []);
    } else {
      // Mode création
      $('#user_form')[0].reset();
      $('#user_id').val('');
      $('#user_username').prop('disabled', false);
      $('#user_is_active').prop('checked', true);
      $('#user_modal_title').text('Nouvel Utilisateur');
    }

    $('#userModal').modal('show');
  }

  function saveUser(){
    const userId = $('#user_id').val();
    const data = {
      username: $('#user_username').val(),
      email: $('#user_email').val() || '',
      first_name: $('#user_firstname').val() || '',
      last_name: $('#user_lastname').val() || '',
      is_active: $('#user_is_active').is(':checked'),
      is_staff: $('#user_is_staff').is(':checked'),
      groups: $('#user_groups').val() || []
    };

    const password = $('#user_password').val();
    if(password) data.password = password;

    if(!data.username){ alert('Username requis'); return; }

    const method = userId ? 'PUT' : 'POST';
    const url = userId ? API_BASE + '/users/' + userId + '/' : API_BASE + '/users/';

    $.ajax({
      url: url,
      method: method,
      contentType: 'application/json',
      headers: { 'X-CSRFToken': getCSRFToken() },
      data: JSON.stringify(data)
    })
    .done(function(){
      $('#userModal').modal('hide');
      loadUsers();
      showNotification(userId ? 'Utilisateur modifié' : 'Utilisateur créé', 'success');
    })
    .fail(function(xhr){
      const msg = (xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur';
      showNotification(msg, 'danger');
    });
  }

  function deleteUser(userId){
    if(!confirm('Supprimer cet utilisateur ?')) return;

    $.ajax({
      url: API_BASE + '/users/' + userId + '/',
      method: 'DELETE',
      headers: { 'X-CSRFToken': getCSRFToken() }
    })
    .done(function(){
      loadUsers();
      showNotification('Utilisateur supprimé', 'success');
    })
    .fail(function(xhr){
      const msg = (xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur suppression';
      showNotification(msg, 'danger');
    });
  }

  /****************************
   * GESTION DES RÔLES
   ****************************/
  function loadRoles(){
    $.ajax({ url: API_BASE + '/roles/', method: 'GET', dataType: 'json' })
      .done(function(data){
        ROLES = asList(data);
        dbg('Rôles chargés:', ROLES.length);
        renderRoles(ROLES);
        fillRoleSelects(ROLES);
        updateStats();
      })
      .fail(function(xhr){
        dbg('Erreur chargement rôles:', xhr);
      });
  }

  function renderRoles(roles){
    const $tbody = $('#roles_table_body');
    $tbody.empty();

    if(!roles || roles.length === 0){
      $tbody.append('<tr><td colspan="4" class="text-center text-muted">Aucun rôle</td></tr>');
      return;
    }

    roles.forEach(function(role){
      const permCount = role.permissions ? role.permissions.length : 0;
      const userCount = USERS.filter(u => (u.groups || []).includes(role.id)).length;

      const tr = $('<tr>');
      tr.append('<td><strong>' + role.name + '</strong></td>');
      tr.append('<td><span class="modern-badge modern-badge-info">' + permCount + '</span></td>');
      tr.append('<td><span class="modern-badge modern-badge-default">' + userCount + '</span></td>');

      const actions = '<button type="button" class="action-btn action-btn-edit" data-action="manage-perm" data-id="' + role.id + '">'+
                     '<i class="fa fa-key"></i> Permissions</button> ' +
                     '<button type="button" class="action-btn action-btn-delete ml-1" data-action="delete-role" data-id="' + role.id + '">'+
                     '<i class="fa fa-trash"></i> Supprimer</button>';
      tr.append('<td>' + actions + '</td>');

      $tbody.append(tr);
    });
  }

  function fillRoleSelects(roles){
    // Remplir le select dans la modal utilisateur
    const $userGroups = $('#user_groups');
    $userGroups.empty();
    roles.forEach(function(role){
      $('<option>').val(role.id).text(role.name).appendTo($userGroups);
    });

    // Remplir le select dans les permissions
    const $permRoleSelect = $('#perm_role_select');
    const first = $permRoleSelect.find('option').first();
    $permRoleSelect.empty().append(first);
    roles.forEach(function(role){
      $('<option>').val(role.id).text(role.name).appendTo($permRoleSelect);
    });
  }

  function addRole(){
    const name = $('#role_name').val().trim();
    if(!name){ alert('Nom du rôle requis'); return; }

    $.ajax({
      url: API_BASE + '/roles/',
      method: 'POST',
      contentType: 'application/json',
      headers: { 'X-CSRFToken': getCSRFToken() },
      data: JSON.stringify({ name: name })
    })
    .done(function(){
      $('#role_name').val('');
      loadRoles();
      showNotification('Rôle créé avec succès', 'success');
    })
    .fail(function(xhr){
      const msg = (xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur création rôle';
      showNotification(msg, 'danger');
    });
  }

  function deleteRole(roleId){
    if(!confirm('Supprimer ce rôle ?')) return;

    $.ajax({
      url: API_BASE + '/roles/' + roleId + '/',
      method: 'DELETE',
      headers: { 'X-CSRFToken': getCSRFToken() }
    })
    .done(function(){
      loadRoles();
      loadUsers();
      showNotification('Rôle supprimé', 'success');
    })
    .fail(function(xhr){
      const msg = (xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur suppression';
      showNotification(msg, 'danger');
    });
  }

  /****************************
   * GESTION DES PERMISSIONS
   ****************************/
  function loadPermissions(){
    $.ajax({ url: API_BASE + '/permissions/', method: 'GET', dataType: 'json' })
      .done(function(data){
        PERMISSIONS = asList(data);
        dbg('Permissions chargées:', PERMISSIONS.length);
        updateStats();
      })
      .fail(function(xhr){
        dbg('Erreur chargement permissions:', xhr);
      });
  }

  function showPermissionsForRole(roleId){
    const role = ROLES.find(r => r.id == roleId);
    if(!role) return;

    const rolePermissions = role.permissions || [];

    // Afficher le container
    $('#permissions_container').fadeIn();

    // Grouper les permissions par modèle
    const grouped = {};
    PERMISSIONS.forEach(function(perm){
      const parts = perm.codename.split('_');
      const action = parts[0];
      const model = parts.slice(1).join('_');

      if(!grouped[model]) grouped[model] = [];
      grouped[model].push(perm);
    });

    // Rendre les permissions en deux colonnes
    const models = Object.keys(grouped).sort();
    const half = Math.ceil(models.length / 2);

    $('#permissions_col_1').empty();
    $('#permissions_col_2').empty();

    models.forEach(function(model, idx){
      const col = idx < half ? '#permissions_col_1' : '#permissions_col_2';

      let html = '<div class="mb-4">';
      html += '<h6 class="text-uppercase text-muted mb-2"><i class="fa fa-cube"></i> ' + model + '</h6>';

      grouped[model].forEach(function(perm){
        const isChecked = rolePermissions.includes(perm.id);
        html += '<div class="permission-checkbox">';
        html += '<input type="checkbox" id="perm_' + perm.id + '" value="' + perm.id + '" data-role="' + roleId + '"' + (isChecked ? ' checked' : '') + '>';
        html += '<label for="perm_' + perm.id + '">' + perm.name + '</label>';
        html += '</div>';
      });

      html += '</div>';
      $(col).append(html);
    });
  }

  function savePermissions(){
    const roleId = $('#perm_role_select').val();
    if(!roleId){ alert('Veuillez sélectionner un rôle'); return; }

    // Récupérer toutes les permissions cochées
    const selectedPermissions = [];
    $('#permissions_container input[type="checkbox"]:checked').each(function(){
      selectedPermissions.push(parseInt($(this).val()));
    });

    $.ajax({
      url: API_BASE + '/roles/' + roleId + '/',
      method: 'PATCH',
      contentType: 'application/json',
      headers: { 'X-CSRFToken': getCSRFToken() },
      data: JSON.stringify({ permissions: selectedPermissions })
    })
    .done(function(){
      loadRoles();
      showNotification('Permissions mises à jour', 'success');
    })
    .fail(function(xhr){
      const msg = (xhr.responseJSON && (xhr.responseJSON.detail || xhr.responseJSON.error)) || 'Erreur sauvegarde';
      showNotification(msg, 'danger');
    });
  }

  /****************************
   * JOURNAL D'AUDIT
   ****************************/
  function loadAuditLogs(filters = {}){
    $.ajax({ url: API_BASE + '/audit-logs/?page_size=100', method: 'GET', dataType: 'json', data: filters })
      .done(function(data){
        AUDIT_LOGS = asList(data);
        dbg('Logs d\'audit chargés:', AUDIT_LOGS.length);
        renderAuditLogs(AUDIT_LOGS);
      })
      .fail(function(xhr){
        dbg('Erreur chargement audit:', xhr);
      });
  }

  function renderAuditLogs(logs){
    const $tbody = $('#audit_table_body');
    $tbody.empty();

    if(!logs || logs.length === 0){
      $tbody.append('<tr><td colspan="5" class="text-center text-muted">Aucune entrée</td></tr>');
      return;
    }

    logs.slice(0, 100).forEach(function(log){
      const date = new Date(log.created_at);
      const dateStr = date.toLocaleString('fr-FR');

      const tr = $('<tr>');
      tr.append('<td>' + dateStr + '</td>');
      tr.append('<td>' + (log.actor_username || '-') + '</td>');
      tr.append('<td><code>' + log.action + '</code></td>');
      tr.append('<td>' + (log.target_model || '-') + ' #' + (log.target_id || '-') + '</td>');
      tr.append('<td><small class="text-muted">' + (log.target_repr || '-') + '</small></td>');

      $tbody.append(tr);
    });
  }

  function fillAuditUserFilter(users){
    const $sel = $('#audit_filter_user');
    const first = $sel.find('option').first();
    $sel.empty().append(first);

    users.forEach(function(u){
      $('<option>').val(u.id).text(u.username).appendTo($sel);
    });
  }

  /****************************
   * RECHERCHE UTILISATEURS
   ****************************/
  function searchUsers(){
    const query = $('#search_users').val().toLowerCase();
    if(!query){
      renderUsers(USERS);
      return;
    }

    const filtered = USERS.filter(function(user){
      return (user.username || '').toLowerCase().includes(query) ||
             (user.email || '').toLowerCase().includes(query) ||
             (user.first_name || '').toLowerCase().includes(query) ||
             (user.last_name || '').toLowerCase().includes(query);
    });

    renderUsers(filtered);
  }

  /****************************
   * EVENT HANDLERS
   ****************************/
  function initEventHandlers(){
    // Bouton nouvel utilisateur
    $(document).off('click', '#btn_new_user').on('click', '#btn_new_user', function(){ openUserModal(); });

    // Sauvegarde utilisateur
    $(document).off('click', '#btn_save_user').on('click', '#btn_save_user', saveUser);

    // Actions table utilisateurs
    $(document).off('click', '#users_table_body [data-action]').on('click', '#users_table_body [data-action]', function(e){
      e.preventDefault();
      const action = $(this).data('action');
      const userId = parseInt($(this).data('id'));

      if(action === 'edit'){
        openUserModal(userId);
      } else if(action === 'delete'){
        deleteUser(userId);
      }
    });

    // Recherche utilisateurs
    let searchTimeout;
    $(document).off('input', '#search_users').on('input', '#search_users', function(){
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(searchUsers, 300);
    });

    // Bouton créer rôle
    $(document).off('click', '#btn_add_role').on('click', '#btn_add_role', addRole);

    // Actions table rôles
    $(document).off('click', '#roles_table_body [data-action]').on('click', '#roles_table_body [data-action]', function(e){
      e.preventDefault();
      const action = $(this).data('action');
      const roleId = parseInt($(this).data('id'));

      if(action === 'manage-perm'){
        // Naviguer vers l'onglet permissions et sélectionner le rôle
        $('.modern-tab[data-target="permissions"]').click();
        setTimeout(() => {
          $('#perm_role_select').val(roleId).trigger('change');
        }, 100);
      } else if(action === 'delete-role'){
        deleteRole(roleId);
      }
    });

    // Changement de rôle dans permissions
    $(document).off('change', '#perm_role_select').on('change', '#perm_role_select', function(){
      const roleId = $(this).val();
      if(roleId){
        showPermissionsForRole(parseInt(roleId));
      } else {
        $('#permissions_container').hide();
      }
    });

    // Sauvegarde permissions
    $(document).off('click', '#btn_save_permissions').on('click', '#btn_save_permissions', savePermissions);

    // Filtrage audit
    $(document).off('click', '#btn_filter_audit').on('click', '#btn_filter_audit', function(){
      const filters = {};
      const action = $('#audit_filter_action').val();
      const user = $('#audit_filter_user').val();
      const date = $('#audit_filter_date').val();

      if(action) filters.action = action;
      if(user) filters.actor = user;
      if(date) filters.date = date;

      loadAuditLogs(filters);
    });
  }

  /****************************
   * INITIALISATION
   ****************************/
  function init(){
    dbg('Initialisation...');

    // Charger toutes les données
    Promise.all([
      loadUsers(),
      loadRoles(),
      loadPermissions(),
      loadAuditLogs()
    ]).then(function(){
      dbg('Toutes les données chargées');
    });

    initEventHandlers();
  }

  $(document).ready(init);

  // Support pour le système de chargement de fragments
  document.addEventListener('fragment:loaded', function(e){
    if(e && e.detail && e.detail.name === 'users'){
      init();
    }
  });

})(jQuery);
