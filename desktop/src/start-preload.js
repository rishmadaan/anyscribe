// The start window's own small bridge (not the dashboard's).
'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('startWindow', {
  state: () => ipcRenderer.invoke('start:state'),
  onState: (callback) => ipcRenderer.on('start:state', (_event, state) => callback(state)),
  retry: () => ipcRenderer.invoke('start:retry'),
  copyDetails: () => ipcRenderer.invoke('start:copy'),
  openGuide: () => ipcRenderer.invoke('start:guide'),
});
