const ROOM=(()=>{
const N=SINGLE.nodes,L=SINGLE.n,cn=document.documentElement.lang==='zh-CN',groups=[],initial=[],meshes=[],verts=[],ids={},labels={},obstacles=[],aims={},dynamic=[],inputs=[],painter=[],frames=[],images={};let texN=1;
if(L===26)for(const o of Object.values(N))if(o.host==='bottom_cabinet_immwzb_0'||o.container?.startsWith('bottom_cabinet_immwzb_0@'))o.p[0]+=.36;
if(N.office_typewriter)N.office_typewriter.p[2]=.908;
if(N.uvwall)N.uvwall.p=[3.85,.46,0];
if(N.sign_far)N.sign_far.p=[6.721,4.12,1.94];
if(N.office_tv)N.office_tv.p[2]=.91;if(N.office_scale)N.office_scale.p[2]=0;
if(L===35&&N.doorplate)N.doorplate.p=[1.53,6.116,1.38];
if(L===30&&N.doorplate){const q=N['office_red_box@1'].p;N.doorplate.p=[q[0],q[1]-.4225,q[2]+.045]}
if(N.socket)N.socket.p=[1.65,6.094,1.12];
for(const o of Object.values(N)){if(SINGLE.jugs[o.id])o.p[2]=.982;
 if(['jug_fill','jug_goal'].includes(o.kind))o.p[2]=.903;
 if(o.kind==='jug_empty')o.p[2]=.908;
 if(o.g?.group==='trays')o.p[2]=.9245}
for(const drawer of Object.values(N).filter(o=>o.kind==='drawer')){
 const base=PME_DRAWERS.base(drawer.part),dz=base-drawer.p[2];drawer.p[2]=base;
 for(const item of Object.values(N))if(item.container===drawer.id)item.p[2]+=dz
}
const atlas=document.createElement('canvas');atlas.width=atlas.height=2048;const ctx=atlas.getContext('2d');ctx.fillStyle='#fff';ctx.fillRect(0,0,2048,2048);
const W=256;function tile(fn){const i=texN++;if(i>=64)throw Error('atlas full');function paint(){ctx.save();ctx.translate(i%8*W,Math.floor(i/8)*W);ctx.beginPath();ctx.rect(0,0,W,W);ctx.clip();ctx.fillStyle='#faf5e9';ctx.fillRect(0,0,W,W);fn(ctx);ctx.restore()}paint();return [i,paint]}
function txt(c,s,y,size=35,color='#263c37'){c.fillStyle=color;c.textAlign='center';c.textBaseline='middle';c.font='bold '+size+'px system-ui, sans-serif';c.fillText(s,128,y,244)}
function label(top,mid,bot='',bg='#f3ead0'){return tile(c=>{c.fillStyle=bg;c.fillRect(0,0,W,W);txt(c,top,39,22);txt(c,mid,126,53);txt(c,bot,211,20)})[0]}
const col=c=>{const h=String(c).replace('#','');return [0,2,4].map(i=>Math.pow(parseInt(h.slice(i,i+2),16)/255,1.4))},wood='#a47b58',dark='#59493b',gold='#cfaa68',white='#f3e9d0',black='#293b39',green='#627c71',teal='#47857e',steel='#8b9993',red='#af5448',blue='#49799b',yellow='#e5bc4f';
function grp(id,p,target=id,on=true){let i=groups.length;groups.push([id,-1,target]);initial.push([p.slice(),[0,0,0],[1,1,1],+on]);ids[id]=i;return i}
const grain=tile(c=>{c.fillStyle='#f2e8d5';c.fillRect(0,0,256,256);c.lineWidth=.7;for(let i=0;i<118;i++){c.strokeStyle=i%5?'#dac9ab':'#c7b493';c.beginPath();for(let j=0;j<=16;j++){let y=i*2.18+1.7*Math.sin(i*.75+j*.53);if(j)c.lineTo(j*16,y);else c.moveTo(0,y)}c.stroke()}})[0];const fix=grp('shell',[0,0,0],'');function mesh(n,gi,points,faces,color,ti=0){if(!ti&&[wood,dark,'#c4a885','#d6b89a','#ccae8a'].includes(color))ti=grain;const start=verts.length/5;for(const face of faces){for(const j of [0,1,2,...(face.length===4?[0,2,3]:[])]){let p=points[face[j]],uv=ti?[[.01,.99],[.99,.99],[.99,.01],[.01,.01]][j]:[.45,.45];verts.push(...p,(ti%8+uv[0])/8,(Math.floor(ti/8)+uv[1])/8)}}meshes.push([n,gi,start,verts.length/5-start,col(color),''])}
function B(g,x,y,z,w,d,h,c){const p=[];for(let k of [-1,1])for(let j of [-1,1])for(let i of [-1,1])p.push([x+i*w/2,y+j*d/2,z+k*h/2]);mesh('box',g,p,[[0,2,3,1],[4,5,7,6],[0,1,5,4],[1,3,7,5],[3,2,6,7],[2,0,4,6]],c)}
function face(g,c,u,v,ti){const ps=[[-1,-1],[1,-1],[1,1],[-1,1]].map(([a,b])=>c.map((x,i)=>x+a*u[i]+b*v[i]));mesh('print',g,ps,[[0,1,2,3]],'#ffffff',ti)}
function E(g,x,y,z,a,b,c,color,seg=16){const p=[],f=[];for(let j=0;j<=10;j++){let lat=-Math.PI/2+j*Math.PI/10;for(let i=0;i<seg;i++){let t=i*2*Math.PI/seg;p.push([x+a*Math.cos(lat)*Math.cos(t),y+b*Math.cos(lat)*Math.sin(t),z+c*Math.sin(lat)])}}for(let j=0;j<10;j++)for(let i=0;i<seg;i++){let k=j*seg+i,l=j*seg+(i+1)%seg;f.push([k,l,l+seg,k+seg])}mesh('round',g,p,f,color)}

const G=(k,p,t=k,on=true)=>grp(k,p,t,on),clamp=(x,a,b)=>Math.max(a,Math.min(b,x)),textface=(g,p,w,h,ti,dir='north')=>face(g,p,dir==='east'?[0,-w/2,0]:dir==='west'?[0,w/2,0]:dir==='south'?[-w/2,0,0]:[w/2,0,0],dir==='table'?[0,h/2,0]:[0,0,h/2],ti);
function name(k){return N[k]?.label||k}function board(g,k,headline){let a=label('ROOM   /   '+String(L).padStart(2,'0'),headline||name(k),'PUZZLEMIX');B(g,0,0,0,.54,.04,.29,dark);textface(g,[0,-.023,0],.52,.274,a)}
function move(g,fn){dynamic.push([g,fn])}
function subgrp(k,p,t){return G(k,p,t)}
const plateDown=s=>(N.office_plate.g.weights[s.mat.office_plate]||0)>=N.office_plate.g.need;
const propBottom={};function pos(s,k){let o=N[k],p=o.p.slice(),at=s.stock[k];if(at && at!=='home'&&at!=='hand'&&at!=='used'){let a=N[at];if(a)p=[a.p[0],a.p[1],a.p[2]+(a.kind==='scale'?.105:a.kind==='slot'&&a.g.group==='laser'?.22:.08)]}if(N[at]?.kind==='slot'&&N[at].g.group!=='laser')p[2]=N[at].p[2]+.0193-(propBottom[k]||0);
if(N[at]?.kind==='scale')p[2]=N[at].p[2]+.098-(propBottom[k]||0);if(L===9&&at==='office_plate')p[2]=N.office_plate.p[2]+.015-(plateDown(s)?.020:0);if(o.container&&(!at||at==='home')){const parent=N[o.container];if(parent.kind==='drawer'){p[1]=parent.p[1]-.19-(s.open[o.container]?PME_DRAWERS.travel:0);p[2]=parent.p[2]+.004}else p[1]+=.24}
if(k==='bottle'&&at==='office_supply_sink')p=[5.95,4.65,.925];if(k==='exitkey'&&o.insideItem==='bottle'&&s.flags['show:bottle'])p=[5.95,4.65,1.244];if(k==='ink'&&at==='office_lamp')p=[6.24,4.48,.916];return p}
const tabletops=[];function table(x,y,w,d,h){tabletops.push([x-w/2,y-d/2,x+w/2,y+d/2,h]);B(fix,x,y,h-.027,w,d,.054,wood);for(let a of [-1,1])for(let b of [-1,1])B(fix,x+a*(w/2-.055),y+b*(d/2-.055),h/2-.045,.066,.066,h-.09,dark);obstacles.push([x-w/2,y-d/2,x+w/2,y+d/2])}
function wall(x,y,w,d){
 const band=(lo,hi,lip,col)=>B(fix,x,y,(lo+hi)/2,w+lip,d+lip,hi-lo,col);
 band(0,0.13,0.044,dark);band(0.13,0.94,0.025,['#91a89a','#b5a18b','#9aabb3','#999c87'][L%4]);band(0.94,0.9475,0,L===16?'#e4e9de':'#ece3d2');band(0.9475,0.9925,0.048,white);band(0.9925,2.9,0,L===16?'#e4e9de':'#ece3d2');
}
const width=6.8,depth=6.12;wall(-.05,3.06,.10,6.12);wall(6.85,3.06,.10,6.12);wall(3.4,-.05,6.8,.10);wall(.11,6.17,.22,.10);wall(3.98,6.17,5.64,.10);B(fix,.69,6.17,2.55,.94,.10,.70,white);B(fix,3.4,3.06,2.94,6.9,6.22,.075,white);
for(let y=0;y<14;y++)for(let x=0;x<5;x++){B(fix,(x+.5)*width/5,(y+.5)*depth/14,-.018,width/5-.003,depth/14-.003,.036,(L===16?['#aab5ae','#bdc9bf']:['#c4a885','#d6b89a','#ccae8a'])[(x+3*y)%(L===16?2:3)])}
B(fix,6.77,3.86,1.73,.05,1.64,1.17,dark);B(fix,6.733,3.86,1.73,.018,1.53,1.07,'#92b9bf');for(let j of [-1,0,1])B(fix,6.716,3.86+j*.5,1.73,.025,.034,1.08,white);B(fix,6.71,3.86,1.71,.033,1.57,.031,white);
for(let x of [2,4.9]){B(fix,x,3.15,2.8,1.02,.28,.065,steel);B(fix,x,3.15,2.756,.94,.235,.023,'#ffedbf')}
table(.47,2.5,.78,4.85,.91);const eastMin=L===23?.98:.235,eastMax=L===26?4.84:L===15?4.75:5.225;
table(6.24,(eastMin+eastMax)/2,.78,eastMax-eastMin,.91);
if(L!==26){const narrow=[30,31,34].includes(L);table(narrow?5.67:5.45,5.55,narrow?1.10:1.54,.65,.99)}
if(SINGLE.southDesk)table(L===7?2.715:2.4,.57,L===7?1.78:1.65,.67,.91);if(L===23){for(let x of [5.85,4.5])table(x,.55,.81,.57,.91);for(let x of [3.15,1.8]){B(fix,x,.55,.452,.83,.58,.904,wood);B(fix,x,.55,.913,.86,.62,.031,dark);B(fix,x,.858,.59,.74,.032,.21,green);B(fix,x,.883,.60,.15,.036,.029,gold);obstacles.push([x-.42,.25,x+.42,.86])}}
function chair(x,y){B(fix,x,y,.47,.42,.40,.07,green);B(fix,x,y+.21,.67,.40,.052,.39,green);for(let a of [-1,1])for(let b of [-1,1])B(fix,x+a*.155,y+b*.145,.23,.041,.041,.46,dark);obstacles.push([x-.23,y-.22,x+.23,y+.23])}
function framePic(x,y,z,dir,scene){
 const k=tile(c=>{
  const rect=(x,y,w,h,col)=>{c.fillStyle=col;c.fillRect(x,y,w,h)}, dot=(x,y,rx,ry,col)=>{c.fillStyle=col;c.beginPath();c.ellipse(x,y,rx,ry,0,0,7);c.fill()},poly=(pts,col)=>{c.fillStyle=col;c.beginPath();pts.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.closePath();c.fill()},line=(p,col,w)=>{c.strokeStyle=col;c.lineWidth=w;c.beginPath();p.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.stroke()};
  rect(0,0,256,256,'#5d4330');rect(7,7,242,242,'#f4ebd2');c.save();c.beginPath();c.rect(15,15,226,226);c.clip();rect(15,15,226,226,'#a9cbd4');dot(190,62,20,20,'#f1d190');
  if(['SEA','PIER','LIGHT'].includes(scene)){poly([[0,143],[90,96],[151,136],[256,112],[256,165],[0,165]],'#73948c');rect(0,145,256,100,'#4d8292');for(let i=0;i<10;i++)line([[18+i*24,164+(i%3)*18],[42+i*24,164+(i%3)*18]],'#bcdad5',3);
   if(scene==='SEA'){poly([[69,169],[152,169],[137,182],[83,182]],'#744d36');poly([[111,85],[111,166],[72,166]],'#fff5db');poly([[116,109],[143,164],[116,164]],'#bc7352')}
   if(scene==='LIGHT'){poly([[79,152],[90,67],[106,67],[119,152]],'#f9e5c7');rect(86,88,25,16,'#b75b44');rect(89,56,19,13,'#524d45');poly([[85,56],[99,44],[113,56]],'#ab513e')}
   if(scene==='PIER'){for(let i of [48,91,135,179])rect(i,150,9,51,'#725439');rect(22,146,194,10,'#9d7550')}
  }else if(scene==='BUS'){rect(0,176,256,80,'#69746e');rect(34,103,187,74,'#cc7844');for(let i=0;i<5;i++)rect(44+i*34,111,27,25,'#d8ece7');for(let x of [68,185]){dot(x,176,17,17,'#2c3839');dot(x,176,7,7,'#cbcab8')}}
  else if(scene==='DEER'){rect(0,174,256,76,'#859263');dot(116,148,51,25,'#996a44');line([[146,145],[166,105]],'#996a44',17);dot(173,102,19,11,'#976840');dot(178,99,3,3,'#322d26');for(let x of [86,102,137,149])line([[x,159],[x-4,201]],'#725037',6);for(let t of [0,12]){line([[163+t,97],[154+t,78],[147+t,58]],'#664c32',4);line([[154+t,79],[161+t,59]],'#664c32',3)}}
  else{poly([[0,169],[68,93],[121,148],[185,87],[256,155],[256,246],[0,246]],'#7e9583');poly([[0,188],[88,150],[177,177],[256,146],[256,246],[0,246]],'#526e60');if(scene==='STUDY'){rect(67,132,59,43,'#efe1c3');poly([[57,136],[95,100],[137,136]],'#a46046');rect(89,152,13,23,'#674c3e')}}
  c.restore()
 })[0];textface(fix,[x,y,z],.46,.35,k,dir)
}
if(L===22||L===37)framePic(5.23,5.98,1.47,'north','SEA');
for(let host of new Set(Object.values(N).filter(o=>o.host).map(o=>o.host))){const os=Object.values(N).filter(o=>o.host===host),o=os[0],[x,y]=o.p;if(o.kind==='drawer'){PME_DRAWERS.shell((u,v,z,...dims)=>B(fix,x+u,y+v,z,...dims),wood,dark);continue}
let high=Math.max(...os.map(o=>o.p[2]))+.15;B(fix,x,y+.39,high/2,.92,.055,high,oakColor());for(let a of [-1,1])B(fix,x+a*.465,y,high/2,.042,.80,high,oakColor());B(fix,x,y,.075,.93,.8,.15,dark);
}function oakColor(){return wood}
if(L===15){chair(4.95,4.94);chair(5.55,4.94);obstacles.push([6.26,4.87,6.70,5.57]);framePic(2.15,.055,1.72,'south','SEA');framePic(3.56,.055,1.73,'south','HILLS');framePic(.055,3.6,1.7,'west','LIGHT');for(let side of [-1,1])B(fix,6.48,5.22+side*.337,.67,.44,.028,1.34,dark);for(let z of [.13,.52,.91,1.3])B(fix,6.48,5.22,z,.44,.70,.045,wood);for(let i=0;i<7;i++)B(fix,6.43,4.96+i*.065,.69,.21,.05,.29,[green,red,blue][i%3])}
if(L===24){framePic(1.8,6.045,1.72,'north','SEA');framePic(4.05,6.045,1.72,'north','PIER');framePic(6.69,2.6,1.72,'east','DEER');for(let x of [2.15,3.5,5.05])framePic(x,.055,1.72,'south','STUDY')}
if(![12,15,16,21,24,25,28].includes(L)){
 B(fix,.045,3.0,1.7,.06,1.33,.57,dark);B(fix,.083,3.0,1.7,.018,1.26,.51,'#cfb58b');textface(fix,[.096,3.29,1.72],.33,.39,label('FIELD OFFICE','WORKSHOP','CATALOGUE','#d5ddbd'),'west');textface(fix,[.096,2.84,1.69],.39,.32,label('CASE FILE',String(L).padStart(2,'0'),'RESEARCH','#dcc0aa'),'west');
 if(!N.office_typewriter&&!N.office_tv&&!SINGLE.jugs.jug5)for(let j=0;j<9;j++){let hh=.20+(j%3)*.045;B(fix,6.51,(L===23?1.21:.79)+j*.063,.91+hh/2,.17,.049,hh,[green,dark,blue,red][j%4]);B(fix,6.421,(L===23?1.21:.79)+j*.063,.978,.006,.044,.012,gold)}
 if(L!==26&&!SINGLE.jugs.jug5){E(fix,5.94,5.63,1.01,.12,.11,.024,green);B(fix,5.94,5.63,1.18,.031,.031,.32,gold);E(fix,5.94,5.63,1.37,.14,.14,.061,green);B(fix,5.94,5.63,1.336,.18,.17,.012,white)}
}
function ringBody(g,rows,color,n=24,capTop=true){
 const pts=[],fs=[];
 for(const [z,rx,ry] of rows)for(let i=0;i<n;i++){const a=2*Math.PI*i/n;pts.push([rx*Math.cos(a),ry*Math.sin(a),z])}
 for(let j=1;j<rows.length;j++)for(let i=0;i<n;i++){const a=(j-1)*n+i,b=(j-1)*n+(i+1)%n;fs.push([a,b,b+n,a+n])}
 const a=(rows.length-1)*n;
 for(let i=1;i<n-1;i++){fs.push([0,i+1,i]);if(capTop)fs.push([a,a+i,a+i+1])}
 mesh('profile',g,pts,fs,color)
}
function rod(g,start,end,r,color){
 const delta=end.map((v,i)=>v-start[i]),l=Math.hypot(...delta);if(!l)return;
 const n=delta.map(v=>v/l),h=Math.hypot(n[0],n[1]),a=h?[-n[1]/h,n[0]/h,0]:[1,0,0],b=[n[1]*a[2]-n[2]*a[1],n[2]*a[0]-n[0]*a[2],n[0]*a[1]-n[1]*a[0]],p=[],f=[];
 for(const t of [start,end])for(let i=0;i<8;i++){let ang=i*Math.PI/4;p.push(t.map((v,j)=>v+r*(Math.cos(ang)*a[j]+Math.sin(ang)*b[j])))}
 for(let i=0;i<8;i++){let j=(i+1)%8;f.push([i,j,j+8,i+8])}mesh('rod',g,p,f,color)
}
function hoop(g,rx,ry,z,r,col){for(let i=0;i<24;i++){let a=i*Math.PI/12,b=(i+1)*Math.PI/12;rod(g,[rx*Math.cos(a),ry*Math.sin(a),z],[rx*Math.cos(b),ry*Math.sin(b),z],r,col)}}
function archedHandle(g,r,z,col,sideMount=false){const point=t=>[sideMount?0:r*Math.cos(t),sideMount?r*Math.cos(t):0,z+r*1.18*Math.sin(t)];for(let i=0;i<16;i++){const a=i*Math.PI/16,b=(i+1)*Math.PI/16;rod(g,point(a),point(b),.005,col)}}
function shallowPool(g,r,z,ti){
 const pts=[[0,0,z]],fs=[];
 for(let j=0;j<32;j++){let a=j*Math.PI/16;pts.push([r*Math.cos(a),r*Math.sin(a),z]);fs.push([0,j+1,(j+1)%32+1])}
 mesh('liquid',g,pts,fs,'#ffffff',ti)
}
function wrapLabel(g,rows,n,center,half,lo,hi,ti){
 const start=verts.length/5;
 function pt(i,z){let [a,b]=rows,t=(z-a[0])/(b[0]-a[0]),angle=i*2*Math.PI/n;
  return [(a[1]+(b[1]-a[1])*t+.00065)*Math.cos(angle),(a[2]+(b[2]-a[2])*t+.00065)*Math.sin(angle),z]}
 for(let j=0;j<half*2;j++){const i=center-half+j;
  for(const [dx,up] of [[0,0],[1,0],[1,1],[0,0],[1,1],[0,1]]){const u=.01+.98*(j+dx)/(half*2),v=up?.01:.99;verts.push(...pt(i+dx,up?hi:lo),(ti%8+u)/8,(Math.floor(ti/8)+v)/8)}}
 meshes.push(['surface-label',g,start,verts.length/5-start,[1,1,1],''])
}
function flaredVessel(g,rows,c){ringBody(g,rows,c,32,false);let [z,r,s]=rows.at(-1);
 ringBody(g,[[rows[0][0]+.014,rows[0][1]-.010,rows[0][2]-.010],[z,r-.007,s-.007]],c,32,false);
 hoop(g,r-.002,s-.002,z,.004,c)
}

const printCache=new Map();
function emblem(g,kind,y,z,w,h){
 if(!printCache.has(kind)) printCache.set(kind,tile(c=>{
 const rice=kind==='rice';c.fillStyle=rice?'#f6e9be':'#b8a178';c.fillRect(0,0,256,256);c.strokeStyle=rice?'#963c32':'#584537';c.lineWidth=8;
 if(rice){c.strokeRect(8,8,240,240);c.beginPath();c.moveTo(103,146);c.quadraticCurveTo(141,110,147,36);c.stroke();c.fillStyle='#aa752e';for(let i=0;i<5;i++)for(let a of [-1,1]){c.save();c.translate(142-4*i+10*a,45+i*18);c.rotate(a*.60);c.beginPath();c.ellipse(0,0,6,14,0,0,7);c.fill();c.restore()}txt(c,cn?'大 米':'RICE',191,42,'#73362f')}
 else{for(let x of [84,162]){c.fillStyle='#584537';c.fillRect(x-7,76,14,90);c.beginPath();c.moveTo(x,47);c.lineTo(x-24,89);c.lineTo(x+24,89);c.fill()}c.fillRect(48,180,146,8)}
 })[0]);textface(g,[0,y,z],w,h,printCache.get(kind))
}
function prop(g,id,cat,c=teal){let k=id+' '+cat;const box=(x,y,z,w,d,h,co)=>B(g,x,y,z,w,d,h,co),e=(x,y,z,a,b,h,co)=>E(g,x,y,z,a,b,h,co,12);
if(id==='briefcase'){
 const leather='#703f2b',edge='#442e23',seam='#bb8956';
 box(0,0,.099,.282,.092,.19,edge);box(0,-.05,.098,.269,.018,.175,leather);box(0,.045,.099,.268,.016,.17,leather);
 box(0,-.062,.144,.267,.011,.060,'#86543a');box(0,-.069,.115,.259,.005,.006,seam);
 for(let a of [-1,1]){box(a*.085,-.071,.116,.025,.009,.054,edge);box(a*.085,-.079,.111,.023,.007,.022,gold);box(a*.119,-.061,.024,.028,.009,.025,'#a27b4e');box(a*.057,0,.202,.025,.032,.014,gold);rod(g,[a*.057,0,.204],[a*.048,0,.241],.008,edge)}
 box(0,0,.242,.101,.024,.018,edge)
}
else if(id==='rice'){
 const rows=[[.007,.090,.058],[.025,.116,.070],[.12,.117,.069],[.176,.103,.063],[.221,.089,.027],[.232,.096,.012]];
 ringBody(g,rows,'#d9c69e',20);box(0,0,.235,.206,.023,.014,'#ad8f62');
 for(let a of [-1,1]){rod(g,[a*.087,0,.226],[a*.111,0,.126],.004,'#a18358');rod(g,[a*.111,0,.126],[a*.093,0,.022],.004,'#b39a74')}
 for(let j=-5;j<=5;j++)rod(g,[j*.016,-.013,.232],[j*.016+.009,-.013,.24],.0018,'#f7e8c1');
 emblem(g,'rice',-.0705,.108,.132,.139)
}
else if(id==='box'||id==='carton'){
 box(0,0,.096,.26,.20,.19,'#ba895d');box(-.065,0,.194,.128,.2,.006,'#cda278');box(.065,0,.194,.128,.2,.006,'#c3996e');box(0,0,.199,.040,.201,.004,'#dfc28f');
 for(let a of [-1,1])box(0,a*.101,.167,.040,.004,.06,'#ddc08d');
 emblem(g,'carton',-.102,.084,.094,.082)
}
else if(id==='paint'||id.startsWith('paint_')){
 const hue=({paint_red:'#af4535',paint_blue:'#396e99',paint_yellow:'#cf9e2d'})[id]||'#4e8a82';
 ringBody(g,[[.006,.085,.085],[.014,.091,.091],[.155,.093,.093],[.167,.097,.097]],'#aeb8b3');
 ringBody(g,[[.030,.092,.092],[.133,.094,.094]],hue,24,false);hoop(g,.095,.095,.166,.004,steel);hoop(g,.089,.089,.011,.004,steel);ringBody(g,[[.166,.085,.085],[.168,.085,.085]],'#848f89');
 for(let j=0;j<14;j++){let a=j*Math.PI/14,b=(j+1)*Math.PI/14;rod(g,[.093*Math.cos(a),.004,.116+.132*Math.sin(a)],[.093*Math.cos(b),.004,.116+.132*Math.sin(b)],.0035,'#626c67')}
 box(0,.004,.245,.051,.013,.015,'#544c42')
}
else if(/key_chain|exitkey|boxkey|^key /.test(k)){for(let j=0;j<12;j++){let a=j*Math.PI/6;e(.042*Math.cos(a),.042*Math.sin(a),.02,.014,.014,.012,gold)}box(.107,0,.02,.15,.018,.025,gold);box(.161,.018,.02,.035,.048,.025,gold)}
else if(id==='bottle'){
 ringBody(g,[[.004,.057,.057],[.013,.063,.063],[.020,.063,.063]],'#85a9a1');
 for(let [r,z] of [[.062,.025],[.061,.196],[.026,.246],[.026,.30]])hoop(g,r,r,z,.0025,'#92b7b0');
 for(let deg of [35,130,210,306]){let a=deg*Math.PI/180,v=[Math.cos(a),Math.sin(a)];for(let [r1,z1,r2,z2] of [[.062,.024,.061,.195],[.061,.195,.026,.246],[.026,.246,.026,.298]])rod(g,[r1*v[0],r1*v[1],z1],[r2*v[0],r2*v[1],z2],.0018,'#afceca')}
}
else if(id==='water'){ringBody(g,[[.004,.047,.047],[.02,.058,.058],[.17,.058,.058],[.216,.023,.023],[.252,.023,.023]],'#6dafa9');ringBody(g,[[.25,.025,.025],[.271,.025,.025]],'#b4966a')}
else if(id==='jug5'||id==='jug3'){
 let a=id==='jug5'?.09:.072,h=id==='jug5'?.24:.173,hue=id==='jug5'?'#89b5b3':'#c7956c';
 ringBody(g,[[.008,a*.78,a*.78],[.023,a*.9,a*.9],[h*.85,a*1.08,a*.93],[h,a,a*.90]],hue,28,false);
 hoop(g,a,a*.9,h,.004,'#e0cfb0');ringBody(g,[[.012,a*.72,a*.72],[.018,a*.77,a*.77]],'#735f46');
 for(const [p,q] of [[[a,0,h*.82],[a+.052,0,h*.72]],[[a+.052,0,h*.72],[a+.047,0,h*.36]],[[a+.047,0,h*.36],[a*.95,0,h*.28]]])rod(g,p,q,.012,hue);
 mesh('pour lip',g,[[-a*.83,-.024,h-.013],[-a-.035,0,h+.003],[-a*.83,.024,h-.013]],[[0,1,2]],hue)
}
else if(/octopus/.test(k)){e(0,0,.087,.068,.069,.081,red);for(let j=0;j<8;j++)e(.072*Math.cos(j*.785),.073*Math.sin(j*.785),.023,.033,.034,.021,red);for(let j of [-1,1])e(j*.026,.059,.108,.012,.01,.014,black)}
else if(/shark|fish/.test(k)){e(0,0,.087,.056,.12,.058,/shark/.test(k)?blue:'#e09a5d');mesh('tail fin',g,[[0,-.084,.092],[.004,-.159,.153],[0,-.14,.087],[-.004,-.158,.041]],[[0,1,2],[0,2,3]],/shark/.test(k)?blue:'#df9156');if(/shark/.test(k)){mesh('dorsal fin',g,[[-.012,-.025,.128],[.012,-.025,.128],[0,-.064,.195],[0,.018,.13]],[[0,1,2],[1,3,2],[3,0,2]],blue);for(let a of [-1,1])mesh('pectoral fin',g,[[a*.030,.034,.09],[a*.108,-.017,.052],[a*.031,-.034,.07]],[[0,1,2]],blue)}for(let j of [-1,1])e(j*.043,.069,.104,.008,.009,.01,black)}
else if(/crab/.test(k)){e(0,0,.053,.08,.055,.045,red);for(let j of [-1,1]){e(j*.075,.049,.076,.035,.032,.028,red);for(let n=-1;n<=1;n++)e(j*.077,n*.032,.023,.043,.015,.016,red)}}
else if(L===6&&id==='office_fig_horse'){
 const ivory='#ede6d1',mane='#c6ae77',hoof='#655244';e(0,0,.114,.055,.105,.052,ivory);
 for(let side of [-1,1])for(let y of [-.069,.062]){let end=y+(side<0?.014:-.012);rod(g,[side*.036,y,.095],[side*.041,end,.021],.013,ivory);box(side*.041,end+.003,.015,.030,.038,.022,hoof)}
 rod(g,[0,.060,.144],[0,.105,.216],.034,ivory);e(0,.127,.211,.031,.053,.032,ivory);e(0,.168,.20,.027,.027,.022,'#cebfa4');
 for(let side of [-1,1]){rod(g,[side*.019,.103,.23],[side*.023,.093,.264],.009,ivory);e(side*.027,.137,.222,.005,.007,.005,black)}
 rod(g,[0,.137,.236],[0,.166,.291],.006,gold);rod(g,[0,.048,.166],[0,.089,.232],.017,mane);rod(g,[0,-.09,.132],[0,-.128,.077],.016,mane);e(0,-.133,.060,.016,.019,.036,mane)
}
else if(L===6&&id==='office_fig_dino'){
 const hide='#bb8a3d',belly='#e0b969',ridge='#765231';e(0,0,.113,.062,.098,.064,hide);
 for(let a of [-1,1]){e(a*.046,-.024,.084,.032,.049,.052,hide);rod(g,[a*.05,-.015,.08],[a*.055,-.046,.028],.017,hide);e(a*.055,-.021,.015,.023,.048,.013,belly);
 for(let j of [-1,0,1])rod(g,[a*.055+j*.012,.005,.014],[a*.055+j*.018,.04,.009],.004,'#594733');
 rod(g,[a*.043,.058,.128],[a*.065,.087,.094],.009,hide);rod(g,[a*.065,.087,.094],[a*.065,.113,.102],.006,belly)}
 rod(g,[0,-.062,.12],[0,-.147,.085],.035,hide);rod(g,[0,-.143,.087],[.014,-.218,.063],.019,hide);rod(g,[.014,-.218,.063],[.03,-.277,.077],.008,ridge);
 rod(g,[0,.055,.139],[0,.097,.173],.034,hide);e(0,.125,.180,.046,.066,.032,hide);box(0,.161,.153,.068,.067,.017,belly);
 for(let a of [-1,1]){e(a*.039,.131,.192,.007,.009,.007,black);for(let j=0;j<3;j++)box(a*.033,.146+j*.016,.162,.005,.005,.009,white)}
 for(let j=0;j<5;j++)e(0,-.083+j*.034,.142+.032*Math.sin(j*.66),.011,.014,.013,ridge);
}
else if(/horse/.test(k)){e(0,0,.079,.052,.087,.043,wood);e(0,.071,.134,.033,.04,.07,wood);e(0,.099,.181,.033,.049,.027,wood);for(let j of [-1,1])for(let n of [-1,1])box(j*.035,n*.047,.041,.028,.029,.071,dark)}
else if(/turtle/.test(k)){e(0,0,.051,.073,.101,.052,'#718443');e(0,.104,.052,.028,.035,.025,'#94ab65');for(let j of [-1,1])for(let i of [-1,1])e(j*.064,i*.058,.02,.025,.032,.014,'#8ba566');for(let x of [-.035,0,.035])e(x,0,.095-Math.abs(x)*.25,.022,.042,.006,'#526b42')}
else if(/dino/.test(k)){e(0,0,.072,.059,.081,.050,'#759b79');rod(g,[0,.045,.085],[0,.089,.179],.019,'#7d9e7a');e(0,.107,.18,.029,.04,.023,'#86a979');rod(g,[0,-.05,.074],[0,-.148,.043],.015,'#799879');for(let j of [-1,1])for(let i of [-1,1])box(j*.04,i*.043,.033,.026,.026,.058,'#658467')}
else if(/panda/.test(k)){e(0,0,.065,.057,.049,.063,'#eee6ce');e(0,.026,.143,.05,.047,.045,'#f2ead3');for(let i of [-1,1]){e(i*.037,.028,.18,.019,.016,.018,black);e(i*.022,.064,.146,.012,.009,.014,black);e(i*.05,.005,.08,.017,.023,.039,black);e(i*.035,.02,.020,.025,.03,.017,black)}e(0,.068,.13,.011,.012,.008,black)}
else if(/^q[1-4]$/.test(id)){let cc=wood;e(0,0,.067,.084,.081,.062,cc);e(0,.075,.11,.053,.054,.05,cc);for(let a of [-1,1]){e(a*.035,.11,.124,.012,.010,.011,black);for(let b of [-1,1])e(a*.066,b*.045,.031,.029,.031,.027,cc);if(/panda/.test(k))e(a*.043,.075,.149,.02,.018,.02,black)}}
else if(/plant|pot[123]/.test(k)){ringBody(g,[[.002,.055,.055],[.12,.084,.084],[.138,.091,.091]],'#b76e4c',20);hoop(g,.090,.090,.138,.006,'#d48f61');ringBody(g,[[.139,.078,.078],[.14,.078,.078]],'#604b36');rod(g,[0,0,.14],[.01,0,.265],.006,'#60815b');for(let j=0;j<7;j++){let t=j*2.399,z=.157+.015*j,dx=.087*Math.cos(t),dy=.087*Math.sin(t),nx=-dy*.28,ny=dx*.28;mesh('leaf',g,[[0,0,z],[dx*.55+nx,dy*.55+ny,z+.039],[dx,dy,z+.054],[dx*.55-nx,dy*.55-ny,z+.031]],[[0,1,2],[0,2,3]],j%2?'#638553':'#84a765')}}
else if(/ball/.test(k)){e(0,0,.095,.095,.095,.095,blue);for(let j=0;j<3;j++)e(.031*Math.cos(j*2),.031*Math.sin(j*2),.181,.009,.009,.005,black)}
else if(/ruler/.test(k)){box(0,0,.016,.35,.058,.022,white);for(let j=0;j<15;j++)box((j-7)*.021,-.017,.03,.003,.02,.004,black)}
else if(/detector/.test(k)){
 const grip='#353e42',tube='#aebcc0',caseCol='#edaa38',coil='#263337',cx=.03,cy=.12;
 const rim=(a,b,z,r,c)=>{for(let j=0;j<32;j++){const t=j*Math.PI/16,v=t+Math.PI/16;rod(g,[cx+a*Math.cos(t),cy+b*Math.sin(t),z],[cx+a*Math.cos(v),cy+b*Math.sin(v),z],r,c)}};
 rim(.165,.114,.023,.014,coil);rod(g,[cx-.14,cy,.024],[cx+.14,cy,.024],.009,coil);
 for(let h of [-1,1])rod(g,[cx+h*.099,cy+.081,.023],[cx,cy,.052],.009,coil);
 rod(g,[cx,cy,.046],[cx,.49,.141],.016,tube);rod(g,[cx,.47,.138],[cx,.79,.206],.022,grip);
 for(let j=0;j<23;j++){const cable=i=>[cx+.022*Math.cos(i*.79),.19+i*.023,.064+i*.0057+.020*Math.sin(i*.79)];rod(g,cable(j),cable(j+1),.004,coil)}
 rod(g,[cx,.55,.15],[cx,.49,.248],.023,grip);box(cx,.48,.259,.124,.126,.052,caseCol);box(cx,.466,.289,.094,.061,.01,'#455f58');
 for(let j of [-1,0,1])box(cx+j*.031,.523,.291,.016,.015,.008,grip);
 for(let side of [-1,1])box(cx+side*.059,.77,.238,.018,.10,.082,caseCol);box(cx,.77,.202,.124,.10,.018,caseCol)
}
else if(id==='camera'){box(0,0,.06,.155,.073,.106,'#384742');box(.058,-.004,.061,.047,.084,.107,'#222b28');e(-.017,-.052,.067,.046,.028,.047,steel);e(-.017,-.077,.067,.032,.011,.032,'#49798a');box(-.014,0,.126,.062,.051,.027,black);box(.045,0,.123,.022,.022,.015,gold)}
else if(id==='controller'){e(0,0,.049,.093,.048,.029,black);for(let j of [-1,1])e(j*.069,-.030,.031,.032,.055,.029,'#354642');box(-.047,-.004,.08,.030,.009,.007,steel);box(-.047,-.004,.08,.009,.030,.007,steel);for(let [x,y,c] of [[.04,0,red],[.058,.012,blue],[.058,-.012,green]])e(x,y,.075,.006,.006,.004,c)}
else if(id==='battery'){ringBody(g,[[.002,.024,.024],[.083,.024,.024],[.086,.021,.021]],'#4a5a56');ringBody(g,[[.065,.025,.025],[.081,.025,.025]],'#be8f57');ringBody(g,[[.087,.011,.011],[.095,.011,.011]],steel)}
else if(id==='flashlight'){rod(g,[-.094,0,.040],[.043,0,.040],.027,black);rod(g,[.042,0,.040],[.089,0,.040],.040,'#43594f');rod(g,[.089,0,.040],[.094,0,.040],.032,'#b8c9dc');box(-.018,0,.07,.026,.023,.007,gold)}
else if(id==='hammer'){rod(g,[-.13,0,.023],[.095,0,.035],.016,wood);box(.089,0,.036,.041,.125,.045,steel);box(.089,-.075,.036,.048,.031,.052,'#798680')}
else if(id==='pencil'){rod(g,[-.112,0,.012],[.071,0,.012],.009,'#d1a23d');rod(g,[.071,0,.012],[.096,0,.012],.006,wood);rod(g,[.096,0,.012],[.106,0,.012],.003,black);rod(g,[-.127,0,.012],[-.112,0,.012],.009,red)}
else if(id==='scraper'||id==='trowel'){rod(g,[-.105,0,.023],[-.018,0,.023],.018,wood);rod(g,[-.018,0,.023],[.052,0,.022],.009,steel);if(id==='scraper'){mesh('scraper blade',g,[[.040,-.015,.025],[.123,-.047,.009],[.123,.047,.009],[.04,.015,.025]],[[0,1,2,3]],steel)}else{e(.083,0,.025,.061,.037,.013,steel);mesh('point',g,[[.093,-.035,.023],[.156,0,.009],[.093,.035,.023]],[[0,1,2]],steel)}}
else if(id==='pillow'){e(0,0,.06,.155,.108,.056,'#aa9d84');for(let a of [-1,1])for(let b of [-1,1])e(a*.112,b*.072,.05,.039,.036,.022,'#aa9d84')}
else if(id==='rag'){box(0,0,.009,.150,.097,.013,'#829f9b');box(-.014,.014,.021,.125,.083,.011,'#9cb5ac');for(let a of [-1,1])box(a*.044,.014,.028,.005,.079,.003,'#496d68')}
else if(id==='mirror'){box(0,0,.009,.18,.13,.018,'#a88751');box(0,0,.020,.164,.113,.006,'#b0cbce');rod(g,[-.057,-.044,.024],[.027,.045,.024],.0025,'#e0eee8')}
else if(/blank_paper|^ink |page/.test(k)){box(0,0,.01,.20,.16,.012,/mirror/.test(k)?'#abbfc0':white)}
else if(id==='mug'||id==='coffee'){
 const c=id==='coffee'?'#a8674c':'#7aa29c';flaredVessel(g,[[.006,.052,.052],[.026,.061,.061],[.128,.072,.072]],c);for(let j=0;j<12;j++){let a=j*Math.PI/12,b=(j+1)*Math.PI/12;rod(g,[.065+.048*Math.sin(a),0,.072+.041*Math.cos(a)],[.065+.048*Math.sin(b),0,.072+.041*Math.cos(b)],.008,c)}
 if(id==='coffee')ringBody(g,[[.100,.066,.066],[.101,.066,.066]],'#49301f',24)
}
else if(id==='soda'){
 ringBody(g,[[.004,.045,.045],[.011,.05,.05],[.023,.054,.054],[.144,.054,.054],[.153,.048,.048],[.16,.047,.047]],'#899caa',24);
 ringBody(g,[[.031,.055,.055],[.134,.055,.055]],'#a64c40',24,false);hoop(g,.047,.047,.159,.003,steel);E(g,.012,0,.162,.014,.018,.002,black);E(g,-.009,0,.164,.01,.019,.003,steel)
}
else if(/pizza/.test(k)){e(0,0,.023,.135,.135,.022,'#cf9654');for(let j=0;j<5;j++)e(.07*Math.cos(j*1.26),.07*Math.sin(j*1.26),.044,.024,.024,.006,red)}
else if(/burger/.test(k)){ringBody(g,[[.003,.084,.081],[.012,.10,.091],[.031,.103,.096]],'#c78946');e(0,0,.043,.104,.098,.019,'#69493a');for(let i=0;i<8;i++)e(.077*Math.cos(i*.785),.072*Math.sin(i*.785),.061,.033,.031,.006,green);ringBody(g,[[.064,.095,.089],[.070,.098,.092]],red);e(0,0,.081,.101,.094,.046,'#d8a25a');for(let j=0;j<8;j++)e(Math.cos(j*2.4)*.052,Math.sin(j*2.4)*.053,.121,.006,.003,.002,white)}
else throw new Error('No authored prop geometry: '+id+' / '+cat);}
function artURL(g,p,w,h,src,dir='north'){const [ti,draw]=tile(c=>{if(images[src]?.complete&&images[src].naturalWidth){const im=images[src],ratio=im.naturalWidth/im.naturalHeight*h/w,dw=256*Math.min(1,ratio),dh=256*Math.min(1,1/ratio);c.drawImage(im,(256-dw)/2,(256-dh)/2,dw,dh)}});textface(g,p,w,h,ti,dir);inputs.push([src,draw])}
// The scale sits on the floor. Its LCD is part of the front lip, angled towards a standing player.
function scaleDisplay(g,k){
 const front=-.305,rear=-.161,z0=.063,z1=.139,x=.212;
 const shell=[[-x,front,.004],[x,front,.004],[-x,rear,.004],[x,rear,.004],
              [-x,front,z0],[x,front,z0],[-x,rear,z1],[x,rear,z1]];
 mesh('scale_lcd_housing',g,shell,[[0,2,3,1],[4,5,7,6],[0,1,5,4],[2,6,7,3],[0,4,6,2],[1,3,7,5]],steel);
 let last;const reading=()=>RULES.draws[k]||'0 kg', [ti,paint]=tile(c=>{
  last=reading();c.save();c.scale(W/512,W/192);
  c.fillStyle='#10261e';c.fillRect(0,0,512,192);c.fillStyle='#fff3bf';c.textAlign='left';c.textBaseline='alphabetic';
  const n=last.replace(/\s*kg$/i,'');c.font='bold 176px Arial, sans-serif';const nw=c.measureText(n).width;
  c.font='bold 80px Arial, sans-serif';const uw=c.measureText('kg').width,left=(512-nw-uw-18)/2;
  c.font='bold 176px Arial, sans-serif';c.fillText(n,left,158);c.font='bold 80px Arial, sans-serif';c.fillText('kg',left+nw+18,155);c.restore();
 });
 // Inset the glass on the slope; it is not a floating caption or an inventory display.
 face(g,[0,(front+rear)/2,(z0+z1)/2+.0007],[.195,0,0],[0,(rear-front)*.452,(z1-z0)*.452],ti);
 painter.push(()=>{if(reading()===last)return false;paint();return true});
}
function display(g,k,p,w,h,dir='north'){let prev=null;const make=c=>{c.fillStyle='#233a34';c.fillRect(0,0,W,W);txt(c,(N[k]?.label||'').toUpperCase().slice(0,22),49,20,'#d4e3ce');txt(c,RULES.draws[k]||(N[k]?.kind==='reveal'&&RULES.flags.paper_in?RULES.ink:'')||(N[k]?.kind==='scale'?'0 kg':'—'),145,59,'#f6e6ab')};let [ti,draw]=tile(make);textface(g,p,w,h,ti,dir);painter.push(()=>{let v=RULES.draws[k]+'|'+RULES.ink+'|'+!!RULES.flags.paper_in;if(v!==prev){prev=v;draw();return true}})}
const mixColor={red,blue,yellow,orange:'#de8b3f',green:'#548953',purple:'#875796',brown:'#80573d',empty:'#eee6cc'};
function diagram(g,o){const key=o.design;
if(key==='figures'){
 const src=SINGLE.art[o.texture],width=1.48,height=width*251/1123;
 B(g,0,0,0,width+.03,.035,height+.03,dark);
 for(let i=0;i<4;i++){
  const [ti,draw]=tile(c=>{const im=images[src];if(im?.naturalWidth){c.drawImage(im,2.56-i*250.88,2.56,4*250.88,250.88)}});
  textface(g,[(i-1.5)*width/4,-.021,0],width/4,height,ti);inputs.push([src,draw])
 }
 return
}
let ti=tile(c=>{if(key==='clock'){c.strokeStyle=black;c.lineWidth=5;c.beginPath();c.arc(128,128,108,0,7);c.stroke();for(let j=1;j<=12;j++){c.fillStyle=black;c.font='21px sans-serif';c.textAlign='center';c.fillText(j,128+86*Math.sin(j*Math.PI/6),128-86*Math.cos(j*Math.PI/6))}for(let [angle,len] of [[300,76],[55,48]]){c.beginPath();c.moveTo(128,128);c.lineTo(128+len*Math.sin(angle*Math.PI/180),128-len*Math.cos(angle*Math.PI/180));c.stroke()}}
else if(key==='dollhouse'){txt(c,'DOLL HOUSE',22,22);for(let j=0;j<3;j++)for(let k=0;k<3;k++){c.fillStyle=k<[2,3,1][j]?'#f1be45':'#525b55';c.fillRect(35+k*67,49+j*60,46,39)}}
else if(key==='pots'){txt(c,'PLANTING PLAN · N ↑',22,20);for(let x=0;x<3;x++)for(let y=0;y<3;y++){c.fillStyle=N['rug_tile_'+x+y].color;c.fillRect(42+y*57,50+x*57,56,56);c.strokeStyle=green;c.strokeRect(42+y*57,50+x*57,56,56);if(SINGLE.groups.pots.targets.includes('rug_tile_'+x+y)){c.fillStyle='#268c33';c.beginPath();c.arc(70+y*57,78+x*57,17,0,7);c.fill()}}}

else if(key==='paint'){txt(c,'COLOUR SAMPLES',29,21);Object.values(SINGLE.groups.paint.answer).forEach((clr,j)=>{c.fillStyle=mixColor[clr];c.fillRect(95,62+57*j,102,35);c.fillStyle=black;c.font='24px sans-serif';c.fillText(j+1,58,86+j*57)})}
})[0];B(g,0,0,0,.92,.035,.67,dark);textface(g,[0,-.02,0],.89,.64,ti)}
for(const o of Object.values(N)){let k=o.id,t=o.kind,g=G(k,o.p,k),p=o.p;let at=[0,0,.045];if(!['item','note','exit'].includes(t))labels[k]=cn?o.labelZh:o.label;else labels[k]=cn?o.labelZh:o.label;
if(t==='item'){const start=verts.length;prop(g,k,o.form,o.colour?mixColor[o.colour]||teal:teal);
 let low=Infinity;for(let i=start+2;i<verts.length;i+=5)low=Math.min(low,verts[i]);if(Number.isFinite(low)){propBottom[k]=low;
 if(!o.container&&!o.buried&&!o.insideItem){const support=tabletops.find(([x,y,X,Y,z])=>p[0]>=x&&p[0]<=X&&p[1]>=y&&p[1]<=Y&&Math.abs(p[2]-z)<.065);
 if(support||Math.abs(p[2])<.05){p[2]=(support?support[4]:0)-low;initial[g][0][2]=p[2]}}}if(k==='bottle'&&L===37){const inside=G('key_seen_at_bottom',p,'bottle');prop(inside,'exitkey','key');move(inside,s=>({p:pos(s,'bottle').map((v,i)=>v+(i===2?.022:0)),r:[0,-69,0],on:s.canSee('bottle')&&!s.flags['show:bottle']}))}if(k==='ink'){const page=G('lit-letter',p,k);textface(page,[0,0,.02],.198,.15,label('','7396',''), 'table');move(page,s=>({p:pos(s,k),on:!!s.flags.lit}))}
if(SINGLE.jugs[k]){
 const r=k==='jug5'?.09:.072,h=k==='jug5'?.24:.173;
 const [ti,paint]=tile(c=>{c.fillStyle='#fff2cf';c.fillRect(0,0,256,256);txt(c,SINGLE.jugs[k]+' L',91,82,'#182f32');txt(c,(cn?'水量 ':'Fill ')+(RULES.fills[k]||0)+' L',192,36,'#2c4244')});
 wrapLabel(g,[[.023,r*.90,r*.90],[h*.85,r*1.08,r*.93]],28,-7,4,h*.22,h*.80,ti);
 let old;painter.push(()=>{if(old===RULES.fills[k])return false;old=RULES.fills[k];paint();return true});}
at=[0,0,(/key|ruler|mirror|blank_paper|scraper/.test(k)?.021:.075)]}
else if(t==='note'){let cc=o.colour&&mixColor[o.colour]||({pink:'#e6a6bb',white:'#f4f1da'})[o.colour]||white;B(g,0,0,.005,.213,.17,.011,cc);let ti=label('FIELD NOTE',o.displayText||o.label||'NOTE',o.text.slice(0,24),cc);textface(g,[0,0,.012],.21,.166,ti,'table');at=[0,0,.013]}
else if(t==='exit'){B(g,0,0,0,.91,.074,2.06,green);for(let z of [-.43,.47])B(g,0,-.046,z,.73,.028,.77,'#779483');B(g,.31,-.09,0,.14,.067,.039,gold);B(fix,.16,6.06,1.08,.075,.1,2.18,white);B(fix,1.14,6.06,1.08,.075,.1,2.18,white);textface(g,[0,-.067,.55],.32,.17,label('EXIT','↗',''), 'north');at=[0,-.06,.22]}
else if(t==='drawer'||t==='chest'){let y=o.p[1];if(t==='drawer'){
 PME_DRAWERS.tray((...args)=>B(g,...args),wood,gold)
}else{const h=p[2]-.034;B(g,0,.006,-p[2]+h/2,.88,.826,h,k.includes('red_box')?'#974c3f':'#927253');B(g,0,.008,-.012,.88,.832,.045,wood);for(let x of [-.425,.425])B(g,x,.02,.05,.035,.87,.16,wood);B(g,0,.43,.05,.86,.04,.16,wood);B(g,0,-.40,.045,.87,.045,.14,wood)}if(t==='drawer'){move(g,s=>({p:[p[0],p[1]-(s.open[k]?PME_DRAWERS.travel:0),p[2]]}))}else{let leaf=G('cover_'+k,[p[0],p[1]+.44,p[2]+.157],k);B(leaf,0,-.428,0,.92,.876,.05,k.includes('red_box')?'#a34a3b':green);B(leaf,0,-.79,.037,.18,.035,.029,gold);move(leaf,s=>({r:[s.open[k]?-80:0,0,0]}));}at=[0,-.4,.055];obstacles.push([p[0]-.45,p[1]-.42,p[0]+.45,p[1]+.44])}
else if(t==='rotator'&&o.g.group==='pipes'){const [ti,paint]=tile(c=>{c.fillStyle='#e1ddcb';c.fillRect(0,0,256,256);let a=SINGLE.groups.pipes.connectivity.tiles[k].ports,dirs=['N','E','S','W'];c.lineCap='round';for(const p of a){let ix=(dirs.indexOf(p)+4-RULES.turn[k])%4;c.beginPath();c.strokeStyle='#43776b';c.lineWidth=28;c.moveTo(128,128);c.lineTo([128,256,128,0][ix],[0,128,256,128][ix]);c.stroke()}});B(g,0,0,0,.272,.055,.272,steel);textface(g,[0,-.032,0],.261,.261,ti);let old=-1;painter.push(()=>{if(old!==RULES.turn[k]){old=RULES.turn[k];paint();return true}});at=[0,-.034,0]}
else if(t==='rotator'){prop(g,k,'toy_');const goalYaw=({office_fig_shark:-133,office_fig_horse:-46,office_fig_turtle:-180,office_fig_dino:-207,office_fig_fish:-180})[k];
move(g,s=>({r:[0,0,L===6&&goalYaw!==undefined?goalYaw-90*(s.turn[k]-o.g.target):-90*s.turn[k]]}));at=[0,0,.07]}
else if(t==='light'){B(g,0,0,0,.25,.04,.25,'#41494e');const lamp=G('lit_'+k,[...p],k);B(lamp,0,-.025,0,.225,.014,.225,'#f3d168');move(lamp,s=>({on:s.cell[k.slice(6)]}));at=[0,-.036,0]}
else if(L===9&&t==='plate'){
 B(fix,p[0],p[1],.016,.53,.53,.032,black);B(g,0,0,0,.45,.45,.029,o.color);
 for(let i=-2;i<=2;i++)B(g,0,i*.064,.015,.30,.009,.003,steel);
 move(g,s=>({p:[p[0],p[1],p[2]-(plateDown(s)?.020:0)]}));
 B(fix,p[0],p[1]-.245,.035,.16,.024,.006,'#615545');
 const led=G('plate-active',[p[0],p[1]-.245,.042],k,false);B(led,0,0,0,.16,.024,.009,'#63db77');move(led,s=>({on:plateDown(s)}));at=[0,0,.014]
}
else if(t==='slot'||t==='tile'||t==='plate'){let sz=(t==='plate'?.45:(k.startsWith('board_')||k.includes('tile')?.37:.26)),cc=o.color||'#bcaf84';if(k.startsWith('mat_')&&L===11)cc=[red,blue,green,yellow][Number(k.slice(4))-1];B(g,0,0,0,sz,sz,.029,cc);if(t==='slot'&&o.g.group==='laser'){B(g,0,0,.070,.028,.028,.115,steel);B(g,0,0,.125,.052,.041,.018,black);B(g,0,0,-.24,.065,.065,.46,steel);B(g,0,0,-.46,.27,.24,.046,dark)}if(o.star||t==='plate'||(t==='slot'&&['family','laser','trays'].includes(o.g.group))){let stamp=label('',o.star?'★':t==='plate'?'▦':k.replace('office_stand_','').replace('mat_','').replace('tray_','').toUpperCase(),'',o.star?'#dfbfa8':'#ddd8c3');textface(g,[0,0,.019],sz*.86,sz*.86,stamp,'table')}at=[0,0,.021]}
else if(t==='paint_bowl'){
 flaredVessel(g,[[.005,.052,.052],[.023,.082,.082],[.073,.123,.123],[.126,.145,.145]],'#e4dbc4');
 let fill=G('mix_'+k,p,k),[ti,paint]=tile(c=>{c.fillStyle=mixColor[RULES.colour(k)];c.fillRect(0,0,W,W)});
 shallowPool(fill,.124,.086,ti);move(fill,s=>({on:s.colour(k)!=='empty'}));
 let old=null;painter.push(()=>{let v=RULES.colour(k);if(old!==v){old=v;paint();return true}});
 B(g,0,-.130,.047,.080,.012,.055,'#dfcfaa');textface(g,[0,-.138,.047],.064,.047,label('',k.slice(-1),''));at=[0,-.052,.073]
}
else if(t==='scale'){B(g,0,0,.035,.43,.36,.07,steel);B(g,0,0,.08,.39,.32,.035,'#697d75');scaleDisplay(g,k);at=[0,-.233,.102]}
else if(t==='ottoman'){
 const H=o.p[2];B(g,0,0,-H+.035,.47,.46,.07,dark);B(g,0,0,-.14,.46,.45,.032,wood);for(const side of [-1,1]){B(g,side*.232,0,-H/2+.035,.026,.48,H-.07,'#896b56');B(g,0,side*.227,-H/2+.035,.45,.026,H-.07,'#896b56')}
 const cap=G('cover_'+k,[p[0],p[1]+.24,p[2]+.053],k);B(cap,0,-.24,0,.50,.50,.108,'#b58964');move(cap,s=>({r:[s.open[k]?-86:0,0,0]}));obstacles.push([p[0]-.25,p[1]-.25,p[0]+.25,p[1]+.25]);at=[0,-.23,.06]}
else if(t==='measure'){B(g,0,0,0,(o.size?.[0]||.35),(o.size?.[1]||.03),.012,'#d4a33a');at=[0,0,.009]}
else if(k==='doorplate'&&(L===30||L===35)){
 if(L===30){groups[g][1]=ids['office_red_box@1'];initial[g][0]=[0,-.4225,.045]}
 B(g,0,-.001,0,.27,.002,.103,'#6f6756');
 const ti=tile(c=>{c.fillStyle='#eee4c8';c.fillRect(0,0,256,256);txt(c,o.displayText,128,98,'#292e28')})[0];
 textface(g,[0,-.0024,0],.262,.095,ti);at=[0,-.0025,0]}
else if(t==='sign'){let dir=o.orientation||'north';if(o.design){diagram(g,o)}else if(o.texture){artURL(g,[0,0,0],.78,.42,SINGLE.art[o.texture],dir)}else if(L===21&&['switch','window','bus','deer'].includes(k)){
 const ti=tile(c=>{txt(c,({switch:'▲',window:'●',bus:'■',deer:'✚'})[k],128,162,'#343e39')})[0];textface(g,[0,0,0],.14,.14,ti,dir)
}else{textface(g,[0,0,0],.55,.255,label('',o.displayText||o.text||o.label,''),dir)}at=[0,0,0]}
else if(t==='reveal'&&k==='office_typewriter'){initial[g][1][2]=-90;B(g,0,0,.062,.48,.34,.12,green);for(let j=0;j<2;j++)for(let h=0;h<5;h++)B(g,-.17+h*.08,-.095+j*.066,.136,.05,.046,.026,white);B(g,0,.106,.162,.44,.053,.056,black);const paper=G('out_'+k,p,k);groups[paper][1]=g;initial[paper][0]=[0,0,0];B(paper,0,.12,.29,.32,.025,.27,white);const [ti,draw]=tile(c=>{c.fillStyle='#f5ecd5';c.fillRect(0,0,256,256);c.strokeStyle='#cac0a6';c.strokeRect(12,15,232,225);txt(c,RULES.ink||'',140,52,'#303b36')});
 textface(paper,[0,.107,.29],.31,.255,ti);let old;painter.push(()=>{if(old===RULES.ink)return false;old=RULES.ink;draw();return true});move(paper,s=>({on:s.flags.paper_in}));at=[-.089,0,.135]}
else if(t==='uvwall'){
 const outer='#d6cdbb',inside='#aa9d87',W=.92,D=.55,H=1.80;B(g,0,0,.061,W,D,.122,dark);
 B(g,0,-.253,.94,W,.045,H-.12,inside);for(const u of [-1,1])B(g,u*.447,0,.94,.031,D,H-.12,outer);
 B(g,0,0,H,W,.57,.045,outer);B(g,0,0,.135,.89,.54,.029,inside);
 const uv=G('uv-writing',[p[0],p[1]-.225,1.19],k,false);textface(uv,[0,0,0],.43,.17,tile(c=>{c.fillStyle=inside;c.fillRect(0,0,256,256);txt(c,o.value,128,84,'#543679')})[0],'south');
 move(uv,s=>({on:!!s.open[k]&&!!s.draws[k]}));N.wardrobe_leaf={id:'wardrobe_leaf',kind:'wardrobe_door',p:[p[0]+.44,p[1]+.28,0],label:'Wardrobe door',labelZh:'衣柜门'};labels.wardrobe_leaf=cn?'衣柜门':'Wardrobe door';
 const door=G('wardrobe_leaf',N.wardrobe_leaf.p,'wardrobe_leaf');B(door,-.44,0,.962,.888,.039,1.66,outer);B(door,-.44,.022,.969,.783,.012,1.47,'#c7baa3');B(door,-.78,.052,1.00,.029,.043,.149,gold);
 move(door,s=>({r:[0,0,s.open[k]?-90:0]}));obstacles.push([p[0]-.46,p[1]-.275,p[0]+.46,p[1]+.30]);at=[0,-.22,1.19]}
else if(k==='office_notepad'){B(g,0,0,.010,.288,.213,.019,'#897552');B(g,.003,0,.034,.27,.204,.035,'#f6edcc');for(let a of [-.07,-.035,0,.035,.07])rod(g,[-.127,a,.026],[-.127,a,.061],.003,black);
 let old=null,[ti,paint]=tile(c=>{c.fillStyle='#f4ecd8';c.fillRect(0,0,W,W);txt(c,'MEMO',43,22);c.strokeStyle='#b4c1b9';for(let i=0;i<5;i++){c.beginPath();c.moveTo(20,78+32*i);c.lineTo(236,78+32*i);c.stroke()}if(RULES.draws[k])txt(c,RULES.draws[k],136,54,'#675d53')});
 textface(g,[.004,0,.054],.259,.198,ti,'table');painter.push(()=>{if(old!==RULES.draws[k]){old=RULES.draws[k];paint();return true}});at=[0,0,.055]}
else if(k==='office_tv'){
 initial[g][1][2]=-90;B(g,0,0,.009,.27,.143,.018,black);B(g,0,.008,.05,.058,.041,.082,'#54625e');
 B(g,0,.006,.24,.58,.044,.342,'#25312f');const [ti,paint]=tile(c=>{c.fillStyle=RULES.draws[k]?'#233e4b':'#1e292b';c.fillRect(0,0,256,256);if(RULES.draws[k]){txt(c,cn?'无线电广播':'BROADCAST',65,22,'#c4dfdb');txt(c,RULES.draws[k],151,73,'#fff0bf')}});
 textface(g,[0,-.0165,.246],.549,.302,ti);let prev;painter.push(()=>{if(prev===RULES.draws[k])return false;prev=RULES.draws[k];paint();return true});B(g,.235,-.017,.082,.014,.005,.006,gold);at=[-.017,0,.246]}
else if(t==='camera'&&k==='sign_far'){
 const garden=tile(c=>{c.fillStyle='#b7d2d7';c.fillRect(0,0,256,256);c.fillStyle='#8baf86';c.fillRect(0,114,256,142);c.fillStyle='#698d66';for(let i=0;i<8;i++){c.beginPath();c.arc(8+36*i,124,24+i%3*5,0,7);c.fill()}c.fillStyle='#b0b690';c.fillRect(0,192,256,64)})[0];
 textface(fix,[6.723,3.86,1.73],1.50,1.045,garden,'east');
 B(g,.0005,0,-.185,.001,.022,.37,'#746447');B(g,0,0,0,.0016,.32,.166,wood);
 const [ti,draw]=tile(c=>{c.fillStyle='#eae3c9';c.fillRect(0,0,256,256);txt(c,cn?'花园':'GARDEN',60,31,'#354a39');txt(c,o.value,158,RULES.draws[k]?76:7,'#354a39')});
 textface(g,[-.0011,0,0],.305,.152,ti,'east');let old;painter.push(()=>{if(old===RULES.draws[k])return false;old=RULES.draws[k];draw();return true});at=[-.001,0,0]}
else if(t==='reveal'||t==='screen'||t==='camera'){B(g,0,0,t==='uvwall'?.35:.085,t==='uvwall'?.58:.38,.15,t==='uvwall'?.78:.17,t==='screen'||t==='camera'?black:wood);display(g,k,[0,-.08,t==='uvwall'?.36:.09],t==='uvwall'?.5:.34,t==='uvwall'?.26:.13);at=[0,-.08,t==='uvwall'?.36:.09]}
else if(t==='sink'){
 const en='#dfdfcc',inside='#a4b8ac';B(g,0,0,.035,.43,.32,.055,inside);B(g,0,-.15,.085,.43,.027,.13,en);B(g,0,.15,.085,.43,.028,.13,en);for(let a of [-1,1])B(g,a*.201,0,.085,.028,.29,.13,en);
 for(let a of [-1,1]){B(g,a*.207,0,.153,.037,.34,.016,steel);B(g,0,a*.156,.153,.43,.032,.016,steel)}
 rod(g,[.127,.13,.15],[.127,.13,.359],.012,steel);rod(g,[.127,.13,.359],[.127,.013,.359],.012,steel);rod(g,[.127,.013,.359],[.127,.013,.324],.014,steel);rod(g,[.083,.13,.214],[.168,.13,.214],.009,blue);
 ringBody(g,[[.063,.023,.023],[.066,.023,.023]],steel);for(let i=-1;i<=1;i++)B(g,i*.008,0,.068,.003,.021,.002,black);at=[0,-.15,.11]
}
else if(t==='jug_fill'||t==='jug_goal'){
 const source=t==='jug_fill',r=source?.154:.132,z=source?.231:.174,c=source?'#7896a1':'#b0b9b6';
 flaredVessel(g,[[.007,r*.75,r*.75],[.025,r*.80,r*.80],[z-.014,r,r],[z,r,r]],c);archedHandle(g,r,z*.76,'#6d7877',!source);
 for(let j of [.038,z-.034])hoop(g,r*(.76+.23*j/z),r*(.76+.23*j/z),j,.0035,steel);
 if(source)shallowPool(g,r*.94,z-.031,tile(c=>{c.fillStyle='#81aebe';c.fillRect(0,0,W,W)})[0]);
 else{
  const amount=o.g.need+' L';
  const ti=tile(c=>{c.fillStyle='#fff9dc';c.fillRect(0,0,256,256);c.fillStyle='#151b19';c.font='bold 180px Arial, sans-serif';c.textAlign='center';c.textBaseline='alphabetic';c.fillText(amount,128,194,226)})[0];
  wrapLabel(g,[[.025,r*.80,r*.80],[z-.014,r,r]],32,16,4,.043,.134,ti);
  labels[k]=(cn?o.labelZh+' · 目标 ':o.label+' · Target: ')+amount
 }
 at=[0,-r*.8,z*.65]
}
else if(t==='dig'||t==='jug_empty'){prop(g,'plant','pot_plant');at=[0,.02,.155]}
else if(t==='jar'){
 ringBody(g,[[.008,.093,.093],[.028,.102,.102],[.134,.107,.107],[.17,.084,.084],[.182,.068,.068]],'#92aca2',28,false);ringBody(g,[[.179,.071,.071],[.194,.077,.077],[.211,.074,.074]],'#9a7c58',28);
 for(let j of [.186,.194,.201])hoop(g,.075,.075,j,.002,'#6e624d');at=[0,0,.15]
}
else if(t==='lamp'){E(g,0,0,.035,.13,.13,.03,black);B(g,0,0,.16,.032,.032,.26,gold);E(g,0,0,.32,.14,.13,.066,green);at=[0,0,.30]}
else if(t==='socket'){B(g,0,0,0,.22,.05,.28,green);textface(g,[0,-.028,0],.18,.16,label('POWER','+ / −','CELL'));at=[0,-.029,0]}
aims[k]=at;if(t==='measure')labels[k]=(cn?'标记的边':'Marked edge');if(t==='item'||o.container)move(g,s=>({p:pos(s,k),on:s.canSee(k)}));if(SINGLE.jugs[k])move(g,s=>({p:pos(s,k),r:[0,0,N[s.stock[k]]?.g?.group==='trays'?-90:0],on:s.canSee(k)}));if(k==='mirror')move(g,s=>{const stand=N[s.stock[k]];
 if(stand?.g?.group==='laser'){const faceOffset=.023*Math.SQRT1_2;
  return {p:[stand.p[0]+faceOffset,stand.p[1]-faceOffset,.68],on:s.canSee(k),r:[-90,0,45]}}
 return {p:pos(s,k),on:s.canSee(k),r:[0,0,0]}});if(t==='jar')move(g,s=>({on:!s.flags['show:jar']}));
}
if(L===2){for(const o of SINGLE.decor.primitives){let [x,y,z]=o.pos,p=[2.5+(x-2.7)*1.8,2.8+(y-17.2)*1.8,z*1.8];B(fix,...p,...o.size.map(v=>v*1.8),o.color)}}
if(L===4){const shelfX=t=>3.06+1.07*t;for(let t=0;t<2;t++){let x=shelfX(t),y=5.76;for(let z of [.28,.70,1.12,1.57])B(fix,x,y,z,1.00,.45,.046,wood);for(let a of [-1,1])B(fix,x+a*.50,y,.814,.044,.45,1.628,dark);obstacles.push([x-.522,y-.225,x+.522,y+.225])}
for(let o of SINGLE.decor.primitives){let t=o.k.startsWith('decor_shR')?1:0,base=t?3.8:3.15,x=shelfX(t)+(o.pos[0]-base)*1.82;let bottom=o.pos[2]-o.size[2]/2;let baseZ=bottom>.90?1.594:bottom>.59?1.143:bottom>.25?.723:.303;B(fix,x,5.72,baseZ+o.size[2]*.85,o.size[0]*1.8,o.size[1]*1.25,o.size[2]*1.7,o.color)}}
if([10,39].includes(L)){textface(fix,[2.85,5.95,2.0],.25,.17,label('','IN →',''));textface(fix,[3.70,5.95,.94],.36,.16,label('','↓ OUT',''))}
if(L===12){prop(G('food',[.49,1.75,.91],'pizza'),'pizza','pizza');prop(G('plantvis',[3.6,1.25,0],'floor plant'),'plant','pot');for(let z of [.21,.68,1.22])B(fix,3.14,5.72,z,1.12,.41,.045,wood);for(let t of [-1,1])B(fix,3.14+t*.56,5.72,.83,.06,.41,1.32,dark);prop(G('mugvis',[3.03,5.67,.708],'cup on the shelf'),'mug','mug');const bin=G('wastebasket',[4.8,2.2,0],'wastebasket');flaredVessel(bin,[[.009,.106,.105],[.034,.113,.112],[.319,.151,.15]],'#637b73');chair(1.13,2.0);obstacles.push([2.54,5.5,3.75,5.95],[4.63,2.04,4.97,2.36])}
if(L===20){for(let [i,k] of ['pizza','burger','soda','coffee'].entries())prop(G('food'+i,[i%2?.48:6.22,i<2?2.85:4.3,.915],k),k,k==='soda'?'can_of_soda':k,k==='coffee'?'#ae6c59':steel)}
if(L===25){
const targets=[[2.0,5.985,1.35,'north'],[.065,3.1,1.45,'west'],[4.55,.12,1.4,'south'],[6.65,2.27,1.7,'east']],centre=[[2.5,.66],[6.19,1.0],[6.19,4.5],[4.75,5.55]],z0=[.91,.91,.91,.99];table(2.5,.66,.65,.6,.91);for(let j=0;j<4;j++){let [x,y,z,dir]=targets[j],n='8527'[j];textface(fix,[x,y,z],.27,.31,label('',n,''),dir);
let [a,b]=centre[j],h=.15+j*.053,g=G('sculpt'+j,[a,b,z0[j]],'bust');B(g,0,0,.034,h*1.2,h*.99,.064,wood);E(g,0,0,.067+h*.55,h*.65,h*.51,h*.54,'#a4a9a1');E(g,0,0,.08+h*1.28,h*.47,h*.45,h*.55,'#bcc1b7');const dx=x-a,dy=y-b,l=Math.hypot(dx,dy);E(g,dx/l*h*.47,dy/l*h*.47,.08+h*1.28,.035,.035,.034,'#a9aca2');for(let side of [-1,1])E(g,dx/l*h*.39-dy/l*side*h*.18,dy/l*h*.39+dx/l*side*h*.18,.09+h*1.43,.012,.012,.011,black)}
for(let [x,y,z,dir,digit] of [[5.4,6.01,1.5,'north','3'],[3.15,.09,1.63,'south','1'],[.065,4.4,1.65,'west','6']])textface(fix,[x,y,z],.27,.31,label('',digit,''),dir)}
if(L===21){const [sx,sy,sz]=N.switch.p;B(fix,sx,sy-.012,sz+.23,.125,.027,.164,'#ded9cb');B(fix,sx,sy-.034,sz+.23,.071,.020,.110,'#665e50');B(fix,sx,sy-.049,sz+.234,.058,.017,.086,white);framePic(2.87,.061,1.9,'south','BUS');framePic(5.4,.06,1.52,'south','DEER')}
if(L===28)framePic(4.02,.058,1.52,'south','DEER');
if(L===19||L===34){B(fix,.81,2.71,.5,.21,.16,.35,black);B(fix,.86,2.71,.68,.23,.15,.1,black);const laser=SINGLE.groups.laser,correct=laser.order[laser.correct],rx=N[correct].p[0],ry=4.03,beamZ=.68,faceY=ry-.105;
const receiver=G('receiver',[rx,ry,0],'');B(receiver,0,0,.028,.32,.26,.056,dark);B(receiver,0,.012,.33,.054,.05,.58,steel);
 B(receiver,0,0,beamZ,.34,.15,.27,'#465457');B(receiver,0,-.08,beamZ,.285,.020,.215,black);
 B(receiver,0,-.012,.458,.40,.03,.103,'#e7dcc4');textface(receiver,[0,-.029,.458],.39,.098,tile(c=>{c.fillStyle='#efe6cb';c.fillRect(0,0,256,256);txt(c,cn?'红外接收器':'IR RECEIVER',128,42)})[0]);
 obstacles.push([rx-.16,ry-.13,rx+.16,ry+.13]);for(const [id,color,on] of [['sensorLed','#ef4138',false],['sensorOn','#52df77',true]]){const lamp=G(id,[rx,faceY+.014,beamZ],'');E(lamp,0,0,0,.079,.014,.079,color);move(lamp,s=>({on:(s.mat[correct]==='mirror')===on}))}}

if(L===16){for(let j=0;j<2;j++){B(fix,4.72+j*.81,.49,.48,.75,.7,.96,'#cad3cf');E(fix,4.72+j*.81,.86,.48,.25,.024,.25,black);E(fix,4.72+j*.81,.885,.48,.2,.012,.2,'#71939a')}obstacles.push([4.32,.13,5.9,.88])}
let fp=N[{"1": "office_scale", "2": "blocks", "3": "rug_tile_11", "4": "shelves", "5": "office_ottoman_1", "6": "office_fig_turtle", "7": "bowl_2", "8": "u5_tile_1_1", "9": "office_plate", "10": "pipe_tile_11", "11": "mat_2", "12": "hint", "13": "light_B2", "14": "board_sq_11", "15": "bottom_cabinet_nddvba_0@1", "16": "note", "17": "card", "18": "card", "19": "office_stand_2", "20": "menu", "21": "playlist", "22": "plan", "23": "card", "24": "rule", "25": "busts", "26": "office_toolbox_2@1", "27": "office_water_bucket", "28": "decor_u1_calendar", "29": "hint", "30": "doll_house", "31": "clock", "32": "clock", "33": "office_water_bucket", "34": "jar", "35": "office_typewriter", "36": "office_scale", "37": "plan", "39": "pipe_tile_11"}[L]]?.p||({2:[3.35,3.26,.2],4:[3.595,5.72,1.01],25:[4.75,5.55,1.37]})[L]||N.hint?.p||[2,5,.9],spawn=[3.4,2.08,1.35];if([1,9,36].includes(L))spawn=[3.45,3.1,1.35];if(L===5)spawn=[3.92,3.84,1.35];let dh=Math.hypot(fp[0]-spawn[0],fp[1]-spawn[1]);let initialPitch=clamp(Math.atan2(fp[2]-spawn[2],dh),-.73,.22);
initial.push(...meshes.map(()=>1));return {laserOrigin:SINGLE.groups.laser?[.976,2.71,.68]:null,groups,initial,meshes,ids,labels,verts:new Float32Array(verts),atlas,origin:spawn,yaw:90-Math.atan2(fp[0]-spawn[0],fp[1]-spawn[1])*180/Math.PI,initialPitch,bounds:[0,width,0,depth],obstacles,aims,dynamic,painter,inputs,images}
})();