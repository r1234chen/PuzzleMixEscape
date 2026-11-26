(()=>{
// Show only text already delivered by a successful read. No camera move, zoom or hidden state inspection.
const reading=document.createElement('aside');reading.id='reading-caption';reading.hidden=true;
reading.setAttribute('aria-hidden','true'); // the original live message already announces the same text
const readingTitle=document.createElement('strong'),readingBody=document.createElement('span');
reading.append(readingTitle,readingBody);document.querySelector('.view').append(reading);
window.PME_readCaption=(title,body)=>{if(!body||!document.querySelector('#entry')?.hidden)return;
 readingTitle.textContent=title;readingBody.textContent=body;reading.hidden=false};
const hideReading=()=>{reading.hidden=true};
window.addEventListener('pointerdown',hideReading,true);window.addEventListener('keydown',hideReading,true);
window.addEventListener('blur',hideReading);
let eStartedInGame=false;
window.addEventListener('keydown',e=>{
 if(e.code!=='KeyE')return;
 if(e.repeat){if(eStartedInGame)e.preventDefault();return}
 eStartedInGame=!e.isComposing&&!e.ctrlKey&&!e.metaKey&&!e.altKey&&
  !!document.querySelector('#entry')?.hidden&&!document.querySelector('dialog[open]')&&
  !e.target.closest?.('input,textarea,select,[contenteditable="true"]');
 if(eStartedInGame)e.preventDefault();
},true);
window.addEventListener('keyup',e=>{if(e.code==='KeyE')eStartedInGame=false},true);
window.addEventListener('blur',()=>{eStartedInGame=false});
document.addEventListener('visibilitychange',()=>{if(document.hidden)eStartedInGame=false});
const overview=new URLSearchParams(location.search).get('embed')==='overview';const requested=overview?38:Math.trunc(Number(new URLSearchParams(location.search).get('level')))||1;const rows=[...EASY.map(r=>({...r,group:'L1',asset:r.number})),...HALLS.map((r,i)=>({...r,group:'H1',asset:i+1})),...ROOMS.filter(r=>r.number<=22).map(r=>({...r,group:'L2',asset:r.number})),...ROOMS.filter(r=>r.number>22).map(r=>({...r,group:'H2',asset:r.number}))].map((r,i)=>({...r,number:i+1}));const n=Math.max(1,Math.min(rows.length,requested)),row=rows[n-1],L=row.asset,cn=document.documentElement.lang==='zh-CN';window.LEVEL_NO=L;window.PLAY_NUMBER=n;document.querySelector('.cap h1').textContent='Level '+n;document.title='Level '+n+' · PuzzleMixEscape';document.querySelector('#status').textContent=cn?row.zh:row.en;const query=n=>{const p=new URLSearchParams(location.search);p.set('level',n);return '?'+p};const list=document.querySelector('#level-list');
if(overview){document.body.classList.add('overview-demo');list.closest('.level-rail').remove();document.querySelector('header.nav').remove();
 const panel=document.querySelector('.game-panel');

 if(parent!==window){
  const origin=location.protocol==='file:'?'*':location.origin;
  const fit=()=>parent.postMessage({type:'pme-overview-height',height:Math.ceil(panel.getBoundingClientRect().height)},origin);
  new ResizeObserver(fit).observe(panel);fit()
 }
}else{
const groups=new Map();
for(const [group,difficulty] of [['L1','easy'],['H1','medium-a'],['L2','medium-b'],['H2','hard']]){
 const section=document.createElement('details'),summary=document.createElement('summary'),name=document.createElement('span'),count=document.createElement('span'),levels=document.createElement('div');
 section.className='difficulty-group';section.open=group===row.group;
 name.textContent=difficulty;count.className='difficulty-count';count.textContent=String(rows.filter(r=>r.group===group).length);
 summary.append(name,count);summary.setAttribute('aria-label',difficulty+' · '+count.textContent+(cn?' 关':' levels'));
 levels.className='difficulty-levels';section.append(summary,levels);list.append(section);groups.set(group,levels)
}
for(const r of rows){
 const a=document.createElement('a'),id=document.createElement('span'),title=document.createElement('span');
 a.href=query(r.number);id.textContent='Level '+r.number;title.className='level-name';title.textContent=cn?r.zh:r.en;
 a.title=id.textContent+' · '+title.textContent;a.setAttribute('aria-label',a.title);a.append(id,title);
 if(r.number===n){a.setAttribute('aria-current','page');a.addEventListener('click',e=>{if(!e.ctrlKey&&!e.metaKey&&!e.shiftKey&&!e.altKey)e.preventDefault()})}
 groups.get(r.group).append(a)
}
const active=list.querySelector('[aria-current]');if(active.offsetTop+active.offsetHeight>list.clientHeight)list.scrollTop=active.offsetTop-(list.clientHeight-active.offsetHeight)/2;
for(const a of document.querySelectorAll('[data-language]'))a.href=a.getAttribute('href')+query(n);if(new URLSearchParams(location.search).has('embed'))document.querySelector('header.nav').style.display='none';}
const add=src=>new Promise((ok,no)=>{const s=document.createElement('script');s.src=src.startsWith('@')?src.slice(1):'../room/'+src;s.onload=ok;s.onerror=()=>no(Error(src));document.head.append(s)});const entry=document.querySelector('#entry'),msg=document.querySelector('#msg');
const fail=error=>{const t=(cn?'房间加载失败。请刷新重试。':'Room could not load. Refresh to retry.');entry.hidden=false;entry.textContent=t;msg.textContent=t;console.error(error)};
(async()=>{if(row.group==='H1'){await add('@hall/'+L+'.js');await add('@hall/rules.js');await add('@hall/scene.js');await add('@single-player.js');entry.hidden=true;return}if(row.group==='L1'){await add('@drawer-unit.js');if(n===38){await add('@office.js');await add('@play.js')}else{await add('@single/'+n+'.js');await add('@single-rules.js');await add('@single-scene.js');await add('@single-player.js')}entry.hidden=true;return}if(L===1){await add('scene.js');await add('room.js');entry.hidden=true;return}
document.querySelector('#crouch').hidden=false;document.querySelector('#context-help').hidden=false;const code=document.querySelector('#code');code.removeAttribute('pattern');code.removeAttribute('maxlength');code.previousSibling.textContent=cn?'输入密码 ':'Combination ';
globalThis.PME_MATERIALS={};await add('first/'+L+'.js');const [packed,keys]=PME_FIRST;
await Promise.all(keys.map(k=>add('first/mat-'+k+'.js')));const raw=Uint8Array.from(atob(packed),c=>c.charCodeAt(0));globalThis.PME_START=JSON.parse(await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream('gzip'))).text());Object.assign(PME_START.pics,PME_MATERIALS);globalThis.PME_FIRST=null;globalThis.PME_MATERIALS=null;
globalThis.PME_START_RULES=async()=>{await Promise.all([add('python/runtime-pack.js'),add('levels/engine-pack.js'),add('levels/'+L+'.js'),add('worker-source.js')])};
await add('multi-room.js')})().catch(fail)})();