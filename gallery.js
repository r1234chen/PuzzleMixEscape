(()=>{const $$=(q)=>Array.from(document.querySelectorAll(q)),cards=$$('.g-card'),dialog=document.querySelector('.g-view'),video=dialog.querySelector('video'),lang=document.querySelector('[data-language]'),zh=document.documentElement.lang.startsWith('zh'),state={model:'all',difficulty:'all'},buttons=$$('[data-axis] button');let last=null,opening=null;
function url(){const u=new URL(location.href);for(const k of Object.keys(state)){if(state[k]==='all')u.searchParams.delete(k);else u.searchParams.set(k,state[k])}return u}
function syncLang(){lang.href=lang.getAttribute('data-language')+location.search+location.hash}
const coming=document.querySelector('.g-coming'),empty=document.querySelector('.g-empty'),emptyText=empty.querySelector('p'),noMatch=emptyText.textContent;
function filters(){let count=0;for(const c of cards){c.hidden=!Object.entries(state).every(([k,v])=>v==='all'||v===c.dataset[k]);if(!c.hidden)count++}for(const b of buttons)b.setAttribute('aria-pressed',String(state[b.parentNode.dataset.axis]===b.value));const pending=['gemini-3.8-flash','qwen3.8-max'].includes(state.model);
 coming.hidden=!(count>0&&state.model==='qwen3.8-max');
 emptyText.textContent=pending&&!count?coming.textContent:noMatch;empty.hidden=count!==0;syncLang()}
function update(){const u=url();u.hash='';history.replaceState(null,'',u.href);filters()}
for(const b of buttons)b.addEventListener('click',()=>{state[b.parentNode.dataset.axis]=b.value;update()});
document.querySelector('.g-empty button').onclick=()=>{state.model=state.difficulty='all';update();buttons[0].focus()};
function read(){for(const k of Object.keys(state)){const v=new URL(location.href).searchParams.get(k);state[k]=buttons.some(b=>b.parentNode.dataset.axis===k&&b.value===v)?v:'all'}filters();const c=cards.find(x=>x.dataset.id===location.hash.slice(1));if(c)openCard(c,false);else if(dialog.open)dialog.close()}
function openCard(c,play){last=c;if(opening!==c){opening=c;video.src=c.getAttribute('href');video.defaultPlaybackRate=video.playbackRate=1;dialog.querySelector('h2').textContent=c.querySelector('.g-name').textContent;video.setAttribute('aria-label',dialog.querySelector('h2').textContent)}
if(!dialog.open)dialog.showModal();if(play){const p=video.play();if(p)p.catch(()=>{})}syncLang()}
for(const c of cards)c.addEventListener('click',e=>{if(e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;e.preventDefault();const u=url();u.hash=c.dataset.id;history.replaceState(null,'',u.href);openCard(c,true)});
dialog.querySelector('button').onclick=()=>dialog.close();dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close()}});
dialog.addEventListener('close',()=>{video.pause();video.removeAttribute('src');video.load();opening=null;const u=url();u.hash='';history.replaceState(null,'',u.href);syncLang();if(last&&!last.hidden)last.focus()});
window.addEventListener('hashchange',read);window.addEventListener('popstate',read);read()})();
