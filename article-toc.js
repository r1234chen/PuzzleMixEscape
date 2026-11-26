(()=>{
const links=[...document.querySelectorAll('.toc a[href^="#"]')],sections=links.map(a=>document.getElementById(a.hash.slice(1)));
if(!links.length||sections.some(s=>!s))return;
let pinned='',frame=0;
function activate(id){for(const a of links){if(a.hash==='#'+id)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current')}}
function sync(){frame=0;if(pinned){activate(pinned);return}let current=sections[0];for(const s of sections){if(s.getBoundingClientRect().top>Math.min(96,innerHeight*.15))break;current=s}if(scrollY>0&&Math.ceil(scrollY+innerHeight)>=document.documentElement.scrollHeight-1)current=sections[sections.length-1];activate(current.id)}
function schedule(){if(!frame)frame=requestAnimationFrame(sync)}
function hash(){const id=location.hash.slice(1);pinned=id==='takeaways'?'overview':sections.some(s=>s.id===id)?id:'';schedule()}
for(const a of links)a.addEventListener('click',e=>{if(!e.ctrlKey&&!e.metaKey&&!e.shiftKey&&!e.altKey){pinned=a.hash.slice(1);activate(pinned)}});
for(const t of ['wheel','touchstart','pointerdown'])window.addEventListener(t,()=>{pinned='';schedule()},{passive:true});
window.addEventListener('keydown',e=>{if(['PageUp','PageDown','ArrowUp','ArrowDown','Home','End',' '].includes(e.key)){pinned='';schedule()}});
window.addEventListener('scroll',schedule,{passive:true});window.addEventListener('resize',schedule);window.addEventListener('hashchange',hash);hash()
})();