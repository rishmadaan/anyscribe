// The start window: "Starting", or "couldn't start" with its reason (mockup section 2).
'use strict';

const $ = (id) => document.getElementById(id);
const api = window.startWindow;

function render(state) {
  $('starting').hidden = state.phase !== 'starting';
  $('failed').hidden = state.phase !== 'failed';
  if (state.phase !== 'failed') return;
  $('message').textContent = state.message;
  $('log').textContent = state.lines.join('\n');
  $('log').hidden = state.lines.length === 0;
}

api.state().then(render);
api.onState(render);
$('retry').addEventListener('click', () => api.retry());
$('guide').addEventListener('click', () => api.openGuide());
$('copy').addEventListener('click', async () => {
  await api.copyDetails();
  $('copy').textContent = 'Copied';
  setTimeout(() => ($('copy').textContent = 'Copy details'), 2000);
});
