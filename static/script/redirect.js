// Dynamic content loader for master_page.html
(function(){
  function setActive(name){
    document.querySelectorAll('#sidebar .sidebar-item').forEach(function(a){
      a.classList.remove('active');
    });
    // Try to set active by matching onclick arg
    const item = Array.from(document.querySelectorAll('#sidebar .sidebar-item'))
      .find(a => (a.getAttribute('onclick')||'').includes("show('"+name+"')"));
    if(item){ item.classList.add('active'); }
  }

  window.show = function(name){
    setActive(name);
    const container = document.getElementById('main-content');
    if(!container){ return; }
    container.innerHTML = '<div class="text-center p-5 text-muted">Chargement...</div>';
    fetch('/page/' + encodeURIComponent(name) + '/')
      .then(function(res){
        if(!res.ok) throw new Error('HTTP '+res.status);
        return res.text();
      })
      .then(function(html){
        container.innerHTML = html;
        window.history.replaceState(null, '', '#'+name);

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

  // Auto-load from hash or default dashboard section
  window.addEventListener('DOMContentLoaded', function(){
    var hash = (location.hash||'').replace('#','');
    if(hash){
      window.show(hash);
    } else {
      window.show('statistiques');
    }
  });
})();
