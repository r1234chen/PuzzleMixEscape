const ROOM=(()=>{
const groups=[],initial=[],meshes=[],verts=[],ids={},labels={},obstacles=[],aims={},dynamic=[],inputs=[],images={},painter=[],cn=document.documentElement.lang==='zh-CN';let texN=1;
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


const N=SINGLE.nodes,WW=4.8,DD=4.2,HS=1.8,front=DD,back=DD+HS,totalY=DD*2+HS,count=1+Math.max(...Object.values(HALL.rooms).map(v=>v[0])),width=count*WW;
const rn={office:['Office','办公室'],bath:['Bathroom','卫生间'],laundry:['Laundry','洗衣房'],kitchen:['Kitchen','厨房'],living:['Living room','客厅'],dining:['Dining room','餐厅'],shared:['Reception','公共办公室'],twinA:['Office A','办公室 A'],twinB:['Office B','办公室 B'],corridor:['Hall','门厅']};
const paint={office:'#94ab9e',laundry:'#a0b6ba',bath:'#abcac6',kitchen:'#afbbb0',living:'#c4a88d',dining:'#b79e87',shared:'#b6b7a6',twinA:'#a0aca4',twinB:'#a0aca4'};
const drawers=[],regions=[],moving=[],surfaces={},cabinets={},names=new Map();
const title=(k,e,z,p,kind,gate={},parent=null)=>{labels[k]=cn?z:e;N[k]={id:k,p:p.slice(),label:e,labelZh:z,kind,gate,parent};return k};
function local(room,u,v,z){const [i,s]=HALL.rooms[room];return [i*WW+(s===1?u:WW-u),s===1?back+v:front-v,z]}
function rot(g,angle){initial[g][1]=[0,0,angle]}
function root(k,p,t='',yaw=0){const g=grp(k,p,t);rot(g,yaw);return g}
function anchor(room,k,u,v,z,t=''){const g=root(k,local(room,u,v,z),t,HALL.rooms[room][1]===1?0:180);return g}
function block(cx,cy,w,d){obstacles.push([cx-w/2,cy-d/2,cx+w/2,cy+d/2])}
function wall(x,y,w,d,c){
 const band=(lo,hi,lip,col)=>B(fix,x,y,(lo+hi)/2,w+lip,d+lip,hi-lo,col);
 band(0,0.096,0.019,dark);band(0.096,0.86,0.014,c);band(0.86,0.8625,0,'#ece2cd');band(0.8625,0.8975,0.028,white);band(0.8975,2.76,0,'#ece2cd');block(x,y,w,d);
}
function wallspan(x1,y1,x2,y2,c){if(Math.hypot(x2-x1,y2-y1)<.01)return;wall((x1+x2)/2,(y1+y2)/2,Math.max(.07,Math.abs(x2-x1)),Math.max(.07,Math.abs(y2-y1)),c)}
function floor(x0,y0,x1,y1,ceramic=false){const nx=ceramic?6:3,ny=ceramic?6:8,sx=(x1-x0)/nx,sy=(y1-y0)/ny;for(let i=0;i<nx;i++)for(let j=0;j<ny;j++)B(fix,x0+(i+.5)*sx,y0+(j+.5)*sy,-.022,sx-.004,sy-.004,.044,(ceramic?['#becac2','#d4dcd1']:['#c4a885','#d6b89a','#ccae8a'])[(i+j)%(ceramic?2:3)]);B(fix,(x0+x1)/2,(y0+y1)/2,2.79,x1-x0,y1-y0,.06,'#eee5d2')}
function tag(s){if(!names.has(s))names.set(s,label('',s,'','#f3e3bb'));return names.get(s)}
function opening(k,cx,cy,angle,lab,gate,side=1){const a=angle*Math.PI/180,cs=Math.cos(a),sn=Math.sin(a),w=1.12;
let h=[cx-.56*cs,cy-.56*sn,0];title(k,lab[0],lab[1],h,'door',gate);const g=root(k,h,k,angle);
const doorColour=k==='exit'?'#537561':'#977357',stile=(w-.90)/2;
for(const px of [stile/2,w-stile/2])B(g,px,0,1.04,stile,.065,2.08,doorColour);
for(const [lo,hi] of [[0,.18],[.94,1.12],[1.88,2.08]])B(g,w/2,0,(lo+hi)/2,.90,.065,hi-lo,doorColour);
for(const z of [.56,1.5])B(g,w/2,0,z,.90,.076,.76,k==='exit'?'#668673':'#ad896b');
for(const s of [-1,1]){B(g,.94,s*.053,1.0,.09,.033,.19,gold);B(g,.88,s*.085,1.04,.17,.033,.035,black)}
const frame=root('frame_'+k,[cx,cy,0],'',angle);for(const u of [-.6,.6])B(frame,u,0,1.08,.085,.12,2.16,dark);B(frame,0,0,2.13,1.29,.12,.095,dark);B(frame,0,0,2.45,1.28,.075,.59,'#e7ddc7');
const tile=tag(cn?lab[1]:lab[0]);for(let s of [-1,1])face(frame,[0,s*.071,2.32],[s<0?.36:-.36,0,0],[0,0,.095],s>0&&HALL.rooms[k]?tag(cn?'门厅':'Hall'):tile);
const leaf={k,h,angle,w,side};moving.push(leaf);dynamic.push([g,state=>({r:[0,0,angle+(state.open[k]?leaf.side*89:0)]})]);aims[k]=[w/2,0,1];}
const cabinetNames={office:['Office cabinet','办公地柜'],kitchen:['Kitchen cabinet','厨房地柜'],laundry:['Laundry cabinet','洗衣柜'],bath:['Bathroom cabinet','浴室柜'],living:['Living-room cabinet','客厅地柜'],twinA:['Office cabinet','办公地柜'],twinB:['Office cabinet','办公地柜']};
function cabinet(room,id,u,v){const host=room+':'+id,[en,zh]=cabinetNames[room],g=anchor(room,host,u,v,0),p=local(room,u,v,0);block(p[0],p[1],.95,.59);B(g,0,.25,.39,.90,.045,.75,wood);B(g,0,0,.055,.88,.55,.11,dark);for(const side of [-1,1])B(g,side*.45,0,.41,.038,.59,.78,wood);B(g,0,0,.802,.96,.62,.037,wood);surfaces[host]=[room,u,v,.824];cabinets[host]=[room,u,v];
for(let j=1;j<=4;j++){const k=host+'@'+j,z=.637-(j-1)*.156;
const q=local(room,u,v,z),sgn=HALL.rooms[room][1];title(k,en+' '+id+' / drawer '+j,zh+' '+id+' · 第 '+j+' 层',q,'drawer',{code:HALL.locks[k]||''});const d=anchor(room,k,u,v,z,k);B(d,0,-.016,-.012,.839,.48,.026,dark);B(d,0,-.271,.048,.86,.04,.142,wood);for(let side of [-1,1])B(d,side*.406,0,.045,.025,.49,.12,wood);B(d,0,.215,.045,.84,.028,.12,wood);B(d,0,-.30,.060,.17,.037,.029,gold);
drawers.push({k,x:q[0],y:q[1],sgn});dynamic.push([d,s=>({p:[q[0],q[1]-(s.open[k]?sgn*.44:0),z]})]);aims[k]=[0,-.30*sgn,.06]}}
function table(room,key,u,v,w,d,h){const g=anchor(room,key,u,v,0),p=local(room,u,v,0);block(p[0],p[1],w,d);B(g,0,0,h-.032,w,d,.064,wood);for(const a of [-1,1])for(const b of [-1,1])B(g,a*(w/2-.055),b*(d/2-.055),h*.46,.065,.065,h*.92,dark);surfaces[room+':'+key]=[room,u,v,h+.003];return g}
function chair(room,u,v,swivel=false){const g=anchor(room,'chair',u,v,0),p=local(room,u,v,0);block(p[0],p[1],.44,.44);B(g,0,0,.47,.47,.43,.07,swivel?black:wood);B(g,0,.193,.70,.42,.048,.40,swivel?green:wood);if(swivel){B(g,0,0,.25,.049,.049,.42,steel);B(g,0,0,.055,.49,.061,.052,black);B(g,0,0,.055,.055,.46,.052,black)}else for(const a of [-1,1])for(const b of [-1,1])B(g,a*.18,b*.16,.22,.042,.04,.43,dark)}
function art(room,u,h,design){const g=anchor(room,'framed_art',u,DD-.09,h);B(g,0,0,0,.61,.06,.48,dark);let ti=tile(c=>{c.fillStyle=['#94b8b8','#d8bc95','#adc3ab'][design%3];c.fillRect(0,0,256,256);c.fillStyle='#f7de96';c.beginPath();c.arc(182-design*26,69,24,0,7);c.fill();for(let j=0;j<2;j++){c.fillStyle=j?'#51756d':'#78958b';c.beginPath();c.moveTo(0,172+j*22);for(let x=0;x<=256;x+=32)c.lineTo(x,160+j*29+29*Math.sin(x*.017+design+j));c.lineTo(256,256);c.lineTo(0,256);c.fill()}})[0];face(g,[0,-.033,0],[.276,0,0],[0,0,.207],ti)}
function lamp(room,u,v){const g=anchor(room,'floor_lamp',u,v,0);E(g,0,0,.055,.17,.17,.048,black);B(g,0,0,.72,.026,.026,1.32,gold);const rings=[[1.31,.22],[1.53,.127]],points=[],faces=[];for(const [z,r] of rings)for(let i=0;i<24;i++){let a=i*Math.PI/12;points.push([r*Math.cos(a),r*Math.sin(a),z])}for(let i=0;i<24;i++){let j=(i+1)%24;faces.push([i,j,j+24,i+24])}mesh('woven lamp shade',g,points,faces,'#e5c997');E(g,0,0,1.34,.052,.052,.067,'#fff0c1');B(g,0,0,1.54,.038,.038,.025,gold);const p=local(room,u,v,0);block(p[0],p[1],.30,.30)}
function shelf(room,u,v){const g=anchor(room,'bookcase',u,v,0);for(let h of [.12,.50,.90,1.3,1.7])B(g,0,0,h,.84,.37,.048,wood);for(let a of [-1,1])B(g,a*.42,0,.87,.05,.37,1.72,dark);for(let j=0;j<3;j++)for(let i=0;i<6;i++){let h=.22+.035*((i+j)%3);B(g,-.32+i*.092,0,.147+j*.39+h/2,.064,.25,h,[green,red,blue,dark][(i+j)%4])}const p=local(room,u,v,0);block(p[0],p[1],.89,.38)}
function sink(room,u,v){const g=table(room,'sink',u,v,.96,.57,.76);B(g,0,.02,.77,.89,.51,.035,steel);B(g,0,-.21,.845,.90,.05,.14,white);B(g,0,.255,.845,.90,.045,.14,white);for(let a of [-1,1])B(g,a*.424,.02,.848,.05,.49,.14,white);B(g,.265,.19,1.055,.035,.035,.30,steel);B(g,.265,.105,1.19,.039,.19,.037,steel);surfaces[room+':sink']=[room,u-.22,v+.24,.922]}
function cylinder(g,x,y,z,r0,r1,h,c){const vs=[],fs=[];for(const [r,zz] of [[r0,z],[r1,z+h]])for(let j=0;j<24;j++){let a=2*Math.PI*j/24;vs.push([x+r*Math.cos(a),y+r*Math.sin(a),zz])}for(let j=0;j<24;j++){let k=(j+1)%24;fs.push([j,k,k+24,j+24]);if(j>0&&j<23)fs.push([24,24+j,25+j])}mesh('turned profile',g,vs,fs,c)}
function plant(room,u,v){let g=anchor(room,'plant',u,v,0);cylinder(g,0,0,.013,.135,.19,.28,'#a26749');cylinder(g,0,0,.27,.198,.198,.041,'#b37954');cylinder(g,0,0,.309,.179,.178,.006,'#574b39');
for(let j=0;j<11;j++){let a=j*2.40,dx=Math.cos(a),dy=Math.sin(a),h=.46+.035*j;B(g,dx*.045,dy*.045,(h+.31)/2,.011,.011,h-.31,'#58734a');let x=dx*.045,y=dy*.045;mesh('pointed leaf',g,[[x,y,h-.035],[x+.104*dx-.043*dy,y+.104*dy+.043*dx,h+.045],[x+.198*dx,y+.198*dy,h+.01],[x+.104*dx+.043*dy,y+.104*dy-.043*dx,h+.033]],[[0,1,2],[0,2,3]],j%2?'#598555':'#7c9b65')}}
floor(0,front,width,back,true);
for(let bay=0;bay<count;bay++){for(const sign of [-1,1]){const yy=sign===1?back:front,room=Object.keys(HALL.rooms).find(k=>HALL.rooms[k][0]===bay&&HALL.rooms[k][1]===sign);
if(!room){wallspan(bay*WW,yy,(bay+1)*WW,yy,'#aeb7a8');continue}
let x=bay*WW,cy=yy+sign*DD,mc=x+WW/2;regions.push([x,Math.min(yy,cy),x+WW,Math.max(yy,cy)]);floor(x,Math.min(yy,cy),x+WW,Math.max(yy,cy),['bath','laundry','kitchen'].includes(room));
wallspan(x,yy,mc-.60,yy,paint[room]);wallspan(mc+.60,yy,x+WW,yy,paint[room]);
const outsideRight=!Object.values(HALL.rooms).some(r=>r[0]===bay+1&&r[1]===sign),gardenOnSide=outsideRight&&room===HALL.exitRoom;
wallspan(x,yy,x,cy,paint[room]);if(gardenOnSide){
 const edge=x+WW,mid=yy+sign*1.65;
 wallspan(edge,yy,edge,mid-sign*.60,paint[room]);wallspan(edge,mid+sign*.60,edge,cy,paint[room]);
 opening('exit',edge,mid,90,['Garden exit','花园出口'],HALL.gates.exit,-1)
}else if(outsideRight)wallspan(x+WW,yy,x+WW,cy,paint[room]);
opening(room,mc,yy,sign===1?0:180,rn[room],HALL.gates[room]||{});
if(room===HALL.exitRoom&&!gardenOnSide){wallspan(x,cy,x+.47,cy,paint[room]);wallspan(x+1.67,cy,x+WW,cy,paint[room]);opening('exit',x+1.07,cy,sign===1?0:180,['Garden exit','花园出口'],HALL.gates.exit,-1)}
else wallspan(x,cy,x+WW,cy,paint[room]);
const light=anchor(room,'ceiling_light',2.45,2.02,2.68);B(light,0,0,0,.73,.38,.07,steel);B(light,0,0,-.044,.69,.34,.02,'#fff1be');
if(room==='office'){cabinet(room,'A',.88,DD-.44);cabinet(room,'B',2.33,DD-.44);const desk=table(room,'desk',3.8,2.85,1.42,.75,.77);B(desk,.40,.17,.785,.38,.22,.015,'#637f73');B(desk,.40,.265,.908,.38,.024,.21,'#485650');B(desk,.40,.248,.908,.342,.008,.176,'#849f9d');chair(room,3.63,2.16,true);shelf(room,.52,1.82);for(let i=0;i<3;i++)art(room,1.06+1.27*i,1.68,i)}
if(room==='laundry'){cabinet(room,'A',1.06,DD-.45);for(let i=0;i<2;i++){const g=anchor(room,'washer',2.56+i*.99,DD-.54,0);B(g,0,0,.50,.83,.75,.96,'#dbe3dc');E(g,0,-.394,.47,.256,.036,.26,steel,24);E(g,0,-.424,.47,.197,.018,.204,'#557879',24);B(g,0,-.393,.86,.56,.03,.10,'#9dafa4');B(g,-.085,-.412,.859,.18,.012,.054,black);for(let t of [.08,.16,.24])E(g,t,-.417,.86,.021,.012,.021,white,12);let p=local(room,2.56+i*.99,DD-.54,0);block(p[0],p[1],.85,.78)}
if(HALL.switchTo){let pt=local(room,1.8,DD-.1,1.28);title('switch','Wall switch','墙壁开关',pt,'switch');let g=anchor(room,'switch',1.8,DD-.1,1.28,'switch');B(g,0,0,0,.158,.043,.24,white);B(g,0,-.035,0,.072,.035,.135,black);const sw=anchor(room,'switch paddle',1.8,DD-.148,1.28,'switch');B(sw,0,0,0,.072,.025,.102,green);dynamic.push([sw,s=>({r:[s.pressed?23:-23,0,sign===1?0:180]})]);aims['switch']=[0,0,0]}}
if(room==='bath'){sink(room,1.25,DD-.47);if(HALL.items.some(o=>o.place==='bath:A'))cabinet(room,'A',3.32,DD-.43);
let g=anchor(room,'mirror',1.25,DD-.073,1.63);B(g,0,0,0,.88,.055,.65,steel);B(g,0,-.035,0,.82,.015,.59,'#a0bdbe');let t=anchor(room,'towel',3.1,DD-.10,1.38);B(t,0,0,0,.57,.04,.04,steel);B(t,0,-.02,-.17,.33,.041,.37,'#7bafab')}
if(room==='dining'){table(room,'table',2.4,2.29,1.68,.82,.79);for(let a of [-1,0,1]){chair(room,2.4+a*.64,1.58);chair(room,2.4+a*.64,3.0)}lamp(room,.60,3.53);lamp(room,4.16,3.53);art(room,2.42,1.73,1)}
if(room==='kitchen'){cabinet(room,'A',2.45,DD-.45);cabinet(room,'B',3.64,DD-.45);const g=anchor(room,'burner',2.45,DD-.45,.827);B(g,0,0,.015,.62,.40,.027,black);for(let a of [-1,1]){E(g,a*.145,-.015,.04,.108,.102,.019,steel,20);E(g,a*.145,-.015,.055,.079,.074,.014,black,20);B(g,a*.145,-.17,.04,.057,.031,.032,black)}B(g,0,.20,1.01,.74,.29,.15,steel)}
if(room==='living'){cabinet(room,'A',.88,DD-.46);cabinet(room,'B',3.89,DD-.46);let g=anchor(room,'fireplace',2.4,DD-.36,0);B(g,0,.06,.59,1.32,.45,1.16,'#b68a70');B(g,0,-.18,.42,.88,.05,.66,'#373934');B(g,0,0,1.21,1.50,.67,.092,dark);for(let i=0;i<4;i++)E(g,-.25+i*.16,-.22,.27,.099,.035,.12+i%2*.064,i%2?'#cb8754':'#d7ac69');let p=local(room,2.4,DD-.36,0);block(p[0],p[1],1.49,.67)}
if(room==='shared')table(room,'table',2.35,2.77,1.63,.82,.76);
if(room==='twinA'||room==='twinB'){cabinet(room,'A',1.30,DD-.46);table(room,'desk',3.53,2.9,1.28,.64,.78);chair(room,3.5,2.25,true);if(room==='twinA')plant(room,2.42,3.53)}
}}
regions.push([0,front,width,back]);wallspan(0,front,0,back,'#aab4a3');
function crossHall(x,key){const y=(front+back)/2;wallspan(x,front,x,y-.60,'#aab4a3');wallspan(x,y+.60,x,back,'#aab4a3');opening(key,x,y,90,key==='exit'?['Hall exit','门厅出口']:['Hall door','门厅门'],HALL.gates[key],-1)}
if(HALL.exitRoom==='corridor')crossHall(width,'exit');else wallspan(width,front,width,back,'#aab4a3');if(HALL.hallGate)crossHall(WW*2,'hall');
const slots={};for(const item of HALL.items){const {id:k,place,part,code}=item;const pos=part?cabinets[place]:surfaces[place];if(!pos)throw Error('Missing physical support: '+place);const [room,u,v]=pos,j=part?place+'@'+part:null,count=slots[place+'#'+part]||0;slots[place+'#'+part]=count+1;const uu=u+(part?-.08:-.05)+count*.21,vv=v+(part?-.14:0),z=part?.637-(part-1)*.156+.005:(pos[3]||.83),p=local(room,uu,vv,z);const [en,zh]=item.key?['Brass key','黄铜钥匙']:item.diary?['Locked diary','日记本']:['Paper note','纸条'];title(k,en,zh,p,item.key?'key':'paper',{code},j);Object.assign(N[k],{en:item.en,zh:item.zh,place});
const gr=anchor(room,k,uu,vv,z,k);if(item.key){for(let j=0;j<18;j++)E(gr,.034*Math.cos(j*Math.PI/9),.034*Math.sin(j*Math.PI/9),.012,.009,.009,.008,gold,8);B(gr,.094,0,.012,.124,.014,.017,gold);B(gr,.141,.014,.012,.030,.030,.018,gold)}
else{B(gr,0,0,.012,.235,.164,item.diary?.022:.006,item.diary?'#65624c':'#f4e9cd');const ti=tile(c=>{c.fillStyle=item.diary?'#746247':'#f4edda';c.fillRect(0,0,256,256);if(item.diary)txt(c,cn?'日记':'DIARY',126,51,white);else{c.strokeStyle='#9b8a72';for(let i=0;i<5;i++){c.beginPath();c.moveTo(29,52+31*i);c.lineTo(220-i%3*17,52+31*i);c.stroke()}}})[0];face(gr,[0,0,item.diary?.025:.017],[.112,0,0],[0,.078,0],ti)}
const sg=HALL.rooms[room][1];dynamic.push([gr,s=>({p:[p[0],p[1]-(part&&s.open[j]?sg*.44:0),p[2]],on:(!part||s.open[j])&&(!item.key||s.stock[k]!=='hand')})]);aims[k]=[0,0,item.key?.018:.022]}
function drawerFront(v,x,y){const t=(v.y-y)*v.sgn;return Math.abs(x-v.x)<.55 && t>.19 && t<.88}
function guard(k,x,y){const v=drawers.find(v=>v.k===k);if(v)return RULES.open[k]||!drawerFront(v,x,y);const d=moving.find(v=>v.k===k);if(!d)return true;const a=d.angle*Math.PI/180,rx=x-d.h[0],ry=y-d.h[1],along=rx*Math.cos(a)+ry*Math.sin(a),side=ry*Math.cos(a)-rx*Math.sin(a);if(!RULES.open[k]){d.side=side>=0?-1:1;return true}return !(along>-.14&&along<d.w+.14&&Math.abs(side)<.145)}
function walkFree(x,y){x=Math.round(x*1e6)/1e6;y=Math.round(y*1e6)/1e6;if(!regions.some(b=>x>=b[0]&&x<=b[2]&&y>=b[1]&&y<=b[3]))return false;
if(drawers.some(v=>RULES.open[v.k]&&drawerFront(v,x,y)))return false;
if(obstacles.some(([a,b,c,d])=>x>a-.116&&x<c+.116&&y>b-.116&&y<d+.116))return false;
for(const d of moving){const a=(d.angle+(RULES.open[d.k]?d.side*89:0))*Math.PI/180,dx=Math.cos(a),dy=Math.sin(a),rx=x-d.h[0],ry=y-d.h[1],l=Math.max(0,Math.min(d.w,rx*dx+ry*dy));if(Math.hypot(rx-l*dx,ry-l*dy)<.136)return false}return true}
initial.push(...meshes.map(()=>1));const orig=local(HALL.start,2.25,1.16,1.35);return {groups,initial,meshes,ids,labels,verts:new Float32Array(verts),atlas,origin:orig,yaw:HALL.rooms[HALL.start][1]===1?90:-90,bounds:[0,width,0,totalY],initialPitch:-.06,dynamic,painter,inputs,images,obstacles,aims,walkFree,guard,customExit:true}
})();