/**
 * Gemma-Aura — Electron Preload Script
 * Safely exposes APIs to the renderer process via contextBridge.
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Window controls
  minimize: () => ipcRenderer.invoke('window:minimize'),
  maximize: () => ipcRenderer.invoke('window:maximize'),
  close: () => ipcRenderer.invoke('window:close'),
  
  // App utilities
  getPath: (name) => ipcRenderer.invoke('app:get-path', name),
});
