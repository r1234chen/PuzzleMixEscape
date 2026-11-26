(()=>{
const root=document.querySelector('#fig-4.analysis-grid');if(!root)return;
const zh=document.documentElement.lang.startsWith('zh');
function select(p,node){
const i=node.dataset.pick;
p.querySelectorAll('[data-pick]').forEach(n=>{const on=n.dataset.pick===i;n.classList.toggle('chosen',on);if(n.classList.contains('af-legend-key'))n.setAttribute('aria-pressed',String(on));if(n.classList.contains('af-bin'))n.classList.toggle('dim',n.dataset.col!==node.dataset.col&&n.dataset.row!==node.dataset.row)});
p.querySelector('.af-read').textContent=node.getAttribute('aria-label');
}
for(const p of root.querySelectorAll('[data-plot]'))for(const n of p.querySelectorAll('[data-pick]')){
for(const t of ['pointerenter','focus','click'])n.addEventListener(t,()=>select(p,n));
n.addEventListener('keydown',e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();select(p,n)}});
}
if('IntersectionObserver'in window){const ob=new IntersectionObserver(es=>{if(es.some(e=>e.isIntersecting)){root.classList.add('af-enter');ob.disconnect()}},{threshold:.12});ob.observe(root)}
})();
