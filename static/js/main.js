// Global initializations
(function(){
  document.addEventListener('DOMContentLoaded', function(){
    // Activate tooltips if Bootstrap is available
    if (window.bootstrap) {
      document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function(el){
        new bootstrap.Tooltip(el);
      });
    }
  });
})();
