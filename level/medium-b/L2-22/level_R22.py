import math
import numpy as np
from PIL import Image,ImageDraw
from easy88_core import make_level,reachable_approach
from easy88_scene import EasyScene
from font_utils import load_font
SPEC={'id':'R22','title':'Lost Property Room','chinese_title':'失物招领间','theme':'lost_property','size':[5.,5.5],
'door':{'side':'north','start':3.23,'width':1.04},'start':[3.75,4.25,1.35],'start_yaw':270,'floor':'wood',
'stages':[
 {'kind':'sequence','name':'photo landmark cabinet','wall':'west','options':['blue left hook','blue right hook','red upper box','red lower box'],'answer':[1,3],'length':2,'distinct':True,'clue_text':''},
 {'kind':'read_code','name':'red and blue password cards','wall':'south','answer':'42','clue_text':''},
 {'kind':'missing_objects','name':'photo and shelf comparison','wall':'east','options':['umbrella','book','ball','cup','hat','shoe'],'answer':[2,4,2],'length':3,'clue_text':''}]}
SPEC['stages'][2].update(kind='assign',name='cross-referenced property returns',items=[{'id':k,'name':'found '+k} for k in ['umbrella','book','hat','cup']],slots=4,target=[0,1,2,3],auto=False,clue_text='Each ticket claims one item.\nRecovered together (one per ticket):\n1 + 2: umbrella, book\n2 + 3: book, hat\n3 + 4: hat, cup')
for k in ['options','answer','length']:SPEC['stages'][2].pop(k,None)
Game,_S,_T,exit_test,cpu_check=make_level(SPEC)
TITLE=SPEC['title'];LEVEL_ID=SPEC['id'];START=SPEC['start'];START_YAW=SPEC['start_yaw']
CAP=150;OBSERVATION_SIZE=(640,360);VISUAL_ONLY=False;READ_ENABLED=True;READ_FEEDBACK_TEXT=True
Game.LABELS.update({'s1_clue':'two numbered cabinet photographs','s1_confirm':'whole photo selection check','s1_reset':'clear photo selection','s2_cover':'password card box lid','s2_clue':'red and blue password cards','s2_lock':'red then blue code lock','s3_cover':'comparison cupboard door','s3_clue':'three reference photos and their shelves','s3_confirm':'missing object check','s3_reset':'clear object entry','key_box':'lost property key drawer','key':'brass door key'})
LABELS=Game.LABELS
_act=Game.act
def lost_act(self,a):
 r=_act(self,a)
 if a.get('_validated364') and a.get('action')=='unlock' and a.get('_hit364')=='s2_lock':self.states[1]['entered_code']=str(a.get('code',''))
 return r
Game.act=lost_act
_old_check=Game._check
def return_check(self,i):
 if i!=2:return _old_check(self,i)
 a={int(k):int(v) for k,v in self.states[2]['assignment'].items()}
 return set(a)==set(range(4)) and len(set(a.values()))==4 and {a[0],a[1]}=={0,1} and {a[1],a[2]}=={1,2} and {a[2],a[3]}=={2,3}
Game._check=return_check
LABELS.update({'s2_cover':'registration pocket flap','s3_clue':'paired-ticket register','s3_confirm':'return tray check'})

class Scene(EasyScene):
    def __init__(self,og,run):
        super().__init__(og,run,SPEC);self.views={};self.focus={};self.labels={};self.drawers={};self.lock_shaders={};self.lock_values={};self.expanded=[];self.seq_sig=None;self.screen_signature=None
    def palette(self):
        super().palette()
        for n,c in [('property_blue',(.18,.34,.41)),('property_red',(.49,.19,.14)),('paper',(.77,.74,.64)),('felt',(.26,.34,.28)),('book_ochre',(.53,.35,.14))]:self.mat(n,c,rough=.93)
    def reg_at(self,key,node,label,view,focus=None):
        self.reg(key,node);self.views[key]=list(view);self.labels[key]=label
        if focus is not None:self.focus[key]=list(focus)
        return node
    def flat(self,name,parent,pos,w,h,im,horizontal=False):
        path=self.tex/(name+'.png');im.save(path)
        return self.plane(name,pos,w,h,(1,0,0),(0,1,0) if horizontal else (0,0,1),None,parent,material=self.image_mat('r22_'+name,path))
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
        mat=self.mats['r22_'+key+'_display']
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
        self.box('drawer_pull',[width/2-.04,-.055,.01],[.025,.045,.16],'brass',face)
        self.drawers[key]=(node,[x,y,z])
        return node,face


    def button_at(self,key,parent,pos,text,view,size=.10):
        n=self.group(key,pos,parent);self.box('button',[0,0,0],[size,.032,size],'iron',n);self.text(key+'_print',n,[0,-.018,0],size*.90,size*.90,text);return self.reg_at(key,n,LABELS.get(key,text+' button'),view)
    def photo(self,entries,centre,width,height,right=(1,0,0),up=(0,0,1),number=None):
        right=np.asarray(right,float);up=np.asarray(up,float);fwd=np.cross(up,right);centre=np.asarray(centre,float)
        im=Image.new('RGB',(1300,800),(208,204,182));d=ImageDraw.Draw(im);polys=[]
        for node,colour in entries:
            for tri in self.triangles(node):
                q=tri-centre;normal=np.cross(tri[1]-tri[0],tri[2]-tri[0]);normal/=max(np.linalg.norm(normal),1e-8)
                light=.70+.30*abs(normal@np.array([.25,-.45,.86]))
                polys.append((float(q.mean(0)@fwd),[(650+(p@right)/width*1200,400-(p@up)/height*700) for p in q],tuple(int(c*light) for c in colour)))
        for z,poly,c in sorted(polys,reverse=True,key=lambda x:x[0]):d.polygon(poly,fill=c)
        d.rectangle((6,6,1294,794),outline=(118,111,84),width=5)
        if number is not None:
            d.rectangle((20,20,140,140),fill=(232,226,202));d.text((80,80),str(number),font=load_font(88),fill=(39,60,48),anchor='mm')
        return im
    def prop(self,name,parent,pos,kind):
        n=self.group(name,pos,parent)
        if kind=='umbrella':
            pts=[]
            for z,r in [(.035,.014),(.065,.035),(.205,.018),(.225,.005)]:
                pts.extend([(r*math.cos(j*math.pi/6),r*math.sin(j*math.pi/6),z) for j in range(12)])
            faces=[]
            for k in range(3):
                for j in range(12):faces.append([k*12+j,k*12+(j+1)%12,(k+1)*12+(j+1)%12,(k+1)*12+j])
            self.mesh('folded_canopy',pts,faces,'property_blue',n)
            self.tube('umbrella_shaft',[0,0,.015],[0,0,.23],.004,'steel',n)
            for k in range(12):
                a=k*math.pi/12;b=(k+1)*math.pi/12
                self.tube('umbrella_hook',[.013+.013*math.cos(a),0,.018-.013*math.sin(a)],[.013+.013*math.cos(b),0,.018-.013*math.sin(b)],.004,'iron',n)
        elif kind=='book':
            self.box('book_pages',[0,0,.083],[.105,.024,.16],'paper',n)
            for y in [-.017,.017]:self.box('book_cover',[0,y,.083],[.115,.009,.17],'book_ochre',n)
            self.box('book_spine',[-.057,0,.083],[.012,.04,.17],'book_ochre',n)
        elif kind=='ball':
            pts=[];faces=[];N=24;M=12
            for i in range(M+1):
                a=-math.pi/2+i*math.pi/M
                pts.extend([(.060*math.cos(a)*math.cos(j*2*math.pi/N),.060*math.cos(a)*math.sin(j*2*math.pi/N),.062+.060*math.sin(a)) for j in range(N)])
            for i in range(M):
                for j in range(N):faces.append([i*N+j,i*N+(j+1)%N,(i+1)*N+(j+1)%N,(i+1)*N+j])
            self.mesh('lost_ball',pts,faces,'property_red',n)
        elif kind=='cup':
            self.cylinder('cup_body',[0,0,.054],.042,.102,'paper','z',n,n=32)
            self.cylinder('cup_dark_inside',[0,0,.106],.034,.003,'iron','z',n,n=32)
            for k in range(20):
                a=k*math.pi/10;b=(k+1)*math.pi/10
                self.tube('cup_handle',[.052+.024*math.cos(a),0,.059+.032*math.sin(a)],[.052+.024*math.cos(b),0,.059+.032*math.sin(b)],.006,'paper',n)
        elif kind=='hat':
            self.cylinder('hat_brim',[0,0,.010],.088,.014,'book_ochre','z',n,n=40)
            self.cylinder('hat_crown',[0,0,.040],.057,.055,'book_ochre','z',n,n=40)
            self.cylinder('hat_band',[0,0,.022],.059,.015,'property_blue','z',n,n=40)
        else:
            pts=[(-.045,-.11,.01),(.045,-.11,.01),(.05,.07,.01),(.025,.12,.01),(-.025,.12,.01),(-.05,.07,.01),(-.035,-.10,.075),(.035,-.10,.075),(.045,.07,.045),(.02,.11,.035),(-.02,.11,.035),(-.045,.07,.045)]
            faces=[[5,4,3,2,1,0],[6,7,8,9,10,11]]+[[j,(j+1)%6,(j+1)%6+6,j+6] for j in range(6)]
            self.mesh('shoe_upper',pts,faces,'property_blue',n);self.box('shoe_sole',[0,0,.012],[.10,.22,.012],'iron',n)
            for z in [0,1,2]:self.tube('shoe_lace',[-.025,-.03+z*.025,.063],[.025,-.03+z*.025,.063],.003,'paper',n)
        return n
    def colour_code(self,colour,value):
        im=Image.new('RGB',(900,600),(229,222,197));d=ImageDraw.Draw(im)
        ink=(164,49,35) if colour=='red' else (36,83,144)
        d.text((450,300),str(value),font=load_font(390),fill=ink,anchor='mm')
        return im
    def object_screen(self,buffer):
        im=Image.new('RGB',(1200,350),(29,45,39));d=ImageDraw.Draw(im)
        for j in range(3):
            x=285+j*270;d.rectangle((x-90,15,x+90,125),outline=(127,153,128),width=3)
            if j<len(buffer):im.paste(self.object_icons[buffer[j]].resize((146,97)),(x-73,22))
        d.text((75,70),'↻',font=load_font(85),fill=(224,222,187),anchor='mm');d.text((1120,70),'✓',font=load_font(85),fill=(224,222,187),anchor='mm')
        for j,imj in enumerate(self.object_icons):im.paste(imj.resize((180,166)),(10+j*200,172))
        p=self.tex/('lost_object_entry_'+(''.join(map(str,buffer)) or 'blank')+'.png');im.save(p);return p
    def screen_piece(self,key,rect,target=True):
        x0,y0,x1,y1=rect;pts=[((x/1200-.5)*.95,-.045,(.5-y/350)*.215) for x,y in [(x0,y1),(x1,y1),(x1,y0),(x0,y0)]]
        uv=[(x0/1200,1-y1/350),(x1/1200,1-y1/350),(x1/1200,1-y0/350),(x0/1200,1-y0/350)]
        n=self.mesh(key+'_screen',pts,[[0,1,2,3]],self.screen_mat,self.input_front,uv=uv)
        if target:self.reg_at(key,n,LABELS.get(key,key.replace('_',' ')),[3.5,3.25])
    def build(self,g):
        self.room_shell('lost_property',size=(5.,5.5),openings={'north':[(3.21,4.31)]})
        self.box('continuous_subfloor',[2.5,2.75,-.06],[5.15,5.65,.10],'darkwood')
        self.landmarks=self.group('landmark_cabinet',[.34,3.25,0]);self.transform(self.landmarks,rpy=[0,0,90])
        self.box('cabinet_body',[0,.02,.66],[2.05,.46,1.32],'wood',self.landmarks)
        backing=self.group('front_reference_panel',parent=self.landmarks);self.box('cabinet_front',[0,-.225,.76],[1.96,.03,1.06],'paper',backing)
        blue=self.group('blue_vertical_landmark',[-.62,-.249,1.0],self.landmarks);self.box('blue_strip',[0,0,0],[.045,.018,.42],'property_blue',blue)
        red=self.group('red_frame_landmark',[.60,-.249,.89],self.landmarks)
        for x in [-.21,.21]:self.box('red_frame_side',[x,0,0],[.025,.018,.17],'property_red',red)
        for z in [-.085,.085]:self.box('red_frame_edge',[0,0,z],[.43,.018,.025],'property_red',red)
        hooks=[];boxes=[]
        for j,x in enumerate([-.85,-.39]):
            n=self.group('fixed_round_hook_'+str(j),[x,-.265,1.0],self.landmarks)
            self.tube('wall_hook_standoff',[0,.025,0],[0,-.025,0],.010,'steel',n)
            for k in range(24):
                a=k*math.pi/12;b=(k+1)*math.pi/12
                self.tube('round_hook',[.065*math.cos(a),-.025,.065*math.sin(a)],[.065*math.cos(b),-.025,.065*math.sin(b)],.009,'steel',n)
            hooks.append(n)
            self.button_at('s1_choice_'+str(j),self.landmarks,[x,-.272,.79],chr(65+j),[1.5,3.25])
        for j,z in enumerate([1.17,.60]):
            n=self.group('fixed_landmark_box_'+str(j),[.60,-.29,z],self.landmarks)
            self.box('fixed_box',[0,0,0],[.34,.11,.16],'paint',n);self.box('box_pull',[0,-.067,0],[.11,.024,.018],'brass',n);boxes.append(n)
            self.button_at('s1_choice_'+str(j+2),self.landmarks,[.91,-.272,z],chr(67+j),[1.5,3.25])
        self.button_at('s1_reset',self.landmarks,[-.78,-.272,.32],'↻',[1.5,3.25])
        self.button_at('s1_confirm',self.landmarks,[.78,-.272,.32],'✓',[1.5,3.25])
        self.echo=[]
        for j in range(2):
            n=self.group('selection_echo_'+str(j),[(j-.5)*.34,-.26,.32],self.landmarks)
            self.box('echo_bezel',[0,0,0],[.28,.022,.12],'iron',n);self.echo.append(n)
        self.add_obstacle(.05,2.16,.73,4.34)
        entries=[(backing,(214,207,177)),(blue,(53,93,116)),(red,(148,53,41))]+[(n,(135,148,145)) for n in hooks]+[(n,(106,124,111)) for n in boxes]
        p1=self.photo(entries,[.60,2.79,1.0],.65,.50,right=(0,1,0),number=1)
        p2=self.photo(entries,[.60,3.85,.76],.65,.60,right=(0,1,0),number=2)
        stand=self.group('photo_wall_rack',[2.72,3.25,0]);self.transform(stand,rpy=[0,0,-90])
        for x in [-.60,.60]:self.box('rack_post',[x,0,.83],[.055,.42,1.66],'darkwood',stand)
        for z in [.18,.75,1.10]:self.box('rack_shelf',[0,0,z],[1.30,.45,.035],'wood',stand)
        self.box('photo_wall_support',[0,.16,1.37],[1.28,.045,.57],'wood',stand)
        for j,im in enumerate([p1,p2]):self.flat('numbered_photo_'+str(j+1),stand,[(j-.5)*.61,.134,1.37],.56,.48,im)
        self.reg_at('s1_clue',stand,'two numbered cabinet photographs',[1.5,3.25],[2.60,3.25,1.37])
        for x in [-.30,.30]:self.box('fixed_paper_storage_box',[x,0,.36],[.48,.35,.31],'paint',stand)
        self.add_obstacle(2.45,2.57,3.0,3.93)

        self.table('transfer_record_bench',(2.5,.42),(2.50,.68),height=.72)
        self.records=self.group('registration_digit_pocket',[0,-.263,.51],self.landmarks)
        self.box('registration_pocket_back',[0,0,0],[.56,.025,.28],'wood',self.records)
        for j,args in enumerate([('red',4),('blue',2)]):self.flat('fixed_colour_password_'+str(j),self.records,[(j-.5)*.26,-.014,0],.24,.23,self.colour_code(*args))
        self.recordlid=self.group('record_lid_hinge',[0,-.024,-.155],self.records)
        self.box('record_lid',[0,0,.155],[.60,.025,.31],'paint',self.recordlid)
        self.box('record_lid_pull',[0,-.025,.275],[.12,.03,.02],'brass',self.recordlid)
        self.reg_at('s2_cover',self.recordlid,'registration pocket flap',[1.5,3.25],[.62,3.25,.51])
        self.reg_at('s2_clue',self.records,'red and blue password cards',[1.5,3.25],[.62,3.25,.51])
        for j in range(2):self.box('fixed_archive_storage_box',[2.10+j*.65,.43,.89],[.48,.39,.25],'paint')
        self.add_obstacle(1.17,.04,3.83,.82)

        self.table('comparison_cabinet_bench',(4.62,3.25),(.68,2.08),height=.72)
        self.comparison=self.group('comparison_cabinet',[4.65,3.25,0]);self.transform(self.comparison,rpy=[0,0,-90])
        self.box('comparison_back',[0,.17,1.21],[2.02,.035,.93],'paint',self.comparison)
        for x in [-1.,1.]:self.box('comparison_side',[x,-.04,1.21],[.035,.46,.93],'wood',self.comparison)
        for z in [.82,1.68]:self.box('comparison_shelf',[0,-.04,z],[2.02,.46,.025],'wood',self.comparison)
        paper=Image.new('RGB',(1400,420),(229,222,197));ink=ImageDraw.Draw(paper)
        for j,line in enumerate(SPEC['stages'][2]['clue_text'].splitlines()):ink.text((35,12+j*78),line,font=load_font(56),fill=(38,52,44))
        note=self.group('paired_ticket_register',[0,.123,1.47],self.comparison);self.flat('return_register_note',note,[0,-.002,0],1.82,.34,paper)
        self.reg_at('s3_clue',note,'paired-ticket return register',[3.5,3.25],[4.65,3.25,1.47])
        self.return_items=[];self.return_positions=[]
        for j,item in enumerate(SPEC['stages'][2]['items']):
            x=(j-1.5)*.44;pos=[x,.055,.85];self.return_positions.append(pos)
            slot=self.group('numbered_return_tray_'+str(j),pos,self.comparison);self.box('return_tray_base',[0,0,0],[.39,.22,.025],'felt',slot)
            for xx in [-.195,.195]:self.box('return_tray_side',[xx,0,.015],[.012,.22,.035],'wood',slot)
            self.text('ticket_number_'+str(j),slot,[0,-.014,.36],.10,.09,str(j+1));self.reg_at('s3_slot_'+str(j),slot,'ticket '+str(j+1)+' return tray',[3.5,3.25])
            n=self.prop('returnable_'+item['id'],self.comparison,[x,-.16,.85],item['id']);self.return_items.append(n);self.reg_at('s3_item_'+str(j),n,item['name'],[3.5,3.25])
        self.cover=self.group('comparison_door_hinge',[1.03,-.29,.765],self.comparison)
        face=self.group('comparison_door_face',parent=self.cover)
        self.box('opaque_comparison_door',[-1.03,0,.46],[2.06,.032,.92],'paint',face)
        self.box('comparison_door_pull',[-1.88,-.037,.32],[.035,.04,.17],'brass',face)
        self.reg_at('s3_cover',face,'comparison cupboard door',[3.5,3.25])
        self.numeric_lock('s2_lock',face,[-1.03,-.027,.42],2,[3.5,3.25])
        for j,col in enumerate(['property_red','property_blue']):
            self.box('bag_order_mark',[-1.09+j*.12,-.028,.30],[.07,.008,.07],col,face)
        self.keydrawer,kfront=self.drawer('lost_key_drawer',self.comparison,(0,-.27),.54,1.10,.43)
        self.reg_at('key_box',kfront,'lost property key drawer',[3.5,3.25])
        self.button_at('s3_confirm',kfront,[.38,-.03,0],'✓',[3.5,3.25],.085)
        self.return_red=self.cylinder('return_red',[-.38,-.03,0],.014,.009,'red_led','y',kfront,n=20)
        self.return_green=self.cylinder('return_green',[-.38,-.03,0],.014,.009,'green','y',kfront,n=20)
        self.box('key_pad',[0,.21,-.025],[1.,.34,.15],'felt',self.keydrawer)
        self.key=self.tool('flat_brass_key',self.keydrawer,[0,.21,.065],'key');self.target_nodes.pop('flat_brass_key',None);self.transform(self.key,rpy=[90,0,0]);self.reg_at('key',self.key,'brass door key',[3.5,3.25])
        self.add_obstacle(4.21,2.12,4.99,4.38)
        self.exit_node=self.door('lost_exit',[4.29,5.44,0],1.04);self.door_view=[3.75,4.75]
        self.reg_at('exit',self.exit_node,'exit door',self.door_view,[3.77,5.44,1.12])
        for x in [3.23,4.31]:self.box('door_jamb',[x,5.45,1.14],[.065,.17,2.30],'paint')
        self.box('door_top',[3.77,5.45,2.29],[1.15,.17,.065],'paint')
        self.stage_views=[[1.5,3.25],[2.5,1.5],[3.5,3.25]];self.stage_centres=[[.34,3.25,.9],[2.5,.42,.82],[4.65,3.25,1.24]]
        self.bases=[([.34,3.25],90),([2.5,.42],180),([4.65,3.25],-90)];self.sync(g)
    def visible(self,key,g):
        if key.startswith('s3_item_'):return bool(g.opened['s3_cover']) and key not in g.holding
        if key.startswith('s3_slot_'):return bool(g.opened['s3_cover'])
        if key=='s2_clue':return bool(g.opened['s2_cover'])
        if key=='s3_clue' or key.startswith('s3_choice_') or key in ('s3_confirm','s3_reset'):return bool(g.opened['s3_cover'])
        if key=='key':return bool(g.opened['key_box']) and key not in g.taken
        return key in self.target_nodes
    def sync(self,g):
        self.transform(self.recordlid,rpy=[110 if g.opened['s2_cover'] else 0,0,0])
        self.transform(self.cover,rpy=[0,0,110 if g.opened['s3_cover'] else 0])
        value=g.states[1].get('entered_code','00')
        if self.lock_values['s2_lock']!=value:
            p=self.tex/('lost_entered_'+value+'.png');self.text_image(value,.27,.088,(47,67,56),(224,228,191)).save(p)
            with self.og.sim.editing_usd():self.lock_shaders['s2_lock'].GetInput('file').Set(str(p))
            self.lock_values['s2_lock']=value
        sig=tuple(g.states[0]['buffer'])
        if sig!=self.seq_sig:
            for j,n in enumerate(self.echo):
                if 'echo' in n:self.visibility(n['echo'],False)
                if j<len(sig):n['echo']=self.text('echo_'+str(j)+'_'+str(len(sig)),n,[0,-.012,0],.24,.09,chr(65+sig[j]))
            self.seq_sig=sig
        assignments={int(k):int(v) for k,v in g.states[2]['assignment'].items()}
        for j,n in enumerate(self.return_items):
            slot=next((k for k,v in assignments.items() if v==j),None);self.transform(n,self.return_positions[slot] if slot is not None else [(j-1.5)*.44,-.16,.85]);self.visibility(n,'s3_item_'+str(j) not in g.holding)
        self.visibility(self.return_red,not g.solved[2]);self.visibility(self.return_green,g.solved[2])
        n,p=self.drawers['lost_key_drawer'];self.transform(n,[p[0],p[1]-(.42 if g.opened['key_box'] else 0),p[2]])
        self.visibility(self.key,'key' not in g.taken)
        self.transform(self.exit_node,rpy=[0,0,180-(103 if g.opened['exit'] else 0)])
        self.expanded=[]
        if g.opened['s3_cover']:
            p=self.triangles(self.cover).reshape(-1,3);self.expanded.append((p.min(0)[:2]-.08,p.max(0)[:2]+.08))
        self.centres={}
        for k,n in self.target_nodes.items():
            p=self.triangles(n).reshape(-1,3)
            if p.size:self.centres[k]=((p.min(0)+p.max(0))/2).tolist()
    def candidates(self,g):return self.base_candidates([k for k in self.target_nodes if self.visible(k,g)])
    def blocked(self,x,y,g):return super().blocked(x,y,g) or any(lo[0]<x<hi[0] and lo[1]<y<hi[1] for lo,hi in self.expanded)
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

    observe('s1_clue','Observe both numbered close-up photographs from the same cabinet front')
    approach('s1_choice_0','Match the photographs to the actual cabinet landmarks')
    for j in [1,3]:click('s1_choice_'+str(j))
    click('s1_confirm')
    approach('s2_cover','Open the unlocked password card box');click('s2_cover','open')
    observe('s2_clue','Observe the red4 and blue2 password cards',stay=True)
    approach('s2_lock','Use the red then blue password digits');click('s2_lock','unlock',code='42');click('s3_cover','open')
    observe('s3_clue','Cross-reference the overlapping ticket pairs',stay=True);click('s3_clue','read')
    for slot,item in enumerate([0,1,2,3]):
        approach('s3_item_'+str(item),'Take the identified property',stay=True);click('s3_item_'+str(item),'take')
        approach('s3_slot_'+str(slot),'Return it to its ticket tray',stay=True);click('s3_slot_'+str(slot),'use','s3_item_'+str(item))
    click('s3_confirm');approach('key_box','Open the unlocked key drawer',stay=True);click('key_box','open')
    d.append('Observe the flat key',18);approach('key','Take the brass key',stay=True);click('key','take')
    approach('exit','Return to the exit');click('exit','use','key');click('exit','open')
    if not exit_test(d.pos,g):raise RuntimeError('Open-door success was not reached')

def cpu_check():
 import itertools
 from easy88_core import stage_actions
 g=Game();checks=[]
 def act(kind,key,**kw):return g.act(dict(action=kind,_hit364=key,_validated364=True,**kw))
 for i in [0,1]:
  for kind,key,extra in stage_actions(g,i):assert act(kind,key,**extra)['ok'],(kind,key)
 assert act('open','s3_cover')['ok'];assert act('read','s3_clue')['ok'];checks.append('actual paired-ticket read clue')
 valid=[]
 for perm in itertools.permutations(range(4)):
  g.states[2]['assignment']=dict(enumerate(perm))
  if g._check(2):valid.append(perm)
 assert valid==[(0,1,2,3)];checks.append('24 ownership permutations, one satisfies all three pair records')
 g.states[2]['assignment']={}
 for kind,key,extra in stage_actions(g,2):assert act(kind,key,**extra)['ok'],(kind,key)
 assert g.solved[2];checks.append('real take/use returns solve, no symbol keypad')
 assert act('take','s3_item_0')['ok'];assert 0 not in g.states[2]['assignment'];assert act('use','s3_slot_0',item='s3_item_0')['ok'];checks.append('returns remain recoverable')
 for kind,key,extra in [('open','key_box',{}),('take','key',{}),('use','exit',{'item':'key'}),('open','exit',{})]:assert act(kind,key,**extra)['ok']
 checks.append('key/use/open door success')
 return dict(level='R22',scope='CPU actual game fixtures; native images pending',passed=len(checks),checks=checks)
