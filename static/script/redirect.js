function show(page) {
	if (page == 'produit') {
		$('a').removeClass('active');
		$('a:contains(Produit)').addClass('active');
		$("#main-content").load("produits");
	}
	if (page == 'client') {
		console.log('active')
		$('a').removeClass('active');
		$('a:contains(Clients)').addClass('active');
		$("#main-content").load("clients");
	}
	if (page == 'fournisseur') {
		$('a').removeClass('active');
		$('a:contains(Fournisseurs)').addClass('active');
		$("#main-content").load("fournisseurs");
	}
		if (page == 'achat') {
		$('a').removeClass('active');
		$('a:contains(Achats)').addClass('active');
		$("#main-content").load("achats");
	}
	if (page == 'vente') {
		$('a').removeClass('active');
		$('a:contains(Ventes)').addClass('active');
		$("#main-content").load("ventes");
	}
	if (page == 'facture') {
		$('a').removeClass('active');
		$('a:contains(Factures)').addClass('active');
		$("#main-content").load("factures");
	}
	if (page == "statistiques") {
		$('a').removeClass('active');
		$('a:contains(Statistiques)').addClass('active');
		$("#main-content").load("statistiques");
	}
	if (page == 'inventaire') {
		$('a').removeClass('active');
		$('a:contains(Inventaires)').addClass('active');
		$("#main-content").load("inventaires");
	}
	if (page == 'mouvements') {
		$('a').removeClass('active');
		$('a:contains(Mouvements)').addClass('active');
		$("#main-content").load("mouvements");
	}
}
$('a').removeClass('active');
$('a:contains(Statistiques)').addClass('active');
$("#main-content").load("statistiques");
