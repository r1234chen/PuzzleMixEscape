const SPEC={"input":"5937","lock":"2481","origin":[3.3,17.6,1.35],"yaw":0,"mats":[[5.38,18.04,0.781],[5.38,18.23,0.781],[5.38,18.42,0.781],[5.38,18.61,0.781]],"order":["octopus","turtle","panda","crab"],"ball":[2.4477,18.0493,0.1179],"plate":[2.95,16.7,0.0125],"writer":[5.4,17.7,0.833],"output":[5.462,17.7,1.038],"toys":{"octopus":[2.55,17.52,0.0504478],"turtle":[2.655,17.52,0.0524599],"panda":[2.55,17.18,0.0570643],"crab":[2.655,17.18,0.045429]},"letter":"I am the stage manager. The paper drawer interlock needs a heavy prop on the floor pressure plate; use the bowling ball. A plate can hold only one object: take it off before trying another. Put the paper into my old typewriter and type the number on the plate beside the exit. The printed result opens the prop box. Its cast list explains the final curtain call.","cast":"The curtain-call order is octopus on red, turtle on blue, panda on green, and crab on yellow. Put each actual stage toy on its own coloured mat; the exit interlock will release after all four return. Leave the heavy ball on the pressure plate while returning all four toys; removing it blocks further placement.","cipher":{"5":"2","9":"4","3":"8","7":"1","0":"6","1":"9","2":"0","4":"3","6":"5","8":"7"}};
const ROOM=(()=>{
const groups=[],initial=[],meshes=[],verts=[],labels={},ids={},cn=document.documentElement.lang==='zh-CN';
const atlas=document.createElement('canvas');atlas.width=atlas.height=1024;const ctx=atlas.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,1024,1024);
function tile(i,bg,lines,ink='#263d35'){const x=i%4*256,y=Math.floor(i/4)*256;ctx.fillStyle=bg;ctx.fillRect(x,y,256,256);ctx.fillStyle=ink;ctx.textAlign='center';for(const [t,h,sz] of lines){ctx.font='bold '+sz+'px Georgia,serif';ctx.fillText(t,x+128,y+h,245)}}
tile(1,'#f5e5bc',[['CUE   /   38',42,24],['BACKSTAGE',105,33],['A letter from',165,22],['the stage manager',196,21]]);tile(2,'#fff0ce',[[SPEC.input,170,96]]);
tile(3,'#e5d7ba',[['STAGE   OFFICE',54,24],['38',164,94],['REHEARSAL',220,21]]);tile(4,'#ebe6cc',[['CAST   LIST',57,32],['OCTOPUS   /   RED',106,18],['TURTLE   /   BLUE',138,18],['PANDA   /   GREEN',170,18],['CRAB   /   YELLOW',202,18]]);
tile(5,'#193e39',[['MATINEE',60,28],['✦',159,90],['STUDIO  /  38',220,24]],'#f4dda9');
tile(6,'#d19769',[['ACT   II',58,32],['◒',166,103],['EVENING SHOW',218,24]],'#3e3435');
tile(7,'#fbefce',[['REHEARSAL',46,23],['•',150,60],['TYPEWRITTEN',220,18]]);
tile(9,'#eee1b5',[['CALL SHEET',54,28],['────────',96,22],['Matinée',133,24],['────────',164,22],['Evening',205,24]]);
{let x=512,y=512;ctx.fillStyle='#f7f2e8';ctx.fillRect(x,y,256,256);for(let i=0;i<115;i++){ctx.strokeStyle=i%4?'#e4d9c4':'#cfc3ac';ctx.lineWidth=.7;ctx.beginPath();for(let j=0;j<=16;j++){let yy=y+2.2*i+1.6*Math.sin(j*.6+i*.79);if(j)ctx.lineTo(x+j*16,yy);else ctx.moveTo(x,yy)}ctx.stroke()}}
const tileNum=8;function print(text){tile(tileNum,'#fff4d7',[['STAGE OFFICE',42,22],[text||'—',153,64],['TYPEWRITTEN',220,18]])}print('');
const col=(hex)=>[1,3,5].map(i=>Math.pow(parseInt(hex.slice(i,i+2),16)/255,1.45));
function grp(id,p,target=id,on=true){let i=groups.length;groups.push([id,-1,target]);initial.push([p.slice(),[0,0,0],[1,1,1],+on]);ids[id]=i;return i}
const fix=grp('shell',[0,0,0],'');function mesh(n,gi,points,faces,color,ti=0){if(!ti&&['#ad7750','#906345','#cbaa82','#d3b58f','#c9ab87'].includes(color))ti=10;const start=verts.length/5;for(const face of faces){for(const j of [0,1,2,...(face.length===4?[0,2,3]:[])]){let p=points[face[j]],uv=ti?[[.01,.99],[.99,.99],[.99,.01],[.01,.01]][j]:[.45,.45];verts.push(...p,(ti%4+uv[0])/4,(Math.floor(ti/4)+uv[1])/4)}}meshes.push([n,gi,start,verts.length/5-start,col(color),''])}
function B(g,x,y,z,w,d,h,c){const p=[];for(let k of [-1,1])for(let j of [-1,1])for(let i of [-1,1])p.push([x+i*w/2,y+j*d/2,z+k*h/2]);mesh('box',g,p,[[0,2,3,1],[4,5,7,6],[0,1,5,4],[1,3,7,5],[3,2,6,7],[2,0,4,6]],c)}
function face(g,c,u,v,ti){const ps=[[-1,-1],[1,-1],[1,1],[-1,1]].map(([a,b])=>c.map((x,i)=>x+a*u[i]+b*v[i]));mesh('print',g,ps,[[0,1,2,3]],'#ffffff',ti)}
function E(g,x,y,z,a,b,c,color,seg=16){const p=[],f=[];for(let j=0;j<=10;j++){let lat=-Math.PI/2+j*Math.PI/10;for(let i=0;i<seg;i++){let t=i*2*Math.PI/seg;p.push([x+a*Math.cos(lat)*Math.cos(t),y+b*Math.cos(lat)*Math.sin(t),z+c*Math.sin(lat)])}}for(let j=0;j<10;j++)for(let i=0;i<seg;i++){let k=j*seg+i,l=j*seg+(i+1)%seg;f.push([k,l,l+seg,k+seg])}mesh('round',g,p,f,color)}
const ivory='#e9dfca',green='#688b79',oak='#ad7750',dark='#634535',brass='#d5af69',cream='#f3e7d1',ink='#293e39',wood='#906345',red='#aa5146';
const [x0,x1,y0,y1]=[1.94,5.86,15.95,19.44];
for(let j=0;j<14;j++)for(let i=0;i<4;i++){let dx=(x1-x0)/4,dy=(y1-y0)/14;B(fix,x0+(i+.5)*dx,y0+(j+.5)*dy,-.025,dx-.006,dy-.005,.05,['#cbaa82','#d3b58f','#c9ab87'][(i+2*j)%3])}
function wall(x,y,w,d){
 const band=(lo,hi,lip,col)=>B(fix,x,y,(lo+hi)/2,w+lip,d+lip,hi-lo,col);
 band(0,0.112,0.04,dark);band(0.112,0.84,0.012,green);band(0.84,0.8475,0,ivory);band(0.8475,0.8925,0.031,cream);band(0.8925,2.7,0,ivory);
}
wall(x0-.045,(y1+y0)/2,.09,y1-y0);wall(x1+.045,(y1+y0)/2,.09,y1-y0);wall((x0+x1)/2,y0-.045,x1-x0,.09);wall((x1+3.03)/2,y1+.045,x1-3.03,.09);wall(2.03,y1+.045,.18,.09);B(fix,2.57,y1+.045,2.44,.94,.09,.52,ivory);B(fix,3.9,17.7,2.73,4.05,3.64,.07,cream);
for(let i=0;i<11;i++)B(fix,x0+.2+i*.37,y0+.016,.43,.022,.034,.78,'#8aa18e');
B(fix,4.7,y1-.035,1.65,1.55,.07,.99,dark);B(fix,4.7,y1-.08,1.65,1.45,.025,.9,'#a8cccb');for(let i=-3;i<=3;i++)B(fix,4.7,y1-.105,1.65+i*.117,1.50,.045,.028,'#887862');B(fix,4.7,y1-.12,1.65,.048,.04,.95,oak);
for(const [x,ti] of [[3.65,5],[4.34,6]]){B(fix,x,y0+.03,1.63,.55,.06,.78,dark);face(fix,[x,y0+.066,1.63],[-.24,0,0],[0,0,.36],ti)}
function table(x,y,w,d,h){B(fix,x,y,h-.037,w,d,.073,oak);B(fix,x,y,h-.095,w-.05,d-.06,.05,dark);for(let i of [-1,1])for(let j of [-1,1])B(fix,x+i*(w/2-.055),y+j*(d/2-.055),h*.47,.064,.064,h*.94,wood)}
table(5.34,18.0375,.88,1.455,.777);table(5.21,18.99,.88,.45,.777);
const G=(id,p,target=id,on=true)=>grp(id,p,target,on);
let l=G('letter',[5.02,18.87,.779]);B(l,0,0,.004,.23,.26,.008,cream);face(l,[0,0,.009],[0,-.113,0],[.129,0,0],1);
const cabinet=[5.38,16.85],drawerIds=['drawer','drawer2','drawer3','drawer4'],widthScale=.83,depthScale=.86;
function drawerBox(g,x,y){return(u,v,z,width,depth,h,color)=>B(g,x+v*depthScale,y+u*widthScale,z,depth*depthScale,width*widthScale,h,color)}
PME_DRAWERS.shell(drawerBox(fix,...cabinet),oak,wood);
drawerIds.forEach((k,i)=>{const g=G(k,[...cabinet,PME_DRAWERS.base(i+1)]);PME_DRAWERS.tray(drawerBox(g,0,0),oak,brass)});
let sheet=G('paper',[cabinet[0]-.19*depthScale,cabinet[1],PME_DRAWERS.base(1)+.004],'paper',false);B(sheet,0,0,.0035,.22,.26,.007,'#fff6dd');
let pl=G('plate',SPEC.plate);B(pl,0,0,0,.45,.45,.025,'#727770');for(let d of [-1,1]){B(pl,d*.205,0,.015,.04,.45,.006,'#efcb50');B(pl,0,d*.205,.015,.37,.04,.006,'#efcb50')}B(pl,0,0,.016,.36,.36,.009,'#92948a');
const ball=G('ball',SPEC.ball);E(ball,0,0,0,.119,.119,.119,'#397ca2',24);for(let [dx,dy] of [[-.027,-.01],[.022,-.03],[.01,.023]])E(ball,dx,dy,.113-.6*(Math.abs(dx)+Math.abs(dy))*.12,.012,.012,.006,'#243e48',10);
let tw=G('writer',SPEC.writer);B(tw,0,0,0,.26,.42,.11,'#456b5d');B(tw,.06,0,.055,.07,.42,.055,ink);B(tw,.095,0,.092,.047,.44,.035,'#37473f');for(let j=0;j<2;j++)for(let i=0;i<5;i++){B(tw,-.077+j*.046,(i-2)*.065,.068,.035,.049,.024,ivory);B(tw,-.074+j*.046,(i-2)*.065,.082,.013,.021,.003,ink)}
let output=G('output',SPEC.output,'writer',false);face(output,[0,0,0],[0,-.112,0],[0,0,.13],8);
const colors=['#be4743','#4f85ae','#6f9b65','#eac454'];SPEC.mats.forEach((p,i)=>{let g=G('mat'+i,p);B(g,0,0,0,.16,.16,.007,colors[i])});
let chest=G('box',[2.6,17.35,0]);B(chest,0,0,.028,.48,.64,.05,'#703f35');for(let j of [-1,1]){B(chest,j*.226,0,.105,.027,.64,.18,red);B(chest,0,j*.307,.105,.44,.026,.18,red)}B(chest,.244,0,.12,.011,.09,.067,brass);let lid=G('lid',[2.365,17.35,.2],'box');B(lid,.235,0,.012,.5,.66,.031,red);B(lid,.31,0,.045,.035,.13,.03,ink);
const names=['octopus','turtle','panda','crab'];let cast=G('cast',[2.585,17.35,.0545],'cast',false);face(cast,[0,0,0],[0,-.145,0],[.055,0,0],4);
for(const [i,id] of names.entries()){const g=G(id,SPEC.toys[id],id,false),size=.85;const sphere=(x,y,z,a,b,c,co)=>E(g,x*size,y*size,z*size,a*size,b*size,c*size,co,12);if(id==='panda'){sphere(0,0,.036,.049,.044,.054,cream);sphere(.012,0,.104,.049,.051,.043,cream);for(let j of [-1,1]){sphere(.008,j*.042,.138,.017,.014,.017,ink);sphere(.048,j*.025,.108,.009,.015,.014,ink);sphere(0,j*.043,.038,.018,.018,.041,ink)}}if(id==='turtle'){sphere(0,0,.035,.071,.051,.041,'#66824b');sphere(.069,0,.042,.031,.026,.025,'#9bad5c');for(let j of [-1,1])for(let k of [-1,1])sphere(j*.038,k*.044,.012,.021,.022,.012,'#819653')}if(id==='octopus'){sphere(0,0,.057,.04,.041,.049,'#b96464');for(let j=0;j<8;j++){let a=j*Math.PI/4;sphere(.043*Math.cos(a),.043*Math.sin(a),.014,.02,.02,.014,'#bc6863')}for(let j of [-1,1])sphere(.034,j*.015,.067,.006,.006,.007,ink)}if(id==='crab'){sphere(0,0,.03,.045,.059,.027,'#ce7951');for(let j of [-1,1]){sphere(.041,j*.05,.059,.023,.022,.02,'#b65e44');for(let k=-1;k<=1;k++)sphere(k*.024,j*.056,.014,.012,.028,.009,'#bc6f46')}}}
let door=G('exit',[2.12,19.39,0]);B(door,.45,0,1.075,.90,.07,2.15,'#486c60');for(const z of [.55,1.63])B(door,.45,-.043,z,.69,.018,.70,'#577d6c');B(door,.77,-.065,1.02,.085,.035,.23,brass);B(door,.72,-.104,1.04,.16,.036,.035,brass);B(fix,2.57,19.39,2.175,1,.12,.07,cream);for(let x of [2.08,3.05])B(fix,x,19.39,1.1,.065,.12,2.2,cream);let plaque=G('plaque',[3.32,19.365,1.15]);B(plaque,0,0,0,.27,.036,.13,brass);face(plaque,[0,-.019,0],[.126,0,0],[0,0,.057],2);
face(door,[.45,-.055,1.77],[.19,0,0],[0,0,.22],3);
B(fix,4.08,17.74,2.62,1.05,.35,.10,ink);B(fix,4.08,17.74,2.555,.95,.29,.03,'#fff0ca');
B(fix,5.825,17.98,1.62,.055,1.08,.61,'#785640');B(fix,5.788,17.98,1.62,.018,1.02,.55,'#b5946d');face(fix,[5.774,18.27,1.63],[0,-.146,0],[0,0,.213],5);face(fix,[5.774,17.95,1.65],[0,-.124,0],[0,0,.18],6);face(fix,[5.774,17.67,1.56],[0,-.114,0],[0,0,.125],9);for(let y of [18.27,17.95,17.67])E(fix,5.768,y,1.78,.012,.014,.014,brass,10);
B(fix,5.55,16.85,.846,.34,.56,.032,'#324c4c');for(let i=0;i<5;i++){const h=.21+.035*(i%3);B(fix,5.58,16.69+i*.068,.866+h/2,.14,.061,h,[ink,'#89564e','#55766d','#655774','#c1915a'][i]);B(fix,5.507,16.69+i*.068,.9,.005,.055,.012,brass)}
E(fix,5.53,18.95,.798,.085,.085,.017,ink);B(fix,5.53,18.95,.948,.028,.028,.28,brass);E(fix,5.51,18.95,1.103,.09,.13,.049,'#436b56');
B(fix,4.75,19.04,.47,.38,.36,.075,'#3d5850');B(fix,4.53,19.04,.68,.06,.36,.31,'#476459');for(let i of [-1,1])for(let j of [-1,1])B(fix,4.75+i*.145,19.04+j*.13,.225,.037,.037,.45,dark);

const bounds=[x0,x1,y0,y1],obstacles=[[4.90,17.31,5.78,18.765],[4.77,18.765,5.65,19.22],[5.0,16.44,5.76,17.25],[2.35,17.02,2.85,17.68]];
initial.push(...meshes.map(()=>1));return {groups,initial,meshes,ids,labels,verts:new Float32Array(verts),atlas,reprint:print,origin:SPEC.origin,yaw:SPEC.yaw,bounds,obstacles,cabinet,drawerIds,depthScale,widthScale}
})();