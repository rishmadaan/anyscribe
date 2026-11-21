// window.anyscribeDesktop: everything the dashboard gets from the app (contract in desktop/README.md).
'use strict';

const { contextBridge, ipcRenderer, webUtils } = require('electron');

const arg = (name) => (process.argv.find((a) => a.startsWith(`--${name}=`)) || '').split('=')[1] || null;

contextBridge.exposeInMainWorld('anyscribeDesktop', {
  version: arg('anyscribe-version'),
  platform: process.platform,
  getSettings: () => ipcRenderer.invoke('settings:get'),
  setDockMode: (mode) => ipcRenderer.invoke('settings:dockMode', mode),
  setStartAtLogin: (on) => ipcRenderer.invoke('settings:startAtLogin', on),
  engineStatus: () => ipcRenderer.invoke('engine:status'),
  onEngineStatus: (callback) => {
    const listener = (_event, status) => callback(status);
    ipcRenderer.on('engine:status', listener);
    return () => ipcRenderer.removeListener('engine:status', listener);
  },
  restartEngine: () => ipcRenderer.invoke('engine:restart'),
  openLogFolder: () => ipcRenderer.invoke('open:logFolder'),
  revealInFinder: (path) => ipcRenderer.invoke('open:reveal', path),
  pathForFile: (file) => webUtils.getPathForFile(file),
});
