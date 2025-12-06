// Basic sidebar toggle and UX helpers
(function(){
  document.addEventListener('DOMContentLoaded', function(){
    var showBtn = document.getElementById('show-sidebar');
    var closeBtn = document.getElementById('close-sidebar');
    var wrapper = document.querySelector('.page-wrapper');
    function toggle(){ if(wrapper){ wrapper.classList.toggle('toggled'); } }
    if(showBtn){ showBtn.addEventListener('click', function(e){ e.preventDefault(); toggle(); }); }
    if(closeBtn){ closeBtn.addEventListener('click', function(e){ e.preventDefault(); toggle(); }); }
  });
})();
