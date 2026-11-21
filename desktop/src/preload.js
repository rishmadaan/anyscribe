// window.anyscribeDesktop: everything the dashboard gets from the app (contract in desktop/README.md).
'use strict';

const { contextBridge, ipcRenderer, webUtils } = require('electron');

// Opened files: each arrives with an id and is acknowledged only after this page's callbacks
// ran. With no callback subscribed, it is not acknowledged and the app keeps it. An id already
// handed over in this page is acknowledged again but not handed over twice: callbacks that come
// and go before a file arrives make the app send an unacknowledged file again.
const openFileCallbacks = new Set();
const openFilesSeen = new Set();
ipcRenderer.on('open-file', (_event, { id, file }) => {
  if (!openFileCallbacks.size) return;
  if (!openFilesSeen.has(id)) {
    openFilesSeen.add(id);
    for (const callback of [...openFileCallbacks]) {
      try {
        callback(file);
      } catch (err) {
        console.error(err); // handed over all the same: never sent again
      }
    }
  }
  ipcRenderer.invoke('openFile:ack', id).catch(() => {});
});

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
  terminal: {
    status: () => ipcRenderer.invoke('terminal:status'),
    turnOn: (opts) => ipcRenderer.invoke('terminal:turnOn', opts),
    turnOff: (opts) => ipcRenderer.invoke('terminal:turnOff', opts),
    addToPath: () => ipcRenderer.invoke('terminal:addToPath'),
    retrySkill: () => ipcRenderer.invoke('terminal:retrySkill'),
  },
  oldLauncher: {
    status: () => ipcRenderer.invoke('oldLauncher:status'),
    remove: () => ipcRenderer.invoke('oldLauncher:remove'),
  },
  firstLaunch: {
    get: () => ipcRenderer.invoke('firstLaunch:get'),
    mark: (key) => ipcRenderer.invoke('firstLaunch:mark', key),
  },
  // Files held by the app are sent as soon as the first callback subscribes.
  onOpenFile: (callback) => {
    const wrapped = (file) => callback(file); // its own entry, even for the same function twice
    openFileCallbacks.add(wrapped);
    if (openFileCallbacks.size === 1) ipcRenderer.invoke('openFile:subscribe').catch(() => {});
    return () => {
      if (openFileCallbacks.delete(wrapped) && openFileCallbacks.size === 0) ipcRenderer.invoke('openFile:unsubscribe').catch(() => {});
    };
  },
});
