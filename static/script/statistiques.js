(function(){
  const DEBUG = true; function dbg(){ if(DEBUG) try{ console.log.apply(console, ['[Stats]'].concat([].slice.call(arguments))); }catch(e){} }
  const API_COUNTS = '/API/prod/count/';
  const API_CHARTS = '/API/statistics/charts/';

  let charts = {};

  function setText(id, value){ var el = document.getElementById(id); if(el) el.textContent = value; }
  function nowStr(){ var d = new Date(); return d.toLocaleString(); }

  function ensureChart(ctx, type, data, options){
    if(!window.Chart || !ctx) return null;
    if(charts[ctx.id]){ charts[ctx.id].destroy(); }
    charts[ctx.id] = new Chart(ctx, { type: type, data: data, options: options || {} });
    return charts[ctx.id];
  }

  function loadCounts(){
    return fetch(API_COUNTS, { credentials:'same-origin' })
      .then(function(res){ if(!res.ok) throw new Error('HTTP '+res.status); return res.json(); })
      .then(function(j){
        dbg('counts', j);
        setText('nbr-produits', j.produits_count ?? '-');
        setText('nbr-clients', j.clients_count ?? '-');
        setText('nbr-fournisseurs', j.fournisseurs_count ?? '-');
        setText('nbr-ventes', j.ventes_count ?? '-');
        setText('ca-total', (j.ca_total ?? 0).toLocaleString());
        setText('stock-alerte', (j.produits_stock_critique ?? 0) + (j.produits_rupture ?? 0));
      });
  }

  function color(idx){ const palette=['#2563eb','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#84cc16','#f43f5e']; return palette[idx % palette.length]; }

  function loadCharts(){
    return fetch(API_CHARTS, { credentials:'same-origin' })
      .then(function(res){ if(!res.ok) throw new Error('HTTP '+res.status); return res.json(); })
      .then(function(j){
        dbg('charts', j);
        // ventes par mois
        var labels = (j.ventes_par_mois||[]).map(x=>x.mois);
        var ventes = (j.ventes_par_mois||[]).map(x=>x.ventes);
        var ca = (j.ventes_par_mois||[]).map(x=>x.ca);
        ensureChart(document.getElementById('ventesChart'), 'line', {
          labels: labels,
          datasets: [
            { label: 'Ventes', data: ventes, borderColor: '#2563eb', backgroundColor:'rgba(37,99,235,.15)', fill:true, tension:.3 },
            { label: 'CA', data: ca, yAxisID:'y1', borderColor: '#10b981', backgroundColor:'rgba(16,185,129,.15)', fill:true, tension:.3 }
          ]
        }, { responsive:true, scales:{ y:{ beginAtZero:true }, y1:{ beginAtZero:true, position:'right' } } });

        // stock status
        var ss = j.stock_status || {}; var sLabels=['normal','alerte','critique','rupture'];
        ensureChart(document.getElementById('stockChart'), 'doughnut', {
          labels: sLabels,
          datasets:[{ data: sLabels.map(k=>ss[k]||0), backgroundColor:['#16a34a','#f59e0b','#ef4444','#6b7280'] }]
        }, { cutout:'60%' });

        // top produits
        var tp = j.top_produits||[];
        ensureChart(document.getElementById('topProduitsChart'), 'bar', {
          labels: tp.map(x=> (x.produit__designation || '—')),
          datasets:[{ label:'Quantité vendue', data: tp.map(x=>x.total_vendu||0), backgroundColor: tp.map((_,i)=>color(i)) }]
        }, { indexAxis:'y', plugins:{ legend:{ display:false } } });

        // ventes par catégorie
        var vc = j.ventes_par_categorie||[];
        ensureChart(document.getElementById('categoriesChart'), 'bar', {
          labels: vc.map(x=> x.produit__categorie__nom || '—'),
          datasets:[{ label:'Qté vendue', data: vc.map(x=>x.total_ventes||0), backgroundColor: vc.map((_,i)=>color(i)) }]
        }, { plugins:{ legend:{ display:false } } });

        // mouvements stock
        var ms = j.mouvements_stock||[];
        ensureChart(document.getElementById('mouvementsChart'), 'line', {
          labels: ms.map(x=>x.date),
          datasets:[
            { label:'Entrées', data: ms.map(x=>x.entrees||0), borderColor:'#10b981', backgroundColor:'rgba(16,185,129,.15)', fill:true, tension:.25 },
            { label:'Sorties', data: ms.map(x=>x.sorties||0), borderColor:'#ef4444', backgroundColor:'rgba(239,68,68,.15)', fill:true, tension:.25 }
          ]
        }, { responsive:true, scales:{ y:{ beginAtZero:true } } });

        // paiements
        var pay = j.ventes_paiement||[];
        ensureChart(document.getElementById('paiementsChart'), 'pie', {
          labels: pay.map(x=>x.type_paiement || x.type || '—'),
          datasets:[{ data: pay.map(x=>x.count||0), backgroundColor: pay.map((_,i)=>color(i)) }]
        });
      });
  }

  function refreshStatistics(){
    document.getElementById('last-update') && (document.getElementById('last-update').textContent = 'Chargement...');
    return Promise.all([ loadCounts(), loadCharts() ])
      .then(function(){ var el = document.getElementById('last-update'); if(el) el.textContent = 'Dernière mise à jour: ' + nowStr(); })
      .catch(function(err){ console.error('refreshStatistics failed', err); });
  }

  window.refreshStatistics = refreshStatistics;

  document.addEventListener('DOMContentLoaded', function(){
    // Auto-initialize only on stats page (detect a chart element)
    if(document.getElementById('ventesChart')){
      refreshStatistics();
    }
  });
})();