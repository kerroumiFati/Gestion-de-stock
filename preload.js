// Preload script pour Electron
// Ce script s'exécute avant le chargement de la page web
// et peut exposer des API sécurisées au renderer process

const { contextBridge, ipcRenderer } = require('electron');

// Exposer des API sécurisées si nécessaire
contextBridge.exposeInMainWorld('electron', {
    // Exemple : exposer une fonction pour communiquer avec le processus principal
    // sendMessage: (channel, data) => {
    //     ipcRenderer.send(channel, data);
    // }
});

console.log('Preload script chargé');
