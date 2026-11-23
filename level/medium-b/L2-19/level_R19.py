import math
import numpy as np
from PIL import Image,ImageDraw
from easy88_core import make_level,reachable_approach
from easy88_scene import EasyScene
from font_utils import load_font
SPEC={'id':'R19','title':'Pottery Workshop','chinese_title':'陶艺工作间','theme':'pottery',
'size':[5.5,5.0],'door':{'side':'south','start':1.48,'width':1.04},'start':[2.75,1.25,1.35],'start_yaw':90,'floor':'tile',
'stages':[
 {'kind':'rotate_picture','name':'bird ceramic plaque','wall':'west','initial':[1,3,2],'target':[0,0,0],'auto':True,'clue_text':''},
 {'kind':'read_code','name':'porcelain backlight','wall':'north','answer':'4263','setup':{'kind':'battery','item':'backlight_battery','item_name':'backlight battery','target_name':'backlight battery holder','consume':True},'clue_text':''},
 {'kind':'half_code','name':'tracing frame','wall':'east','answer':'2318','setup':{'kind':'overlay','item_count':2,'items':[{'id':'first_sheet','name':'first tracing sheet'},{'id':'second_sheet','name':'second tracing sheet'}]},'clue_text':''}]}
Game,_S,_T,exit_test,cpu_check=make_level(SPEC)
TITLE=SPEC['title'];LEVEL_ID=SPEC['id'];START=SPEC['start'];START_YAW=SPEC['start_yaw']
CAP=150;OBSERVATION_SIZE=(640,360);VISUAL_ONLY=False;READ_ENABLED=True;READ_FEEDBACK_TEXT=True
Game.LABELS.update({'s1_clue':'three bird ceramic tiles','s2_cover':'battery drawer','s2_tool':'backlight battery','s2_setup':'empty battery holder','s2_clue':'four porcelain windows','s2_lock':'tracing sheet drawer lock','s3_cover':'tracing sheet drawer','s3_tool_0':'first tracing sheet','s3_tool_1':'second tracing sheet','s3_overlay_0':'front tracing slot','s3_overlay_1':'back tracing slot','s3_clue':'registered tracing frame','s3_lock':'tracing cabinet code lock','key_box':'pottery key drawer','key':'brass door key'})
LABELS=Game.LABELS
_act=Game.act
def pottery_act(self,a):
 k=a.get('_hit364');kind=a.get('action')
 r=_act(self,a)
 if a.get('_validated364') and kind=='unlock' and k in ('s2_lock','s3_lock'):self.states[int(k[1])-1]['entered_code']=str(a.get('code',''))
 return r
Game.act=pottery_act
_pottery_init=Game.__init__
def _init_tracings(self):
    _pottery_init(self);self.states[2]['alignment']=[1,0]
Game.__init__=_init_tracings
_pottery_action=Game.act
def _orient_tracing(self,a):
    key=str(a.get('_hit364',''));kind=a.get('action')
    if a.get('_validated364') and key in ('s3_control_0','s3_control_1'):
        from action_feedback import failure_for
        j=int(key[-1])
        if kind!='press' or not self.states[2]['overlay'][j]:return {'ok':False,'text':failure_for(kind)}
        self.states[2]['alignment'][j]=1-self.states[2]['alignment'][j]
        return {'ok':True,'text':''}
    return _pottery_action(self,a)
Game.act=_orient_tracing
LABELS.update({'s3_control_0':'front tracing half-turn knob','s3_control_1':'back tracing half-turn knob'})

def _mark_image(kind):
    import math
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (200, 200), (232, 196, 40)); d = ImageDraw.Draw(im); ink = (34, 40, 42)
    if kind == 'turn':
        d.arc([36, 36, 164, 164], 200, 500, fill=ink, width=18)
        a = math.radians(140); px, py = 100 + 55*math.cos(a), 100 + 55*math.sin(a)
        d.polygon([(px - 30, py - 4), (px + 8, py - 34), (px + 14, py + 14)], fill=ink)
    else:
        d.line([(40, 76), (150, 76)], fill=ink, width=16); d.polygon([(172, 76), (140, 50), (140, 102)], fill=ink)
        d.line([(50, 128), (160, 128)], fill=ink, width=16); d.polygon([(28, 128), (60, 102), (60, 154)], fill=ink)
    return im


def _defer(sc, fn):
    pending = getattr(sc, '_aff_pending', None)
    if pending is None:
        return fn()
    pending.append(fn)


def _add_box(sc, *args, **kwargs):
    _defer(sc, lambda: sc.box(*args, **kwargs))


def _aff_build_last(cls):
    original = cls.build

    def build(self, *args, **kwargs):
        self._aff_pending = []
        result = original(self, *args, **kwargs)
        pending, self._aff_pending = self._aff_pending, None
        for fn in pending:
            fn()
        return result
    cls.build = build
    return cls


def _add_mark(sc, key, parent, pos, kind, size, right=(1, 0, 0), up=(0, 0, 1)):
    def make():
        p = sc.tex/('press_mark_%s.png' % kind)
        if not p.exists():
            _mark_image(kind).save(p)
        sc.plane(key, pos, size, size, right, up, None, parent, material=sc.image_mat('press_mark_' + kind, p))
    _defer(sc, make)


def _outline_image(shape, w=600, h=200):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (w, h), (70, 74, 76)); d = ImageDraw.Draw(im); ink = (250, 250, 244)

    def dash(pts, closed=True):
        pts = list(pts) + ([pts[0]] if closed else [])
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            n = max(1, int(((bx - ax)**2 + (by - ay)**2)**.5/16))
            for k in range(n):
                t0, t1 = k/n, (k + .55)/n
                d.line([(ax + (bx - ax)*t0, ay + (by - ay)*t0), (ax + (bx - ax)*t1, ay + (by - ay)*t1)], fill=ink, width=7)
    if shape == 'pick':
        sx, sy = w/600, h/200
        dash([(x*sx, y*sy) for x, y in [(20, 55), (190, 55), (190, 80), (520, 80), (585, 100), (520, 120), (190, 120), (190, 145), (20, 145)]])
    elif shape == 'hook':
        cx = w/2
        dash([(cx - 22, h - 15), (cx + 22, h - 15), (cx + 22, h*.62), (cx + 8, h*.62), (cx + 8, h*.18), (cx + 40, h*.10),
              (cx + 30, 15), (cx - 8, 30), (cx - 8, h*.62), (cx - 22, h*.62)])
    else:
        dash([(15, 30), (w - 15, 30), (w - 15, h - 30), (15, h - 30)])
        for k in range(1, 11):
            x = 15 + k*(w - 30)/11
            d.line([(x, 30), (x, 30 + (40 if k % 2 else 65))], fill=ink, width=5)
    return im


def _add_outline(sc, key, parent, pos, shape, w, h, right=(1, 0, 0), up=(0, 0, 1)):
    def make():
        px = (int(w*1500), int(h*1500))
        p = sc.tex/('tool_outline_%s.png' % shape)
        _outline_image(shape, *px).save(p)
        sc.plane(key, pos, w, h, right, up, None, parent, material=sc.image_mat('tool_outline_' + shape, p))
    _defer(sc, make)


class Scene(EasyScene):
    def __init__(self,og,run):
        super().__init__(og,run,SPEC)
        self.views={};self.focus={};self.labels={};self.drawers={};self.lock_shaders={};self.lock_values={};self.expanded=[]
    def palette(self):
        super().palette()
        for n,c in [('clay',(.52,.30,.19)),('porcelain',(.77,.75,.65)),('bird_ink',(.13,.29,.34)),('felt',(.24,.32,.29))]:
            self.mat(n,c,rough=.92)
    def display_pot(self,name,pos,profile,material,parent=None):
        node=self.group(name,pos,parent);n=36;points=[]
        inner_z=max(.025,profile[-1][0]-.10)
        inner_r=max(.012,min(profile[-1][1]-.020,float(np.interp(inner_z,[x[0] for x in profile],[x[1] for x in profile]))-.012))
        rings=list(profile)+[(profile[-1][0],profile[-1][1]-.012),(inner_z,inner_r)]
        for z,radius in rings:
            for k in range(n):
                a=2*math.pi*k/n;points.append([radius*math.cos(a),radius*math.sin(a),z])
        faces=[]
        for j in range(len(rings)-1):
            for k in range(n):faces.append([j*n+k,j*n+(k+1)%n,(j+1)*n+(k+1)%n,(j+1)*n+k])
        faces.append(list(reversed(range(n))));self.mesh('hollow_ceramic_body',points,faces,material,node)
        self.cylinder('pot_dark_inner_bottom',[0,0,rings[-1][0]],rings[-1][1],.004,'felt','z',node,n=36)
        return node
    def reg_at(self,key,node,label,view,focus=None):
        self.reg(key,node);self.views[key]=list(view);self.labels[key]=label
        if focus is not None:self.focus[key]=list(focus)
        return node
    def flat(self,name,parent,pos,w,h,im,horizontal=False):
        path=self.tex/(name+'.png');im.save(path)
        return self.plane(name,pos,w,h,(1,0,0),(0,1,0) if horizontal else (0,0,1),None,parent,material=self.image_mat('r19_'+name,path))
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
        mat=self.mats['r19_'+key+'_display']
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


    def bird_image(self):
        im=Image.new('RGB',(1200,400),(220,212,185));d=ImageDraw.Draw(im)
        d.line([(30,320),(240,285),(470,300),(680,280),(925,305),(1180,268)],fill=(49,83,83),width=16)
        d.polygon([(185,220),(285,170),(350,76),(505,126),(650,72),(810,146),(900,185),(1005,172),(1110,205),(1007,230),(900,222),(805,271),(700,268),(630,234),(480,264),(330,251)],fill=(43,82,88))
        d.line([(320,212),(445,145),(580,196),(684,133),(800,205)],fill=(220,212,185),width=16)
        d.ellipse((936,188,954,206),fill=(220,212,185));d.polygon([(1010,188),(1155,163),(1075,212)],fill=(43,82,88))
        d.line([(754,257),(744,292),(780,294)],fill=(43,82,88),width=10)
        return im
    def holder(self,name,pos,width=1.2,height=.9):
        p=self.group(name,pos)
        self.box('holder_back',[0,.10,height/2],[width,.055,height],'paint',p)
        self.box('holder_floor',[0,-.11,.015],[width,.48,.03],'wood',p)
        for x in [-width/2,width/2]:self.box('holder_side',[x,-.11,height/2],[.035,.48,height],'wood',p)
        return p
    def strokes(self,parent,which,pos,name):
        node=self.group(name,pos,parent)
        seg=[((-.075,.13),(.075,.13)),((.075,.13),(.075,0)),((.075,0),(.075,-.13)),((-.075,-.13),(.075,-.13)),((-.075,0),(-.075,-.13)),((-.075,.13),(-.075,0)),((-.075,0),(.075,0))]
        maps={'2':[0,1,6,4,3],'3':[0,1,6,2,3],'1':[1,2],'8':list(range(7))}
        for j,ch in enumerate('2318'):
            for k,idx in enumerate(maps[ch]):
                if k%2!=which:continue
                a,b=seg[idx];x=(j-1.5)*.27
                self.tube('permanent_tracing_stroke',[x+a[0],0,.00+a[1]],[x+b[0],0,.00+b[1]],.010,'bird_ink',node)
        self.box('orange_registration_corner',[-.54,-.006,.17],[.04,.012,.025],'clay',node)
        for x in [-.57,.57]:
            for z in [-.19,.19]:
                self.box('sheet_registration_corner',[x,0,z],[.035,.008,.010],'clay',node)
        for x in [-.59,.59]:self.box('clear_sheet_edge',[x,0,0],[.006,.006,.43],'steel',node)
        for z in [-.215,.215]:self.box('clear_sheet_edge',[0,0,z],[1.18,.006,.006],'steel',node)
        return node
    def build(self,g):
        self.room_shell('pottery_workshop',size=(5.5,5.0),openings={'south':[(1.46,2.56)]})
        self.box('continuous_subfloor',[2.75,2.5,-.06],[5.65,5.15,.10],'darkwood')
        self.table('bird_repair_bench',(.42,2.60),(.70,2.15),height=.72)
        self.bird=self.group('bird_mount',[.34,2.60,1.15]);self.transform(self.bird,rpy=[0,0,90])
        self.box('continuous_tile_backing',[0,.025,0],[1.58,.04,.59],'darkwood',self.bird)
        im=self.bird_image();self.rotors=[]
        for j in range(3):
            tile=self.group('ceramic_tile_'+str(j),[(j-1)*.50,-.014,0],self.bird)
            self.box('ceramic_tile_body',[0,0,0],[.485,.045,.485],'porcelain',tile)
            self.flat('bird_piece_'+str(j),tile,[0,-.024,0],.475,.475,im.crop((j*400,0,(j+1)*400,400)))
            self.reg_at('s1_control_'+str(j),tile,'ceramic bird tile',[1.25,2.5],[.38,2.60,1.15]);self.rotors.append(tile)
            _add_mark(self,'tile_turn_mark_'+str(j),tile,[.195,-.0295,-.195],'turn',.055)
        self.reg_at('s1_clue',self.bird,'bird ceramic plaque',[1.25,2.5],[.38,2.60,1.15])
        root=self.group('battery_drawer_support',[.34,2.60,0]);self.transform(root,rpy=[0,0,90])
        self.batdrawer,front=self.drawer('battery_drawer',root,(0,-.22),.54,1.30,.43)
        self.reg_at('s2_cover',front,'battery drawer',[1.25,2.5])
        self.box('drawer_felt',[0,.2,-.065],[1.2,.34,.08],'felt',self.batdrawer)
        self.battery=self.tool('s2_tool',self.batdrawer,[0,.22,.025],'battery')
        self.transform(self.battery,rpy=[90,0,0]);self.views['s2_tool']=[1.25,2.5];self.labels['s2_tool']='backlight battery'
        self.add_obstacle(.05,1.48,.82,3.72)
        self.table('porcelain_light_bench',(2.75,4.58),(3.40,.66),height=.72)
        self.lightbox=self.group('porcelain_backlight',[2.00,4.56,.755])
        self.box('lightbox_housing',[0,0,.11],[1.30,.44,.22],'paint',self.lightbox)
        self.ink=self.group('powered_porcelain_ink',[0,0,.229],self.lightbox)
        for j,value in enumerate('4263'):
            x=(j-1.5)*.29
            self.box('thin_porcelain_window',[x,0,.226],[.26,.35,.015],'porcelain',self.lightbox)
            self.flat('lit_slit_'+str(j),self.ink,[x,0,.006],.25,.32,self.text_image(value,.25,.32,(218,223,187),(31,49,44)),True)
        self.reg_at('s2_clue',self.lightbox,'four porcelain light windows',[2.0,3.75],[2.0,4.55,1.00])
        self.holdernode=self.group('battery_holder',[1.18,4.53,.77])
        self.box('battery_holder_base',[0,0,0],[.21,.29,.035],'iron',self.holdernode)
        for x in [-.085,.085]:self.box('battery_contact',[x,0,.035],[.015,.18,.035],'brass',self.holdernode)
        self.installed=self.tool('installed_battery',self.holdernode,[0,0,.035],'battery')
        self.target_nodes.pop('installed_battery',None);self.transform(self.installed,rpy=[90,0,0])
        self.reg_at('s2_setup',self.holdernode,'battery holder',[1.25,3.75],[1.18,4.53,.80])
        self.tracedrawer,trfront=self.drawer('tracing_drawer',None,(3.60,4.25),.54,1.25,.43)
        self.reg_at('s3_cover',trfront,'tracing sheet drawer',[3.5,3.5])
        self.numeric_lock('s2_lock',trfront,[.10,-.044,.016],4,[3.5,3.5])
        self.sheets=[]
        for j in range(2):
            node=self.strokes(self.tracedrawer,j,[(j-.5)*.54,.22,-.091],'tracing_sheet_'+str(j))
            with self.og.sim.editing_usd():
                self.G.Xformable(node['prim']).AddScaleOp().Set(self.F.Vec3f(.43,.43,.43))
            self.transform(node,rpy=[90,0,0])
            self.reg_at('s3_tool_'+str(j),node,LABELS['s3_tool_'+str(j)],[3.5,3.5]);self.sheets.append(node)
        self.add_obstacle(.97,4.18,4.53,4.98)

        self.table('tracing_cabinet_table',(5.08,2.85),(.67,1.75),height=.72)
        self.frame=self.group('registration_frame',[5.10,2.85,1.10]);self.transform(self.frame,rpy=[0,0,-90])
        self.box('frame_backing',[0,.035,0],[1.35,.055,.61],'porcelain',self.frame)
        for x in [-.65,.65]:self.box('frame_side',[x,0,0],[.035,.08,.65],'wood',self.frame)
        for z in [-.29,.29]:self.box('frame_edge',[0,0,z],[1.32,.08,.035],'wood',self.frame)
        for j in range(2):
            slot=self.group('registration_slot_'+str(j),[.61,-.035-j*.015,(j-.5)*.25],self.frame)
            self.box('sheet_guide_slot',[0,0,0],[.08,.045,.18],'iron',slot)
            self.text('guide_num_'+str(j),slot,[0,-.024,0],.06,.10,str(j+1))
            self.reg_at('s3_overlay_'+str(j),slot,LABELS['s3_overlay_'+str(j)],[4.0,2.75])
        self.reg_at('s3_clue',self.frame,'two-layer registered frame',[4.0,2.75],[5.10,2.85,1.10])
        self.box('fixed_orange_frame_corner',[-.54,-.018,.17],[.04,.012,.025],'clay',self.frame)
        for j in range(2):
            knob=self.group('sheet_turn_knob_'+str(j),[(j-.5)*.40,-.035,-.265],self.frame)
            self.cylinder('brass_half_turn_knob',[0,0,0],.034,.025,'brass','y',knob,n=24)
            self.box('knob_grip',[0,-.017,0],[.050,.018,.012],'iron',knob)
            self.reg_at('s3_control_'+str(j),knob,LABELS['s3_control_'+str(j)],[4.0,2.75])
        self.placed=[]
        for j in range(2):
            n=self.strokes(self.frame,j,[0,-.012-j*.012,0],'fixed_tracing_layer_'+str(j));self.placed.append(n)
        kroot=self.group('key_drawer_support',[5.10,2.85,0]);self.transform(kroot,rpy=[0,0,-90])
        self.keydrawer,kfront=self.drawer('pottery_key_drawer',kroot,(0,-.26),.54,1.25,.43)
        self.reg_at('key_box',kfront,'pottery key drawer',[4.0,2.75])
        self.numeric_lock('s3_lock',kfront,[.10,-.044,.016],4,[4.0,2.75])
        self.box('key_pad',[0,.21,-.025],[1.14,.34,.15],'felt',self.keydrawer)
        self.key=self.tool('flat_brass_key',self.keydrawer,[0,.21,.065],'key');self.target_nodes.pop('flat_brass_key',None)
        self.transform(self.key,rpy=[90,0,0]);self.reg_at('key',self.key,'brass door key',[4.0,2.75])
        self.add_obstacle(4.71,1.91,5.49,3.79)
        self.table('low_pottery_island',(2.75,2.0),(.90,.65),height=.58)
        self.cylinder('turntable_on_island',[2.75,2.0,.623],.23,.05,'steel','z',n=40)
        self.cylinder('unfinished_clay_cup',[2.75,2.0,.75],.11,.20,'clay','z',n=32)
        for j in range(3):self.cylinder('fixed_clay_lump',[4.05+j*.15,4.56,.805],.06,.10,'clay','z',n=20)
        self.box('pottery_tool_wall_panel',[.055,3.87,1.50],[.035,.70,.47],'wood')
        for j in range(3):
            y=3.65+j*.22;self.cylinder('fixed_pottery_tool_handle',[.092,y,1.47],.014,.23,'wood','z',n=16)
            self.tube('tool_hanging_peg',[.06,y,1.65],[.14,y,1.65],.009,'iron')
            self.box('pottery_tool_head',[.092,y,1.35],[.025,.058,.072],'steel',bevel=.007)
        self.cylinder('brushes_cup',[4.23,4.55,.81],.070,.15,'clay','z',n=28)
        self.cylinder('brushes_cup_dark_opening',[4.23,4.55,.887],.055,.004,'iron','z',n=28)
        for j in range(2):
            x=4.205+j*.05;self.tube('fixed_brush_stem',[x,4.55,.82],[x,4.55,1.055],.006,'wood')
            self.cylinder('fixed_brush_ferrule',[x,4.55,1.04],.010,.040,'steel','z',n=16)
            self.cylinder('fixed_brush_tip',[x,4.55,1.075],.013,.035,'clay','z',n=16)
        shelf=self.group('finished_ware_wall_shelf',[2.75,4.77,1.56])
        self.box('ware_display_board',[0,0,0],[2.35,.32,.035],'wood',shelf)
        for x in [-.91,.91]:
            self.box('ware_shelf_wall_fixing',[x,.12,-.12],[.045,.04,.25],'iron',shelf)
            self.tube('ware_shelf_diagonal',[x,-.10,-.015],[x,.12,-.23],.012,'iron',shelf)
        self.display_pot('finished_clay_vase',[-.72,0,.020],[(0,.075),(.02,.09),(.12,.15),(.23,.12),(.30,.06),(.33,.065)],'clay',shelf)
        self.display_pot('finished_cream_bowl',[.03,0,.020],[(0,.055),(.02,.07),(.08,.13),(.14,.16),(.16,.165)],'porcelain',shelf)
        self.display_pot('finished_blue_vase',[.72,0,.020],[(0,.08),(.02,.09),(.16,.11),(.26,.075),(.31,.075)],'bird_ink',shelf)
        self.exit_node=self.door('pottery_exit',[1.50,.06,0],1.04);self.door_angle=0
        self.door_view=[2.0,1.0];self.reg_at('exit',self.exit_node,'exit door',self.door_view,[2.02,.06,1.12])
        for x in [1.48,2.56]:self.box('door_jamb',[x,.05,1.14],[.065,.17,2.30],'paint')
        self.box('door_top',[2.02,.05,2.29],[1.15,.17,.065],'paint')
        self.stage_views=[[1.25,2.5],[2.0,3.75],[4.0,2.75]]
        self.stage_centres=[[.38,2.60,1.15],[2.,4.55,1.0],[5.10,2.85,1.10]]
        self.bases=[([.34,2.6],90),([2.,4.56],0),([5.1,2.85],-90)]
        self.sync(g)
    def visible(self,key,g):
        if key=='s2_tool':return bool(g.opened['s2_cover']) and key not in g.taken
        if key.startswith('s3_tool_'):return bool(g.opened['s3_cover']) and key not in g.taken
        if key=='key':return bool(g.opened['key_box']) and key not in g.taken
        return key in self.target_nodes
    def sync(self,g):
        for j,n in enumerate(self.rotors):self.transform(n,rpy=[0,90*g.states[0]['angles'][j],0])
        for key,state in [('battery_drawer','s2_cover'),('tracing_drawer','s3_cover'),('pottery_key_drawer','key_box')]:
            node,p=self.drawers[key];self.transform(node,[p[0],p[1]-(.42 if g.opened[state] else 0),p[2]])
        self.visibility(self.battery,'s2_tool' not in g.taken)
        self.visibility(self.ink,g.states[1]['setup_used']);self.visibility(self.installed,g.states[1]['setup_used'])
        for j,n in enumerate(self.sheets):self.visibility(n,'s3_tool_'+str(j) not in g.taken)
        for j,n in enumerate(self.placed):self.visibility(n,bool(g.states[2]['overlay'][j]))
        for j,node in enumerate(self.placed):self.transform(node,rpy=[0,180*g.states[2]['alignment'][j],0])
        self.visibility(self.key,'key' not in g.taken)
        for key,shader in self.lock_shaders.items():
            value=g.states[int(key[1])-1].get('entered_code','0000')
            if self.lock_values[key]!=value:
                path=self.tex/(key+'_entered_'+str(value)+'.png');self.text_image(value,.27,.088,(47,67,56),(224,228,191)).save(path)
                with self.og.sim.editing_usd():shader.GetInput('file').Set(str(path))
                self.lock_values[key]=value
        self.transform(self.exit_node,rpy=[0,0,-103 if g.opened['exit'] else 0])
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

    observe('s1_clue','Join the bird outline and branch across the three real tiles')
    for j,count in enumerate([3,1,2]):
        for _ in range(count):click('s1_control_'+str(j))
    approach('s2_cover','Open the unlocked battery drawer',stay=True);click('s2_cover','open')
    approach('s2_tool','Take the backlight battery',stay=True);click('s2_tool','take')
    approach('s2_setup','Install the battery in the backlight');click('s2_setup','use','s2_tool')
    observe('s2_clue','Observe the four illuminated porcelain windows')
    approach('s2_lock','Open the tracing sheet drawer with the observed number');click('s2_lock','unlock',code='4263');click('s3_cover','open')
    for j in range(2):
        approach('s3_tool_'+str(j),'Take one of the two incomplete tracings',stay=True);click('s3_tool_'+str(j),'take')
    for j in range(2):
        approach('s3_overlay_'+str(j),'Register the tracing sheet in the frame',stay=j>0);click('s3_overlay_'+str(j),'use','s3_tool_'+str(j))
    click('s3_control_0');d.append('The orange registration corners now match and the strokes join',18)
    observe('s3_clue','Read the joined strokes of the two tracing sheets',stay=True)
    approach('s3_lock','Use the visible combined code',stay=True);click('s3_lock','unlock',code='2318')
    click('key_box','open');d.append('Observe the flat key',18);approach('key','Take the brass key',stay=True);click('key','take')
    approach('exit','Return to the exit');click('exit','use','key');click('exit','open')
    if not exit_test(d.pos,g):raise RuntimeError('Open-door success was not reached')

_aff_build_last(Scene)
