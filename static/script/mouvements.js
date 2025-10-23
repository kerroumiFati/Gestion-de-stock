let mvTable = null;
function loadProductsSelect(){
  $.getJSON('../API/produits/?format=json', function(data){
    const sel = $('#mv_prod').empty().append('<option value="">Tous</option>');
    data.forEach(p=> sel.append(`<option value="${p.id}">${p.reference} - ${p.designation}</option>`));
  });
}
function buildUrl(){
  const params = [];
  const p = $('#mv_prod').val(); if(p) params.push('produit='+p);
  const s = $('#mv_src').val(); if(s) params.push('source='+s);
  const a = $('#mv_after').val(); if(a) params.push('date_after='+encodeURIComponent(a));
  const b = $('#mv_before').val(); if(b) params.push('date_before='+encodeURIComponent(b));
  const qs = params.length? ('?'+params.join('&')) : '';
  return '../API/mouvements/'+qs;
}
$(document).ready(function(){
  loadProductsSelect();
  mvTable = $('#tmouv').DataTable({
    ajax: { url: buildUrl(), dataSrc: '' },
    columns: [
      { data: 'date' },
      { data: 'produit' },
      { data: 'delta' },
      { data: 'source' },
      { data: 'ref_id' },
      { data: 'note' }
    ]
  });
  $('#mv_filter').click(function(){
    mvTable.ajax.url(buildUrl()).load();
  });
});
