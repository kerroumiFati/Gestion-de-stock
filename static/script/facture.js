$(document).ready(function(){
  const table = $('#tfacture').DataTable({
    ajax: { url: '../API/factures/?format=json', dataSrc: '' },
    columns: [
      { data: 'id' },
      { data: 'numero' },
      { data: 'date_emission' },
      { data: 'client' },
      { data: 'statut' },
      { data: 'total_ttc' },
      { render: function(_,__,row){
          return `
            <button class="btn btn-sm btn-outline-primary action-issue">Émettre</button>
            <button class="btn btn-sm btn-outline-success action-pay">Payer</button>
            <button class="btn btn-sm btn-outline-secondary action-print">Export PDF</button>
          `;
        }
      }
    ]
  });

  // Populate clients
  $.getJSON('../API/clients/?format=json', function(data){
    const sel = $('#fact_client').empty().append(`<option value="">Choisir...</option>`);
    data.forEach(c => sel.append(`<option value="${c.id}">${c.nom} ${c.prenom}</option>`));
  });
  // Populate validated BLs
  $.getJSON('../API/bons/?format=json', function(data){
    const sel = $('#fact_bl').empty().append(`<option value="">Depuis BL validé...</option>`);
    data.filter(b=> b.statut==='validated').forEach(b => sel.append(`<option value="${b.id}">${b.numero}</option>`));
  });

  $('#btn_create_from_bl').click(function(){
    const bl = $('#fact_bl').val();
    const tva = parseFloat($('#fact_tva').val()||'20');
    const num = $('#fact_num').val();
    if(!bl){ alert('Sélectionnez un BL validé'); return; }
    $.ajax({
      url: '../API/factures/from_bl/',
      method: 'POST',
      contentType: 'application/json',
      data: JSON.stringify({bon_livraison: bl, tva_rate: tva, numero: num||undefined}),
      success: function(){ table.ajax.reload(); },
      error: function(xhr){ alert('Erreur création facture: '+xhr.responseText); }
    });
  });

  $('#fact_table').on('click','.action-issue',function(){
    const id = $(this).closest('tr').find('td').eq(0).text();
    $.post(`../API/factures/${id}/issue/`).done(()=>table.ajax.reload());
  });
  $('#fact_table').on('click','.action-pay',function(){
    const id = $(this).closest('tr').find('td').eq(0).text();
    $.post(`../API/factures/${id}/pay/`).done(()=>table.ajax.reload());
  });
  $('#fact_table').on('click','.action-print',function(){
    const id = $(this).closest('tr').find('td').eq(0).text();
    window.open(`../API/factures/${id}/printable/`, '_blank');
  });
});
