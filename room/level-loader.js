(()=>{const L=Math.max(1,Math.min(44,Math.trunc(Number(new URLSearchParams(location.search).get('level')))||1));window.LEVEL_NO=L;const existing=document.querySelector('.cap h1');existing.textContent='Level '+L;document.title='Level '+L+' · PuzzleMixEscape';const cn=document.documentElement.lang==='zh-CN',row=ROOMS[L-1];document.querySelector('#status').textContent=cn?row.zh:row.en;const query=n=>{const p=new URLSearchParams(location.search);p.set('level',n);return '?'+p};const list=document.querySelector('#level-list');
for(const r of ROOMS){
 const a=document.createElement('a'),id=document.createElement('span'),title=document.createElement('span');
 a.href=query(r.number);id.textContent='Level '+r.number;title.className='level-name';title.textContent=cn?r.zh:r.en;
 a.title=id.textContent+' · '+title.textContent;a.setAttribute('aria-label',a.title);a.append(id,title);
 if(r.number===L){a.setAttribute('aria-current','page');a.addEventListener('click',e=>{if(!e.ctrlKey&&!e.metaKey&&!e.shiftKey&&!e.altKey)e.preventDefault()})}
 list.append(a)
}
const active=list.querySelector('[aria-current]');if(active.offsetTop+active.offsetHeight>list.clientHeight)list.scrollTop=active.offsetTop-(list.clientHeight-active.offsetHeight)/2;
for(const a of document.querySelectorAll('[data-language]'))a.href=a.getAttribute('href')+query(L);if(new URLSearchParams(location.search).has('embed'))document.querySelector('header.nav').style.display='none';const add=src=>new Promise((ok,no)=>{const s=document.createElement('script');s.src=src;s.onload=ok;s.onerror=()=>no(Error(src));document.head.append(s)});const entry=document.querySelector('#entry'),msg=document.querySelector('#msg');
const fail=error=>{const t=(cn?'房间加载失败。请刷新重试。':'Room could not load. Refresh to retry.');entry.hidden=false;entry.textContent=t;msg.textContent=t;console.error(error)};
(async()=>{if(L===1){await add('scene.js');await add('room.js');entry.hidden=true;return}
document.querySelector('#crouch').hidden=false;document.querySelector('#context-help').hidden=false;const code=document.querySelector('#code');code.removeAttribute('pattern');code.removeAttribute('maxlength');code.previousSibling.textContent=cn?'输入密码 ':'Combination ';
globalThis.PME_MATERIALS={};await add('first/'+L+'.js');const [packed,keys]=PME_FIRST;
await Promise.all(keys.map(k=>add('first/mat-'+k+'.js')));const raw=Uint8Array.from(atob(packed),c=>c.charCodeAt(0));globalThis.PME_START=JSON.parse(await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream('gzip'))).text());Object.assign(PME_START.pics,PME_MATERIALS);globalThis.PME_FIRST=null;globalThis.PME_MATERIALS=null;
globalThis.PME_START_RULES=async()=>{await Promise.all([add('python/runtime-pack.js'),add('levels/engine-pack.js'),add('levels/'+L+'.js'),add('worker-source.js')])};
await add('multi-room.js')})().catch(fail)})();