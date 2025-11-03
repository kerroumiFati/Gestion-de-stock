const { app, BrowserWindow, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const net = require('net');
const fs = require('fs');

let mainWindow;
let djangoProcess;
const DJANGO_PORT = 8000;
const DJANGO_HOST = '127.0.0.1';

// Déterminer le chemin de base de l'application
// En mode développement : __dirname
// En mode production : process.resourcesPath/app
const isDev = !app.isPackaged;
const appPath = isDev ? __dirname : path.join(process.resourcesPath, 'app');

// Fonction pour vérifier si le port est disponible
function isPortAvailable(port) {
    return new Promise((resolve) => {
        const server = net.createServer();
        server.once('error', () => resolve(false));
        server.once('listening', () => {
            server.close();
            resolve(true);
        });
        server.listen(port);
    });
}

// Fonction pour attendre que Django soit prêt
function waitForDjango(url, maxAttempts = 30) {
    return new Promise((resolve, reject) => {
        let attempts = 0;
        const checkServer = setInterval(() => {
            const http = require('http');
            const req = http.get(url, (res) => {
                if (res.statusCode === 200 || res.statusCode === 302) {
                    clearInterval(checkServer);
                    resolve();
                }
            });
            req.on('error', () => {
                attempts++;
                if (attempts >= maxAttempts) {
                    clearInterval(checkServer);
                    reject(new Error('Django n\'a pas démarré à temps'));
                }
            });
            req.end();
        }, 1000);
    });
}

// Démarrer le serveur Django
async function startDjangoServer() {
    return new Promise(async (resolve, reject) => {
        // Vérifier si le port est disponible
        const portAvailable = await isPortAvailable(DJANGO_PORT);
        if (!portAvailable) {
            dialog.showErrorBox(
                'Erreur de démarrage',
                `Le port ${DJANGO_PORT} est déjà utilisé. Veuillez fermer l'application qui l'utilise.`
            );
            app.quit();
            return;
        }

        const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
        const managePath = path.join(appPath, 'manage.py');

        console.log('Démarrage de Django depuis:', appPath);
        console.log('Fichier manage.py:', managePath);

        djangoProcess = spawn(pythonPath, [
            managePath,
            'runserver',
            `${DJANGO_HOST}:${DJANGO_PORT}`,
            '--noreload'
        ], {
            cwd: appPath,
            env: { ...process.env, PYTHONUNBUFFERED: '1' }
        });

        djangoProcess.stdout.on('data', (data) => {
            console.log(`Django: ${data}`);
        });

        djangoProcess.stderr.on('data', (data) => {
            console.error(`Django Error: ${data}`);
        });

        djangoProcess.on('error', (error) => {
            console.error('Erreur au démarrage de Django:', error);
            dialog.showErrorBox(
                'Erreur',
                'Impossible de démarrer le serveur Django. Assurez-vous que Python et Django sont installés.'
            );
            reject(error);
        });

        djangoProcess.on('close', (code) => {
            console.log(`Django s'est arrêté avec le code ${code}`);
        });

        // Attendre que Django soit prêt
        try {
            await waitForDjango(`http://${DJANGO_HOST}:${DJANGO_PORT}`);
            console.log('Django est prêt!');
            resolve();
        } catch (error) {
            reject(error);
        }
    });
}

// Créer la fenêtre principale
function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        },
        icon: path.join(__dirname, 'icon.png'),
        title: 'Gestion de Stock'
    });

    // Charger l'application Django
    mainWindow.loadURL(`http://${DJANGO_HOST}:${DJANGO_PORT}`);

    // Ouvrir les DevTools en mode développement (commentez en production)
    // mainWindow.webContents.openDevTools();

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    // Gérer les liens externes
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        require('electron').shell.openExternal(url);
        return { action: 'deny' };
    });
}

// Quand Electron est prêt
app.whenReady().then(async () => {
    try {
        await startDjangoServer();
        createWindow();
    } catch (error) {
        console.error('Erreur lors du démarrage:', error);
        dialog.showErrorBox(
            'Erreur de démarrage',
            'Impossible de démarrer l\'application. Consultez la console pour plus de détails.'
        );
        app.quit();
    }

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

// Quitter quand toutes les fenêtres sont fermées
app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// Arrêter le serveur Django à la fermeture
app.on('before-quit', () => {
    if (djangoProcess) {
        console.log('Arrêt du serveur Django...');
        djangoProcess.kill('SIGTERM');

        // Force kill après 5 secondes si pas terminé
        setTimeout(() => {
            if (djangoProcess && !djangoProcess.killed) {
                djangoProcess.kill('SIGKILL');
            }
        }, 5000);
    }
});
