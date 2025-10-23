let INV_SESSION_ID = null;
function loadProductsForSelect(){
  $.getJSON('../API/produits/?format=json', function(data){
    const sel = $('#inv_add_product').empty().append('<option value="">Choisir...</option>');
    data.forEach(p=> sel.append(`<option value="${p.id}">${p.reference} - ${p.designation}</option>`));
  });
}
function addLineRow(prodId, theoretical){
  const tr = $(`<tr data-pid="${prodId}">
    <td>${prodId}</td>
    <td class="theoretical">${theoretical}</td>
    <td><input type="number" class="form-control counted" value="${theoretical}"></td>
    <td class="delta">0</td>
    <td><button class="btn btn-sm btn-outline-danger remove">X</button></td>
  </tr>`);
  $('#inv_table').append(tr);
  tr.find('.counted').on('input', function(){
    const counted = parseInt($(this).val()||'0');
    const theo = parseInt(tr.find('.theoretical').text()||'0');
    tr.find('.delta').text(counted - theo);
  });
  tr.find('.remove').click(()=> tr.remove());
}
$(document).ready(function(){
  loadProductsForSelect();
  $('#btn_add_line').click(function(){
    const pid = $('#inv_add_product').val();
    if(!pid){ alert('Choisir un produit'); return; }
    // fetch theoretical from product stock endpoint
    $.getJSON(`../API/produits/${pid}/stock/`, function(data){
      const theoretical = data.book_quantity; // could combine with moves_sum
      addLineRow(pid, theoretical);
    });
  });
  $('#btn_create_session').click(function(){
    const payload = {
      numero: $('#inv_num').val() || undefined,
      date: $('#inv_date').val() || undefined,
      note: $('#inv_note').val() || '' ,
      lignes: []
    };
    // build lines from table
    $('#inv_table tr').each(function(){
      const pid = parseInt($(this).attr('data-pid'));
      const theo = parseInt($(this).find('.theoretical').text()||'0');
      const counted = parseInt($(this).find('.counted').val()||'0');
      payload.lignes.push({produit: pid, counted_qty: counted, snapshot_qty: theo});
    });
    $.ajax({
      url: '../API/inventaires/',
      method: 'POST', contentType: 'application/json',
      data: JSON.stringify(payload),
      success: function(resp){ INV_SESSION_ID = resp.id; $('#btn_validate_session').prop('disabled', false); alert('Session créée'); },
      error: function(xhr){ alert('Erreur création session: '+xhr.responseText); }
    });
  });
  $('#btn_validate_session').click(function(){
    if(!INV_SESSION_ID){ alert('Aucune session'); return; }
    $.post(`../API/inventaires/${INV_SESSION_ID}/validate/`).done(function(){
      alert('Inventaire validé');
      $('#btn_validate_session').prop('disabled', true);
    });
  });
});
