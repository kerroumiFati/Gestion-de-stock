// Dynamic content loader for master_page.html
(function(){
  // Barre de progression fine en haut de page
  function progressStart() {
    const bar = document.getElementById('page-progress-bar');
    if (!bar) return;
    bar.classList.remove('done');
    bar.classList.add('running');
  }
  function progressDone() {
    const bar = document.getElementById('page-progress-bar');
    if (!bar) return;
    bar.classList.remove('running');
    bar.classList.add('done');
    setTimeout(function() { bar.classList.remove('done'); }, 600);
  }
  function setActive(name){
    // remove active from all submenu links
    document.querySelectorAll('#sidebar .sidebar-submenu a').forEach(function(a){
      a.classList.remove('active');
    });
    // set active by matching onclick arg OR href mapping
    const candidates = Array.from(document.querySelectorAll('#sidebar .sidebar-submenu a'));
    const el = candidates.find(a => (a.getAttribute('onclick')||'').includes("show('"+name+"')"));
    if(el){ el.classList.add('active'); }
  }

  function prettyPathFor(name){
    switch(name){
      case 'livreurs': return '/admindash/livreurs';
      case 'tournees': return '/admindash/tournees';
      case 'distribution_dashboard': return '/admindash/distribution';
      case 'clients_solde_dashboard': return '/admindash/clients-solde-dashboard';
      case 'config_clients_chauffeurs': return '/admindash/config-clients-chauffeurs';
      case 'livreur_mobile': return '/livreur/app';
      case 'promotions': return '/admindash/promotions';
      default: return null;
    }
  }

  function nameFromPath(path){
    if(path.startsWith('/admindash/livreurs')) return 'livreurs';
    if(path.startsWith('/admindash/tournees')) return 'tournees';
    if(path.startsWith('/admindash/clients-solde-dashboard')) return 'clients_solde_dashboard';
    if(path.startsWith('/admindash/config-clients-chauffeurs')) return 'config_clients_chauffeurs';
    if(path.startsWith('/admindash/distribution')) return 'distribution_dashboard';
    if(path.startsWith('/admindash/promotions')) return 'promotions';
    if(path.startsWith('/livreur/app')) return 'livreur_mobile';
    const hash = (location.hash||'').replace('#','');
    return hash || null;
  }

  window.show = function(name, opts){
    console.log('[REDIRECT] Loading page:', name);
    setActive(name);
    const container = document.getElementById('main-content');
    if(!container){ return; }
    // Vider le contenu précédent et démarrer la barre de progression
    container.innerHTML = '';
    progressStart();
    const targetPath = prettyPathFor(name);
    if(!opts || opts.push !== false){
      if(targetPath){ history.pushState({page:name}, '', targetPath); }
      else { history.pushState({page:name}, '', '#'+name); }
    }
    // Support for query parameters via opts.params
    let fetchUrl = '/page/' + encodeURIComponent(name) + '/';
    if(opts && opts.params){
      const queryString = new URLSearchParams(opts.params).toString();
      if(queryString) fetchUrl += '?' + queryString;
    }
    console.log('[REDIRECT] Fetching URL:', fetchUrl);
    // _silent=true : la barre de progression est gérée ici, pas l'overlay global
    fetch(fetchUrl, { _silent: true })
      .then(function(res){
        if(!res.ok) throw new Error('HTTP '+res.status);
        return res.text();
      })
      .then(function(html){
        progressDone();
        container.innerHTML = html;

        // Execute script tags in the injected HTML
        (function executeScripts(root){
          var loadedSrc = window.__loadedDynamicScripts = window.__loadedDynamicScripts || new Set();
          var scripts = Array.from(root.querySelectorAll('script'));
          scripts.forEach(function(oldScript){
            if (oldScript.src) {
              // External script - only load once
              if (!loadedSrc.has(oldScript.src)) {
                loadedSrc.add(oldScript.src);
                var newScript = document.createElement('script');
                Array.from(oldScript.attributes).forEach(function(attr){
                  newScript.setAttribute(attr.name, attr.value);
                });
                document.body.appendChild(newScript);
              }
            } else {
              // Inline script - execute via indirect eval to preserve global scope
              try {
                var scriptContent = oldScript.textContent;
                // Use indirect eval (0, eval) to execute in global scope
                (0, eval)(scriptContent);
              } catch(e) {
                console.warn('Inline script execution error:', e.message);
              }
            }
          });
        })(container);

        // initialize datatables or plugins if present
        if(window.$ && $.fn && $.fn.DataTable){
          $('.table').each(function(){
            // Ne pas initialiser DataTable si l'attribut data-no-datatable est présent
            if($(this).attr('data-no-datatable') === 'true') return;
            // Ne pas initialiser les tables de vente (panier dynamique)
            if($(this).attr('id') === 'tbl_vente') return;
            // Vérifier que la table a des colonnes définies dans thead
            var headerCols = $(this).find('thead th').length;
            if(headerCols === 0) return;
            if(!$.fn.dataTable.isDataTable(this)){
              try {
                $(this).DataTable();
              } catch(e) {
                console.warn('DataTable init failed for table:', this.id, e);
              }
            }
          });
        }

        // Notify listeners that a fragment has been loaded
        try {
          document.dispatchEvent(new CustomEvent('fragment:loaded', { detail: { name: name, container: container } }));
        } catch (e) { /* no-op */ }
      })
      .catch(function(err){
        progressDone();
        container.innerHTML = '<div class="alert alert-danger m-3">Erreur de chargement: '+ err.message +'</div>';
      });
  };

  // Handle browser navigation
  window.addEventListener('popstate', function(e){
    console.log('[REDIRECT] popstate event triggered', e.state, 'pathname:', location.pathname);
    const name = (e.state && e.state.page) || nameFromPath(location.pathname) || 'statistiques';
    console.log('[REDIRECT] popstate resolved to page:', name);
    window.show(name, {push:false});
  });

  // Auto-load based on current pathname or hash
  window.addEventListener('DOMContentLoaded', function(){
    const initial = nameFromPath(location.pathname);
    if(initial){
      window.show(initial, {push:false});
    } else {
      const hash = (location.hash||'').replace('#','');
      if(hash){
        window.show(hash, {push:false});
      } else {
        window.show('statistiques', {push:false});
      }
    }
  });
})();
