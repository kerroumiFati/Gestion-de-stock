/**
 * Planning de la semaine des prévendeurs (sans dates), présenté comme un calendrier :
 * 7 colonnes (Lundi → Dimanche). On glisse un client ou un secteur de la liste vers un jour,
 * ou on clique sur « + Ajouter » (fenêtre : un client / tout un secteur).
 * Les clients d'un jour = clients des secteurs du jour + clients ajoutés un par un.
 * Le téléphone et la tournée utilisent exactement la même liste (même calcul côté serveur).
 */
(function () {
  const API = '/API/distribution/livreurs/';
  const LETTRES = ['L', 'M', 'M', 'J', 'V', 'S', 'D'];
  const COULEURS = ['#2563eb', '#7c3aed', '#0891b2', '#059669', '#d97706', '#dc2626', '#4b5563'];
  const ps = { livreurs: [], clients: [], livreurId: null, planning: null, jour: 1, onglet: 'clients', liste: 'clients', glisse: null,
               global: { clients: {}, secteurs: {} } };   // jours pris par TOUS les prévendeurs

  // ---------------------------------------------------------------- outils
  function csrf() {
    const m = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }
  function esc(t) {
    return String(t == null ? '' : t).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  const $id = id => document.getElementById(id);
  const liste = d => (Array.isArray(d) ? d : (d && d.results) || []);
  const pluriel = (n, mot) => `${n} ${mot}${n > 1 ? 's' : ''}`;
  const nomClient = c => `${c.nom || ''} ${c.prenom || ''}`.trim();
  const sansAccent = t => String(t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const jourInfo = j => ps.planning.jours[j - 1];
  const nomJour = j => jourInfo(j).nom.toLowerCase();

  async function getJSON(url) {
    const r = await fetch(url, { credentials: 'same-origin' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }
  async function postJSON(url, data) {
    const r = await fetch(url, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
      body: JSON.stringify(data)
    });
    let corps = {};
    try { corps = await r.json(); } catch (_) { /* vide */ }
    return { ok: r.ok, status: r.status, data: corps };
  }

  function message(texte, type) {
    const zone = $id('ps-toast');
    if (!zone) return;
    const icone = { success: 'check-circle', warning: 'info-circle', danger: 'exclamation-circle' }[type || 'success'];
    zone.innerHTML = `<div class="ps-toast ps-toast-${type || 'success'}"><i class="fas fa-${icone}" style="margin-top:3px"></i><span>${esc(texte)}</span></div>`;
    clearTimeout(message._t);
    message._t = setTimeout(() => { zone.innerHTML = ''; }, type === 'warning' ? 7000 : 4000);
  }

  function confirmer({ titre, texte, bouton, couleur, siOui }) {
    $id('ps-confirm-titre').textContent = titre;
    $id('ps-confirm-texte').innerHTML = texte;
    const oui = $id('ps-confirm-oui');
    oui.textContent = bouton;
    oui.style.cssText = `background:${couleur || '#1d4ed8'};color:#fff`;
    oui.onclick = () => { $id('ps-fenetre-confirm').style.display = 'none'; siOui(); };
    $id('ps-fenetre-confirm').style.display = 'flex';
  }

  // ---------------------------------------------------------------- chargement
  async function init() {
    if (!$id('planning-semaine-section')) return;
    try {
      const [livreurs, clients] = await Promise.all([getJSON(API), getJSON('/API/clients/?page_size=1000')]);
      ps.livreurs = liste(livreurs);
      ps.clients = liste(clients).sort((a, b) => nomClient(a).localeCompare(nomClient(b)));
    } catch (e) {
      message('Impossible de charger les prévendeurs ou les clients. Actualisez la page.', 'danger');
      return;
    }
    const sel = $id('ps-livreur');
    sel.innerHTML = '<option value="">— Cliquez ici pour choisir —</option>' +
      ps.livreurs.map(l => `<option value="${l.id}">${esc(l.nom || l.username)}${l.matricule ? ' (' + esc(l.matricule) + ')' : ''}</option>`).join('');
    if (ps.livreurId) { sel.value = ps.livreurId; chargerPlanning(); } else afficher();
  }

  async function chargerPlanning() {
    if (!ps.livreurId) return;
    const sect = $id('planning-semaine-section');
    sect.classList.add('ps-chargement');
    try {
      // Planning du prévendeur choisi + vue d'ensemble de tous les prévendeurs (cases L M M J V S D)
      const [planning, global] = await Promise.all([
        getJSON(`${API}${ps.livreurId}/planning/`),
        getJSON(`${API}planning-clients/`).catch(() => null)
      ]);
      ps.planning = planning;
      if (global) ps.global = global;
    } catch (e) {
      message('Impossible de charger le planning. Réessayez.', 'danger');
      return;
    } finally {
      sect.classList.remove('ps-chargement');
    }
    afficher();
    if ($id('ps-fenetre-ajout').style.display === 'flex') afficherChoix();
  }

  // ---------------------------------------------------------------- affichage

  function afficher() {
    const p = ps.planning;
    $id('ps-etape-semaine').classList.toggle('ps-inactive', !p);
    if (!p) {
      $id('ps-semaine').innerHTML = ''; $id('ps-panneau-liste').innerHTML = '';
      $id('ps-semaine-total').innerHTML = ''; $id('ps-avert-sans-jour').style.display = 'none';
      return;
    }
    $id('ps-semaine-total').innerHTML = `<b>${p.total_clients}</b> client${p.total_clients > 1 ? 's' : ''} visité${p.total_clients > 1 ? 's' : ''} dans la semaine`;
    const avert = $id('ps-avert-sans-jour');
    const n = p.clients_sans_jour.length;
    if (n) {
      avert.style.display = 'block';
      avert.innerHTML = `<i class="fas fa-exclamation-triangle"></i> <strong>${pluriel(n, 'client')} de ${esc(p.livreur_nom)}
        ${n > 1 ? 'n\'ont' : 'n\'a'} aucun jour de visite</strong> : ${n > 1 ? 'ils ne sont' : 'il n\'est'} ni sur le téléphone ni dans les tournées.
        ${n > 1 ? 'Ils sont' : 'Il est'} en haut de la liste avec l'étiquette <span class="ps-badge-orange">Aucun jour</span> : glissez-${n > 1 ? 'les' : 'le'} vers un jour.`;
    } else {
      avert.style.display = 'none';
    }
    afficherSemaine();
    afficherPanneau();
  }

  function afficherSemaine() {
    $id('ps-semaine').innerHTML = ps.planning.jours.map(j => {
      const blocsSecteurs = j.secteurs.map(s => {
        const membres = j.liste.filter(c => c.source === 'secteur' && c.secteur_id === s.id);
        // Les clients retirés du secteur ce jour-là disparaissent simplement (pas de nom barré) ;
        // pour les remettre : bouton « + Ajouter » du jour → onglet Clients.
        return `<div class="ps-secteur-bloc" style="border-left-color:${esc(s.couleur || '#2563eb')}">
          <div class="ps-secteur-tete" title="Tous les clients de ce secteur sont visités ce jour-là">
            <span><i class="fas fa-map-marked-alt" style="color:${esc(s.couleur || '#2563eb')}"></i> ${esc(s.nom)} <small>(${membres.length})</small></span>
            <button type="button" class="ps-x" data-retirer-secteur="${s.id}" data-jour="${j.jour}" title="Retirer tout le secteur du ${esc(j.nom.toLowerCase())}"><i class="fas fa-times"></i></button>
          </div>
          ${membres.length ? `<div class="ps-secteur-membres">
            ${membres.map(c => `<div class="ps-membre" draggable="true" data-glisse-client="${c.id}" data-depuis="${j.jour}"
                data-ouvrir-client="${c.id}" data-jour="${j.jour}" title="Cliquez pour retirer ce client, le donner à un autre prévendeur ou le changer de jour">
                <span>${esc(c.nom)}</span><i class="fas fa-ellipsis-h"></i></div>`).join('')}
          </div>` : ''}
        </div>`;
      }).join('');
      const seuls = j.liste.filter(c => c.source === 'client').map(c => `
        <div class="ps-item" draggable="true" data-glisse-client="${c.id}" data-depuis="${j.jour}"
             data-ouvrir-client="${c.id}" data-jour="${j.jour}" title="Glissez vers un autre jour, ou cliquez pour plus de choix">
          <span class="ps-item-nom">${esc(c.nom)}</span>
          <button type="button" class="ps-x" data-retirer-client="${c.id}" data-jour="${j.jour}" title="Retirer du ${esc(j.nom.toLowerCase())}"><i class="fas fa-times"></i></button>
        </div>`).join('');
      const doublons = (j.doublons || []).length ? `
        <div class="ps-doublons" title="Un client ne doit avoir qu'un seul prévendeur par jour">
          <i class="fas fa-exclamation-triangle"></i> <strong>Aussi chez un autre prévendeur :</strong>
          ${j.doublons.map(d => `<div><button type="button" class="ps-doublon" data-ouvrir-client="${d.id}" data-jour="${j.jour}">${esc(d.nom)}</button> → ${d.chez.map(esc).join(', ')}</div>`).join('')}
          <small>Cliquez sur un nom pour le retirer ou le donner.</small>
        </div>` : '';
      return `<div class="ps-col" data-col="${j.jour}">
        <div class="ps-col-tete ps-j${j.jour}">${esc(j.nom)} <span>${j.total}</span></div>
        <div class="ps-col-corps" data-depot="${j.jour}">
          ${doublons}${blocsSecteurs + seuls ||'<div class="ps-col-vide"><i class="fas fa-arrow-down"></i>Glissez un client ou un secteur ici</div>'}
        </div>
        <button type="button" class="ps-col-ajout" data-ajouter-jour="${j.jour}"><i class="fas fa-plus"></i> Ajouter</button>
      </div>`;
    }).join('');
  }

  function afficherPanneau() {
    document.querySelectorAll('#planning-semaine-section .ps-mini-onglet').forEach(b => b.classList.toggle('active', b.dataset.liste === ps.liste));
    const filtre = $id('ps-filtre');
    filtre.placeholder = ps.liste === 'clients' ? 'Rechercher un client…' : 'Rechercher un secteur…';
    const q = sansAccent(filtre.value.trim());
    const zone = $id('ps-panneau-liste');
    if (ps.liste === 'secteurs') {
      const secteurs = ps.planning.secteurs_disponibles.filter(s => !q || sansAccent(s.nom).includes(q));
      zone.innerHTML = secteurs.length ? secteurs.map(s => `
        <div class="ps-carte" draggable="true" data-glisse-secteur="${s.id}">
          <div class="ps-carte-nom"><i class="fas fa-grip-vertical"></i><i class="fas fa-map-marked-alt" style="color:${esc(s.couleur || '#2563eb')}"></i> ${esc(s.nom)}</div>
          <div class="ps-carte-info">${pluriel(s.nb_clients, 'client')}</div>
          ${joursPris(ps.global.secteurs[s.id])}
        </div>`).join('')
        : '<p class="ps-astuce" style="padding:8px">Aucun secteur. Renseignez le secteur sur la fiche des clients, ou utilisez l\'onglet « Clients ».</p>';
      return;
    }
    const sansJour = new Set(ps.planning.clients_sans_jour.map(c => c.id));
    const trouves = ps.clients
      .filter(c => !q || sansAccent(`${nomClient(c)} ${c.telephone || ''} ${c.secteur_nom || ''}`).includes(q))
      .sort((a, b) => (sansJour.has(b.id) - sansJour.has(a.id)));
    const affiches = trouves.slice(0, 60);
    zone.innerHTML = affiches.length ? affiches.map(c => `
      <div class="ps-carte" draggable="true" data-glisse-client="${c.id}">
        <div class="ps-carte-nom"><i class="fas fa-grip-vertical"></i> ${esc(nomClient(c))} ${sansJour.has(c.id) ? '<span class="ps-badge-orange">Aucun jour</span>' : ''}</div>
        <div class="ps-carte-info">${[c.telephone, c.secteur_nom ? 'Secteur ' + c.secteur_nom : ''].filter(Boolean).map(esc).join(' · ') || '&nbsp;'}</div>
        ${joursPris(ps.global.clients[c.id])}
      </div>`).join('') + (trouves.length > affiches.length ? `<p class="ps-astuce" style="padding:4px 2px">${trouves.length - affiches.length} autres : tapez le nom pour les trouver.</p>` : '')
      : '<p class="ps-astuce" style="padding:8px">Aucun client trouvé.</p>';
  }

  // Petites cases L M M J V S D d'un client (ou d'un secteur), pour TOUS les prévendeurs :
  //   couleur du jour = visité ce jour-là par le prévendeur choisi ;
  //   gris foncé      = déjà pris ce jour-là par un autre prévendeur (nom au survol) ;
  //   clair           = libre.
  // entrees : [{jour, livreur_id, livreur_nom}] (vue d'ensemble /livreurs/planning-clients/)
  function joursPris(entrees) {
    const parJour = {};
    (entrees || []).forEach(e => { (parJour[e.jour] = parJour[e.jour] || []).push(e); });
    return `<div class="ps-jours-pris">${LETTRES.map((l, i) => {
      const jour = i + 1;
      const liste = parJour[jour] || [];
      const nomJour = ps.planning ? ps.planning.jours[i].nom : l;
      if (!liste.length) return `<span title="${esc(nomJour)} : libre">${l}</span>`;
      const moi = liste.some(e => String(e.livreur_id) === String(ps.livreurId));
      const noms = [...new Set(liste.map(e => e.livreur_nom))].join(', ');
      return `<span class="on ${moi ? '' : 'ps-autre'}" ${moi ? `style="background:${COULEURS[i]}"` : ''}
        title="${esc(nomJour)} : ${esc(noms)}">${l}</span>`;
    }).join('')}</div>`;
  }

  // ---------------------------------------------------------------- fenêtre « + Ajouter » (un client / tout un secteur)
  function ouvrirAjout(jour) {
    ps.jour = jour;
    $id('ps-ajout-titre').textContent = `Ajouter au ${nomJour(jour)}`;
    $id('ps-recherche').value = '';
    choisirOnglet('clients');
    $id('ps-fenetre-ajout').style.display = 'flex';
    setTimeout(() => $id('ps-recherche').focus(), 50);
  }

  function choisirOnglet(nom) {
    ps.onglet = nom;
    document.querySelectorAll('#ps-fenetre-ajout .ps-onglet').forEach(b => b.classList.toggle('active', b.dataset.onglet === nom));
    $id('ps-panneau-clients').style.display = nom === 'clients' ? 'block' : 'none';
    $id('ps-panneau-secteurs').style.display = nom === 'secteurs' ? 'block' : 'none';
    afficherChoix();
  }

  function afficherChoix() {
    const j = jourInfo(ps.jour);
    if (ps.onglet === 'secteurs') {
      const pris = new Set(j.secteurs.map(s => s.id));
      const secteurs = ps.planning.secteurs_disponibles;
      $id('ps-liste-choix-secteurs').innerHTML = secteurs.length ? secteurs.map(s => `
        <div class="ps-choix">
          <div><div class="ps-choix-nom"><i class="fas fa-map-marked-alt" style="color:${esc(s.couleur || '#2563eb')}"></i> ${esc(s.nom)}</div>
            <div class="ps-choix-info">${pluriel(s.nb_clients, 'client')}</div></div>
          ${pris.has(s.id) ? '<button type="button" disabled><i class="fas fa-check"></i> Déjà ajouté</button>'
                           : `<button type="button" data-choix-secteur="${s.id}"><i class="fas fa-plus"></i> Ajouter</button>`}
        </div>`).join('')
        : '<p class="ps-astuce">Aucun secteur n\'est créé. Utilisez plutôt « Un client », ou renseignez le secteur sur la fiche des clients.</p>';
      return;
    }
    const deja = new Set(j.liste.map(c => c.id));
    const q = sansAccent($id('ps-recherche').value.trim());
    const trouves = ps.clients.filter(c => !q || sansAccent(`${nomClient(c)} ${c.telephone || ''} ${c.secteur_nom || ''}`).includes(q));
    const affiches = trouves.slice(0, 40);
    $id('ps-liste-choix-clients').innerHTML = affiches.length ? affiches.map(c => `
      <div class="ps-choix">
        <div><div class="ps-choix-nom">${esc(nomClient(c))}</div>
          <div class="ps-choix-info">${[c.telephone, c.secteur_nom ? 'Secteur ' + c.secteur_nom : ''].filter(Boolean).map(esc).join(' · ') || '&nbsp;'}</div></div>
        ${deja.has(c.id) ? '<button type="button" disabled><i class="fas fa-check"></i> Déjà prévu</button>'
                         : `<button type="button" data-choix-client="${c.id}"><i class="fas fa-plus"></i> Ajouter</button>`}
      </div>`).join('') + (trouves.length > affiches.length ? `<p class="ps-astuce" style="margin-top:10px">${trouves.length - affiches.length} autres clients : tapez quelques lettres du nom pour les trouver.</p>` : '')
      : '<p class="ps-astuce">Aucun client trouvé. Vérifiez l\'orthographe.</p>';
  }

  // ---------------------------------------------------------------- actions
  async function ajouterSecteur(jour, secteurId) {
    const j = jourInfo(jour);
    const s = ps.planning.secteurs_disponibles.find(x => x.id === secteurId) || {};
    if (j.secteurs.some(x => x.id === secteurId)) { message(`Le secteur ${s.nom} est déjà prévu le ${nomJour(jour)}`, 'warning'); return; }
    await enregistrerSecteurs(jour, j.secteurs.map(x => x.id).concat([secteurId]), `Secteur ${s.nom} ajouté au ${nomJour(jour)}`);
  }

  async function enregistrerSecteurs(jour, ids, texteOk, transferer) {
    const r = await postJSON(`${API}${ps.livreurId}/planning/secteurs/`, { jour: jour, secteurs: ids, transferer: !!transferer });
    if (r.status === 409 && r.data.conflits) {
      // Un secteur n'est visité que par un seul prévendeur le même jour
      const c = r.data.conflits[0];
      const noms = [...new Set(r.data.conflits.map(x => x.livreur_nom))].map(esc);
      const qui = noms.length > 1 ? noms.slice(0, -1).join(', ') + ' et ' + noms[noms.length - 1] : noms[0];
      confirmer({
        titre: 'Ce secteur a déjà un prévendeur',
        texte: `Le secteur <strong>${esc(c.secteur_nom)}</strong> est déjà visité par <strong>${qui}</strong>
          le ${esc(c.jour_nom.toLowerCase())}.<br><br>Un client ne peut pas avoir deux prévendeurs le même jour.
          Voulez-vous donner ce secteur à <strong>${esc(ps.planning.livreur_nom)}</strong> ?
          <br><small style="color:#6b7280">Il sera retiré du ${esc(c.jour_nom.toLowerCase())} de ${qui}.</small>`,
        bouton: `Oui, donner à ${ps.planning.livreur_nom}`, couleur: '#d97706',
        siOui: () => enregistrerSecteurs(jour, ids, texteOk, true)
      });
      return;
    }
    if (!r.ok) { message(r.data.error || 'L\'enregistrement a échoué', 'danger'); return; }
    message(texteOk, 'success');
    await chargerPlanning();
  }

  // Ajoute un client à un jour. « apres » est appelé une fois l'ajout réussi (ex. : retirer de l'ancien jour).
  async function ajouterClient(jour, client, transferer, apres) {
    if (jourInfo(jour).liste.some(c => c.id === client.id)) { message(`${client.nom} est déjà prévu le ${nomJour(jour)}`, 'warning'); return; }
    const r = await postJSON(`${API}${ps.livreurId}/planning/ajouter-client/`,
      { client_id: client.id, jours: [jour], transferer: !!transferer });
    if (r.status === 409 && r.data.conflits) {
      const c = r.data.conflits[0];
      confirmer({
        titre: 'Ce client a déjà un prévendeur',
        texte: `<strong>${esc(client.nom)}</strong> est déjà visité par <strong>${esc(c.livreur_nom)}</strong> le ${esc(c.jour_nom.toLowerCase())}${c.secteur_nom ? ` (secteur ${esc(c.secteur_nom)})` : ''}.<br><br>
          Voulez-vous qu'il soit visité par <strong>${esc(ps.planning.livreur_nom)}</strong> à la place ?
          <br><small style="color:#6b7280">Il sera retiré du ${esc(c.jour_nom.toLowerCase())} de ${esc(c.livreur_nom)}.</small>`,
        bouton: `Oui, donner à ${ps.planning.livreur_nom}`, couleur: '#d97706',
        siOui: () => ajouterClient(jour, client, true, apres)
      });
      return;
    }
    if (!r.ok) { message(r.data.error || 'L\'ajout a échoué', 'danger'); return; }
    if (apres) { await apres(); return; }
    message(`${client.nom} sera visité le ${nomJour(jour)}`, 'success');
    await chargerPlanning();
  }

  async function retirerClient(jour, clientId, silencieux) {
    const r = await postJSON(`${API}${ps.livreurId}/planning/retirer-client/`, { client_id: clientId, jour: jour });
    if (!r.ok) { message(r.data.error || 'Le retrait a échoué', 'danger'); return false; }
    if (!silencieux) {
      const resteParSecteur = r.data.message && r.data.message.includes('reste visité');
      message(resteParSecteur ? r.data.message : `Client retiré du ${nomJour(jour)}`, resteParSecteur ? 'warning' : 'success');
      await chargerPlanning();
    }
    return true;
  }

  function deplacerClient(depuis, vers, client) {
    if (depuis === vers) return;
    ajouterClient(vers, client, false, async () => {
      await retirerClient(depuis, client.id, true);
      message(`${client.nom} : déplacé du ${nomJour(depuis)} au ${nomJour(vers)}`, 'success');
      await chargerPlanning();
    });
  }

  // Fenêtre « Que voulez-vous faire avec ce client ? » (clic sur un client du calendrier)
  function ouvrirActions(jour, clientId) {
    const c = jourInfo(jour).liste.find(x => x.id === clientId);
    if (!c) return;
    const autresLivreurs = ps.livreurs.filter(l => String(l.id) !== String(ps.livreurId));
    const autresJours = ps.planning.jours.filter(j => j.jour !== jour);
    const viaSecteur = c.source === 'secteur';
    $id('ps-confirm-titre').textContent = c.nom;
    $id('ps-confirm-texte').innerHTML = `
      <p style="margin:0 0 14px;color:#475569">Visité le <strong>${esc(nomJour(jour))}</strong> par <strong>${esc(ps.planning.livreur_nom)}</strong>
        ${viaSecteur ? `<br><small>(fait partie du secteur ${esc(c.secteur_nom)} — les autres clients du secteur ne changent pas)</small>` : ''}</p>
      <div class="ps-action">
        <div class="ps-action-titre"><i class="fas fa-user-friends"></i> Le donner à un autre prévendeur</div>
        <div class="ps-action-ligne">
          <select id="ps-action-livreur" class="no-select2"><option value="">— Choisir —</option>
            ${autresLivreurs.map(l => `<option value="${l.id}">${esc(l.nom || l.username)}</option>`).join('')}</select>
          <button type="button" id="ps-action-donner" style="background:#d97706">Donner</button>
        </div>
      </div>
      <div class="ps-action">
        <div class="ps-action-titre"><i class="fas fa-calendar-alt"></i> Le visiter un autre jour</div>
        <div class="ps-action-ligne">
          <select id="ps-action-jour" class="no-select2"><option value="">— Choisir —</option>
            ${autresJours.map(j => `<option value="${j.jour}">${esc(j.nom)}</option>`).join('')}</select>
          <button type="button" id="ps-action-deplacer" style="background:#1d4ed8">Déplacer</button>
        </div>
      </div>
      <div class="ps-action" style="border:none">
        <button type="button" id="ps-action-retirer" class="ps-action-retirer"><i class="fas fa-times"></i> Ne plus le visiter le ${esc(nomJour(jour))}</button>
      </div>`;
    $id('ps-confirm-oui').style.display = 'none';
    $id('ps-fenetre-confirm').style.display = 'flex';
    const fermer = () => { $id('ps-fenetre-confirm').style.display = 'none'; };
    const client = { id: c.id, nom: c.nom };
    $id('ps-action-donner').onclick = () => {
      const lid = $id('ps-action-livreur').value;
      if (!lid) { $id('ps-action-livreur').focus(); return; }
      fermer();
      donnerClient(jour, client, lid);
    };
    $id('ps-action-deplacer').onclick = () => {
      const vers = Number($id('ps-action-jour').value);
      if (!vers) { $id('ps-action-jour').focus(); return; }
      fermer();
      deplacerClient(jour, vers, client);
    };
    $id('ps-action-retirer').onclick = () => { fermer(); retirerClient(jour, c.id); };
  }

  async function donnerClient(jour, client, autreLivreurId) {
    const autre = ps.livreurs.find(l => String(l.id) === String(autreLivreurId)) || {};
    const r = await postJSON(`${API}${autreLivreurId}/planning/ajouter-client/`,
      { client_id: client.id, jours: [jour], transferer: true });
    if (!r.ok) { message(r.data.error || 'Le transfert a échoué', 'danger'); return; }
    // S'il était aussi ajouté un par un chez ce prévendeur, la ligne a été transférée ; sinon il sort du secteur
    message(`${client.nom} est maintenant visité par ${autre.nom || 'l\'autre prévendeur'} le ${nomJour(jour)}`, 'success');
    await chargerPlanning();
  }

  async function remettreClient(jour, clientId, chez) {
    const faire = async () => {
      const r = await postJSON(`${API}${ps.livreurId}/planning/remettre-client/`, { client_id: clientId, jour: jour });
      if (!r.ok) { message(r.data.error || 'L\'opération a échoué', 'danger'); return; }
      message(r.data.message || 'Client remis', 'success');
      await chargerPlanning();
    };
    if (!chez) { faire(); return; }
    const c = (jourInfo(jour).exclus || []).find(x => x.id === clientId) || {};
    confirmer({
      titre: 'Reprendre ce client ?',
      texte: `<strong>${esc(c.nom)}</strong> est visité par <strong>${esc(chez)}</strong> le ${esc(nomJour(jour))}.<br><br>
        Le reprendre pour <strong>${esc(ps.planning.livreur_nom)}</strong> ? Il sera retiré du ${esc(nomJour(jour))} de ${esc(chez)}.`,
      bouton: `Oui, reprendre`, couleur: '#d97706', siOui: faire
    });
  }

  function clientParId(id) {
    const c = ps.clients.find(x => x.id === id);
    if (c) return { id: c.id, nom: nomClient(c) };
    for (const j of ps.planning.jours) { const t = j.liste.find(x => x.id === id); if (t) return { id: t.id, nom: t.nom }; }
    const s = ps.planning.clients_sans_jour.find(x => x.id === id);
    return s ? { id: s.id, nom: s.nom } : null;
  }

  // ---------------------------------------------------------------- glisser-déposer
  document.addEventListener('dragstart', function (e) {
    const el = e.target.closest && e.target.closest('#planning-semaine-section [draggable="true"]');
    if (!el) return;
    ps.glisse = el.dataset.glisseSecteur
      ? { type: 'secteur', id: Number(el.dataset.glisseSecteur) }
      : { type: 'client', id: Number(el.dataset.glisseClient), depuis: el.dataset.depuis ? Number(el.dataset.depuis) : null };
    e.dataTransfer.effectAllowed = 'copyMove';
    try { e.dataTransfer.setData('text/plain', JSON.stringify(ps.glisse)); } catch (_) { /* rien */ }
    el.classList.add('ps-glisse');
  });
  document.addEventListener('dragend', function () {
    document.querySelectorAll('#planning-semaine-section .ps-glisse, #planning-semaine-section .ps-survol')
      .forEach(el => el.classList.remove('ps-glisse', 'ps-survol'));
  });
  document.addEventListener('dragover', function (e) {
    const zone = e.target.closest && e.target.closest('#planning-semaine-section [data-depot]');
    if (!zone || !ps.glisse) return;
    e.preventDefault();
    document.querySelectorAll('#planning-semaine-section .ps-survol').forEach(el => { if (el !== zone) el.classList.remove('ps-survol'); });
    zone.classList.add('ps-survol');
  });
  document.addEventListener('drop', function (e) {
    const zone = e.target.closest && e.target.closest('#planning-semaine-section [data-depot]');
    if (!zone || !ps.glisse) return;
    e.preventDefault();
    zone.classList.remove('ps-survol');
    const jour = Number(zone.dataset.depot);
    const g = ps.glisse;
    ps.glisse = null;
    if (g.type === 'secteur') { ajouterSecteur(jour, g.id); return; }
    const client = clientParId(g.id);
    if (!client) return;
    if (g.depuis) deplacerClient(g.depuis, jour, client);
    else ajouterClient(jour, client);
  });

  // ---------------------------------------------------------------- clics
  document.addEventListener('click', function (e) {
    const t = e.target;
    if (!t.closest) return;
    // fenêtres
    if (t.closest('[data-action="fermer-ajout"]') || t.id === 'ps-fenetre-ajout') { $id('ps-fenetre-ajout').style.display = 'none'; return; }
    if (t.closest('[data-action="fermer-confirm"]') || t.id === 'ps-fenetre-confirm') { $id('ps-fenetre-confirm').style.display = 'none'; return; }
    const onglet = t.closest('#ps-fenetre-ajout [data-onglet]');
    if (onglet) { choisirOnglet(onglet.dataset.onglet); return; }
    const choixClient = t.closest('[data-choix-client]');
    if (choixClient && !choixClient.disabled) {
      const c = clientParId(Number(choixClient.dataset.choixClient));
      if (c) { choixClient.disabled = true; ajouterClient(ps.jour, c); }
      return;
    }
    const choixSecteur = t.closest('[data-choix-secteur]');
    if (choixSecteur && !choixSecteur.disabled) {
      choixSecteur.disabled = true;
      ajouterSecteur(ps.jour, Number(choixSecteur.dataset.choixSecteur));
      return;
    }
    // page
    if (!t.closest('#planning-semaine-section')) return;
    const mini = t.closest('[data-liste]');
    if (mini) { ps.liste = mini.dataset.liste; $id('ps-filtre').value = ''; afficherPanneau(); return; }
    const ajout = t.closest('[data-ajouter-jour]');
    if (ajout) { ouvrirAjout(Number(ajout.dataset.ajouterJour)); return; }
    const rs = t.closest('[data-retirer-secteur]');
    if (rs) {
      const jour = Number(rs.dataset.jour);
      const id = Number(rs.dataset.retirerSecteur);
      const s = jourInfo(jour).secteurs.find(x => x.id === id) || {};
      confirmer({
        titre: 'Retirer ce secteur ?',
        texte: `Les clients du secteur <strong>${esc(s.nom)}</strong> ne seront plus visités le <strong>${esc(nomJour(jour))}</strong>
          par ${esc(ps.planning.livreur_nom)}.<br><small style="color:#6b7280">Les clients eux-mêmes ne sont pas supprimés.</small>`,
        bouton: 'Oui, retirer', couleur: '#dc2626',
        siOui: () => enregistrerSecteurs(jour, jourInfo(jour).secteurs.map(x => x.id).filter(x => x !== id), `Secteur ${s.nom} retiré du ${nomJour(jour)}`)
      });
      return;
    }
    const rc = t.closest('[data-retirer-client]');
    if (rc) { retirerClient(Number(rc.dataset.jour), Number(rc.dataset.retirerClient)); return; }
    const rm = t.closest('[data-remettre-client]');
    if (rm) { remettreClient(Number(rm.dataset.jour), Number(rm.dataset.remettreClient), rm.dataset.chez); return; }
    const oc = t.closest('[data-ouvrir-client]');
    if (oc) ouvrirActions(Number(oc.dataset.jour), Number(oc.dataset.ouvrirClient));
  });

  document.addEventListener('change', function (e) {
    if (e.target.id !== 'ps-livreur') return;
    ps.livreurId = e.target.value || null;
    ps.planning = null;
    if (!ps.livreurId) { afficher(); return; }
    chargerPlanning();
  });

  document.addEventListener('input', function (e) {
    if (e.target.id === 'ps-recherche') afficherChoix();
    if (e.target.id === 'ps-filtre' && ps.planning) afficherPanneau();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    ['ps-fenetre-confirm', 'ps-fenetre-ajout'].some(id => {
      const f = $id(id);
      if (f && f.style.display === 'flex') { f.style.display = 'none'; return true; }
      return false;
    });
  });

  window.initPlanningSemaine = init;
})();
