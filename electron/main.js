/**
 * Gemma-Aura — Electron Main Process
 * Creates the desktop window and manages the Python backend lifecycle.
 */
const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow = null;
let pythonProcess = null;
let ollamaProcess = null;

const isDev = !app.isPackaged;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    frame: false,
    transparent: false,
    backgroundColor: '#0a0a0f',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    icon: path.join(__dirname, '..', 'assets', 'icons', 'icon.png'),
    title: 'Gemma-Aura — AI Assistant',
  });

  // Load the Vite dev server in development, or the built files in production
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    // Open DevTools in dev mode
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function startOllamaBackend() {
  const ollamaPath = path.join(__dirname, '..', 'backend', 'ollama', 'ollama.exe');
  const modelsPath = path.join('D:', 'ollama_models');

  console.log('[Electron] Starting Ollama daemon...');

  ollamaProcess = spawn(ollamaPath, ['serve'], {
    cwd: path.join(__dirname, '..', 'backend'),
    env: { ...process.env, OLLAMA_MODELS: modelsPath }, // Pass the custom local D: drive model path
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  ollamaProcess.stdout.on('data', (data) => console.log(`[Ollama] ${data.toString().trim()}`));
  ollamaProcess.stderr.on('data', (data) => console.error(`[Ollama] ${data.toString().trim()}`));
  
  ollamaProcess.on('error', (err) => {
    console.error(`[Ollama] Failed to start: ${err.message}. Is ollama.exe in backend/ollama/ ?`);
  });
}

function stopOllamaBackend() {
  if (ollamaProcess) {
    console.log('[Electron] Stopping Ollama daemon...');
    ollamaProcess.kill('SIGTERM');
    ollamaProcess = null;
  }
}

function startPythonBackend() {
  const backendPath = path.join(__dirname, '..', 'backend', 'main.py');
  
  console.log('[Electron] Starting Python backend...');
  
  pythonProcess = spawn('python', [backendPath], {
    cwd: path.join(__dirname, '..', 'backend'),
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[Backend] ${data.toString().trim()}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[Backend] ${data.toString().trim()}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`[Backend] Process exited with code ${code}`);
  });

  pythonProcess.on('error', (err) => {
    console.error(`[Backend] Failed to start: ${err.message}`);
  });
}

function stopPythonBackend() {
  if (pythonProcess) {
    console.log('[Electron] Stopping Python backend...');
    pythonProcess.kill('SIGTERM');
    pythonProcess = null;
  }
}

// ─── IPC Handlers ──────────────────────────────────────────────────────────
ipcMain.handle('window:minimize', () => {
  mainWindow?.minimize();
});

ipcMain.handle('window:maximize', () => {
  if (mainWindow?.isMaximized()) {
    mainWindow.unmaximize();
  } else {
    mainWindow?.maximize();
  }
});

ipcMain.handle('window:close', () => {
  mainWindow?.close();
});

ipcMain.handle('app:get-path', (_, name) => {
  return app.getPath(name);
});

// ─── App Lifecycle ─────────────────────────────────────────────────────────
app.whenReady().then(() => {
  startOllamaBackend(); // Automatically boot up local LLM Server
  
  // Give Ollama a short window before booting up Python
  setTimeout(() => {
    startPythonBackend();
  }, 1000);
  
  // Give backend a moment to start before showing UI
  setTimeout(() => {
    createWindow();
  }, 3000);

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  stopPythonBackend();
  stopOllamaBackend();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  stopPythonBackend();
  stopOllamaBackend();
});
