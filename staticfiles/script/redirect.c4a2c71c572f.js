// Dynamic content loader for master_page.html
(function(){
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
      case 'config_clients_chauffeurs': return '/admindash/config-clients-chauffeurs';
      case 'livreur_mobile': return '/livreur/app';
      default: return null;
    }
  }

  function nameFromPath(path){
    if(path.startsWith('/admindash/livreurs')) return 'livreurs';
    if(path.startsWith('/admindash/tournees')) return 'tournees';
    if(path.startsWith('/admindash/config-clients-chauffeurs')) return 'config_clients_chauffeurs';
    if(path.startsWith('/admindash/distribution')) return 'distribution_dashboard';
    if(path.startsWith('/livreur/app')) return 'livreur_mobile';
    const hash = (location.hash||'').replace('#','');
    return hash || null;
  }

  window.show = function(name, opts){
    console.log('[REDIRECT] Loading page:', name);
    setActive(name);
    const container = document.getElementById('main-content');
    if(!container){ return; }
    container.innerHTML = '<div class="text-center p-5 text-muted">Chargement...</div>';
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
    fetch(fetchUrl)
      .then(function(res){
        if(!res.ok) throw new Error('HTTP '+res.status);
        return res.text();
      })
      .then(function(html){
        container.innerHTML = html;

        // Execute script tags in the injected HTML
        (function executeScripts(root){
          var loadedSrc = window.__loadedDynamicScripts = window.__loadedDynamicScripts || new Set();
          var scripts = Array.from(root.querySelectorAll('script'));
          scripts.forEach(function(oldScript){
            var newScript = document.createElement('script');
            // Copy attributes
            Array.from(oldScript.attributes).forEach(function(attr){
              newScript.setAttribute(attr.name, attr.value);
            });
            if (oldScript.src) {
              if (!loadedSrc.has(oldScript.src)) {
                loadedSrc.add(oldScript.src);
                document.body.appendChild(newScript);
              }
            } else {
              newScript.text = oldScript.textContent;
              document.body.appendChild(newScript);
            }
          });
        })(container);

        // initialize datatables or plugins if present
        if(window.$ && $.fn && $.fn.DataTable){
          $('.table').each(function(){
            // Ne pas initialiser DataTable si l'attribut data-no-datatable est présent
            if($(this).attr('data-no-datatable') === 'true') return;
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
