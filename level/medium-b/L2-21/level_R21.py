import math
import numpy as np
from PIL import Image,ImageDraw
from easy88_core import make_level,reachable_approach
from easy88_scene import EasyScene
from font_utils import load_font
SPEC={'id':'R21','title':'Coffee Equipment Store','chinese_title':'咖啡器具备货间','theme':'coffee','size':[5.,4.8],
'door':{'side':'east','start':.98,'width':1.04},'start':[3.75,1.5,1.35],'start_yaw':180,'floor':'tile',
'stages':[
{'kind':'cup_orient','name':'cup drying tray','wall':'north','initial':[2,3],'target':[0,1],'moduli':[4,4],'auto':True,'clue_text':''},
{'kind':'liquid_read','name':'graduated cylinder cabinet','wall':'west','answer':'0240','clue_text':''},
{'kind':'sequence','name':'coffee pattern chest','wall':'south','options':['red_circle','blue_stripe','yellow_dot','green_grid','purple_star','white_wave'],'answer':[0,1,1,2],'length':4,'clue_text':''}]}
SIEVE_OPENINGS=[.004,.026];BEAN_DIAMETER=.012;KEY_BOW_DIAMETER=.066
SPEC['stages'][2].update(kind='assign',name='coffee bean sieve',items=[{'id':'fine','name':'fine coffee sieve'},{'id':'coarse','name':'coarse coffee sieve'}],slots=1,target=[1],setup={'kind':'pour','item':'bean_tin','item_name':'coffee bean tin','gate':False},clue_text='')
for field in ['options','answer','length']:SPEC['stages'][2].pop(field,None)
Game,_S,_T,exit_test,cpu_check=make_level(SPEC)
TITLE=SPEC['title'];LEVEL_ID=SPEC['id'];START=SPEC['start'];START_YAW=SPEC['start_yaw']
CAP=150;OBSERVATION_SIZE=(640,360);VISUAL_ONLY=False;READ_ENABLED=True;READ_FEEDBACK_TEXT=True
Game.LABELS.update({'s1_clue':'cup tray reference photo','s1_control_0':'left cup turntable button','s1_control_1':'right cup turntable button','s2_cover':'cylinder cabinet door','s2_clue':'cylinder waterline and own scale','s2_lock':'millilitre pattern case lock','s3_cover':'pattern reference cover','s3_clue':'four colour and texture cells','s3_confirm':'pattern check','s3_reset':'clear pattern','key_box':'coffee key drawer','key':'brass door key'})
LABELS=Game.LABELS
_act=Game.act
def coffee_act(self,a):
 r=_act(self,a)
 if a.get('_validated364') and a.get('action')=='unlock' and a.get('_hit364')=='s2_lock':self.states[1]['entered_code']=str(a.get('code',''))
 return r
Game.act=coffee_act
_old_coffee_act=Game.act

def _sieve_act(self,a):
 key=a.get('_hit364');kind=a.get('action')
 if not a.get('_validated364'):return _old_coffee_act(self,a)
 from action_feedback import failure_for,NO_ITEM
 def fail():return {'ok':False,'text':failure_for(kind)}
 def ok():return {'ok':True,'text':''}
 st=self.states[2]
 if key=='s2_handle_drawer':
  if kind not in ['open','close'] or kind=='open' and not self.solved[0]:return fail()
  self.states[0]['handle_drawer_open']=kind=='open';return ok()
 if key=='s2_tool':
  if kind!='take' or not self.states[0].get('handle_drawer_open') or key in self.taken:return fail()
  self.taken.add(key);self.holding.append(key);return ok()
 if key=='s2_cover':
  if kind=='use':
   item=self._resolve_item(a.get('item'))
   if item is None:return {'ok':False,'text':NO_ITEM}
   if item!='s2_tool':return fail()
   self.holding.remove(item);self.states[1]['handle_installed']=True;return ok()
  if kind=='open' and not self.states[1].get('handle_installed'):return fail()
 if key=='key':
  if kind=='take' and self.solved[2] and key not in self.taken:self.taken.add(key);self.holding.append(key);return ok()
  return fail()
 if str(key).startswith('s3_') and key not in ['s3_cover']:
  if not self.opened['s3_cover']:return fail()
  if kind=='use' and key in ['s3_slot_0','s3_setup','s3_item_0','s3_item_1'] and self._resolve_item(a.get('item'))=='s3_tool':
   j=st.get('sieve')
   if j is None or self.solved[2] or key.startswith('s3_item_') and int(key[-1])!=j:return fail()
   if not BEAN_DIAMETER<SIEVE_OPENINGS[j]<KEY_BOW_DIAMETER:return fail()
   st['beans_passed']=True;st['setup_used']=True;st['assignment']={0:j};self.solved[2]=True;return ok()
  if key in ['s3_item_0','s3_item_1']:
   if kind!='take' or key in self.holding:return fail()
   j=int(key[-1])
   if self.solved[2]:return fail()
   if st.get('sieve')==j:st['sieve']=None
   self.taken.add(key);self.holding.append(key);return ok()
  if key=='s3_tool':
   if kind!='take' or key in self.holding or self.solved[2]:return fail()
   self.taken.add(key);self.holding.append(key);return ok()
  if key=='s3_slot_0' and kind=='use':
   item=self._resolve_item(a.get('item'))
   if item not in ['s3_item_0','s3_item_1']:return fail()
   old=st.get('sieve')
   if old is not None:self.holding.append('s3_item_'+str(old))
   st['sieve']=int(item[-1]);self.holding.remove(item);return ok()
  if key=='s3_setup' and kind=='use':
   item=self._resolve_item(a.get('item'));j=st.get('sieve')
   if item!='s3_tool' or j is None:return fail()
   if not BEAN_DIAMETER<SIEVE_OPENINGS[j]<KEY_BOW_DIAMETER:return fail()
   st['beans_passed']=True;st['setup_used']=True;st['assignment']={0:j};self.solved[2]=True;return ok()
  return fail()
 return _old_coffee_act(self,a)
Game.act=_sieve_act
LABELS.update({'s2_handle_drawer':'drawer below cup tray','s2_tool':'long cabinet pull','s3_clue':'bean tin and sieve apertures','s3_setup':'sieve over the bowl','s3_slot_0':'collecting bowl rim','s3_tool':'coffee bean tin'})

def cup_geometry():
    pts=[];faces=[];N=40
    for r,z in [(.069,.012),(.075,.145),(.061,.145),(.055,.025)]:
        pts.extend([(r*math.cos(t*2*math.pi/N),r*math.sin(t*2*math.pi/N),z) for t in range(N)])
    for k in range(3):
        for j in range(N):faces.append([k*N+j,k*N+(j+1)%N,(k+1)*N+(j+1)%N,(k+1)*N+j])
    faces.append(list(range(3*N,4*N)))
    body=(np.asarray(pts),faces)
    pts=[];faces=[];M=28;T=8
    for k in range(M):
        a=k*2*math.pi/M;rr=.086+.046*math.cos(a);zz=.080+.052*math.sin(a)
        for j in range(T):
            b=j*2*math.pi/T;pts.append([.009*math.sin(b),-rr-.009*math.cos(b)*math.cos(a),zz+.009*math.cos(b)*math.sin(a)])
    for k in range(M):
        for j in range(T):faces.append([k*T+j,k*T+(j+1)%T,((k+1)%M)*T+(j+1)%T,((k+1)%M)*T+j])
    return [body,(np.asarray(pts),faces)]
class Scene(EasyScene):
    def __init__(self,og,run):
        super().__init__(og,run,SPEC);self.views={};self.focus={};self.labels={};self.drawers={};self.lock_shaders={};self.lock_values={};self.expanded=[];self.screen_signature=None
    def palette(self):
        super().palette()
        for n,c in [('coffee_blue',(.22,.37,.42)),('coffee_white',(.75,.73,.63)),('felt',(.28,.34,.27)),('coffee_water',(.18,.43,.46)),('water_top',(.38,.61,.60)),('water_meniscus',(.035,.13,.14))]:self.mat(n,c,rough=.85)
        self.mat('clear_cylinder',(.79,.87,.86),rough=.08,opacity=.12)
    def reg_at(self,key,node,label,view,focus=None):
        self.reg(key,node);self.views[key]=list(view);self.labels[key]=label
        if focus is not None:self.focus[key]=list(focus)
        return node
    def flat(self,name,parent,pos,w,h,im,horizontal=False):
        path=self.tex/(name+'.png');im.save(path)
        return self.plane(name,pos,w,h,(1,0,0),(0,1,0) if horizontal else (0,0,1),None,parent,material=self.image_mat('r21_'+name,path))
    def text_image(self,value,w,h,bg=(217,213,189),ink=(35,54,45)):
        ih=360;iw=max(180,int(round(ih*w/h)));im=Image.new('RGB',(iw,ih),bg)
        d=ImageDraw.Draw(im);size=int(ih*.70)
        while size>12:
            b=d.textbbox((0,0),str(value),font=load_font(size))
            if b[2]-b[0]<=iw*.85 and b[3]-b[1]<=ih*.78:break
            size-=8
        d.text((iw/2,ih/2),str(value),font=load_font(size),fill=ink,anchor='mm')
        return im
    def text(self,name,parent,pos,w,h,value):
        return self.flat(name,parent,pos,w,h,self.text_image(value,w,h))
    def numeric_lock(self,key,parent,pos,digits,view):
        node=self.group(key,pos,parent)
        self.box('numeric_lock_bezel',[0,0,0],[.31,.038,.14],'iron',node)
        self.flat(key+'_display',node,[0,-.0215,0],.27,.088,self.text_image('0'*digits,.27,.088,(47,67,56),(224,228,191)))
        mat=self.mats['r21_'+key+'_display']
        self.lock_shaders[key]=self.S.Shader(self.stage.GetPrimAtPath(str(mat.GetPath())+'/texture'))
        self.lock_values[key]='0'*digits
        self.reg_at(key,node,LABELS[key],view)
        return node
    def drawer(self,key,parent,front,z,width=1.10,depth=.43):
        x,y=front
        for xx in [x-width/2-.025,x+width/2+.025]:
            self.box(key+'_housing_side',[xx,y+depth/2,z],[.035,depth+.035,.245],'wood',parent)
        self.box(key+'_housing_floor',[x,y+depth/2,z-.128],[width+.08,depth+.04,.026],'darkwood',parent)
        self.box(key+'_housing_back',[x,y+depth,z],[width+.08,.03,.245],'wood',parent)
        self.box(key+'_housing_top',[x,y+depth/2,z+.1275],[width+.08,depth+.04,.025],'wood',parent)
        for xx in [x-width/2,x+width/2]:
            self.box(key+'_fixed_slide',[xx,y+depth/2,z-.045],[.016,depth-.01,.026],'steel',parent)
        node=self.group(key,[x,y,z],parent)
        self.box(key+'_bottom',[0,depth/2,-.113],[width-.055,depth,.025],'wood',node)
        for xx in [-width/2,width/2]:
            self.box(key+'_side',[xx,depth/2,-.005],[.025,depth,.235],'wood',node)
            self.box(key+'_slide',[xx,depth/2,-.045],[.012,depth-.01,.022],'steel',node)
        self.box(key+'_rear',[0,depth,-.005],[width,.025,.235],'wood',node)
        face=self.group(key+'_face',parent=node)
        self.box('drawer_front',[0,0,0],[width+.04,.045,.25],'paint',face)
        self.box('drawer_pull',[-.26,-.055,.01],[.19,.045,.028],'brass',face)
        self.drawers[key]=(node,[x,y,z])
        return node,face


    def reference_photo(self):
        im=Image.new('RGB',(1400,900),(199,190,163));dr=ImageDraw.Draw(im)
        eye=np.array([0.,-1.40,1.6]);aim=np.array([0.,0.,.06]);fwd=(aim-eye)/np.linalg.norm(aim-eye)
        right=np.array([1.,0.,0.]);up=np.cross(right,fwd)
        def proj(p):
            q=np.asarray(p)-eye;z=q@fwd
            return (700+1900*(q@right)/z,450-1900*(q@up)/z)
        dr.polygon([proj(x) for x in [(-.47,-.27,0),(.47,-.27,0),(.47,.27,0),(-.47,.27,0)]],fill=(111,83,53),outline=(73,57,40),width=7)
        tris=[]
        for j,angle in enumerate([0,math.pi/2]):
            c,s=math.cos(angle),math.sin(angle);R=np.array([[c,-s,0],[s,c,0],[0,0,1]])
            for pts,faces in cup_geometry():
                pp=pts@R.T+np.array([(j-.5)*.43,0,.016])
                for face in faces:
                    p=pp[face];normal=np.cross(p[1]-p[0],p[2]-p[0]);normal=normal/max(1e-9,np.linalg.norm(normal))
                    light=.66+.34*abs(normal@np.array([-.3,-.4,.86]))
                    colour=tuple(int(v*light) for v in (77,119,128))
                    tris.append((float((p.mean(0)-eye)@fwd),[proj(x) for x in p],colour))
        for z,p,c in sorted(tris,reverse=True,key=lambda a:a[0]):dr.polygon(p,fill=c)
        arrow=[(-.035,-.13,.003),(.035,-.13,.003),(.035,-.20,.003),(.07,-.20,.003),(0,-.255,.003),(-.07,-.20,.003),(-.035,-.20,.003)]
        dr.polygon([proj(p) for p in arrow],fill=(229,225,200))
        return im
    def pattern(self,index):
        im=Image.new('RGB',(250,250),(224,220,191));d=ImageDraw.Draw(im)
        cols=[(155,53,43),(49,85,126),(194,155,35),(51,116,69),(108,62,135),(230,228,207)]
        c=cols[index];d.rectangle((8,8,242,242),fill=c)
        if index==0:d.ellipse((63,63,187,187),outline=(240,223,191),width=13)
        elif index==1:
            for x in range(-100,250,65):d.line((x,240,x+150,10),fill=(219,226,208),width=18)
        elif index==2:
            for x in [65,125,185]:
                for y in [65,125,185]:d.ellipse((x-10,y-10,x+10,y+10),fill=(76,67,41))
        elif index==3:
            for x in range(38,250,43):d.line((x,10,x,240),fill=(216,225,194),width=8);d.line((10,x,240,x),fill=(216,225,194),width=8)
        elif index==4:
            points=[(125+80*math.sin(t*math.pi/5),125-80*math.cos(t*math.pi/5)) if t%2==0 else (125+35*math.sin(t*math.pi/5),125-35*math.cos(t*math.pi/5)) for t in range(10)];d.polygon(points,fill=(231,223,196))
        else:
            for y in [60,125,190]:d.line([(x,y+18*math.sin(x/24)) for x in range(15,240,3)],fill=(67,105,111),width=11)
        return im
    def pattern_screen(self,buffer):
        im=Image.new('RGB',(1200,500),(29,45,39));d=ImageDraw.Draw(im)
        for j in range(4):
            x=365+(j%2)*240;y=70+(j//2)*135
            d.rectangle((x-65,y-55,x+65,y+55),outline=(129,155,130),width=3)
            if j<len(buffer):im.paste(self.pattern(buffer[j]).resize((108,98)),(x-54,y-49))
        d.text((100,140),'↻',font=load_font(105),fill=(224,224,191),anchor='mm');d.text((1100,140),'✓',font=load_font(105),fill=(224,224,191),anchor='mm')
        for j in range(6):im.paste(self.pattern(j).resize((176,176)),(12+j*200,308))
        p=self.tex/('coffee_patterns_'+(''.join(map(str,buffer)) or 'empty')+'.png');im.save(p);return p
    def screen_piece(self,key,rect,target=True):
        x0,y0,x1,y1=rect;pts=[((x/1200-.5)*.90,-.12+(.5-y/500)*.375,.783) for x,y in [(x0,y1),(x1,y1),(x1,y0),(x0,y0)]]
        uv=[(x0/1200,1-y1/500),(x1/1200,1-y1/500),(x1/1200,1-y0/500),(x0/1200,1-y0/500)]
        n=self.mesh(key+'_screen',pts,[[0,1,2,3]],self.screen_mat,self.chest,uv=uv)
        if target:self.reg_at(key,n,LABELS.get(key,key.replace('_',' ')),[2.5,1.5])
    def long_pull(self,name,parent,pos):
        n=self.group(name,pos,parent);self.cylinder('pull_grip',[0,0,0],.010,.19,'steel','z',n,n=20)
        for z in [-.085,.085]:self.cylinder('pull_standoff',[0,.025,z],.010,.050,'steel','y',n,n=20)
        return n
    def sieve(self,name,parent,pos,opening):
        n=self.group(name,pos,parent);bar=.005;step=opening+bar;count=int(.30/step);extent=count*step
        for side in [-1,1]:
            self.box('sieve_frame_x',[side*(extent/2+.008),0,0],[.018,extent+.036,.018],'steel',n)
            self.box('sieve_frame_y',[0,side*(extent/2+.008),0],[extent+.036,.018,.018],'steel',n)
        for j in range(count+1):
            q=-extent/2+j*step;self.box('real_mesh_bar_x',[q,0,0],[bar,extent,.006],'steel',n);self.box('real_mesh_bar_y',[0,q,0],[extent,bar,.006],'steel',n)
        for x in [-.185,.185]:self.box('sieve_support_tab',[x,0,0],[.08,.065,.018],'steel',n)
        return n
    def build(self,g):
        self.room_shell('coffee_store',size=(5.,4.8),openings={'east':[(.96,2.06)]})
        self.box('continuous_subfloor',[2.5,2.4,-.06],[5.15,4.95,.10],'darkwood')
        self.table('cup_preparation_bench',(1.65,4.38),(2.6,.66),height=.72)
        self.tray=self.group('cup_drying_tray',[1.50,4.34,.775])
        self.box('wood_cup_tray',[0,0,0],[.96,.58,.035],'darkwood',self.tray)
        self.cups=[]
        for j in range(2):
            x=(j-.5)*.43
            self.cylinder('turntable_base',[x,0,.030],.105,.025,'steel','z',self.tray,n=40)
            cup=self.group('fixed_cup_'+str(j),[x,0,.043],self.tray)
            for k,(pts,faces) in enumerate(cup_geometry()):self.mesh('hollow_cup_body' if k==0 else 'cup_handle',pts,faces,'coffee_blue',cup)
            self.cups.append(cup)
            button=self.group('cup_button_'+str(j),[x,-.279,.012],self.tray)
            self.box('button_cap',[0,0,0],[.11,.026,.09],'iron',button)
            self.text('cup_rotation_mark_'+str(j),button,[0,-.014,0],.09,.07,'↻')
            self.reg_at('s1_control_'+str(j),button,LABELS['s1_control_'+str(j)],[1.5,3.5],[1.5,4.34,.88])
        arrow=Image.new('RGB',(180,240),(117,91,61));d=ImageDraw.Draw(arrow);d.polygon([(65,20),(115,20),(115,135),(150,135),(90,222),(30,135),(65,135)],fill=(230,223,192))
        self.flat('tray_forward',self.tray,[0,-.15,.019],.09,.12,arrow,True)
        photo=self.group('cup_reference_frame',[1.50,4.72,1.51])
        self.box('photo_wood_frame',[0,0,0],[.92,.035,.62],'wood',photo)
        p=self.flat('same_mesh_cup_reference',photo,[0,-.020,0],.86,.56,self.reference_photo())
        self.reg_at('s1_clue',p,'cup tray reference photo',[1.5,3.5],[1.5,4.70,1.51])
        self.add_obstacle(.28,4.01,3.02,4.77)

        self.handledrawer,handlefront=self.drawer('cup_handle_drawer',None,(1.50,4.04),.54,.90,.43)
        self.reg_at('s2_handle_drawer',handlefront,'drawer below cup tray',[1.5,3.5],[1.5,4.04,.54])
        self.box('handle_pad',[0,.20,-.035],[.78,.32,.14],'felt',self.handledrawer)
        self.loose_handle=self.long_pull('loose_cabinet_pull',self.handledrawer,[0,.20,.069]);self.transform(self.loose_handle,rpy=[-90,0,0]);self.reg_at('s2_tool',self.loose_handle,'long cabinet pull',[1.5,3.5])
        self.cup_red=self.cylinder('cup_drawer_red',[.34,-.027,0],.014,.009,'red_led','y',handlefront,n=20);self.cup_green=self.cylinder('cup_drawer_green',[.34,-.027,0],.014,.009,'green','y',handlefront,n=20)
        self.table('cylinder_cabinet_bench',(.43,2.15),(.68,1.35),height=.72)
        self.cab=self.group('graduated_cylinder_case',[.36,2.15,.755]);self.transform(self.cab,rpy=[0,0,90])
        for x in [-.47,.47]:self.box('cabinet_side',[x,.04,.4513],[.035,.48,.9026],'wood',self.cab)
        for z in [0,.9126]:self.box('cabinet_floor_roof',[0,.04,z],[.97,.48,.030],'wood',self.cab)
        self.box('cabinet_back',[0,.265,.4513],[.97,.035,.9026],'paint',self.cab)
        self.cabdoor=self.group('cylinder_door_hinge',[-.49,-.215,.015],self.cab)
        panel=self.group('cylinder_door_face',parent=self.cabdoor)
        self.box('opaque_cylinder_door',[.49,0,.4413],[.98,.035,.8826],'paint',panel)
        for z in [.315,.485]:self.cylinder('missing_pull_socket',[.80,-.021,z],.012,.006,'iron','y',panel,n=20)
        self.fitted_handle=self.long_pull('installed_pull',panel,[.80,-.060,.40])
        self.reg_at('s2_cover',panel,'cylinder cabinet door',[1.5,2.25],[.575,2.15,1.3926])
        self.box('eye_level_cylinder_shelf',[0,.04,.3576],[.94,.45,.030],'wood',self.cab)
        cy=self.group('fixed_measuring_cylinder',[0,-.005,.3726],self.cab)
        self.cylinder('cylinder_base',[0,0,.015],.11,.03,'coffee_white','z',cy,n=48)
        self.cylinder('transparent_wall',[0,0,.23],.076,.40,'clear_cylinder','z',cy,n=64)
        self.cylinder('real_water',[0,0,.04+.38*.48/2],.067,.38*.48,'coffee_water','z',cy,n=64)
        self.cylinder('waterline_surface',[0,0,.04+.38*.48],.067,.003,'water_top','z',cy,n=64)
        for t in np.linspace(-5*math.pi/6,-math.pi/6,24):
            a=float(t);b=a+math.pi/36
            self.tube('actual_front_meniscus',[.068*math.cos(a),.068*math.sin(a),.04+.38*.48],[.068*math.cos(b),.068*math.sin(b),.04+.38*.48],.0025,'water_meniscus',cy)
        for z in [.035,.435]:
            for t in np.linspace(0,2*math.pi,48,endpoint=False):
                a=float(t);b=a+2*math.pi/48;self.tube('cylinder_rim',[.077*math.cos(a),.077*math.sin(a),z],[.077*math.cos(b),.077*math.sin(b),z],.004,'steel',cy)
        scale=Image.new('RGB',(430,1500),(222,220,190));d=ImageDraw.Draw(scale)
        for ml in range(0,501,10):
            y=1450-ml/500*1400;d.line((8,y,95 if ml%50 else 155,y),fill=(30,54,45),width=4)
            if ml%50==0:d.text((165,y),str(ml),font=load_font(83),fill=(30,54,45),anchor='lm')
        d.text((350,30),'ml',font=load_font(62),fill=(30,54,45),anchor='mm')
        self.flat('cylinder_own_scale',cy,[.070,-.077,.23],.11,.40714285714285714,scale)
        self.reg_at('s2_clue',cy,'waterline at the cylinder own scale',[1.5,2.25],[.365,2.15,1.35])
        self.add_obstacle(.05,1.42,.82,2.88)

        self.table('coffee_pattern_bench',(2.5,.41),(2.55,.66),height=.72)
        self.chest=self.group('coffee_pattern_chest',[2.5,.40,0]);self.transform(self.chest,rpy=[0,0,180])
        self.box('tool_case_floor',[0,0,.765],[2.32,.55,.025],'wood',self.chest)
        for x in [-1.16,1.16]:self.box('tool_case_side',[x,0,.90],[.025,.55,.25],'wood',self.chest)
        for y in [.275]:self.box('tool_case_wall',[0,y,.90],[2.32,.025,.25],'wood',self.chest)
        self.samplelid=self.group('sample_cover_hinge',[0,.275,1.035],self.chest);self.box('tool_case_lid',[0,-.275,0],[2.38,.58,.025],'paint',self.samplelid)
        self.box('tool_case_front_apron',[0,-.55,-.135],[2.32,.025,.25],'wood',self.samplelid)
        self.box('tool_case_pull',[0,-.56,0],[.15,.035,.028],'brass',self.samplelid);self.reg_at('s3_cover',self.samplelid,'sieve case lid',[2.5,1.5],[2.5,.4,1.035])
        self.numeric_lock('s2_lock',self.samplelid,[0,-.567,-.125],4,[2.5,1.5]);self.text('lock_unit',self.samplelid,[.32,-.568,-.125],.23,.055,'ml / 0000')
        bowl=self.group('coffee_collecting_bowl',[0,.01,.79],self.chest);self.cylinder('bowl_body',[0,0,.065],.18,.13,'coffee_white','z',bowl,n=40);self.cylinder('bowl_inside',[0,0,.133],.163,.005,'felt','z',bowl,n=40);self.cylinder('bowl_foot',[0,0,-.006],.10,.012,'coffee_white','z',bowl,n=36)
        for j in range(48):
            u=j*2*math.pi/48;v=(j+1)*2*math.pi/48;self.tube('bowl_lip',[.177*math.cos(u),.177*math.sin(u),.135],[.177*math.cos(v),.177*math.sin(v),.135],.006,'coffee_white',bowl)
        self.reg_at('s3_slot_0',bowl,'collecting bowl rim',[2.5,1.5])
        self.sieves=[]
        for j,opening in enumerate(SIEVE_OPENINGS):
            n=self.sieve('coffee_sieve_'+str(j),self.chest,[(j-.5)*1.10,0,.787],opening);self.sieves.append(n);self.reg_at('s3_item_'+str(j),n,LABELS['s3_item_'+str(j)],[3.0 if j==0 else 2.0,1.25])
        self.mount=self.group('sieve_pouring_target',[0,.01,.94],self.chest);self.box('sieve_rim_target',[0,-.18,0],[.35,.015,.018],'steel',self.mount);self.reg_at('s3_setup',self.mount,'sieve over the bowl',[2.5,1.5])
        self.tin=self.group('coffee_bean_tin',[-.94,-.02,.778],self.chest);self.cylinder('bean_tin_body',[0,0,.075],.075,.15,'coffee_blue','z',self.tin,n=36);self.cylinder('bean_tin_dark_top',[0,0,.151],.064,.004,'felt','z',self.tin,n=36);self.reg_at('s3_tool',self.tin,'coffee bean tin',[2.5,1.5])
        self.bean_piles=[]
        for name,parent,origin,radius in [('source_beans',self.tin,[0,0,.15],.06),('fallen_beans',self.chest,[0,.01,.83],.14)]:
            pile=self.group(name,origin,parent)
            for j in range(45):
                angle=j*2.399;rr=radius*math.sqrt((j+.5)/45);self.cylinder('visible_coffee_bean',[rr*math.cos(angle),rr*math.sin(angle),.006+(j%3)*.004],BEAN_DIAMETER/2,.009,'darkwood','z',pile,n=10)
            self.bean_piles.append(pile)
        self.key=self.tool('flat_brass_key',self.chest,[-.94,-.02,.932],'key');self.target_nodes.pop('flat_brass_key',None);self.transform(self.key,rpy=[90,0,0]);self.reg_at('key',self.key,'brass door key',[2.5,1.5])
        self.add_obstacle(1.15,.04,3.85,.82)
        stock=self.group('coffee_stock',[4.70,3.55,0]);self.transform(stock,rpy=[0,0,-90])
        for x in [-.45,.45]:self.box('stock_post',[x,0,.55],[.05,.36,1.10],'darkwood',stock)
        for z in [.18,.74,1.12]:self.box('stock_shelf',[0,0,z],[1.05,.39,.035],'wood',stock)
        for j in range(3):self.cylinder('coffee_tin',[(j-1)*.28,0,.865],.10,.22,'coffee_white','z',stock,n=28)
        self.add_obstacle(4.46,2.97,4.99,4.13)
        self.exit_node=self.door('coffee_exit',[4.94,1.,0],1.04);self.door_view=[3.75,1.5]
        self.reg_at('exit',self.exit_node,'exit door',self.door_view,[4.94,1.52,1.12])
        for y in [.98,2.06]:self.box('door_jamb',[4.95,y,1.14],[.17,.065,2.30],'paint')
        self.box('door_top',[4.95,1.52,2.29],[.17,1.15,.065],'paint')
        self.stage_views=[[1.5,3.5],[1.5,2.25],[2.5,1.5]];self.stage_centres=[[1.5,4.34,.87],[.36,2.15,1.35],[2.5,.24,1.03]]
        self.bases=[([1.5,4.34],0),([.36,2.15],90),([2.5,.4],180)];self.sync(g)
    def visible(self,key,g):
        if key=='s2_clue':return bool(g.opened['s2_cover'])
        if key=='s3_clue' or key.startswith('s3_choice_') or key in ('s3_confirm','s3_reset'):return bool(g.opened['s3_cover'])
        if key=='s2_tool':return bool(g.states[0].get('handle_drawer_open')) and key not in g.taken
        if key.startswith('s3_item_'):return bool(g.opened['s3_cover']) and key not in g.holding
        if key in ['s3_tool','s3_slot_0','s3_setup']:return bool(g.opened['s3_cover']) and key not in g.holding
        if key=='key':return bool(g.opened['s3_cover']) and key not in g.taken and (g.solved[2] or 's3_tool' not in g.holding)
        return key in self.target_nodes
    def sync(self,g):
        for j,n in enumerate(self.cups):self.transform(n,rpy=[0,0,90*g.states[0]['angles'][j]])
        self.transform(self.cabdoor,rpy=[0,0,-110 if g.opened['s2_cover'] else 0])
        self.transform(self.samplelid,rpy=[-85 if g.opened['s3_cover'] else 0,0,0])
        value=g.states[1].get('entered_code','0000')
        if self.lock_values['s2_lock']!=value:
            p=self.tex/('coffee_entered_'+value+'.png');self.text_image(value,.27,.088,(47,67,56),(224,228,191)).save(p)
            with self.og.sim.editing_usd():self.lock_shaders['s2_lock'].GetInput('file').Set(str(p))
            self.lock_values['s2_lock']=value
        n,pos=self.drawers['cup_handle_drawer'];self.transform(n,[pos[0],pos[1]-(.42 if g.states[0].get('handle_drawer_open') else 0),pos[2]])
        self.visibility(self.loose_handle,bool(g.states[0].get('handle_drawer_open')) and 's2_tool' not in g.taken);self.visibility(self.fitted_handle,bool(g.states[1].get('handle_installed')))
        self.visibility(self.cup_red,not g.solved[0]);self.visibility(self.cup_green,g.solved[0])
        which=g.states[2].get('sieve')
        for j,n in enumerate(self.sieves):
            self.transform(n,[0,.01,.94] if which==j else [(j-.5)*1.10,0,.787]);self.visibility(n,'s3_item_'+str(j) not in g.holding)
        self.visibility(self.tin,'s3_tool' not in g.holding)
        self.visibility(self.bean_piles[0],not g.solved[2]);self.visibility(self.bean_piles[1],g.solved[2])
        self.transform(self.key,[0,.01,.953] if g.solved[2] else [-.94,-.02,.932])
        self.visibility(self.key,'key' not in g.taken and (g.solved[2] or 's3_tool' not in g.holding))
        self.transform(self.exit_node,rpy=[0,0,90-(103 if g.opened['exit'] else 0)])
        self.centres={}
        for k,n in self.target_nodes.items():
            p=self.triangles(n).reshape(-1,3)
            if p.size:self.centres[k]=((p.min(0)+p.max(0))/2).tolist()
    def candidates(self,g):return self.base_candidates([k for k in self.target_nodes if self.visible(k,g)])
    def view_for(self,key):return self.views.get(key,self.door_view)
    def focus_for(self,key):return self.focus.get(key,self.centres.get(key))
    def label_for(self,key):return self.labels.get(key,LABELS.get(key,key.replace('_',' ')))
    def animate(self,d,before):self.sync(d.game)

def standard(d):
    import heapq
    from observation1280 import FX,FY,CX,CY
    from pixel355 import find_point
    from oracle355 import _edge_clear,_turn_actions,_wrap
    g=d.game;sc=d.scene
    def candidate(key):
        return next((c for c in sc.candidates(g) if c['key']==key),None)
    def centre(key):
        c=candidate(key)
        if c is None:raise RuntimeError('Physical object not currently exposed: '+key)
        return (np.asarray(c['lo'],float)+np.asarray(c['hi'],float))/2
    def focus(key):
        p=sc.focus_for(key) if hasattr(sc,'focus_for') else None
        return np.asarray(centre(key) if p is None else p,float)
    def axis_focus(key,xy=None):
        p=focus(key).copy();xy=np.asarray(d.pos[:2] if xy is None else xy,float)
        k=int(round(math.atan2(p[1]-xy[1],p[0]-xy[0])/(math.pi/2)))%4
        if k in (0,2):p[1]=xy[1]
        else:p[0]=xy[0]
        return p,k
    def route_short(destination,goal_heading,purpose):
        start=tuple(int(round(float(v)/.25)) for v in d.pos[:2])
        goal=tuple(int(round(float(v)/.25)) for v in destination)
        xy=lambda n:(n[0]*.25,n[1]*.25)
        if math.dist(xy(start),d.pos[:2])>.005 or math.dist(xy(goal),destination)>.005:
            raise ValueError('Non-lattice route; no snapping')
        extra=[]
        if g.opened.get('key_box'):
            tri=sc.triangles(sc.target_nodes['key_box'])
            if tri.size:
                lo=tri.reshape(-1,3).min(0);hi=tri.reshape(-1,3).max(0)
                extra=[(lo[:2]-.12,hi[:2]+.12)]
        def blocked(x,y):
            return sc.blocked(x,y,g) or any(lo[0]<x<hi[0] and lo[1]<y<hi[1] for lo,hi in extra)
        if blocked(*xy(start)) or blocked(*xy(goal)):
            raise ValueError('Blocked actual public route endpoint')
        queue=[];cost={};parents={};initial={}
        for k in range(4):
            turns=_turn_actions(_wrap(k*math.pi/2-d.yaw));state=(*start,k)
            value=(len(turns),0.,sum(a['degrees'] for a in turns))
            cost[state]=value;initial[state]=turns;heapq.heappush(queue,(*value,state))
        final=None
        while queue:
            n,dist,angle,state=heapq.heappop(queue)
            if cost[state]!=(n,dist,angle):continue
            x,y,k=state
            if (x,y)==goal and k==goal_heading:final=state;break
            transitions=[]
            for side,dk in [('left',1),('right',-1)]:
                transitions.append(((x,y,(k+dk)%4),{'action':'turn','direction':side,'degrees':90},0.,90))
            for rel,action,steps in [(0,'walk',(4,2,1)),(1,'side_step',(2,1)),(-1,'side_step',(2,1)),(2,'step_back',(2,1))]:
                dx,dy=((1,0),(0,1),(-1,0),(0,-1))[(k+rel)%4]
                for step in steps:
                    end=(x+dx*step,y+dy*step)
                    if not _edge_clear(xy((x,y)),xy(end),blocked):continue
                    a={'action':action,'distance':step*.25}
                    if action=='side_step':a['direction']='left' if rel==1 else 'right'
                    transitions.append(((*end,k),a,step*.25,0))
            for nxt,a,length,turn in transitions:
                value=(n+1,dist+length,angle+turn)
                if value<cost.get(nxt,(math.inf,math.inf,math.inf)):
                    cost[nxt]=value;parents[nxt]=(state,a);heapq.heappush(queue,(*value,nxt))
        if final is None:raise RuntimeError('No legal public action route')
        actions=[];state=final
        while state in parents:
            state,a=parents[state];actions.append(a)
        actions=list(initial[state])+list(reversed(actions))
        if any(a['action'] in ('walk','side_step','step_back') for a in actions) and d.pitch<math.radians(-25):
            d._turn_vertical_to(math.radians(-20),'Look ahead while moving between the furniture')
        for a in actions:d.execute(a,purpose)
    def approach(key,purpose,stay=False):
        view=list(d.pos[:2]) if stay else [round(float(v)*4)/4 for v in sc.view_for(key)]
        if view is None:raise RuntimeError('No physical approach for '+key)
        p,k=axis_focus(key,view)
        if not stay:route_short(view,k,purpose)
        d.aim(p,purpose)
    def observe(key,purpose,stay=False):
        approach(key,purpose,stay);d.append(purpose,18)
    def click(key,kind='press',item=None,code=None):
        c=candidate(key)
        if c is None:raise RuntimeError('Physical object not currently exposed: '+key)
        hit=find_point(key,d.pos,d.quat,d.depth,sc.candidates(g),fx=FX,fy=FY,cx=CX,cy=CY,actor_xy=d.pos[:2],tolerance=.05,mesh_tolerance=.04,grid=41,return_hit=True)
        if hit is None:
            d.aim(centre(key),'Look at the actual visible object')
            hit=find_point(key,d.pos,d.quat,d.depth,sc.candidates(g),fx=FX,fy=FY,cx=CX,cy=CY,actor_xy=d.pos[:2],tolerance=.05,mesh_tolerance=.04,grid=61,return_hit=True)
        reach=1.5 if key=='exit' else 1.2
        if hit is not None and float(hit['distance'])>reach:
            view=reachable_approach(d.pos[:2],d.yaw,hit,lambda x,y:sc.blocked(x,y,g),SPEC['size'],reach)
            route_short(view,axis_focus(key,view)[1],'Approach the actual visible surface')
            d.aim(centre(key),'Look at the reachable object')
            hit=find_point(key,d.pos,d.quat,d.depth,sc.candidates(g),fx=FX,fy=FY,cx=CX,cy=CY,actor_xy=d.pos[:2],tolerance=.05,mesh_tolerance=.04,grid=61,return_hit=True)
        if hit is None or float(hit['distance'])>reach:
            raise RuntimeError('No current visible native pixel within unchanged reach for '+key)
        a={'thought':'Use the clue and the actual room object.','action':kind,'point':hit['point'],'target':LABELS.get(key,key.replace('_',' '))}
        if item is not None:a['item']=LABELS.get(item,item)
        if code is not None:a['code']=str(code)
        return d.execute(a,'Observe the physical response')

    observe('s1_clue','Compare the reference photograph and the tray forward arrow')
    approach('s1_control_0','Orient the two real cup handles')
    for j in range(2):
        for _ in range(2):click('s1_control_'+str(j))
    approach('s2_handle_drawer','Open the drawer directly below the aligned cups');click('s2_handle_drawer','open');click('s2_tool','take')
    approach('s2_cover','Fit the long pull to the two empty mounting sockets');click('s2_cover','use','s2_tool');click('s2_cover','open')
    observe('s2_clue','Read the waterline against the cylinder scale',stay=True)
    approach('s2_lock','Use the observed millilitre level');click('s2_lock','unlock',code='0240');click('s3_cover','open')
    approach('s3_item_1','Compare mesh openings with the beans and key');click('s3_item_1','take');click('s3_slot_0','use','s3_item_1')
    click('s3_tool','take');approach('s3_setup','Pour beans through the coarse sieve',stay=True);click('s3_setup','use','s3_tool')
    d.append('Observe the flat key',18);approach('key','Take the brass key',stay=True);click('key','take')
    approach('exit','Return to the exit');click('exit','use','key');click('exit','open')
    if not exit_test(d.pos,g):raise RuntimeError('Open-door success was not reached')

def cpu_check():
 from easy88_core import stage_actions
 g=Game();checks=[]
 def act(kind,key,**kw):return g.act(dict(action=kind,_hit364=key,_validated364=True,**kw))
 for kind,key,extra in stage_actions(g,0):assert act(kind,key,**extra)['ok']
 assert not act('open','s2_cover')['ok'];checks.append('cup solution alone cannot remotely open cylinder cabinet')
 assert act('open','s2_handle_drawer')['ok'];assert act('take','s2_tool')['ok'];assert act('use','s2_cover',item='s2_tool')['ok'];assert act('open','s2_cover')['ok'];checks.append('real long pull required for missing sockets')
 assert act('unlock','s2_lock',code='0240')['ok'];assert act('open','s3_cover')['ok'];assert not act('take','key')['ok'];checks.append('buried key cannot be taken')
 for j in [0,1]:
  assert act('take','s3_item_'+str(j))['ok'];assert act('use','s3_slot_0',item='s3_item_'+str(j))['ok']
  if 's3_tool' not in g.holding:assert act('take','s3_tool')['ok']
  result=act('use','s3_setup',item='s3_tool')
  if j==0:assert not result['ok'] and not g.solved[2];checks.append('fine mesh blocks beans without consuming them; replaceable')
  else:assert result['ok'] and g.solved[2];checks.append('actual aperture passes beans but retains larger key bow')
 for kind,key,extra in [('take','key',{}),('use','exit',{'item':'key'}),('open','exit',{})]:assert act(kind,key,**extra)['ok']
 checks.append('manual take/use/open exit')
 return dict(level='R21',scope='CPU actual game and physical-size predicates; native visuals pending',passed=len(checks),checks=checks)
