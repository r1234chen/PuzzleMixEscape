(()=>{'use strict';
const $=s=>document.querySelector(s),zh=document.documentElement.lang==='zh-CN',T=(a,b)=>zh?b:a,cv=document.querySelector('.view>canvas'),gl=cv.getContext('webgl',{antialias:true,alpha:false});if(!gl){$('#entry').textContent=$('#msg').textContent=T('Enable WebGL to play.','请开启 WebGL。');return}
const unit=v=>{const n=Math.hypot(...v)||1;return v.map(a=>a/n)},dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0),sub=(a,b)=>a.map((v,i)=>v-b[i]),cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],bytes=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
const pipeline=(ctx,vs,fs)=>{const pr=ctx.createProgram();for(const [t,source] of [[ctx.VERTEX_SHADER,vs],[ctx.FRAGMENT_SHADER,fs]]){const sh=ctx.createShader(t);ctx.shaderSource(sh,source);ctx.compileShader(sh);if(!ctx.getShaderParameter(sh,ctx.COMPILE_STATUS))throw Error(ctx.getShaderInfoLog(sh));ctx.attachShader(pr,sh)}ctx.linkProgram(pr);if(!ctx.getProgramParameter(pr,ctx.LINK_STATUS))throw Error(ctx.getProgramInfoLog(pr));ctx.useProgram(pr);return pr};
const pr=pipeline(gl,'attribute vec3 p,n;attribute vec2 uv;uniform vec3 eye,side,up,fwd;uniform float aspect;varying vec2 st;varying float light;void main(){vec3 d=p-eye;float z=dot(d,fwd);gl_Position=vec4(dot(d,side)*1.7/aspect,dot(d,up)*1.7,z*1.002-.05,z);st=vec2(uv.x,1.-uv.y);light=.71+.31*abs(dot(normalize(n),vec3(.32,.4,.85)));}','precision mediump float;varying vec2 st;varying float light;uniform vec3 col;uniform float opacity;uniform sampler2D tex;void main(){gl_FragColor=vec4(texture2D(tex,st).rgb*light*col,opacity);}');
const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);for(const [id,n,off] of [['p',3,0],['uv',2,12],['n',3,20]]){let i=gl.getAttribLocation(pr,id);gl.enableVertexAttribArray(i);gl.vertexAttribPointer(i,n,gl.FLOAT,false,32,off)}gl.enable(gl.DEPTH_TEST);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.clearColor(.31,.36,.32,1);const uni=Object.fromEntries(['eye','side','up','fwd','aspect','col','opacity'].map(k=>[k,gl.getUniformLocation(pr,k)]));
const txt={},white=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,white);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGB,1,1,0,gl.RGB,gl.UNSIGNED_BYTE,new Uint8Array([255,255,255]));gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);
function upload(d){for(const [k,p] of Object.entries(d)){const im=new Image();im.onload=()=>{const t=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGB,gl.RGB,gl.UNSIGNED_BYTE,im);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);txt[k]=t;dirty=true};im.src='data:image/jpeg;base64,'+p}}
const eyeMat=[1,0,0,0,1,0,0,0,1,0,0,0],rads=Math.PI/180;
function combine(p,g){let [,par,,pos,r,sc]=g,[x,y,z]=r.map(v=>v*rads),A=Math.cos(x),B=Math.cos(y),C=Math.cos(z),i=Math.sin(x),j=Math.sin(y),k=Math.sin(z);
let l=[B*C,C*i*j-A*k,A*C*j+i*k,B*k,A*C+i*j*k,A*j*k-C*i,-j,B*i,A*B].map((v,n)=>v*sc[n%3]),o=[];for(let u=0;u<3;u++)for(let v=0;v<3;v++)o.push(p[u*3]*l[v]+p[u*3+1]*l[3+v]+p[u*3+2]*l[6+v]);for(let u=0;u<3;u++)o.push(p[u*3]*pos[0]+p[u*3+1]*pos[1]+p[u*3+2]*pos[2]+p[9+u]);return o}
let x=0,y=0,z=1.35,yaw=0,pitch=0,dirty=false,ready=false,busy=true,won=false,lost66=false,hit='',held=null,page=0,sel=0,keys=new Set(),R,mask,raw=[],data,batches=[],allTargets=[],worker,bag=[],dlg=$('dialog'),pending='';
const bars=[],slots=Array(9).fill(null),bar=$('#items'),layer=$('#gear');function say(t){$('#msg').textContent=t}function name(k){
 if(LEVEL_NO===11&&k==='filter_hatch_handle')return T('Inspection hatch switch','检修盖开关');
 if(LEVEL_NO===11&&k==='s2_setup')return T('Drain button','排水按钮');
 if(k.startsWith('turn::'))return T('Rotate / flip','旋转或翻面')+' · E';
 if(k.startsWith('take::'))return T('Take back · aim at the curved arrow to turn instead','取回 · 要转动请对准弯箭头');
 if(LEVEL_NO===18&&k==='s2_stack')return T('Take back top sheet','取回最上面的折页');return R?.labels[k]||k.replaceAll('_',' ')}
for(let i=0;i<9;i++){let b=document.createElement('button');b.type='button';b.className='slot';b.dataset.slot=i+1;b.innerHTML='<span>'+(i+1)+'</span>';b.onclick=()=>select(i);bar.append(b);bars.push(b)}
function select(i){sel=i;held=slots[i]||null;inventory();dirty=true}function inventory(){if(held&&!bag.includes(held))held=null;for(let i=0;i<9;i++){let k=bag[page*9+i]||null;slots[i]=k;bars[i].title=k?name(k):T('Empty','空');bars[i].setAttribute('aria-label',String(i+1)+' '+bars[i].title);bars[i].setAttribute('aria-pressed',String(i===sel));bars[i].dataset.item=k||''}$('#moreitems').hidden=bag.length<=9;paintGear()}
$('#moreitems').onclick=()=>{page=(page+1)%Math.ceil(bag.length/9);sel=0;held=bag[page*9]||null;inventory()};
let paintGear=()=>{};function prepGear(){
const h=layer.getContext('webgl',{alpha:true,antialias:true});if(!h)return;const prog=pipeline(h,'attribute vec3 p,c;uniform float angle;varying vec3 tint;void main(){float x=cos(angle)*p.x+sin(angle)*p.y,z=-sin(angle)*p.x+cos(angle)*p.y;gl_Position=vec4(.79*x+.61*p.z,-.61*x+.79*p.z,z*.8,1.);tint=c;}','precision mediump float;varying vec3 tint;void main(){gl_FragColor=vec4(tint,1.);}');const b=h.createBuffer();h.bindBuffer(h.ARRAY_BUFFER,b);for(const [k,off] of [['p',0],['c',12]]){let a=h.getAttribLocation(prog,k);h.enableVertexAttribArray(a);h.vertexAttribPointer(a,3,h.FLOAT,false,24,off)}h.enable(h.DEPTH_TEST);const loc=h.getUniformLocation(prog,'angle'),cache=new Map();
paintGear=(tm=0)=>{let rect=layer.getBoundingClientRect(),px=Math.min(2,devicePixelRatio||1),w=Math.round(rect.width*px),ht=Math.round(rect.height*px);if(!w||!ht)return;if(layer.width!==w||layer.height!==ht){layer.width=w;layer.height=ht}h.clearColor(0,0,0,0);h.clear(h.COLOR_BUFFER_BIT|h.DEPTH_BUFFER_BIT);slots.forEach((k,i)=>{if(!k)return;if(!cache.has(k)){let a=[],lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];R.meshes.forEach((me,j)=>{if(allTargets[j]!==k&&me[0]!==k)return;let v=raw[j],col=R.materials[me[3]][0];const mat=worldM[j]||eyeMat;for(let n=0;n<v.length;n+=8){let p=[0,1,2].map(l=>mat[3*l]*v[n]+mat[3*l+1]*v[n+1]+mat[3*l+2]*v[n+2]+mat[9+l]);for(let u=0;u<3;u++){lo[u]=Math.min(lo[u],p[u]);hi[u]=Math.max(hi[u],p[u])}a.push(...p,...col.map(c=>Math.pow(c,.55)*(.72+.23*Math.abs(v[n+7]))))}});let size=Math.max(...hi.map((v,j)=>v-lo[j]))||1;for(let j=0;j<a.length;j+=6)for(let l=0;l<3;l++)a[j+l]=(a[j+l]-(lo[l]+hi[l])/2)*1.75/size;cache.set(k,new Float32Array(a))}let ar=cache.get(k),r=bars[i].getBoundingClientRect(),size=Math.min(r.width,r.height)*px*.88;h.viewport((r.left+r.width/2-rect.left)*px-size/2,(rect.bottom-r.bottom+r.height/2)*px-size/2,size,size);h.bufferData(h.ARRAY_BUFFER,ar,h.STATIC_DRAW);h.uniform1f(loc,.57+(i===sel?.2*Math.sin(tm*.0016):0));h.drawArrays(h.TRIANGLES,0,ar.length/6);if(!ar.length)bars[i].lastChild.title=name(k)})};new ResizeObserver(()=>paintGear()).observe(bar)}prepGear();
function clearSwing(oldMask,grid){
if(!oldMask||grid.nx!==R.mask.nx||grid.ny!==R.mask.ny)return;
const w=grid.nx,h=grid.ny,ix=Math.round((x+.6)*16),iy=Math.round((y+.6)*16),st=iy*w+ix;
if(!mask[st]||oldMask[st])return;
const seen=new Set([st]),queue=[st];for(let i=0;i<queue.length;i++){const cell=queue[i],cx=cell%w,cy=Math.floor(cell/w);if(!mask[cell]){x=cx/16-.6;y=cy/16-.6;return}
for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]){const nx=cx+dx,ny=cy+dy,n=ny*w+nx;if(nx>=0&&ny>=0&&nx<w&&ny<h&&Math.abs(nx-ix)+Math.abs(ny-iy)<=16&&!seen.has(n)&&!oldMask[n]){queue.push(n);seen.add(n)}}}}

function doorwaySurface(name,v){
 const m=/^room_(A_east|B_west)_(wall|lower|rail|lintel)$/.exec(name);if(!m)return null;
 const a=m[1]==='A_east',part=m[2],lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
 for(let j=0;j<v.length;j+=8)for(let k=0;k<3;k++){lo[k]=Math.min(lo[k],v[j+k]);hi[k]=Math.max(hi[k],v[j+k])}
 const [xl,yl]=lo,[xr,yr]=hi,mid=(xl+xr)/2,x=a?xl:xr;
 const railBottom=1.0175,railTop=1.0625,head=2.32,top=2.8;
 const z0=part==='wall'?railTop:part==='rail'?railBottom:part==='lintel'?head:0,z1=part==='rail'?railTop:part==='lower'?railBottom:top;
 const out=[];function quad(P,Q,R,S,n){for(const p of [P,Q,R,P,R,S]){const u=n[0]?p[1]:p[0],v=n[2]?p[1]:p[2];out.push(...p,u,v,...n)}}
 quad([x,yl,z0],[x,yr,z0],[x,yr,z1],[x,yl,z1],[a?-1:1,0,0]);
 if(a&&part!=='lintel'){
  const lowY=yl>1,j=lowY?yl:yr,h=Math.min(z1,head);
  quad([xl,j,z0],[xr,j,z0],[xr,j,h],[xl,j,h],[0,lowY?-1:1,0])
 }
 if(part==='rail'){
  for(const [z,inset,nz] of [[z0,.0675,-1],[z1,.060,1]]){const inner=mid+(a?-1:1)*inset;
   quad([inner,yl,z],[x,yl,z],[x,yr,z],[inner,yr,z],[0,0,nz])}
 }else if(part==='lintel'&&a){
  quad([xl,yl,z0],[xl,yr,z0],[xr,yr,z0],[xr,yl,z0],[0,0,-1])
 }
 return new Float32Array(out)
}
function sampleRoomSurface(name,v){
 if(name==='sc_body'){
  const rest=[],front=[],apertures=[[.2,.5],[.6,.9],[1,1.3]];
  for(let i=0;i<v.length;i+=24){const tri=v.subarray(i,i+24);if([1,9,17].every(k=>Math.abs(tri[k]+.18)<1e-5))front.push(...tri);else rest.push(...tri)}
  if(!front.length)return v;
  let l=Infinity,r=-Infinity,b=Infinity,t=-Infinity;for(let i=0;i<front.length;i+=8){l=Math.min(l,front[i]);r=Math.max(r,front[i]);b=Math.min(b,front[i+2]);t=Math.max(t,front[i+2])}
  const y=front[1],quad=(x0,z0,x1,z1)=>{for(const [x,z] of [[x0,z0],[x1,z0],[x1,z1],[x0,z0],[x1,z1],[x0,z1]])rest.push(x,y,z,0,0,0,-1,0)};
  quad(l,b,-.418,t);quad(.418,b,r,t);let z=b;for(const [lo,hi] of apertures){quad(-.418,z,.418,lo+.002);z=hi-.002}quad(-.418,z,.418,t);
  return new Float32Array(rest)
 }
 return v
}
function clippedWall(v,height,above){
 const out=[],inside=p=>above?p[2]>=height:p[2]<=height;
 for(let i=0;i<v.length;i+=24){
  const tri=[v.subarray(i,i+8),v.subarray(i+8,i+16),v.subarray(i+16,i+24)],poly=[];
  for(let j=0;j<3;j++){const q=tri[(j+2)%3],p=tri[j];if(inside(q)!==inside(p)){const f=(height-q[2])/(p[2]-q[2]);poly.push(q.map((x,k)=>x+(p[k]-x)*f))}if(inside(p))poly.push(p)}
  for(let j=1;j+1<poly.length;j++)out.push(...poly[0],...poly[j],...poly[j+1])
 }return new Float32Array(out)
}
function fittedSurface(name,v,names){
 // Camp rack: hem ends 10 mm above the counter; keep the rings at their original rail height.
 if(LEVEL_NO===15&&name==='rope_check_tie'){
  // Reseat the button end of its linkage, keeping the elbow end fixed.
  for(let i=0;i<v.length;i+=8)v[i+1]+=.030*Math.max(0,Math.min(1,(-.045-v[i])/.355));
  return v
 }
 if(LEVEL_NO===15&&name==='real_cloth_curtain'){
  for(let i=2;i<v.length;i+=8)if(v[i]<0)v[i]=-.330;
  return v
 }
 // Keep the curved-arrow controls within the existing plate/knob boundaries, but readable and easy to target.
 const marks={28:['panel_mark_turn',.14,.080,1.8],42:['knob_mark_turn',0,-.022,1.65],43:['tile_mark_flip',.054,.025,1.6]};
 const mark=marks[LEVEL_NO];
 if(mark&&name===mark[0]){let cx=0,cz=0;for(let i=0;i<v.length;i+=8){cx+=v[i];cz+=v[i+2]}cx/=v.length/8;cz/=v.length/8;
  for(let i=0;i<v.length;i+=8){v[i]=mark[1]+(v[i]-cx)*mark[3];v[i+2]=mark[2]+(v[i+2]-cz)*mark[3];v[i+1]-=.001}return v}

 // A shallow drawer liner supports the tracing sheets above the front lip's shadow.
 if(LEVEL_NO===19&&name==='tracing_drawer_bottom'){
  for(let i=2;i<v.length;i+=8)if(v[i]>-.112)v[i]+=.080;
 }
 // Binding room: the lettering sits on the front edge of the middle shelf,
 // above the moving folder lid. Widen that edge into a solid wooden fascia.
 if(LEVEL_NO===18&&name==='rack_shelf'&&v[2]>.69&&v[2]<.75){
  for(let i=2;i<v.length;i+=8)if(v[i]<.72)v[i]=.658;
 }else if(LEVEL_NO===18&&name==='spine_join_hint'){
  for(let i=0;i<v.length;i+=8){v[i+1]=-.231;v[i+2]=.698+(v[i+2]-.48)*.82}
 }else if(LEVEL_NO===18&&name==='booklet_note_print'){
  // Use the spare margin at the hinge so the shelf cannot mask the title.
  for(let i=1;i<v.length;i+=8)v[i]-=.050;
 }
 // Level 66: keep the comb-case pull clear of the central adhesive seal.
 if(LEVEL_NO===16&&name==='comb_cover_pull'){for(let i=0;i<v.length;i+=8)v[i]+=.24;return v}
 if(LEVEL_NO>=23){const partition=doorwaySurface(name,v);if(partition)return partition}
 const m=/^(.+_(?:north|south|east|west))_(wall|lower)$/.exec(name);
 if(m&&names.has(m[1]+'_lower')&&names.has(m[1]+'_rail'))return clippedWall(v,m[2]==='wall'?1.0625:1.0175,m[2]==='wall');
 if((LEVEL_NO===7||LEVEL_NO===17)&&/^L_(?:inner|return)_[xy]$/.test(name))return clippedWall(v,LEVEL_NO===7?1.02:1.0625,true);
 if(LEVEL_NO===17&&/^L_lower_[xy]$/.test(name))return clippedWall(v,1.0175,false);
 if(LEVEL_NO===33&&name==='cradle_ring'){
  const out=[],rim=new Map();for(let i=0;i<v.length;i+=24){const tri=v.subarray(i,i+24);if(![2,10,18].every(k=>Math.abs(tri[k]-.006)<1e-5)){out.push(...tri);continue}
   for(let j=0;j<24;j+=8){const p=tri.subarray(j,j+8);if(Math.hypot(p[0],p[1])>.07)rim.set(p[0]+','+p[1],p)}
  }
  const edge=[...rim.values()].sort((a,b)=>Math.atan2(a[1],a[0])-Math.atan2(b[1],b[0])),inner=p=>[p[0]*.065/.075,p[1]*.065/.075,...p.slice(2)];
  for(let i=0;i<edge.length;i++){const a=edge[i],b=edge[(i+1)%edge.length];out.push(...a,...b,...inner(b),...a,...inner(b),...inner(a))}
  return new Float32Array(out)
 }
 if(LEVEL_NO===12&&(name==='reader_back'||name==='pipe_cabinet_back')){const f=name==='reader_back'?.56/.60:.69/.73;for(let i=0;i<v.length;i+=8)v[i]*=f}
 if(LEVEL_NO===2&&name==='light_table_leg'){
  let cx=0;for(let i=0;i<v.length;i+=8)cx+=v[i];cx/=v.length/8;
  for(let i=0;i<v.length;i+=8)v[i]+=cx<2.65?-.032:.032
 }
 if(LEVEL_NO===41){if(name==='cup_body')return displayVesselMesh();if(name==='sc_body')return sampleRoomSurface(name,v)}
 return v
}
function displayVesselMesh(){const a=[],n=20;const ring=(r,z,i)=>[r*Math.cos(i*2*Math.PI/n),r*Math.sin(i*2*Math.PI/n),z],tri=(p,q,r)=>{const v=unit(cross(sub(q,p),sub(r,p)));for(const pt of [p,q,r])a.push(...pt,.5,.5,...v)};
 const profiles=[[.035,.001],[.040,.008],[.045,.097],[.044,.100],[.040,.100],[.039,.095],[.032,.016]];
 for(let j=0;j<profiles.length-1;j++)for(let i=0;i<n;i++){let p=ring(...profiles[j],i),q=ring(...profiles[j],i+1),r=ring(...profiles[j+1],i+1),s=ring(...profiles[j+1],i);tri(p,q,r);tri(p,r,s)}
 for(let i=0;i<n;i++){tri([0,0,.001],ring(.035,.001,i+1),ring(.035,.001,i));tri([0,0,.016],ring(.032,.016,i),ring(.032,.016,i+1))}return new Float32Array(a)}

let cupDrawerHomeY;
function markDrawer(grid,lo,hi){
 const x0=Math.max(0,Math.ceil((lo[0]-.10+.6)*16)),x1=Math.min(grid.nx-1,Math.floor((hi[0]+.10+.6)*16)),y0=Math.max(0,Math.ceil((lo[1]-.10+.6)*16)),y1=Math.min(grid.ny-1,Math.floor((hi[1]+.10+.6)*16));
 for(let iy=y0;iy<=y1;iy++)mask.fill(1,iy*grid.nx+x0,iy*grid.nx+x1+1)
}
let cartPlateOrder='';
function cartPlate(j){
 const ids=['circle','star','square','leaf'];
 const colours=new Map(),lanes=[];
 for(const [nm,gi,,mi] of j.meshes){if(nm==='toy_body')colours.set(j.groups[gi][0],j.materials[mi][0])}
 for(const g of j.groups){if(/^car[1-4]$/.test(g[0]))lanes.push([g[3][0],+g[0].slice(3)-1])}
 const paint=ids.map(id=>colours.get('toy_'+id));if(lanes.length!==4||paint.some(c=>!c))return null;
 lanes.sort((a,b)=>a[0]-b[0]);const order=lanes.map(l=>l[1]).join('');
 if(order!==cartPlateOrder){
  const c=document.createElement('canvas');c.width=512;c.height=180;const p=c.getContext('2d');
  p.fillStyle='#e2dbc4';p.fillRect(0,0,512,180);p.lineWidth=3;p.strokeStyle='#292c29';
  lanes.forEach((l,i)=>{const x=14+53*i;p.fillStyle='rgb('+paint[l[1]].map(v=>Math.round(255*Math.pow(v,.69))).join(',')+')';p.fillRect(x,57,45,57);p.strokeRect(x,57,45,57)});
  p.fillStyle='#292c29';p.beginPath();p.moveTo(238,80);p.lineTo(273,80);p.lineTo(273,71);p.lineTo(294,87);p.lineTo(273,103);p.lineTo(273,94);p.lineTo(238,94);p.fill();
  for(let i=0;i<4;i++){p.strokeRect(309+49*i,57,42,57);p.fillRect(317+49*i,103,26,3)}
  const t=txt['cart-order-plate']||gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,c);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);txt['cart-order-plate']=t;cartPlateOrder=order
 }
 return paint
}
// Legible printing for the binding room only. Keep the cut edge strips intact:
// those incomplete marks are intentional and form a different clue in the cradle.
function bindingPrint(n,label){
 let key='binding:'+n+':'+label;if(txt[key])return key;
 const c=document.createElement('canvas');c.width=1024;
 const leaf=n.endsWith('_page_numbers'),note=n==='booklet_note_print';
 c.height=leaf?768:note?288:128;const p=c.getContext('2d');
 p.fillStyle=note?'#fff4d8':leaf?'#fff8e5':'#273b32';p.fillRect(0,0,c.width,c.height);
 p.textAlign='center';p.textBaseline='middle';
 function line(text,x,y,size,color,max){p.fillStyle=color;p.font='bold '+size+'px system-ui, sans-serif';p.fillText(text,x,y,max)}
 if(leaf){const m=/([0-9]+)\/([0-9]+)$/.exec(label);if(!m)return null;
  p.fillStyle='#ac8659';p.fillRect(502,125,16,518);
  line(m[1],250,384,344,'#192c26',438);line(m[2],766,384,344,'#192c26',438);
 }else if(note){
  line(T('BOOKLET  /  PAGES 1–12','小册子  /  第 1–12 页'),512,54,67,'#182d25',956);
  p.fillStyle='#b99561';p.fillRect(55,98,914,5);
  line(T('Each outer sheet wraps the inner ones.','外层折页包住内层折页。'),512,151,56,'#222c25',962);
  line(T('Nest the sheets: outside → inside','套叠顺序：由外到内'),512,234,63,'#182d25',954);
 }else{line(T('JOIN THE BRANCH','拼接书脊上的树枝'),512,64,92,'#fff5d9',928)}
 const tex=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,tex);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGB,gl.RGB,gl.UNSIGNED_BYTE,c);
 // These sizes need clamp + linear filtering in WebGL 1.
 for(const axis of [gl.TEXTURE_WRAP_S,gl.TEXTURE_WRAP_T])gl.texParameteri(gl.TEXTURE_2D,axis,gl.CLAMP_TO_EDGE);
 gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);txt[key]=tex;return key;
}
// The loose sheets have ink, trim and registration marks but no pane between
// them. Add a real, translucent two-triangle sheet, used by draw AND pick.
// Laundry inspection unit: add stationary mounting hardware without moving the handle or changing the alignment puzzle.
function laundryPrint(n){
 const latch=n==='switch_open_label'||n==='switch_close_label',title=n==='service_drain_caption'||latch,down=n==='drain_button_label',key='laundry-'+(title?n:down?'down':'right');
 if(txt[key])return key;
 const c=document.createElement('canvas');c.width=256;c.height=latch?128:title?64:128;
 const p=c.getContext('2d');p.fillStyle=latch?'#efc568':title?'#203941':'#fff4d4';p.fillRect(0,0,c.width,c.height);
 if(title){p.textAlign='center';p.textBaseline='middle';p.font='bold 54px system-ui,sans-serif';p.fillStyle=latch?'#272b25':'#fff8e8';p.fillText(latch?(n==='switch_open_label'?T('OPEN','开盖'):T('CLOSE','关盖')):T('DRAIN','排水'),128,c.height/2,238)}
 else{p.translate(128,64);p.scale(2,1);if(down)p.rotate(Math.PI/2);p.fillStyle='#192d32';p.beginPath();
  [[-44,-9],[8,-9],[8,-39],[47,0],[8,39],[8,9],[-44,9]].forEach(([x,y],i)=>i?p.lineTo(x,y):p.moveTo(x,y));p.closePath();p.fill()}
 const t=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGB,gl.RGB,gl.UNSIGNED_BYTE,c);
 gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);txt[key]=t;return key
}
function laundryMounts(j){
 const group=k=>j.groups.findIndex(g=>g[0]===k),material=k=>j.meshes.find(m=>m[0]===k)[3],
 unit=group('laundry_filter_unit'),hinge=group('inspection_hatch_hinge'),enamel=material('filter_left_side'),blue=material('filter_back'),steel=material('filter_base');
 function box(n,g,mat,L,H,target=''){
  const v=[];
  for(let k=0;k<3;k++)for(const side of [0,1]){
   const u=(k+1)%3,w=(k+2)%3,norm=[0,0,0];norm[k]=side?1:-1;
   for(const i of (side?[0,1,3,0,3,2]:[0,2,3,0,3,1])){
    const q=L.slice();q[k]=side?H[k]:L[k];q[u]=(i&1)?H[u]:L[u];q[w]=(i&2)?H[w]:L[w];v.push(...q,0,0,...norm)
   }
  }
  raw[j.meshes.length]=new Float32Array(v);j.meshes.push([n,g,target,mat,1,v.length/8]);
 }
 // Panel spans the internal side walls and is seated between base and top; the original rear wall stays intact.
 box('service_bulkhead',unit,enamel,[-.858,-.228,.1075],[.858,-.205,1.0775]);
 // Keep the existing gated open/close action ID, but replace ALL three handle tubes.
 const latch=group('inside_filter_handle'),key='filter_hatch_handle',opened=j.eligible.includes('s2_setup');
 for(const mesh of j.meshes)if(mesh[1]===latch&&['handle_left','handle_right','handle_grip'].includes(mesh[0]))mesh[4]=0;
 box('latch_switch_mount',unit,blue,[-.088,-.250,.796],[.088,-.228,.944],key);
 box('latch_switch_bezel',latch,steel,[-.073,-.017,-.054],[.073,0,.054],key);
 const front=opened?-.023:-.035;
 box('latch_switch_cap',latch,material('handle_grip'),[-.061,front,-.041],[.061,-.017,.041],key);
 const label=new Float32Array([[0,0],[1,0],[1,1],[0,0],[1,1],[0,1]].flatMap(([u,v])=>[-.055+.11*u,front-.0008,-.033+.066*v,u,v,0,-1,0]));
 raw[j.meshes.length]=label;j.meshes.push([opened?'switch_close_label':'switch_open_label',latch,key,steel,1,6]);
 box('drain_mount',unit,blue,[.307,-.250,.566],[.493,-.228,.794],'s2_setup');
 const face=new Float32Array([[0,0],[1,0],[1,1],[0,0],[1,1],[0,1]].flatMap(([u,v])=>[.314+.172*u,-.2508,.746+.043*v,u,v,0,-1,0]));
 raw[j.meshes.length]=face;j.meshes.push(['service_drain_caption',unit,'s2_setup',blue,1,6]);
 // The rear slider guides were hanging free behind the hatch frame. Tie both tracks into the side stiles.
 let i=0;for(const x of [-.841,.841])for(const z of [-.438,-.062]){
  box('guide_mount_'+i++,hinge,steel,[x-.012,-.032,z-.018],[x+.012,.053,z+.018]);
 }
}
function tracingSheetSurface(j){
 const mat=j.materials.push([[.46,.76,.82],'',.19])-1;
 for(let gi=0;gi<j.groups.length;gi++)if(/^tracing_sheet_[01]$/.test(j.groups[gi][0])){
  const corners=[[-.59,-.215],[.59,-.215],[.59,.215],[-.59,.215]];
  const v=new Float32Array([0,1,2,0,2,3].flatMap(i=>[corners[i][0],-.011,corners[i][1],0,0,0,1,0]));
  raw[j.meshes.length]=v;j.meshes.push(['loose_tracing_pane',gi,'',mat,1,6]);
 }
}
// The folio rack is one placement surface, including the paper already in it.
let folioCount=0;
const isFolio=key=>/^s2_item_[0-3]$/.test(key||'');
if($('#context-help'))$('#context-help').textContent=T(' C: crouch / stand.',' C 蹲下 / 起身。');
function onFolioTray(k){return LEVEL_NO===18&&(k==='s2_slot_0'||k==='s2_clue')}
let worldM=[];function apply(j){const fresh=!ready;if(fresh){[x,y,z]=j.origin;yaw=(90-j.yaw)*rads}let oldMask=mask,oldGrid=R?.mask;R=j;mask=bytes(j.mask.data);const tray=LEVEL_NO===21?j.groups.find(g=>g[0]==='cup_handle_drawer'):null;if(tray&&cupDrawerHomeY===undefined)cupDrawerHomeY=tray[3][1];const trayOpen=tray&&Math.abs(tray[3][1]-cupDrawerHomeY)>.01;upload(j.pics);const newV=new Float32Array(bytes(j.verts).buffer);let p=0;for(let i=j.offset;i<j.meshes.length;i++){const n=j.meshes[i][5]*8;raw[i]=newV.subarray(p,p+n);p+=n}const meshNames=new Set(j.meshes.map(m=>m[0]));
for(let i=0;i<j.meshes.length;i++){const m=j.meshes[i];if(i>=j.offset)raw[i]=fittedSurface(m[0],raw[i],meshNames);m[5]=raw[i].length/8}
if(LEVEL_NO===11)laundryMounts(j);
if(LEVEL_NO===19)tracingSheetSurface(j);
const folioTray=LEVEL_NO===18&&!j.eligible.includes('s3_clue');
if(folioTray)folioCount=j.groups.filter(g=>/^nested_folded_leaf_[0-3]$/.test(g[0])&&g[6]).length;
let mats=[],show=[],targets=[];const carPaint=LEVEL_NO===38?cartPlate(j):null;const eligible=new Set(j.eligible);j.groups.forEach((g,i)=>{let par=g[1];
 // Mount both selection screens flush on the upper cabinet panel. Dynamic
 // letter meshes inherit these same parents when the buffer changes.
 if(LEVEL_NO===22&&/^selection_echo_[01]$/.test(g[0])){
  g=g.slice();g[3]=[g[3][0],-.251,1.14];
 }
 if(LEVEL_NO===18&&g[0]==='accession_folder'&&j.eligible.includes('s2_note')){
  g=g.slice();g[3]=g[3].slice();g[3][1]-=.365; // pull-out folio tray, lid and contents together
 }
 if(LEVEL_NO===19&&['battery_drawer_support','key_drawer_support','tracing_sheet_0','tracing_sheet_1'].includes(g[0])){
  g=g.slice();g[3]=g[3].slice();
  if(g[0]==='battery_drawer_support')g[3][0]+=.188;
  else if(g[0]==='key_drawer_support')g[3][0]-=.073;
  else g[3][2]+=.080;
 }
 if(LEVEL_NO===18&&g[0]==='s1_confirm'){g=g.slice();g[3]=[g[3][0],-.238,.698]}
 if(LEVEL_NO===35&&par>=0&&j.groups[par][0]==='easel'&&/^sheet[0-3]$/.test(g[0])){g=g.slice();g[3]=g[3].slice();g[3][1]-=.026}
 if(LEVEL_NO===15&&g[0]==='rope_pair_check'){
  g=g.slice();g[3]=[g[3][0],-.266,.8325]; // bezel seated on board floor, entirely behind the nearest fold
 }else if(LEVEL_NO===15&&g[0]==='pleated_protective_curtain'){
  g=g.slice();g[3]=[g[3][0]*(.63/.66),g[3][1],g[3][2]]; // gathered cloth stops before the latch bracket
 }
 mats[i]=combine(par<0?eyeMat:mats[par],g);show[i]=(par<0||show[par])&&g[6];targets[i]=g[2]||(par>=0?targets[par]:'')});let total=j.meshes.reduce((n,m)=>n+m[5],0);data=new Float32Array(total*8);let pos=0;batches=[];allTargets=[];worldM=[];
j.meshes.forEach(([nm,gi,target,mi,on,len],id)=>{const mat=gi<0?eyeMat:mats[gi],t=target||(gi>=0?targets[gi]:'');allTargets[id]=t;worldM[id]=mat;let [col,tex,opacity]=j.materials[mi];if(LEVEL_NO===11&&['switch_open_label','switch_close_label','service_drain_caption','drain_button_label','slider_button_mark_0','slider_button_mark_1'].includes(nm))tex=laundryPrint(nm);
if(LEVEL_NO===18&&(nm==='spine_join_hint'||nm==='booklet_note_print'||/^loose_folded_leaf_[0-3]_page_numbers$/.test(nm)))tex=bindingPrint(nm,j.labels[t]||'')||tex;if(carPaint){if(nm==='code_plate')tex='cart-order-plate';else if(nm==='car_body')col=carPaint[+j.groups[gi][0].slice(3)-1]}if(!on||(gi>=0&&!show[gi])||opacity<.05)return;const v=raw[id],start=pos/8,lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];for(let i=0;i<v.length;i+=8){for(let k=0;k<3;k++){let a=mat[k*3]*v[i]+mat[k*3+1]*v[i+1]+mat[k*3+2]*v[i+2]+mat[k+9];data[pos+k]=a;if(a<lo[k])lo[k]=a;if(a>hi[k])hi[k]=a;data[pos+5+k]=mat[k*3]*v[i+5]+mat[k*3+1]*v[i+6]+mat[k*3+2]*v[i+7]}data[pos+3]=v[i+3];data[pos+4]=v[i+4];pos+=8}if(trayOpen&&nm.startsWith('cup_handle_drawer_'))markDrawer(j.mask,lo,hi);const surface=folioTray&&gi>=0&&/^(folded_leaf_cradle|folio_insertion_point|nested_folded_leaf_[0-3])$/.test(j.groups[gi][0]);
// Bind visible faces to the real mechanism, never through covers or past the normal reach.
let partTarget=t;
if(LEVEL_NO===34&&(nm==='claw_house'||(gi>=0&&j.groups[gi][0]==='claw_hook')))partTarget='claw';
if(LEVEL_NO===39&&gi>=0&&['light_box','face','pane_fitted'].includes(j.groups[gi][0]))partTarget='lightbox';
const dual=j.dualTap?.includes(t)&&eligible.has(t);
const pickTarget=dual?((/^(panel_mark_turn|knob_mark_turn|tile_mark_flip)$/.test(nm)?'turn::':'take::')+t):surface?(eligible.has('s2_clue')?'s2_clue':'s2_slot_0'):(eligible.has(partTarget)?partTarget:'');
const folioPaper=surface&&j.groups[gi][0].startsWith('nested_folded_leaf_');
batches.push({offset:start,len,lo,hi,folioPaper,target:pickTarget,color:tex?[1,1,1]:col.map(v=>Math.pow(v,.69)),tex,opacity})});if(!fresh)clearSwing(oldMask,oldGrid);gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,data.subarray(0,pos),gl.STATIC_DRAW);const newest=j.holding.find(v=>!bag.includes(v));bag=j.holding;if(newest&&LEVEL_NO===18&&pending==='s2_stack'){
 // Stow the returned leaf: another short press peels the next one, rather than putting this one back.
 held=null;sel=bag.length%9;page=Math.floor(bag.length/9)
}else if(newest){let n=bag.indexOf(newest);sel=n%9;page=Math.floor(n/9);held=newest}else if(held&&!bag.includes(held)){held=null;sel=bag.length%9;page=Math.floor(bag.length/9)}inventory();ready=true;busy=false;dirty=true;if(j.won&&!won){won=true;keys.clear();$('#status').textContent=T('Escaped','已通关');$('#win').showModal()}if(fresh)say(T('Explore the room and open the exit.','探索房间，想办法打开出口。'))}
function basis(){const sy=Math.sin(yaw),cy=Math.cos(yaw),sp=Math.sin(pitch),cp=Math.cos(pitch);return [[sy*cp,cy*cp,sp],[cy,-sy,0],[-sy*sp,-cy*sp,cp]]}
function pick(dx=0,dy=0){if(!ready)return "";let [f,s,u]=basis(),dir=unit(f.map((v,i)=>v+dx*s[i]*cv.width/cv.height/1.7+dy*u[i]/1.7)),eye=[x,y,z],near=1.65,best='';
for(const b of batches){let t0=0,t1=near;for(let k=0;k<3;k++){if(Math.abs(dir[k])<1e-9){if(eye[k]<b.lo[k]||eye[k]>b.hi[k])t1=-1}else{let a=(b.lo[k]-eye[k])/dir[k],z=(b.hi[k]-eye[k])/dir[k];t0=Math.max(t0,Math.min(a,z));t1=Math.min(t1,Math.max(a,z))}}if(t1<t0)continue;
for(let k=b.offset*8;k<(b.offset+b.len)*8;k+=24){let p=[data[k],data[k+1],data[k+2]],e1=[data[k+8]-p[0],data[k+9]-p[1],data[k+10]-p[2]],e2=[data[k+16]-p[0],data[k+17]-p[1],data[k+18]-p[2]],h=cross(dir,e2),det=dot(e1,h);if(Math.abs(det)<1e-9)continue;let D=sub(eye,p),a=dot(D,h)/det;if(a<0||a>1)continue;let n=cross(D,e1),v=dot(dir,n)/det;if(v<0||a+v>1)continue;let t=dot(e2,n)/det;if(t>.025&&t<near){near=t;best=b.folioPaper&&(!isFolio(held)||folioCount>=3)?'s2_stack':b.target}}}return best}

function drawScene(forward){
 const depth=b=>((b.lo[0]+b.hi[0])*.5-x)*forward[0]+((b.lo[1]+b.hi[1])*.5-y)*forward[1]+((b.lo[2]+b.hi[2])*.5-z)*forward[2];
 const draw=b=>{gl.uniform3fv(uni.col,b.color);gl.uniform1f(uni.opacity,b.opacity);gl.bindTexture(gl.TEXTURE_2D,txt[b.tex]||white);gl.drawArrays(gl.TRIANGLES,b.offset,b.len)};
 const translucent=[];gl.disable(gl.BLEND);for(const b of batches){if(b.opacity>=.999)draw(b);else translucent.push(b)}
 if(translucent.length){gl.enable(gl.BLEND);gl.depthMask(false);translucent.sort((a,b)=>depth(b)-depth(a));for(const b of translucent)draw(b);gl.depthMask(true)}
}
// Service passage: explain how to read the two matching grids without giving away the code.
const pipeDisplay=LEVEL_NO===23?PME_START.groups.find(g=>g[0]==='display'):null;
const pipeKey=pipeDisplay?document.createElement('aside'):null;
if(pipeKey){
 pipeKey.id='pipe-reading-key';pipeKey.className='hint';pipeKey.hidden=true;
 const title=document.createElement('strong');title.textContent=T('Pipe diagram key: ','管路读数提示：');
 pipeKey.append(title,T('Align the red corners of the pipe board and the number grid. Follow the connected pipe from inlet to outlet. Read the number at each bend in order; skip straight pipes.','把管道板和数字屏的红色角标对齐。从入口沿接通的管道走向出口，只读每个弯头对应格子的数字，跳过直管。'));
 $('#msg').before(pipeKey);
}
function render(){const [f,s,u]=basis();gl.viewport(0,0,cv.width,cv.height);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);for(const [k,v] of Object.entries({eye:[x,y,z],side:s,up:u,fwd:f}))gl.uniform3fv(uni[k],v);gl.uniform1f(uni.aspect,cv.width/cv.height);drawScene(f);hit=pick();if(pipeKey)pipeKey.hidden=!(hit==='exit_lock'||hit==='display'||Math.hypot(x-pipeDisplay[3][0],y-pipeDisplay[3][1])<1.55);$('#target').textContent=hit?name(hit):T('Approach and aim at an object','靠近并瞄准物体');dirty=false}
function walk(a,b){let i=Math.round((a+.6)*16),j=Math.round((b+.6)*16);return i>=0&&j>=0&&i<R.mask.nx&&j<R.mask.ny&&!mask[j*R.mask.nx+i]}
let rules=false,queued=null,bootFailed=false;function dispatch(k,verb='auto',code=''){if(!ready||busy||won||lost66||dlg.open)return;
 if(verb==='auto'&&(k.startsWith('turn::')||k.startsWith('take::'))){verb=k.startsWith('turn::')?'press':'take';k=k.slice(6)}
 if(LEVEL_NO===18){
 if(k==='s2_stack'&&verb==='auto')verb='take';
}
if(onFolioTray(k)&&verb==='auto'){
 if(k==='s2_slot_0'&&folioCount&&(!isFolio(held)||folioCount>=3)){k='s2_stack';verb='take'}
 else if(k==='s2_clue'){verb='read'}
 else if(!/^s2_item_[0-3]$/.test(held||'')){say(T('Select a folded sheet in your inventory, then interact with the tray.','先在物品栏选中一张折页，再对托架按 E 或点击放入。'));return}
 else{verb='use'}
}if(!k){say(T('Aim at an object within reach.','请靠近并瞄准物体。'));return}pending=k;const req={kind:'action',key:k,item:held||'',verb,code,position:[x,y,z]};if(!rules){if(!bootFailed){queued=queued||req;say(T('Preparing this interaction…','正在准备这次交互…'))}return}busy=true;worker.postMessage(req)}
function codeBox(){if(!pending||dlg.open)return;keys.clear();$('#locktitle').textContent=name(pending);$('#code').value='';$('#err').textContent='';dlg.showModal();$('#code').focus()}
$('#form').onsubmit=e=>{e.preventDefault();let c=$('#code').value.trim();dlg.close();dispatch(pending,'unlock',c)};$('#cancel').onclick=()=>dlg.close();function keyAction(k){if(k==='KeyC')toggleCrouch();if(/^Digit[1-9]$/.test(k))select(Number(k.slice(-1))-1);if(k==='Digit0'){sel=slots.indexOf(null);held=null;inventory();dirty=true}}
let eStart=null;const moveKeys=['KeyW','KeyS','KeyA','KeyD','ArrowLeft','ArrowRight','ArrowUp','ArrowDown'];window.addEventListener('keydown',e=>{if(won||lost66||dlg.open||e.ctrlKey||e.metaKey||e.altKey)return;if(e.code==='KeyE'&&!e.repeat){e.preventDefault();eStart={key:ready?pick():''};return}if(moveKeys.includes(e.code)){e.preventDefault();keys.add(e.code)}else if(!e.repeat)keyAction(e.code)});window.addEventListener('keyup',e=>{keys.delete(e.code);if(e.code==='KeyE'&&eStart){let a=eStart;eStart=null;dispatch(a.key)}});window.addEventListener('blur',()=>{keys.clear();eStart=null});document.addEventListener('visibilitychange',()=>{if(document.hidden)keys.clear()});
let drag=null;cv.onpointerdown=e=>{drag={i:e.pointerId,x:e.clientX,y:e.clientY,sum:0};cv.setPointerCapture(e.pointerId);cv.focus()};cv.onpointermove=e=>{if(!drag||drag.i!==e.pointerId)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;drag.sum+=Math.abs(dx)+Math.abs(dy);yaw+=dx*.005;pitch=Math.max(-1.42,Math.min(1.42,pitch-dy*.005));drag.x=e.clientX;drag.y=e.clientY;dirty=true};cv.onpointerup=e=>{if(drag&&drag.sum<6){const r=cv.getBoundingClientRect();dispatch(pick((e.clientX-r.left)/r.width*2-1,1-(e.clientY-r.top)/r.height*2))}drag=null};cv.onpointercancel=cv.onlostpointercapture=()=>drag=null;$('#interact').onclick=()=>dispatch(pick());$('#reset').onclick=()=>location.reload();for(const b of document.querySelectorAll('[data-key]')){b.onpointerdown=e=>{b.setPointerCapture(e.pointerId);keys.add(b.dataset.key)};b.onpointerup=b.onlostpointercapture=b.onpointercancel=()=>keys.delete(b.dataset.key)}

let crouched=false;function toggleCrouch(){if(!ready||busy||won||lost66)return;crouched=!crouched;z=R.origin[2]-(crouched?.65:0);$('#crouch').setAttribute('aria-pressed',String(crouched));dirty=true}$('#crouch').onclick=toggleCrouch;
function startRules(){const wurl=URL.createObjectURL(new Blob(['('+PME_WORKER.toString()+')()'],{type:'text/javascript'}));worker=new Worker(wurl);worker.onerror=e=>ruleFail(e.message);worker.onmessage=e=>{const j=e.data;if(j.kind==='fault'){ruleFail(j.text);return}if(j.result)apply(j.result);if(j.kind==='scene'){rules=true;if(queued){const req=queued;queued=null;busy=true;worker.postMessage(req)}else say(T('Explore the room and open the exit.','探索房间，想办法打开出口。'))}if(j.kind==='action'){busy=false;const a=j.answer;if(a.bottleLoss&&LEVEL_NO===16){if(!lost66){lost66=true;keys.clear();eStart=null;const label=T('Round lost','本局失败');$('#status').textContent=label;say(label);const end=document.createElement('dialog');end.id='level66-loss';const title=document.createElement('h2'),again=document.createElement('button');title.id='level66-loss-title';title.textContent=label;end.setAttribute('aria-labelledby',title.id);again.textContent=T('Restart level','重新开始');again.onclick=()=>location.reload();end.append(title,again);document.body.append(end);end.showModal()}return}if(a.needsCode){codeBox();return}if(a.closedNoChange){say(T('Already closed. Check the lock or its release mechanism.','仍然关着。请检查门锁或解锁机关。'));return}if(LEVEL_NO===18&&zh&&a.ok&&pending==='s2_note'&&a.verb==='read'){say('小册子：第 1–12 页。外层折页包住内层折页。套叠顺序：由外到内。');window.PME_readCaption?.(name(pending),$('#msg').textContent);return}if(LEVEL_NO===18&&a.ok&&pending==='s2_stack'&&a.verb==='take'){say(T('Top sheet returned to inventory','顶页已取回背包')+' · '+T('Sheets on tray: ','托架剩余：')+folioCount+'/3');return}if(LEVEL_NO===18&&a.ok&&pending==='s2_slot_0'&&a.verb==='use'){
 say(T('Sheet placed','已放入折页')+' ('+folioCount+'/3)'+(folioCount<3?T(' · Press E on the stack to take it back, or select another sheet to place.',' · 对纸叠按 E 可取回；要继续放，请先选下一张。'):T(' · Press E on the stack to take the top sheet, or on the wooden tray to inspect the edge code.',' · 对纸叠按 E 取回顶页，对旁边的木托按 E 查看纸边拼码。')));return}
if(a.ok&&a.verb==='read'&&a.text)window.PME_readCaption?.(name(pending),a.text);const words={open:'已打开',close:'已关闭',take:'已拿起',use:'已使用',press:'已操作',read:'已查看',unlock:'已解锁'};say(a.ok&&a.verb==='take'&&a.pickupDetail?[T('Picked up','已拿起'),name(pending),...new Set([a.text,a.pickupDetail].filter(Boolean))].join(' · '):a.text||(a.ok?(zh?words[a.verb]||'已操作':a.verb)+' · '+name(pending):T('No change. Try another item or interaction.','状态没有改变，试试别的道具或操作。')))}};
worker.postMessage({kind:'boot',number:LEVEL_NO,files:PME_PY,common:PME_ENGINE,level:PME_LEVEL});window.addEventListener('pagehide',e=>{if(!e.persisted){worker.terminate();URL.revokeObjectURL(wurl)}})}function ruleFail(e){bootFailed=true;busy=false;say(T('Room controls could not load. Refresh to retry.','机关未能加载，请刷新重试。'));console.error(e)}let last=performance.now(),lastGear=0;function frame(t){let dt=Math.min(.05,(t-last)/1000);last=t;if(ready&&!won&&!lost66&&!busy&&!dlg.open&&keys.size){const ax=(k,n)=>Number(keys.has(k))-Number(keys.has(n));yaw+=ax('ArrowRight','ArrowLeft')*1.65*dt;pitch=Math.max(-1.42,Math.min(1.42,pitch+ax('ArrowUp','ArrowDown')*1.25*dt));let f=ax('KeyW','KeyS'),r=ax('KeyD','KeyA'),spd=1.25*dt/Math.max(1,Math.hypot(f,r)),nx=x+(f*Math.sin(yaw)+r*Math.cos(yaw))*spd,ny=y+(f*Math.cos(yaw)-r*Math.sin(yaw))*spd;if(walk(nx,y))x=nx;if(walk(x,ny))y=ny;dirty=true}if(dirty&&ready)render();if(held&&t-lastGear>90){paintGear(matchMedia('(prefers-reduced-motion:reduce)').matches?0:t);lastGear=t}requestAnimationFrame(frame)}apply(PME_START);globalThis.PME_START=null;render();$('#entry').hidden=true;requestAnimationFrame(frame);setTimeout(()=>PME_START_RULES().then(startRules).catch(ruleFail),30)
})();