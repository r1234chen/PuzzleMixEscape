const PME_DRAWERS=Object.freeze({
 travel:.49,
 base(part){return .61-.15*(part-1)},
 shell(box,wood,dark){
  box(0,.39,.40,.92,.055,.80,wood);for(const sign of [-1,1])box(sign*.465,0,.399,.042,.80,.798,wood);
  box(0,0,.075,.93,.8,.15,dark);box(0,0,.809,.97,.88,.038,wood);box(0,-.39,.758,.905,.055,.064,dark);
  for(let j=1;j<4;j++)box(0,-.355,this.base(j)-.03,.90,.04,.025,dark)
 },
 tray(box,wood,gold){
  box(0,0,-.012,.86,.80,.032,'#c5a17c');for(const sign of [-1,1])box(sign*.423,0,.055,.030,.80,.13,wood);
  box(0,.39,.055,.85,.032,.13,wood);box(0,-.40,.045,.892,.045,.145,wood);box(0,-.431,.046,.19,.055,.04,gold)
 }
});