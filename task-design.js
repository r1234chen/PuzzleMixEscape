(()=>{
const f=document.querySelector('.design-demo');if(!f)return;
const cn=document.documentElement.lang.startsWith('zh'),T=(a,b)=>cn?b:a,$=s=>f.querySelector(s);
const map=$('.dd-map'),chain=$('.dd-chain');
const levels=[T('Low','低'),T('Medium','中'),T('High','高')],roomNames=[T('Room 1','房间 1'),T('Room 2','房间 2'),T('Room 3','房间 3')];
const sequences=[['note','key','exit'],['note','weigh','case','key','exit'],['note','plate','case','uv','props','key','exit']];
function actionName(k,p){return ({note:T('Read the note','读纸条'),weigh:T('Weigh the items','称重'),plate:T('Press the plate','压下踏板'),case:T('Open the case','开工具箱'),uv:T('Reveal the clue','照出图案'),props:T('Match the toys','摆玩偶'),key:p===2?T('Scan for the key','探测取钥匙'):T('Take the key','取钥匙'),exit:T('Unlock the door','开门')})[k]}
let selected='key';
const rect=(x,y,w,h,fill,stroke='none',r=0,sw=1)=>`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`;
const path=(d,stroke,width=1,fill='none',attr='')=>`<path d="${d}" fill="${fill}" stroke="${stroke}" stroke-width="${width}" stroke-linejoin="round" ${attr}/>`;
const circle=(x,y,r,fill,stroke='none',sw=1)=>`<circle cx="${x}" cy="${y}" r="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`;
const group=(x,y,contents,deg=0)=>`<g transform="translate(${x} ${y}) rotate(${deg})">${contents}</g>`;
const text=(x,y,s,size,fill='#4a554a')=>`<text x="${x}" y="${y}" text-anchor="middle" font-family="system-ui,sans-serif" font-size="${size}" fill="${fill}">${s}</text>`;
function stations(e,p){
 const bx=e>=2?360:241,by=e>=2?51:163,cx=[254,458,484][e-1],cy=[40,171,-90][e-1];
 const station={note:[105,43,0],side:[37,176,0],case:[bx,by,e>=2?1:0],fuse:e===3?[363,-64,2]:[277,204,0],cab:[cx,cy,e-1],power:e===1?[239,105,0]:[488,98,1],exit:[113,222,0]};
 const step={note:'note',weigh:'side',plate:'side',case:'case',uv:'fuse',props:'power',key:'cab',exit:'exit'};
 return {station,step}
}
const palette=['#247696','#9a6020','#785899','#2c8179','#a34f55','#546696','#426444'];
const tier=v=>Math.min(3,Math.max(1,Math.round(v)));
let fraction=0,lastConfig='',routeModel=null;
function routes(e,p,seq){
 // Ground-plane bounds from the illustrated floor plan. Pad solid footprints
 // so the centre of the traveller (and the ink of the line) clears the prop.
 const solids=[];
 const block=(x0,y0,x1,y1)=>solids.push([x0,y0,x1,y1]);
 const furniture=(x,y,w,h)=>block(x-w/2,y-h/2,x+w/2,y+h/2);
 furniture(113,37,100,36); furniture(105,64,28,28); furniture(35,114,46,84);
 furniture(134,118,31,31); furniture(44,205,54,20); furniture(30,34,24,24);
 if(!(p===2&&e===1))furniture(252,40,51,31);
 if(p>1)furniture(37,176,46,25);
 if(e===1&&p>1)furniture(241,163,62,31);
 if(e>=2){
  block(312,7,318,102);block(312,166,318,224);
  furniture(365,48,67,37); furniture(391,88,20,20); furniture(346,204,48,20);
  if(!(p===2&&e===2))furniture(458,171,55,32);
 }
 if(e===3){
  // The third room only occupies the upper-right quadrant.
  block(-20,-160,318,15);block(315,9,409,15);block(477,9,538,15);
  furniture(354,-112,58,32);furniture(343,-82,26,26);
  furniture(349,-7,51,20);furniture(509,-11,24,24);
  if(p!==2)furniture(484,-90,52,32);
 }
 const cab=[[254,40],[458,171],[484,-90]][e-1];
 if(p===2)furniture(...cab,36,32);
 if(p===3){
  furniture(...(e===3?[363,-64]:[277,204]),40,25);
  furniture(...(e===1?[239,105]:[488,98]),44,31)
 }
 // A segment may touch a padded corner, but cannot cross its open interior.
 const pads=m=>solids.map(([x,y,X,Y])=>[x-m,y-m,X+m,Y+m]);
 const hard=pads(3),guide=pads(7);
 const enters=([x,y],[X,Y],box)=>{
  let lo=0,hi=1;
  for(const [i,a,b] of [[0,x,X],[1,y,Y]]){
   const L=box[i]+1e-7,H=box[i+2]-1e-7;
   if(Math.abs(a-b)<1e-9){if(a<=L||a>=H)return false;continue}
   const t=(L-a)/(b-a),u=(H-a)/(b-a);
   lo=Math.max(lo,Math.min(t,u));hi=Math.min(hi,Math.max(t,u));if(lo>=hi)return false
  }return true
 };
 const dist=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
 const clear=(a,b,boxes)=>!boxes.some(rect=>enters(a,b,rect));
 const valid=([x,y])=>x>=10&&x<=(e===1?306:521)&&y>=(e===3?-132:20)&&y<=216;
 const corner=guide.flatMap(([x,y,X,Y])=>[[x,y],[X,y],[X,Y],[x,Y]])
  .filter(q=>valid(q)&&clear(q,q,guide));
 const stop={note:[132,71],plate:[68,174],weigh:[68,174],case:e===1?[241,136]:[360,79],
  uv:e===3?[372,-40]:(e===1?[294,182]:[277,182]),props:e===1?[238,130]:[483,126],
  key:[[254,70],[460,143],[483,-63]][e-1],exit:[101,198]};
 const blend=(a,b,t)=>a.map((v,j)=>v+(b[j]-v)*t);
 function floorPath(start,end){
  if(clear(start,end,guide))return [start,end];
  const v=[start,end,...corner],cost=v.map(()=>Infinity),prev=[],used=new Set();cost[0]=0;
  while(true){
   let n=-1;for(let i=0;i<v.length;i++)if(!used.has(i)&&(n<0||cost[i]<cost[n]))n=i;
   if(n<0||!Number.isFinite(cost[n]))throw Error('Unreachable diagram station');
   if(n===1)break;used.add(n);
   for(let j=0;j<v.length;j++)if(!used.has(j)){
    const c=cost[n]+dist(v[n],v[j]);if(c+1e-7<cost[j]&&clear(v[n],v[j],guide)){cost[j]=c;prev[j]=n}
   }
  }
  const raw=[];for(let n=1;n!=null;n=prev[n])raw.unshift(v[n]);
  // Small rounded turns, using the exact same polyline for ink and motion.
  const out=[start];
  for(let i=1;i<raw.length-1;i++){
   const a=raw[i-1],b=raw[i],c=raw[i+1],r=Math.min(6,dist(a,b)/3,dist(b,c)/3);
   const l=blend(b,a,r/dist(a,b)),h=blend(b,c,r/dist(b,c));
   const bend=[l,...[.25,.5,.75,1].map(t=>blend(blend(l,b,t),blend(b,h,t),t))];
   if(bend.every((v,j)=>!j||clear(bend[j-1],v,hard)))out.push(...bend);else out.push(b)
  }return [...out,end]
 }
 let from=[101,181];return seq.map((k,i)=>{
  const pts=floorPath(from,stop[k]);from=stop[k];if(k==='exit')pts.push([101,237]);
  const lengths=pts.slice(1).map((v,j)=>dist(pts[j],v)),total=lengths.reduce((a,b)=>a+b,0);
  return {k,pts,lengths,total,colour:palette[i],d:pts.map((v,j)=>(j?'L':'M')+v.join(' ')).join(' ')}
 })
}
function point(r,u){
 if(!r.total)return r.pts[0];let dist=r.total*Math.max(0,Math.min(1,u));for(let i=0;i<r.lengths.length;i++){const len=r.lengths[i];if(dist<=len||i===r.lengths.length-1){const a=r.pts[i],b=r.pts[i+1];return a.map((v,j)=>v+(b[j]-v)*dist/len)}dist-=len}
}
function routeDrawing(seq,st){
 let layer='<g class="dd-routes" fill="none">';
 const active=seq.indexOf(selected);
 const ordered=[active];
 for(const i of ordered){const r=routeModel[i],live=i===active;
  if(r.total){layer+=path(r.d,'#fff9ea',live?5:3.4,'none','opacity="'+(live?.9:.55)+'"')+path(r.d,r.colour,live?2.8:1.7,'none','stroke-dasharray="5 4" stroke-linecap="round" opacity="'+(live?1:.64)+'"');
   const tip=point(r,.63),back=point(r,.60),angle=Math.atan2(tip[1]-back[1],tip[0]-back[0])*180/Math.PI;layer+=group(...tip,path('M-4 -3L2 0l-6 3',r.colour,2),angle)}
 }
 layer+='</g>';return layer
}
function markers(seq,st,p){
 // Put numbers on the clear side of each prop, not over the route or traveller.
 const legs=routeModel[seq.indexOf(selected)].pts.map(([x,y])=>[x,y*A]),used=[];
 const near=([x,y],[a,b],[c,d])=>{const u=c-a,v=d-b,t=Math.max(0,Math.min(1,((x-a)*u+(y-b)*v)/(u*u+v*v||1)));return Math.hypot(x-a-t*u,y-b-t*v)};
 const bounds=fullBox;
 function offset(x,y){
  let best,score=-Infinity;
  for(const [dx,dy] of [[21,-21],[-21,-21],[21,19],[-21,19],[0,-28],[-28,0],[28,0],[0,28]]){
   const q=[x+dx,y+dy],room=Math.min(q[0]-bounds[0],q[1]-bounds[1],bounds[0]+bounds[2]-q[0],bounds[1]+bounds[3]-q[1]);
   const clearance=Math.min(18,room,...legs.slice(1).map((v,j)=>near(q,legs[j],v)),...used.map(v=>Math.hypot(q[0]-v[0],q[1]-v[1])-8));
   if(clearance>score){best=[dx,dy];score=clearance}
  }used.push([x+best[0],y+best[1]]);return best
 }
 let out='';for(const [i,k] of seq.entries()){
 const [x,y]=st.station[st.step[k]],live=k===selected,[dx,dy]=offset(x,y);
 out+='<g data-pin="'+k+'" transform="translate('+x+' '+y+')" style="cursor:pointer"><title>'+(i+1)+'. '+actionName(k,p)+'</title>'+path('M'+dx*.45+' '+dy*.45+'L'+dx+' '+dy,palette[i],1.05)+group(dx,dy,circle(0,0,7.6,live?palette[i]:'#fffaf0',palette[i],1.5)+text(0,3.1,String(i+1),8.8,live?'white':palette[i]))+'</g>'}
 return out+'<g class="dd-avatar" pointer-events="none">'+circle(0,0,8,'#fff9e8','#24483a',1.3)+circle(0,0,5,'#335a48')+path('M-2 -2h4','#e6f2de',1.3)+'</g>'
}

const A=.92,B=Math.sqrt(1-A*A);
// All coordinates use the room renderer's orthographic projection. These layers
// belong to surfaces or to the explorer, never to a step card.
const media='media/task-room/', crops={ball:[119,55,84,82],brief:[119,70,84,61],rice:[130,59,62,81],cabinet:[84,27,154,133],key:[120,47,85,125],detector:[108,84,134,49],torch:[119,88,93,37],octopus:[102,51,118,111],turtle:[102,65,118,85],panda:[107,1,108,150],crab:[122,49,77,115]};
const toys=['octopus','turtle','panda','crab'],colours=['#be4743','#4f85ae','#6f9b65','#eac454'];
const mix=(a,b,t)=>a+(b-a)*t, ramp=(v,a,b)=>Math.max(0,Math.min(1,(v-a)/(b-a)));
function prop(id,x,y,w,h=w){
 const vb=crops[id];return '<svg x="'+(x-w/2)+'" y="'+(y-h/2)+'" width="'+w+'" height="'+h+'" viewBox="'+vb.join(' ')+'"><image width="308" height="210" href="'+media+'cue-'+id+'.webp"/></svg>'
}
function deskNote(p){
 const ink='#564936', arrow=path('M-3 0h6m-2 -2l2 2-2 2',ink,1.05);
 const diagrams=[prop('cabinet',-11,0,13,12)+arrow+prop('key',11,0,10,12),
 prop('brief',-11,0,12)+arrow+prop('rice',11,0,10,12),
 prop('ball',-11,0,10)+arrow+group(10,0,rect(-6,-2,12,5,'#788176',ink,.6,.5)+circle(0,-3,3.6,'#55788a',ink,.5)+rect(-1,2,3,1,'#b5da83'))];
 return group(106,43*A-36.5*B,rect(-19,-8.5,38,17,'#7a694d','none',.5)+rect(-19,-9.2,38,17,'#fff0ca','#a18d66',.5,.5)+diagrams[p-1])
}
let anchor,fullBox,focused=false,baseId='',patchState='';
const focusButton=$('.dd-focus');
function camera(){
 const [x,y,w,h]=fullBox;map.dataset.focus=String(focused);
 if(!focused){map.setAttribute('viewBox',fullBox.join(' '));return}
 const ratio=map.clientWidth/Math.max(1,map.clientHeight),cw=Math.min(w,Math.max(105,84*ratio)),ch=Math.min(h,cw/ratio);
 map.setAttribute('viewBox',[Math.min(x+w-cw,Math.max(x,anchor[0]-cw/2)),Math.min(y+h-ch,Math.max(y,anchor[1]-ch/2)),cw,ch].join(' '))
}
focusButton.addEventListener('click',()=>{focused=!focused;focusButton.setAttribute('aria-pressed',String(focused));focusButton.textContent=focused?T('Show all rooms','查看全景'):T('Inspect object','放大当前物体');camera()});
new ResizeObserver(()=>{if(fullBox)camera()}).observe(map);
const footprints={"1-1":{"door":[73.87409200968524,149.6225042881647,68.3002421307506,77.53934819897086],"key":[225.88377723970947,1.630737564322473,59.13801452784504,59.19670668953689]},"1-2":{"door":[73.87409200968524,149.6225042881647,68.3002421307506,77.53934819897086],"key":[225.88377723970947,1.630737564322473,59.13801452784504,59.19670668953689],"case":[218.8038740920097,117.52288164665525,44.56174334140436,33.767135506003434],"weigh":[11.82082324455206,135.8655231560892,53.30750605326877,38.35279588336193],"first-weight":[11.82082324455206,135.8655231560892,53.30750605326877,38.35279588336193]},"1-3":{"door":[73.87409200968524,149.6225042881647,68.3002421307506,77.53934819897086],"key":[225.88377723970947,1.630737564322473,59.13801452784504,59.19670668953689],"case":[218.8038740920097,117.52288164665525,44.56174334140436,33.767135506003434],"ultraviolet":[258.7845036319613,165.46387650085765,37.481840193704606,27.513962264150948],"stage":[215.88861985472155,78.33632933104633,46.22760290556901,24.595814751286454],"plate":[15.985472154963684,142.9524528301887,46.22760290556901,30.432109777015445]},"2-1":{"door":[73.89046199701937,149.6225042881647,68.31296572280179,77.53934819897086],"key":[429.6177347242921,122.10854202401374,59.5655737704918,59.61358490566039]},"2-2":{"door":[73.89046199701937,149.6225042881647,68.31296572280179,77.53934819897086],"key":[429.6177347242921,122.10854202401374,59.5655737704918,59.61358490566039],"case":[337.97839046199704,12.052692967409955,44.153502235469446,33.350257289879934],"weigh":[11.825633383010434,135.8655231560892,53.317436661698956,38.35279588336193],"first-weight":[11.825633383010434,135.8655231560892,53.317436661698956,38.35279588336193]},"2-3":{"door":[73.89046199701937,149.6225042881647,68.31296572280179,77.53934819897086],"key":[429.6177347242921,122.10854202401374,59.5655737704918,59.61358490566039],"case":[337.97839046199704,12.052692967409955,44.153502235469446,33.350257289879934],"ultraviolet":[258.8353204172876,165.46387650085765,37.48882265275708,27.513962264150948],"stage":[464.60730253353205,72.08315608919385,46.65275707898659,24.178936535162954],"plate":[15.991058122205665,142.9524528301887,46.23621460506706,30.432109777015445]},"3-1":{"door":[73.89046199701937,149.6710337323177,68.31296572280179,77.49257889009793],"key":[455.85991058122204,-117.80335146898804,59.14903129657228,59.16100108813928]},"3-2":{"door":[73.89046199701937,149.6710337323177,68.31296572280179,77.49257889009793],"key":[455.85991058122204,-117.80335146898804,59.14903129657228,59.16100108813928],"case":[337.97839046199704,12.184200217627847,44.153502235469446,33.33014145810664],"weigh":[11.825633383010434,135.92235038084874,53.317436661698956,38.32966267682263],"first-weight":[11.825633383010434,135.92235038084874,53.317436661698956,38.32966267682263]},"3-3":{"door":[73.89046199701937,149.6710337323177,68.31296572280179,77.49257889009793],"key":[455.85991058122204,-117.80335146898804,59.14903129657228,59.16100108813928],"case":[337.97839046199704,12.184200217627847,44.153502235469446,33.33014145810664],"ultraviolet":[344.6430700447094,-81.14019586507074,37.48882265275708,27.497366702937974],"stage":[464.60730253353205,71.76182807399346,46.65275707898659,24.580979325353645],"plate":[15.991058122205665,142.58837867247007,46.23621460506706,30.413754080522306]}},swingRect=[73.87409200968524, 149.6225042881647, 68.3002421307506, 77.53934819897086];
function plan(e,p,seq,st){
 const right=(e===1?315:530)+15,top=(e===3?-140:12)*A-24,left=-14,bottom=224*A+24,id=e+'-'+p;
 if(baseId!==id){baseId=id;fullBox=[left,top,right-left,bottom-top];
 map.innerHTML='<title>'+T('Rendered overhead room view','三维房间俯视渲染')+'</title><image class="dd-render" href="'+media+'room-'+id+'.webp" x="'+left+'" y="'+top+'" width="'+(right-left)+'" height="'+(bottom-top)+'" preserveAspectRatio="none"/><g class="dd-changes"></g><g class="dd-overlay"></g>'}
 const zs={note:36,side:p===3?8:25,case:e===1?38:44,cab:p===2?21:34,fuse:24,power:27,exit:15},projected={station:{},step:st.step};
 for(const [k,[x,y,r]] of Object.entries(st.station))projected.station[k]=[x,A*y-B*zs[k],r];
 const loc=st.step[selected];anchor=projected.station[loc].slice(0,2);const col=palette[seq.indexOf(selected)];
 map.querySelector('.dd-overlay').innerHTML='<g transform="scale(1 '+A+')">'+routeDrawing(seq,st)+'</g>'+markers(seq,projected,p);
 camera()
}
function showChanges(c,i,u,xy){
 const {e,p,seq,st}=c,k=seq[i],parts=[],shape=footprints[baseId];
 // A single scrub position drives every state, including reverse scrubbing.
 const at=(name,time)=>{const n=seq.indexOf(name);return n>=0&&(i>n||(i===n&&u>=time))};
 const layer=(tag,r,file)=>{const [x,y,w,h]=r;parts.push('<image data-change="'+tag+'" href="'+media+file+'.webp" x="'+x+'" y="'+y+'" width="'+w+'" height="'+h+'" preserveAspectRatio="none"/>')};
 const patch=(id,area=id)=>layer(id,shape[area],baseId+'-'+id);
 const loc=(id,z)=>{const [x,y]=st.station[id];return [x,A*y-B*z]};
 let hand='',desc=actionName(k,p);
 if(p===2){
  const n=at('weigh',.87)?5:at('weigh',.65)?3:0;if(n)patch(n===3?'first-weight':'weigh');
  const lcd=group(37,176*A-20*B+6,rect(-8,-3.2,16,6.4,'#263e35','#858e7e',.65,.55)+text(0,1.8,n+' kg',4.8,'#d8ffac'));
  parts.push('<g data-dial="'+n+'">'+lcd+'</g>');if(k==='weigh'&&n)desc+=' · '+n+' kg';
 }
 if(p===3&&at('plate',.82)){patch('plate');parts.push(group(42,183*A-2*B,rect(-3.6,-1,7.2,2,'#78f290','#3a7039',.7,.5)))}
 if(p>1&&at('case',.72)){
  if(at('case',.96)){patch('empty-case','case');if(!at(p===2?'key':'uv',.72))hand=p===2?'detector':'torch'}
  else patch('case')
 }
 if(p===2&&!at('case',.72)){
  const [x,y]=loc('case',e===1?37:43.5);
  parts.push(group(x,y+4,rect(-5,-2.7,10,5.4,'#353c36','none',.5)+text(0,1.7,at('case',.62)?'35':'··',4.5,'#f1dc93')))
 }
 if(p===3){
  const [x,y]=loc('fuse',22),lit=at('uv',.72);
  if(lit){
   patch('ultraviolet');const plate=rect(-16.7,-6.5,33.4,13,'#51415d','#886899',.6,.6);
   const order=toys.map((t,j)=>group((j-1.5)*8,0,rect(-3.7,-4.6,7.4,9.2,colours[j],'none',.6)+prop(t,0,0,6.7,7.9))).join('');
   parts.push('<g data-uv="lit">'+group(x,y,plate+order)+'</g>');
   if(k==='uv')parts.push(group(x,y,path('M-16 10L-15 -6L15 6Z','none',0,'#c8a3f0','opacity=".31"')+prop('torch',-19,10,10,4)))
  }
  // Keep each Level 38 toy identifiable as it travels from the bench to its own mat.
  patch('bare-mats','stage');
  const [tx,ty]=st.station.power;
  let figures='';for(let j=0;j<4;j++){
   const t=at('props',1)?1:k==='props'?ramp(u,.50+.115*j,.61+.115*j):0;
   const xx=tx+mix(((j+2)%4-1.5)*10,(j-1.5)*10,t),yy=(ty+mix(8,-3,t))*A-(23+Math.sin(Math.PI*t)*5)*B;
   figures+='<g data-toy="'+toys[j]+'" data-placed="'+(t===1)+'">'+prop(toys[j],xx,yy,8,8)+'</g>'
  }parts.push(figures)
 }
 const [cx,cy]=loc('cab',p===2?20:34);
 if(p===2&&k==='key'&&u>=.72&&u<.92){
  parts.push(group(cx,cy,prop('detector',-4+6*ramp(u,.72,.88),-3,24,9)+path('M6 -9q5 4 0 8m3 -11q8 7 0 14','#4f9760',1.1)))
 }
 if(at('key',p===1?.92:.84)){
  patch('key');if(!at('key',.92))parts.push(prop('key',cx,cy+(p===3?12:0),11,12))
 }
 if(at('key',.92)&&!at('exit',.68))hand='key';
 const door=k==='exit'&&at('key',.92),f=door?Math.min(5,Math.max(0,Math.floor((u-.73)/.034))):0;
 const phase=!door||u<.68?'locked':u<.764?'unlocking':f<5?'opening':'open';
 if(f===5)patch('door');else if(f>0)layer('door',swingRect,'swing-'+f);
 if(phase==='unlocking')parts.push(group(112,224*A-15*B,prop('key',0,0,12,11),ramp(u,.68,.764)*65));
 if(hand)parts.push('<g data-carried="'+hand+'">'+prop(hand,xy[0]-8,A*xy[1]-4,hand==='key'?11:17,hand==='key'?12:8)+'</g>');
 parts.push(deskNote(p));
 const token=baseId+'|'+parts.join('');if(token!==patchState){map.querySelector('.dd-changes').innerHTML=parts.join('');patchState=token}
 map.dataset.door=phase;map.dataset.hasKey=String(at('key',.92));map.setAttribute('aria-label',desc)
}
function actor(r,u,isExit){
 if(!isExit)return point(r,Math.min(1,u/({weigh:.60,props:.50,case:.69,uv:.70,key:.70,plate:.80}[r.k]||.86)));
 const end=r.pts.at(-1),prev=r.pts.at(-2),last=r.lengths.at(-1),fraction=(210-prev[1])/(end[1]-prev[1]),hold=1-(1-fraction)*last/r.total;
 return point(r,u<.68?u/.68*hold:u<.92?hold:hold+(1-hold)*(u-.92)/.08)
}

const progress=$('#dd-progress'),ticks=$('.dd-progress-value');
function painted(input,pct){input.style.setProperty('--dd-filled',pct+'%')}
function config(){
 const e=Number($('input[name="dd-explore"]:checked').value),p=Number($('input[name="dd-puzzle"]:checked').value),seq=sequences[p-1],st=stations(e,p);return {e,p,seq,st}
}
function stage(c){
 const v=Number(progress.value)/1000*c.seq.length,i=Math.min(c.seq.length-1,Math.floor(v));return [i,Math.min(1,v-i)]
}
function selectStep(k){
 const c=config(),i=c.seq.indexOf(k);if(i<0)return;progress.value=Math.round((i+.985)*1000/c.seq.length);update()
}
function update(){
 const c=config(),{e,p,seq,st}=c,[i,u]=stage(c),next=seq[i],signature=e+'-'+p,changed=signature!==lastConfig;
 const redraw=changed||next!==selected;selected=next;
 if(changed){
  routeModel=routes(e,p,seq,st);lastConfig=signature;
  $('.dd-count').textContent=cn?e+' 个房间 · '+seq.length+' 个解谜步骤':e+(e===1?' room':' rooms')+' · '+seq.length+' puzzle steps';
  chain.replaceChildren(...seq.map((k,j)=>{const li=document.createElement('li'),b=document.createElement('button');b.type='button';b.dataset.step=k;b.style.setProperty('--dd-stage',palette[j]);
   const num=document.createElement('span');num.className='dd-stage-number';num.textContent=String(j+1);
   const body=document.createElement('span');body.className='dd-card-body';const hd=document.createElement('strong');hd.textContent=actionName(k,p);body.append(hd);b.append(num,body);li.append(b);return li}))
 }
 if(redraw){plan(e,p,seq,st);for(const b of chain.querySelectorAll('button'))b.setAttribute('aria-pressed',String(b.dataset.step===next));
 }
 const xy=actor(routeModel[i],u,next==='exit');showChanges(c,i,u,xy);map.querySelector('.dd-avatar').setAttribute('transform','translate('+xy[0]+' '+(xy[1]*A)+')');painted(progress,Number(progress.value)/10);
 const label=(cn?'步骤 ':'Step ')+(i+1)+' / '+seq.length;ticks.textContent=label;progress.setAttribute('aria-valuetext',label+' · '+actionName(next,p))
}
$('.dd-settings').addEventListener('change',ev=>{if(ev.target.type!=='radio')return;progress.value=0;update()});
progress.addEventListener('input',update);chain.addEventListener('click',e=>{const b=e.target.closest('[data-step]');if(b)selectStep(b.dataset.step)});
map.addEventListener('click',e=>{const g=e.target.closest('[data-pin]');if(g)selectStep(g.dataset.pin)});
update();f.dataset.ready='true'
})();
