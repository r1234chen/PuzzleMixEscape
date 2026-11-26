const start = document.querySelector('[data-start-room]');
if (start) start.addEventListener('click', () => {
  const url = new URL(start.dataset.startRoom, document.baseURI);
  url.searchParams.set('embed', 'overview');
  const frame = document.createElement('iframe');
  frame.title = document.documentElement.lang === 'zh-CN' ? 'Level 38 试玩' : 'Play Level 38';
  window.addEventListener('message', event => {
    if (event.source !== frame.contentWindow || (event.origin !== url.origin && !(url.protocol === 'file:' && event.origin === 'null'))) return;
    const data = event.data;
    if (data?.type === 'pme-overview-height' && Number.isSafeInteger(data.height) && data.height > 0) {
      frame.style.height = (data.height + 2) + 'px';
    }
  });
  frame.src = url.href;
  frame.addEventListener('load', () => frame.focus(), { once: true });
  start.closest('.room-gate').replaceWith(frame);
}, { once: true });