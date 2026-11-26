const SINGLE={n:HALL.n,nodes:{}};
const RULES=(()=>{
const N=SINGLE.nodes,open={},unlocked={},bag=[],stock=Object.fromEntries(HALL.items.filter(x=>x.key).map(x=>[x.id,'home']));let held=null,prompt=null,text='',won=false,pressed=false;
const t=(e,z)=>document.documentElement.lang==='zh-CN'?z:e;
function operate(k){let a=N[k];if(!a||won)return;if(a.parent&&!open[a.parent])return;
if(a.kind==='switch'){pressed=!pressed;if(unlocked[HALL.switchTo]){text=t('The switch clicks; the remote latch is already released.','开关响了一声，远处的门闩已经解开。');return}unlocked[HALL.switchTo]=true;text=t('Click. A latch releases in another room.','咔哒一声，另一间房的门闩松开了。');return}
if(a.kind==='key'){if(stock[k]==='home'){stock[k]='hand';bag.push(k);held=k;text=t('You picked up the brass key.','已拿起黄铜钥匙。')}return}
if(a.gate?.code&&!unlocked[k]){prompt=k;text=t('Enter the combination.','请输入密码。');return}
if(a.gate?.switch&&!unlocked[k]){text=t('Locked. There is no keyhole or keypad.','门闩扣着。这扇门没有钥匙孔，也没有密码键盘。');return}
if(a.gate?.key&&!unlocked[k]){if(held===a.gate.key){unlocked[k]=true;text=t('The key turns. Open the exit door.','锁已解开，再按 E 打开出口。')}else{text=t('The door is locked.','门锁着。')}return}
if(a.kind==='paper'){text=t(a.en,a.zh);return}
if(a.kind==='door'||a.kind==='drawer'){open[k]=!open[k];text=open[k]?t('Opened.','已打开。'):t('Closed.','已关闭。');if(k==='exit'&&open[k]){won=true;text=t('You opened the exit.','你打开了出口。')}}
}
return {stock,bag,draws:{},open,unlocked,operate,select(k){held=bag.includes(k)?k:null},submit(s){if(!prompt||String(s).trim()!==N[prompt].gate.code){text=t('Incorrect combination.','密码不对。');return false}unlocked[prompt]=true;prompt=null;text=t('Unlocked. Interact again.','已解锁，再按 E 操作。');return true},shut(){prompt=null},get prompt(){return prompt},get won(){return won},get held(){return held},get text(){return text},get pressed(){return pressed},get mode(){return 'code'}}
})();