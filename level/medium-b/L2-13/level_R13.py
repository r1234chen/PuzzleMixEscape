from easy88_core import make_level

SPEC = {'id': 'R13', 'title': 'R13 · Toy Collection Room / 玩具收藏室', 'theme': 'toys', 'size': [5.2, 5.0], 'door': {'side': 'west', 'start': 0.65, 'width': 1.04}, 'start': [1.0, 1.0, 1.35], 'start_yaw': 0, 'floor': 'wood', 'stages': [{'kind': 'rotate_rails', 'name': 'small railway table', 'wall': 'island', 'centre': [2.6, 2.6], 'view': [2.5, 1.5], 'board_height': 0.78, 'visual': {'type': 'rail_grid', 'rows': 2, 'cols': 2, 'inlet_side': 'north', 'outlet_side': 'south', 'destination': 'star', 'route_cells': [[0, 0], [0, 1], [1, 1], [1, 0]]}, 'clue': {'type': 'rail_grid', 'rows': 2, 'cols': 2, 'inlet_side': 'north', 'outlet_side': 'south', 'destination': 'star', 'route_cells': [[0, 0], [0, 1], [1, 1], [1, 0]]}, 'clue_text': '', 'furniture_style': 'low_railway_island', 'grid': [2, 2], 'cells': [[0, 0], [0, 1], [1, 0], [1, 1]], 'ports': [[0, 1], [0, 1], [0, 1], [0, 1]], 'initial': [3, 1, 0, 2], 'target': [0, 2, 1, 3], 'inlet': [0, 0, 0], 'outlet': [1, 0, 2], 'auto': False, 'confirm': True, 'design_notes': 'All4 real elbow tracks rotate; check true N/E/S/W connectivity and press launch to send the car to the star. Cargo gate opens only after arrival.'}, {'kind': 'block_faces', 'name': 'two-block display box', 'wall': 'east', 'centre': [4.87, 2.5], 'view': [4.0, 2.5], 'board_height': 0.98, 'visual': {'type': 'block_faces', 'reference': ['triangle', 'leaf'], 'options': ['circle', 'triangle', 'square', 'star', 'leaf', 'cross'], 'faces': 6}, 'clue': {'type': 'block_faces', 'reference': ['triangle', 'leaf'], 'options': ['circle', 'triangle', 'square', 'star', 'leaf', 'cross'], 'faces': 6}, 'clue_text': '', 'furniture_style': 'low_wall_cabinet', 'initial': [0, 3], 'target': [1, 4], 'moduli': [6, 6], 'options': ['circle', 'triangle', 'square', 'star', 'leaf', 'cross'], 'auto': False, 'confirm': True, 'setup': {'kind': 'key', 'item': 'block_cover_key', 'item_name': 'small cover key', 'target_name': 'block cover keyhole', 'gate': True}, 'control_names': ['left display block', 'right display block'], 'design_notes': 'The key is an ordinary transition from stage1. Both fixed blocks can show any of6 faces, including equal faces; no hidden uniqueness rule.'}, {'kind': 'sequence', 'name': 'butterfly pattern box', 'wall': 'north', 'centre': [2.5, 4.67], 'view': [2.5, 3.75], 'board_height': 0.98, 'visual': {'type': 'mirror_grid', 'left': ['leaf', 'square', 'circle', 'leaf'], 'rows': 2, 'cols': 2, 'symmetry_axis': 'vertical', 'input_order': ['top_left', 'top_right', 'bottom_left', 'bottom_right']}, 'clue': {'type': 'mirror_grid', 'left': ['leaf', 'square', 'circle', 'leaf'], 'rows': 2, 'cols': 2, 'symmetry_axis': 'vertical', 'input_order': ['top_left', 'top_right', 'bottom_left', 'bottom_right']}, 'clue_text': '', 'furniture_style': 'low_wall_cabinet', 'options': ['circle', 'triangle', 'square', 'star', 'leaf', 'cross'], 'answer': [2, 4, 4, 0], 'length': 4, 'distinct': False, 'confirm': True, 'design_notes': 'Left wing is [leaf,square;circle,leaf]; reflect across the centre line to complete right wing [square,leaf;leaf,circle]. Never print the right-wing solution as another reference.'}], 'decor': [{'kind': 'toy_cars', 'wall': 'south'}, {'kind': 'teddy_bear', 'wall': 'east'}, {'kind': 'block_shelf', 'wall': 'north'}, {'kind': 'toy_house', 'wall': 'south'}], 'design_notes': 'Central low rail island with a full perimeter passage; block box and butterfly box on different walls. Conventional press/take/use/open only.'}


SPEC['stages'][1].update(target=[3,5],name='opposite-face toy display',clue_text='')
SPEC['stages'][2].update(kind='assign',name='butterfly wing inset',
 items=[{'id':'leaf_a','name':'leaf wing tile A','symbol':'leaf'},{'id':'square','name':'square wing tile','symbol':'square'},
        {'id':'circle','name':'circle wing tile','symbol':'circle'},{'id':'leaf_b','name':'leaf wing tile B','symbol':'leaf'}],
 slots=4,target=[1,0,3,2],auto=False)
for field in ['options','answer','length','distinct']:SPEC['stages'][2].pop(field,None)
Game,_OriginalScene,_OriginalStandard,exit_test,cpu_check=make_level(SPEC)
TITLE=SPEC['title'];LEVEL_ID=SPEC['id'];START=SPEC['start'];START_YAW=SPEC['start_yaw']
CAP=150;OBSERVATION_SIZE=(640,360);VISUAL_ONLY=False;READ_ENABLED=True;READ_FEEDBACK_TEXT=True
Game.LABELS.update({'s1_clue':'four curved toy tracks','s1_confirm':'train launch button','s1_reset':'track reset button',
 's2_cover':'star station cargo drawer','s2_tool':'small block cover key','s2_setup':'block display cover lock',
 's2_clue':'two reference shapes','s2_control_0':'left mounted block','s2_control_1':'right mounted block','s2_confirm':'block pair check button',
 's3_cover':'butterfly sliding cover','s3_clue':'butterfly left wing and four input slots','s3_confirm':'butterfly check icon','s3_reset':'butterfly clear icon',
 'key_box':'key drawer','key':'brass door key'})
LABELS=Game.LABELS
_original_act=Game.act
Game.stage_accessible=lambda self,index:0<=index<3
Game.stage_exposed=lambda self,index:0<=index<3 and bool(self.states[index]['setup_ready'])
def _toy_act(self,a):
    key=a.get('_hit364');kind=a.get('action')
    if a.get('_validated364') and key=='s2_reward':
        from action_feedback import failure_for
        if kind not in ('open','close') or kind=='open' and not self.solved[1]:return {'ok':False,'text':failure_for(kind)}
        self.states[1]['reward_open']=kind=='open';return {'ok':True,'text':''}
    if a.get('_validated364') and key=='s3_tool':
        from action_feedback import failure_for
        if kind!='take' or not self.states[1].get('reward_open') or key in self.taken:return {'ok':False,'text':failure_for(kind)}
        self.taken.add(key);self.holding.append(key);return {'ok':True,'text':''}
    if a.get('_validated364') and key=='s3_cover':
        from action_feedback import failure_for,NO_ITEM
        if kind=='use':
            item=self._resolve_item(a.get('item'))
            if item is None:return {'ok':False,'text':NO_ITEM}
            if item!='s3_tool':return {'ok':False,'text':failure_for(kind)}
            self.states[2]['cover_key_used']=True;return {'ok':True,'text':''}
        if kind=='open' and not self.states[2].get('cover_key_used'):return {'ok':False,'text':failure_for(kind)}
    if a.get('_validated364') and ((key=='s2_tool' and kind=='take' and not self.opened['s2_cover']) or (str(key).startswith('s3_') and key!='s3_cover' and not self.opened['s3_cover'])):
        from action_feedback import failure_for
        return {'ok':False,'text':failure_for(kind)}
    return _original_act(self,a)
Game.act=_toy_act
LABELS.update({'s2_reward':'small drawer below the blocks','s2_tool':'blue cube-tag key','s3_tool':'orange butterfly-tag key'})

_toy_check=Game._check
def _wing_check(self,index):
    if index!=2:return _toy_check(self,index)
    a={int(k):int(v) for k,v in self.states[2]['assignment'].items()}
    if set(a)!=set(range(4)) or len(set(a.values()))!=4:return False
    return [self.SPEC['stages'][2]['items'][a[i]]['symbol'] for i in range(4)]==['square','leaf','leaf','circle']
Game._check=_wing_check

import math
import numpy as np
from PIL import Image,ImageDraw
from easy88_scene import EasyScene
from easy88_clues import draw_symbol
from font_utils import load_font
BLOCK_POSES=[(0,0,0),(0,0,-90),(0,0,180),(0,0,90),(90,0,0),(-90,0,0)]

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
        self.views={};self.focus={};self.labels={};self.drawers={};self.rotors=[];self.blocks=[];self.expanded=[];self._moving_train=False;self.train_fraction=0.;self.screen_signature=None
    def palette(self):
        super().palette()
        for name,c in [('toy_blue',(.17,.32,.38)),('toy_red',(.48,.15,.10)),('toy_green',(.22,.38,.26)),('toy_yellow',(.64,.48,.20)),('toy_cream',(.75,.70,.57)),('track_felt',(.19,.28,.25)),('block_felt',(.28,.37,.30)),('bear_brown',(.45,.29,.16))]:self.mat(name,c,rough=.90)
    def reg_at(self,key,node,label,view,focus=None):
        self.reg(key,node);self.views[key]=list(view);self.labels[key]=label
        if focus is not None:self.focus[key]=list(focus)
        return node
    def flat(self,name,parent,pos,w,h,im,horizontal=False,right=None,up=None):
        path=self.tex/(name+'.png');im.save(path)
        return self.plane(name,pos,w,h,right or (1,0,0),up or ((0,1,0) if horizontal else (0,0,1)),None,parent,material=self.image_mat('r13_'+name,path))
    def identity_badge(self,name,parent,pos,kind,size=.13,reverse=False):
        bg=(48,90,119) if kind=='cube' else (153,95,38)
        im=Image.new('RGB',(320,320),bg);draw=ImageDraw.Draw(im);ink=(240,229,187)
        if kind=='cube':
            draw.polygon([(160,48),(252,99),(160,151),(68,99)],outline=ink,width=13)
            draw.line([(68,99),(68,211),(160,266),(252,211),(252,99)],fill=ink,width=13)
            draw.line([(160,151),(160,266)],fill=ink,width=13)
        else:
            draw.ellipse((63,56,151,174),fill=ink);draw.ellipse((169,56,257,174),fill=ink)
            draw.ellipse((84,163,151,260),fill=ink);draw.ellipse((169,163,236,260),fill=ink)
            draw.line([(160,80),(160,258)],fill=ink,width=15)
            draw.line([(160,104),(135,52)],fill=ink,width=10);draw.line([(160,104),(185,52)],fill=ink,width=10)
        return self.flat(name,parent,pos,size,size,im,right=(-1,0,0) if reverse else (1,0,0),up=(0,0,1))
    def tagged_key(self,key,kind,name):
        colour='toy_blue' if kind=='cube' else 'toy_yellow'
        self.box(name+'_brass_blade',[0,0,-.045],[.014,.012,.120],'brass',key,bevel=.001)
        self.box(name+'_brass_teeth',[.017,0,-.085],[.047,.014,.026],'brass',key,bevel=.001)
        self.box(name+'_coloured_bow',[0,0,.055],[.100,.018,.100],colour,key,bevel=.008)
        self.identity_badge(name+'_top',key,[0,.010,.055],kind,.086,True)
        self.identity_badge(name+'_back',key,[0,-.010,.055],kind,.086)
    def text(self,name,parent,pos,w,h,value,horizontal=False):
        ih=360;iw=max(200,int(ih*w/h));im=Image.new('RGB',(iw,ih),(219,211,183));d=ImageDraw.Draw(im);size=int(ih*.70)
        while size>12:
            box=d.textbbox((0,0),str(value),font=load_font(size))
            if box[2]-box[0]<iw*.84 and box[3]-box[1]<ih*.80:break
            size-=8
        d.text((iw/2,ih/2),str(value),font=load_font(size),fill=(36,60,45),anchor='mm');return self.flat(name,parent,pos,w,h,im,horizontal)
    def drawer(self,key,parent,front,z,width=1.10,depth=.43):
        x,y=front
        for xx in [x-width/2-.025,x+width/2+.025]:self.box(key+'_housing_side',[xx,y+depth/2,z],[.035,depth+.035,.245],'wood',parent)
        self.box(key+'_housing_floor',[x,y+depth/2,z-.128],[width+.08,depth+.04,.026],'darkwood',parent)
        self.box(key+'_housing_back',[x,y+depth,z],[width+.08,.03,.245],'wood',parent)
        self.box(key+'_housing_top',[x,y+depth/2,z+.1275],[width+.08,depth+.04,.025],'wood',parent)
        for xx in [x-width/2,x+width/2]:self.box(key+'_fixed_slide',[xx,y+depth/2,z-.045],[.016,depth-.01,.026],'steel',parent)
        n=self.group(key,[x,y,z],parent)
        self.box(key+'_bottom',[0,depth/2,-.113],[width-.055,depth,.025],'wood',n)
        for xx in [-width/2,width/2]:self.box(key+'_side',[xx,depth/2,-.005],[.025,depth,.235],'wood',n)
        self.box(key+'_rear',[0,depth,-.005],[width,.025,.235],'wood',n)
        for xx in [-width/2,width/2]:self.box(key+'_slide',[xx,depth/2,-.045],[.012,depth-.01,.022],'steel',n)
        face=self.group(key+'_face',parent=n);self.box('drawer_front',[0,0,0],[width+.04,.045,.25],'paint',face);self.box('drawer_pull',[-.26,-.055,.01],[.19,.045,.028],'brass',face)
        self.drawers[key]=(n,[x,y,z]);return n,face

    def glyph(self,name,parent,pos,symbol,size=.22,right=None,up=None):
        im=Image.new('RGB',(320,320),(221,212,181));draw_symbol(ImageDraw.Draw(im),symbol,(55,55,265,265),fill=(42,72,53),outline=(42,72,53))
        return self.flat(name,parent,pos,size,size,im,right=right,up=up)
    def elbow_track(self,parent):
        angles=np.linspace(math.pi,1.5*math.pi,19);points=[]
        for z in [.014,.034]:
            for radius in [.165,.265]:
                points.extend([[.215+radius*math.cos(a),.215+radius*math.sin(a),z] for a in angles])
        n=len(angles);faces=[]
        for j in range(n-1):faces.extend([[j,j+1,n+j+1,n+j],[2*n+j,3*n+j,3*n+j+1,2*n+j+1],[j,2*n+j,2*n+j+1,j+1],[n+j,n+j+1,3*n+j+1,3*n+j]])
        faces.extend([[0,n,3*n,2*n],[n-1,3*n-1,4*n-1,2*n-1]])
        self.mesh('curved_wood_track_bed',points,faces,'wood',parent)
        for radius in [.1875,.2425]:
            path=[[.215+radius*math.cos(a),.215+radius*math.sin(a),.044] for a in angles]
            for a,b in zip(path,path[1:]):self.tube('curved_metal_rail',a,b,.007,'steel',parent)
        for a in np.linspace(math.pi,1.5*math.pi,7):
            self.tube('wooden_rail_tie',[.215+.158*math.cos(a),.215+.158*math.sin(a),.030],[.215+.272*math.cos(a),.215+.272*math.sin(a),.030],.010,'darkwood',parent)
    def rail_route(self):
        points=[(np.array([2.385,3.22]),-90.),(np.array([2.385,3.03]),-90.)]
        for row,col,q,reverse in [(0,0,0,False),(0,1,2,True),(1,1,3,True),(1,0,1,False)]:
            centre=np.array([2.6+(col-.5)*.43,2.6+(.5-row)*.43]);a=-q*math.pi/2;R=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
            angles=np.linspace(1.5*math.pi,math.pi,5) if reverse else np.linspace(math.pi,1.5*math.pi,5)
            for theta in angles[1:]:
                point=centre+R@np.array([.215+.215*math.cos(theta),.215+.215*math.sin(theta)])
                tangent=R@np.array([-math.sin(theta),math.cos(theta)])*(-1 if reverse else 1);points.append((point,math.degrees(math.atan2(tangent[1],tangent[0]))))
        points.extend([(np.array([2.385,2.08]),-90.),(np.array([2.385,1.98]),-90.)]);return points
    def place_train(self,fraction):
        route=self.rail_route();index=min(len(route)-1,int(round(float(fraction)*(len(route)-1))));xy,yaw=route[index];self.transform(self.train,[float(xy[0]),float(xy[1]),.747],[0,0,yaw])
    def butterfly_screen(self,buffer,solved=False):
        im=Image.new('RGB',(1200,660),(31,46,42));d=ImageDraw.Draw(im)
        left=[(550,235),(470,70),(120,45),(95,190),(195,390),(520,400)];right=[(1200-x,y) for x,y in left]
        d.polygon(left,fill=(65,89,81),outline=(174,188,158),width=5);d.polygon(right,fill=(65,89,81),outline=(174,188,158),width=5)
        for z in range(107,330,30):d.line((600,z,600,z+15),fill=(179,193,165),width=5)
        reference=['leaf','square','circle','leaf']
        for j,symbol in enumerate(reference):
            x=190+(j%2)*200;y=135+(j//2)*180;d.rounded_rectangle((x-81,y-72,x+81,y+72),radius=12,fill=(220,213,183));draw_symbol(d,symbol,(x-49,y-49,x+49,y+49),fill=(42,69,51),outline=(42,69,51))
        for j in range(4):
            x=810+(j%2)*200;y=135+(j//2)*180;d.rounded_rectangle((x-81,y-72,x+81,y+72),radius=12,fill=(39,58,49),outline=(132,159,126),width=4)
            if j<len(buffer):draw_symbol(d,SPEC['stages'][2]['options'][buffer[j]],(x-49,y-49,x+49,y+49),fill=(224,219,188),outline=(224,219,188))
            else:d.text((x-67,y-62),str(j+1),font=load_font(27),fill=(145,166,139))
        d.line([(567,42),(592,69),(637,17)],fill=(224,230,191),width=10)
        d.arc((568,342,634,408),35,306,fill=(224,230,191),width=8);d.polygon([(636,340),(641,372),(610,356)],fill=(224,230,191))
        for j,symbol in enumerate(SPEC['stages'][2]['options']):
            x=200+(j%3)*400;y=495+(j//3)*110;d.rounded_rectangle((x-181,y-47,x+181,y+47),radius=13,fill=(45,65,52),outline=(94,124,100),width=3)
            draw_symbol(d,symbol,(x-36,y-36,x+36,y+36),fill=(226,219,187),outline=(226,219,187))
        d.rounded_rectangle((3,3,1197,657),radius=20,outline=(98,158,100) if solved else (101,130,107),width=6)
        path=self.tex/('butterfly_input_'+(''.join(map(str,buffer)) or 'empty')+('_ok' if solved else '')+'.png');im.save(path);return path
    def butterfly_piece(self,key,rect,target=True):
        x0,y0,x1,y1=rect;points=[]
        for x,y in [(x0,y1),(x1,y1),(x1,y0),(x0,y0)]:points.append([(x/1200-.5)*1.10,-.280,1.09+(.5-y/660)*.60])
        uv=[(x0/1200,1-y1/660),(x1/1200,1-y1/660),(x1/1200,1-y0/660),(x0/1200,1-y0/660)]
        node=self.mesh(key+'_display',points,[[0,1,2,3]],self.screen_mat,self.butterfly,uv=uv)
        if target:self.reg_at(key,node,LABELS.get(key,key.replace('_',' ')),[2.75,3.5],[2.8,4.32,1.09])
        return node
    def rounded_toy(self,name,parent,pos,size,material):
        n=self.group(name,pos,parent);pts=[[0,0,-size[2]],[0,0,size[2]]];faces=[];rings=7;count=20
        for j in range(1,rings+1):
            phi=-math.pi/2+math.pi*j/(rings+1)
            for k in range(count):
                a=k*2*math.pi/count;pts.append([size[0]*math.cos(phi)*math.cos(a),size[1]*math.cos(phi)*math.sin(a),size[2]*math.sin(phi)])
        for k in range(count):
            q=(k+1)%count;faces.extend([[0,2+q,2+k],[1,2+(rings-1)*count+k,2+(rings-1)*count+q]])
        for j in range(rings-1):
            for k in range(count):
                q=(k+1)%count;faces.append([2+j*count+k,2+j*count+q,2+(j+1)*count+q,2+(j+1)*count+k])
        self.mesh('rounded_toy_part',pts,faces,material,n);return n
    def build(self,g):
        self.room_shell('toy_collection_room',size=(5.2,5),openings={'west':[(.62,1.72)]});self.box('solid_subfloor',[2.6,2.5,-.075],[5.34,5.14,.10],'darkwood',bevel=.001)
        self.table('low_railway_table',(2.6,2.6),(1.28,1.40),height=.62)
        self.track=self.group('rotating_railway_board',[2.6,2.6,.673]);self.box('rail_board_base',[0,0,-.010],[1.19,1.32,.025],'track_felt',self.track)
        for j,(row,col) in enumerate([[0,0],[0,1],[1,0],[1,1]]):
            node=self.group('curved_track_tile_'+str(j),[(col-.5)*.43,(.5-row)*.43,0],self.track);self.box('rotating_tile',[0,0,0],[.421,.421,.026],'toy_cream',node);self.elbow_track(node);self.rotors.append(node)
            self.reg_at('s1_control_'+str(j),node,'curved track tile',[2.5,1.5],[2.6,2.6,.72])
            _add_mark(self,'track_turn_mark_'+str(j),node,[.17,.17,.0135],'turn',.05,up=(0,1,0))
        for y0,y1 in [(3.22,3.03),(2.17,1.98)]:
            self.box('straight_track_bed',[2.385,(y0+y1)/2,.699],[.11,abs(y1-y0),.020],'wood')
            for x in [2.3575,2.4125]:self.tube('straight_metal_rail',[x,y0,.717],[x,y1,.717],.007,'steel')
        self.station=self.group('south_star_station',[2.65,1.995,.705]);self.box('station_sign',[0,0,0],[.19,.15,.025],'toy_blue',self.station)
        star=Image.new('RGB',(240,180),(42,73,77));draw_symbol(ImageDraw.Draw(star),'star',(56,24,184,156),fill=(228,202,116),outline=(228,202,116));self.flat('station_star',self.station,[0,0,.014],.17,.13,star,True)
        self.launch=self.group('train_launch_button',[3.03,2.0,.705]);self.cylinder('launch_bezel',[0,0,0],.064,.025,'iron','z',self.launch,n=28)
        image=Image.new('RGB',(180,180),(219,213,183));ImageDraw.Draw(image).polygon([(60,38),(60,142),(143,90)],fill=(41,76,56));self.flat('launch_play',self.launch,[0,0,.014],.105,.105,image,True);self.reg_at('s1_confirm',self.launch,'train launch button',[2.5,1.5],[2.6,2.6,.72])
        self.reset=self.group('rail_reset_button',[2.03,2.0,.705]);self.cylinder('reset_bezel',[0,0,0],.047,.024,'iron','z',self.reset,n=24);self.reg_at('s1_reset',self.reset,'track reset button',[2.5,1.5],[2.6,2.6,.72])
        self.text('reset_label',self.reset,[0,-.002,.016],.07,.06,'↻',True)
        self.reg_at('s1_clue',self.track,'four curved toy tracks',[2.5,1.5],[2.6,2.6,.72])
        self.train=self.group('wooden_toy_train');self.box('train_chassis',[0,0,.020],[.145,.077,.025],'toy_red',self.train)
        self.cylinder('toy_locomotive_boiler',[.025,0,.055],.026,.10,'toy_green','x',self.train,n=24);self.box('train_cab',[-.045,0,.061],[.05,.068,.072],'toy_blue',self.train)
        self.cylinder('train_chimney',[.055,0,.092],.009,.048,'iron','z',self.train,n=20)
        for x in [-.045,.045]:
            for y in [-.035,.035]:self.cylinder('toy_train_wheel',[x,y,0],.023,.013,'iron','y',self.train,n=24)
        self.cargodrawer,cargofront=self.drawer('station_cargo_drawer',None,(2.385,1.90),.44,width=.59,depth=.40)
        self.reg_at('s2_cover',cargofront,'star station cargo drawer',[2.5,1.0],[2.385,1.90,.44]);self.box('cover_key_pad',[0,.20,-.021],[.46,.31,.158],'block_felt',self.cargodrawer)
        self.cover_key=self.group('block_cover_key',[0,.20,.069],self.cargodrawer);self.target_nodes.pop('block_cover_key',None);self.transform(self.cover_key,rpy=[90,0,0]);self.reg_at('s2_tool',self.cover_key,LABELS['s2_tool'],[2.5,1.0],[2.385,1.68,.509])
        self.tagged_key(self.cover_key,'cube','cube_key_identity')
        self.blockcase=self.group('mounted_block_cabinet',[4.78,2.5,0]);self.transform(self.blockcase,rpy=[0,0,-90])
        self.box('block_cabinet_plinth',[0,0,.0175],[1.26,.48,.035],'darkwood',self.blockcase)
        self.box('block_cabinet_back',[0,.28,.34],[1.38,.035,.61],'wood',self.blockcase)
        for x in [-.67,.67]:self.box('block_cabinet_side',[x,0,.34],[.035,.60,.61],'wood',self.blockcase)
        self.box('block_cabinet_bottom',[0,0,.045],[1.38,.60,.035],'wood',self.blockcase)
        self.box('block_counter',[0,0,.70],[1.47,.65,.05],'wood',self.blockcase)
        for x in [-.34,.34]:
            self.box('lower_cupboard_door',[x,-.31,.20],[.64,.034,.29],'paint',self.blockcase);self.box('lower_cupboard_handle',[x+(.20 if x<0 else -.20),-.34,.21],[.022,.04,.14],'brass',self.blockcase)
        self.add_obstacle(4.43,1.75,5.14,3.25)
        for x in [-.62,.62]:self.box('block_case_side',[x,-.05,1.065],[.03,.50,.68],'wood',self.blockcase)
        self.box('block_case_back',[0,.19,1.065],[1.27,.03,.68],'wood',self.blockcase);self.box('block_case_top',[0,-.05,1.415],[1.30,.53,.035],'wood',self.blockcase)
        self.box('block_case_floor',[0,-.05,.7375],[1.27,.50,.025],'wood',self.blockcase);self.box('block_case_lining',[0,-.05,.7545],[1.21,.45,.009],'block_felt',self.blockcase)
        self.reference=self.group('block_reference_strip',[0,.151,1.20],self.blockcase)
        for j,symbol in enumerate(['triangle','leaf']):self.glyph('reference_shape_'+str(j),self.reference,[(j-.5)*.62,-.001,0],symbol,.16)
        self.text('opposite_face_instruction',self.reference,[0,-.003,.14],.93,.10,'SHOW OPPOSITE')
        self.reg_at('s2_clue',self.reference,'opposite-face reference',[3.5,2.5],[4.63,2.5,1.27])
        for j in range(2):
            x=(j-.5)*.62
            self.box('block_pivot_base',[x,-.05,.774],[.53,.32,.03],'darkwood',self.blockcase)
            for side in [-1,1]:
                self.box('block_support_fork',[x+side*.235,-.04,.885],[.026,.035,.23],'wood',self.blockcase);self.cylinder('block_pivot_pin',[x+side*.18,-.04,.99],.012,.14,'brass','x',self.blockcase,n=20)
            n=self.group('six_face_block_'+str(j),[x,-.04,.99],self.blockcase);self.box('wooden_cube',[0,0,0],[.25,.25,.25],'toy_cream',n,bevel=.008)
            for k,(pos,right,up) in enumerate([([0,-.126,0],(1,0,0),(0,0,1)),([.126,0,0],(0,1,0),(0,0,1)),([0,.126,0],(-1,0,0),(0,0,1)),([-.126,0,0],(0,-1,0),(0,0,1)),([0,0,.126],(1,0,0),(0,1,0)),([0,0,-.126],(1,0,0),(0,-1,0))]):self.glyph('block_face_'+str(j)+'_'+str(k),n,pos,SPEC['stages'][1]['options'][k],.218,right,up)
            self.blocks.append(n);self.reg_at('s2_control_'+str(j),n,LABELS['s2_control_'+str(j)],[3.75,2.5],[4.70,2.5,.99])
            _add_box(self,'block_turn_tag',[x+.20,-.195,.81],[.05,.008,.045],'darkwood',self.blockcase)
            _add_mark(self,'block_turn_mark_'+str(j),self.blockcase,[x+.20,-.2,.81],'turn',.04)
        check=self.group('block_pair_check',[0,-.285,.805],self.blockcase);self.box('block_check_button',[0,0,0],[.14,.028,.070],'iron',check);self.text('block_check_mark',check,[0,-.015,0],.126,.06,'✓');self.reg_at('s2_confirm',check,'block pair check button',[3.75,2.5],[4.48,2.5,.81])
        self.block_cover=self.group('block_cover_hinge',[0,-.32,1.415],self.blockcase)
        face=self.group('block_cover_face',parent=self.block_cover);self.box('block_protection_cover',[0,0,-.335],[1.30,.035,.67],'paint',face)
        self.box('cover_pull',[0,-.040,-.57],[.19,.045,.030],'brass',face);self.cylinder('cover_keyhole',[.45,-.022,-.54],.012,.008,'iron','y',face,n=20);self.reg_at('s2_setup',face,'block display cover lock',[3.75,2.5],[4.44,2.5,1.0])
        self.identity_badge('cube_lock_identity',face,[.22,-.021,-.32],'cube',.22)
        self.cube_net=self.group('folded_cube_reference',[0,.021,-.32],self.block_cover)
        self.reg_at('s2_net',self.cube_net,'cube unfolding diagram',[3.5,2.5])
        for j,(symbol,cx,cz) in enumerate([('circle',0,0),('triangle',1,0),('square',2,0),('star',-1,0),('leaf',0,1),('cross',0,-1)]):
            self.glyph('cube_net_face_'+str(j),self.cube_net,[cx*.12,0,cz*.12],symbol,.112,right=(1,0,0),up=(0,0,-1))
        root=self.group('block_reward_drawer_support',[4.78,2.50,0]);self.transform(root,rpy=[0,0,-90])
        self.wing_keydrawer,face=self.drawer('block_reward_drawer',root,(0,-.30),.54,1.02,.43)
        self.reg_at('s2_reward',face,LABELS['s2_reward'],[3.75,2.50],[4.50,2.50,.54])
        self.box('wing_key_pad',[0,.21,-.02],[.88,.32,.15],'block_felt',self.wing_keydrawer)
        self.wing_key=self.group('physical_butterfly_key',[0,.21,.065],self.wing_keydrawer);self.target_nodes.pop('physical_butterfly_key',None);self.transform(self.wing_key,rpy=[90,0,0]);self.reg_at('s3_tool',self.wing_key,LABELS['s3_tool'],[3.75,2.50])
        self.tagged_key(self.wing_key,'butterfly','butterfly_key_identity')
        self.block_red=self.cylinder('block_drawer_red',[.42,-.027,.025],.014,.010,'red_led','y',face,n=20)
        self.block_green=self.cylinder('block_drawer_green',[.42,-.027,.025],.014,.010,'green','y',face,n=20)
        self.table('butterfly_work_cabinet',(2.60,4.60),(3.20,.70),height=.72)
        self.butterfly=self.group('butterfly_pattern_box',[2.80,4.60,0])
        for x in [-.62,.62]:self.box('butterfly_box_side',[x,-.01,1.10],[.03,.55,.70],'wood',self.butterfly)
        self.box('butterfly_box_back',[0,.245,1.10],[1.27,.03,.70],'paint',self.butterfly);self.box('butterfly_box_top',[0,-.01,1.46],[1.30,.57,.035],'wood',self.butterfly);self.box('butterfly_box_bottom',[0,-.01,.745],[1.27,.55,.025],'wood',self.butterfly)
        self.wing_slots=[];self.wing_tiles=[]
        for j,symbol in enumerate(['leaf','square','circle','leaf']):
            row,col=divmod(j,2);x=-.43+col*.22;z=1.28-row*.24
            self.glyph('fixed_left_wing_'+str(j),self.butterfly,[x,-.266,z],symbol,.19)
        self.box('butterfly_axis',[0,-.268,1.16],[.012,.015,.53],'brass',self.butterfly)
        self.reg_at('s3_clue',self.butterfly,'left butterfly wing',[2.75,3.5],[2.8,4.3,1.17])
        for j in range(4):
            row,col=divmod(j,2);pos=[.21+col*.22,-.268,1.28-row*.24]
            slot=self.group('wing_recess_'+str(j),pos,self.butterfly);self.box('empty_wing_socket',[0,0,0],[.20,.022,.20],'block_felt',slot)
            self.reg_at('s3_slot_'+str(j),slot,'right wing recess',[2.75,3.5]);self.wing_slots.append(pos)
            tile=self.group('loose_wing_tile_'+str(j),[(j-1.5)*.24,-.12,.795],self.butterfly)
            self.box('wood_wing_inset',[0,0,0],[.18,.18,.025],'wood',tile)
            symbol=SPEC['stages'][2]['items'][j]['symbol'];self.glyph('loose_wing_face_'+str(j),tile,[0,0,.014],symbol,.17,right=(1,0,0),up=(0,1,0))
            label=SPEC['stages'][2]['items'][j]['name'];self.reg_at('s3_item_'+str(j),tile,label,[2.75,3.5]);LABELS['s3_item_'+str(j)]=label;self.wing_tiles.append(tile)
        button=self.group('wing_check',[.55,-.27,.805],self.butterfly);self.box('wing_check_button',[0,0,0],[.11,.035,.065],'iron',button);self.text('wing_check_mark',button,[0,-.020,0],.08,.05,'✓');self.reg_at('s3_confirm',button,'wing check button',[2.75,3.5])
        self.butterfly_cover=self.group('butterfly_sliding_cover',[0,-.316,1.10],self.butterfly)
        cover=self.group('butterfly_cover_face',parent=self.butterfly_cover);self.box('sliding_wood_cover',[0,0,0],[1.30,.032,.72],'paint',cover);self.box('sliding_cover_pull',[.53,-.039,0],[.024,.045,.15],'brass',cover)
        for z in [.728,1.473]:self.box('long_cover_slide_rail',[-.62,-.300,z],[2.61,.055,.025],'iron',self.butterfly)
        self.box('sliding_cover_support_stile',[-1.72,-.235,1.10],[.035,.050,.76],'wood',self.butterfly)
        for z in [.728,1.473]:self.box('slide_rail_support_bracket',[-1.72,-.275,z],[.042,.080,.022],'iron',self.butterfly)
        self.identity_badge('butterfly_lock_identity',cover,[0,-.020,.08],'butterfly',.25)
        self.cylinder('butterfly_cover_keyhole',[.46,-.020,-.16],.012,.008,'iron','y',cover,n=20)
        self.reg_at('s3_cover',cover,'butterfly sliding cover',[2.75,3.5],[2.8,4.27,1.1])
        self.keydrawer,keyfront=self.drawer('butterfly_key_drawer',None,(2.80,4.25),.54,width=1.14,depth=.44)
        self.reg_at('key_box',keyfront,'key drawer',[2.75,3.5],[2.8,4.25,.54]);self.box('door_key_pad',[0,.21,-.021],[.92,.34,.158],'block_felt',self.keydrawer)
        self.key=self.tool('flat_brass_key',self.keydrawer,[0,.21,.069],'key');self.target_nodes.pop('flat_brass_key',None);self.transform(self.key,rpy=[90,0,0]);self.reg_at('key',self.key,'brass door key',[2.75,3.5],[2.8,4.04,.609])
        shelf=self.group('toy_display_shelf',[.25,3.20,0]);self.transform(shelf,rpy=[0,0,90])
        for x in [-.66,.66]:self.box('shelf_upright',[x,0,.71],[.055,.40,1.42],'darkwood',shelf)
        for z in [.15,.75,1.33]:self.box('shelf_board',[0,0,z],[1.39,.43,.04],'wood',shelf)
        self.box('shelf_back',[0,.18,.71],[1.32,.035,1.40],'paint',shelf);self.add_obstacle(.03,2.48,.50,3.92)
        bear=self.group('fixed_toy_bear',[0,-.02,1.35],shelf)
        self.rounded_toy('bear_body',bear,[0,0,.13],[.10,.07,.13],'bear_brown');self.rounded_toy('bear_head',bear,[0,-.01,.31],[.10,.08,.09],'bear_brown')
        for side in [-1,1]:
            self.rounded_toy('bear_ear_'+str(side+1),bear,[side*.077,0,.37],[.035,.025,.04],'bear_brown');self.rounded_toy('bear_arm_'+str(side+1),bear,[side*.12,0,.17],[.04,.045,.08],'bear_brown');self.rounded_toy('bear_foot_'+str(side+1),bear,[side*.055,-.04,.035],[.045,.065,.035],'bear_brown')
            self.cylinder('bear_eye',[side*.035,-.086,.325],.008,.005,'iron','y',bear,n=16)
        car=self.group('fixed_toy_car',[0,-.015,.794],shelf);self.box('car_body',[0,0,.03],[.29,.12,.055],'toy_red',car);self.box('car_cabin',[-.02,0,.082],[.13,.11,.065],'toy_blue',car)
        for x in [-.095,.095]:
            for y in [-.066,.066]:self.cylinder('car_wheel',[x,y,.008],.032,.015,'iron','y',car,n=24)
        for j in range(4):self.box('fixed_building_block',[(j-1.5)*.20,0,.245],[.16,.18,.15],['toy_red','toy_blue','toy_yellow','toy_green'][j],shelf,bevel=.008)
        house=self.group('fixed_toy_house',[3.95,.28,0]);self.box('house_body',[0,0,.17],[.56,.35,.34],'toy_cream',house)
        self.mesh('toy_house_roof',[[-.33,-.22,.32],[.33,-.22,.32],[0,-.22,.55],[-.33,.22,.32],[.33,.22,.32],[0,.22,.55]],[[0,1,2],[3,5,4],[0,3,4,1],[1,4,5,2],[2,5,3,0]],'toy_red',house)
        self.box('house_front_door',[0,-.183,.13],[.12,.012,.24],'toy_blue',house);self.add_obstacle(3.57,.04,4.33,.56)
        self.exit_node=self.door('toy_room_exit',[.06,1.69,0],1.04);self.door_angle=-90;self.reg_at('exit',self.exit_node,'exit door',[1.0,1.25],[.06,1.17,1.12]);self.door_view=[1.0,1.25]
        for y in [.63,1.71]:self.box('door_jamb',[.05,y,1.14],[.17,.065,2.30],'paint')
        self.box('door_lintel',[.05,1.17,2.29],[.17,1.15,.065],'paint')
        for y in [.64,1.70]:self.box('door_stop_jamb',[.01,y,1.14],[.026,.035,2.28],'darkwood')
        self.box('door_stop_top',[.01,1.17,2.28],[.026,1.13,.035],'darkwood')
        self.stage_views=[[2.5,1.5],[3.75,2.5],[2.75,3.5]];self.stage_centres=[[2.6,2.6,.72],[4.68,2.5,1.12],[2.8,4.32,1.09]]
        self.bases=[([2.6,2.6],0),([4.78,2.5],-90),([2.8,4.6],0)];self.sync(g)
    def visible(self,key,g):
        if key=='s3_tool':return bool(g.states[1].get('reward_open')) and key not in g.taken
        if key=='s2_net':return bool(g.states[1]['setup_open'])
        if key.startswith('s3_item_') or key.startswith('s3_slot_'):return bool(g.opened['s3_cover']) and key not in g.holding
        if key=='s2_tool':return bool(g.opened['s2_cover']) and key not in g.taken
        if key in ('s2_clue','s2_control_0','s2_control_1','s2_confirm'):return bool(g.states[1]['setup_open'])
        if key=='s3_clue' or key.startswith('s3_choice_') or key in ('s3_confirm','s3_reset'):return bool(g.opened['s3_cover'])
        if key=='key':return bool(g.opened['key_box']) and key not in g.taken
        return key in self.target_nodes
    def sync(self,g):
        node,pos=self.drawers['block_reward_drawer'];self.transform(node,[pos[0],pos[1]-(.42 if g.states[1].get('reward_open') else 0),pos[2]])
        self.visibility(self.wing_key,bool(g.states[1].get('reward_open')) and 's3_tool' not in g.taken)
        self.visibility(self.block_red,not g.solved[1]);self.visibility(self.block_green,g.solved[1])
        for j,node in enumerate(self.rotors):self.transform(node,rpy=[0,0,-90*g.states[0]['angles'][j]])
        if not self._moving_train:self.train_fraction=float(bool(g.states[0]['launched']))
        self.place_train(self.train_fraction)
        for name,flag in [('station_cargo_drawer',g.opened['s2_cover']),('butterfly_key_drawer',g.opened['key_box'])]:
            n,p=self.drawers[name];self.transform(n,[p[0],p[1]-(.42 if flag else 0),p[2]])
        self.visibility(self.cover_key,'s2_tool' not in g.taken)
        self.transform(self.block_cover,rpy=[-160 if g.states[1]['setup_open'] else 0,0,0])
        for j,node in enumerate(self.blocks):self.transform(node,rpy=BLOCK_POSES[g.states[1]['angles'][j]])
        self.transform(self.butterfly_cover,[-1.27 if g.opened['s3_cover'] else 0,-.316,1.10])
        assignments={int(k):int(v) for k,v in g.states[2]['assignment'].items()}
        for j,tile in enumerate(self.wing_tiles):
            slot=next((k for k,v in assignments.items() if v==j),None)
            if slot is None:self.transform(tile,[(j-1.5)*.24,-.12,.795],rpy=[0,0,0])
            else:
                p=self.wing_slots[slot];self.transform(tile,[p[0],p[1]-.026,p[2]],rpy=[90,0,0])
            self.visibility(tile,'s3_item_'+str(j) not in g.holding and g.opened['s3_cover'])
        self.visibility(self.key,'key' not in g.taken);self.transform(self.exit_node,rpy=[0,0,self.door_angle-(103 if g.opened['exit'] else 0)])
        self.expanded=[]
        for flag,node in [(g.opened['s2_cover'],self.cargodrawer),(g.states[1]['setup_open'],self.block_cover),(g.opened['key_box'],self.keydrawer)]:
            if flag:
                pts=self.triangles(node).reshape(-1,3);self.expanded.append((pts.min(0)[:2]-.12,pts.max(0)[:2]+.12))
        self.centres={}
        for key,node in self.target_nodes.items():
            pts=self.triangles(node).reshape(-1,3)
            if pts.size:self.centres[key]=((pts.min(0)+pts.max(0))/2).tolist()
    def candidates(self,g):return self.base_candidates([k for k in self.target_nodes if self.visible(k,g)])
    def blocked(self,x,y,g):return super().blocked(x,y,g) or any(lo[0]<x<hi[0] and lo[1]<y<hi[1] for lo,hi in self.expanded)
    def view_for(self,key):return self.views.get(key,[1.0,1.0])
    def focus_for(self,key):return self.focus.get(key,self.centres.get(key))
    def label_for(self,key):return self.labels.get(key,LABELS.get(key,key.replace('_',' ')))
    def animate(self,d,before):
        old_angles=before['states'][0]['angles'];new_angles=d.game.states[0]['angles']
        for j,(a,b) in enumerate(zip(old_angles,new_angles)):
            if a!=b:
                for q in [.33,.67]:self.sync(d.game);self.transform(self.rotors[j],rpy=[0,0,-90*(a+(b-a)*q)]);d.frame(warm=4);d.append('Curved toy track turns',4)
        if d.game.states[0]['launched'] and not before['states'][0]['launched']:
            self._moving_train=True
            route=self.rail_route()
            for k in range(len(route)):
                self.train_fraction=k/(len(route)-1);self.sync(d.game);d.frame(warm=4);d.append('The toy train follows the connected track to the star station',3)
            self._moving_train=False;self.train_fraction=1.
        old=before.get('opened',{})
        for key,name in [('s2_cover','station_cargo_drawer'),('key_box','butterfly_key_drawer')]:
            if bool(old.get(key))!=bool(d.game.opened[key]):
                n,p=self.drawers[name]
                for q in [.33,.67]:
                    t=float(bool(old.get(key)))+(float(bool(d.game.opened[key]))-float(bool(old.get(key))))*q;self.sync(d.game);self.transform(n,[p[0],p[1]-.42*t,p[2]]);d.frame(warm=4);d.append('Toy compartment opens',4)
        prev=before['states'][1].get('setup_open',False);cur=d.game.states[1]['setup_open']
        if bool(prev)!=bool(cur):
            for q in [.33,.67]:
                t=float(bool(prev))+(float(bool(cur))-float(bool(prev)))*q;self.sync(d.game);self.transform(self.block_cover,rpy=[-160*t,0,0]);d.frame(warm=4);d.append('Block display cover opens',4)
        from scipy.spatial.transform import Rotation,Slerp
        for j,(a,b) in enumerate(zip(before['states'][1]['angles'],d.game.states[1]['angles'])):
            if a!=b:
                interpolation=Slerp([0,1],Rotation.from_euler('xyz',[BLOCK_POSES[a],BLOCK_POSES[b]],degrees=True))
                for q in [.33,.67]:self.sync(d.game);self.transform(self.blocks[j],rpy=interpolation([q]).as_euler('xyz',degrees=True)[0]);d.frame(warm=4);d.append('The mounted wooden block turns to its next face',4)
        if bool(old.get('s3_cover'))!=bool(d.game.opened['s3_cover']):
            for q in [.33,.67]:
                t=float(bool(old.get('s3_cover')))+(float(bool(d.game.opened['s3_cover']))-float(bool(old.get('s3_cover'))))*q;self.sync(d.game);self.transform(self.butterfly_cover,[-1.27*t,-.316,1.10]);d.frame(warm=4);d.append('Butterfly cover slides along the wall',4)
        self.sync(d.game)

def standard(d):
    import heapq,numpy as np
    from observation1280 import FX,FY,CX,CY
    from pixel355 import find_point
    from oracle355 import _edge_clear,_turn_actions,_wrap
    from easy88_core import reachable_approach
    g=d.game;sc=d.scene
    def candidate(key):return next((c for c in sc.candidates(g) if c['key']==key),None)
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
        start=tuple(int(round(float(v)/.25)) for v in d.pos[:2]);goal=tuple(int(round(float(v)/.25)) for v in destination)
        xy=lambda n:(n[0]*.25,n[1]*.25)
        if math.dist(xy(start),d.pos[:2])>.005 or math.dist(xy(goal),destination)>.005:raise ValueError('Non-lattice route; no snapping')
        extra=[]
        if g.opened.get('key_box'):
            tri=sc.triangles(sc.target_nodes['key_box'])
            if tri.size:
                lo=tri.reshape(-1,3).min(0);hi=tri.reshape(-1,3).max(0);extra=[(lo[:2]-.12,hi[:2]+.12)]
        def blocked(x,y):return sc.blocked(x,y,g) or any(lo[0]<x<hi[0] and lo[1]<y<hi[1] for lo,hi in extra)
        if blocked(*xy(start)) or blocked(*xy(goal)):raise ValueError('Blocked actual public route endpoint')
        queue=[];cost={};parents={};initial={}
        for k in range(4):
            turns=_turn_actions(_wrap(k*math.pi/2-d.yaw));state=(*start,k);value=(len(turns),0.,sum(a['degrees'] for a in turns));cost[state]=value;initial[state]=turns;heapq.heappush(queue,(*value,state))
        final=None
        while queue:
            n,dist,angle,state=heapq.heappop(queue)
            if cost[state]!=(n,dist,angle):continue
            x,y,k=state
            if (x,y)==goal and k==goal_heading:final=state;break
            transitions=[]
            for side,dk in [('left',1),('right',-1)]:transitions.append(((x,y,(k+dk)%4),{'action':'turn','direction':side,'degrees':90},0.,90))
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
                if value<cost.get(nxt,(math.inf,math.inf,math.inf)):cost[nxt]=value;parents[nxt]=(state,a);heapq.heappush(queue,(*value,nxt))
        if final is None:raise RuntimeError('No legal public action route')
        actions=[];state=final
        while state in parents:state,a=parents[state];actions.append(a)
        actions=list(initial[state])+list(reversed(actions))
        if any(a['action'] in ('walk','side_step','step_back') for a in actions) and d.pitch<math.radians(-25):
            d._turn_vertical_to(math.radians(-20),'Look ahead while moving between the furniture')
        for a in actions:d.execute(a,purpose)
    def approach(key,purpose,stay=False):
        view=list(d.pos[:2]) if stay else [round(float(v)*4)/4 for v in sc.view_for(key)]
        if view is None:raise RuntimeError('No physical approach for '+key)
        point,k=axis_focus(key,view)
        if not stay:route_short(view,k,purpose)
        d.aim(point,purpose)
    def observe(key,purpose,stay=False):approach(key,purpose,stay);d.append(purpose,18)
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
            route_short(view,axis_focus(key,view)[1],'Approach the actual visible surface');d.aim(centre(key),'Look at the reachable object')
            hit=find_point(key,d.pos,d.quat,d.depth,sc.candidates(g),fx=FX,fy=FY,cx=CX,cy=CY,actor_xy=d.pos[:2],tolerance=.05,mesh_tolerance=.04,grid=61,return_hit=True)
        if hit is None or float(hit['distance'])>reach:raise RuntimeError('No current visible native pixel within unchanged reach for '+key)
        a={'thought':'Use the clue and the actual room object.','action':kind,'point':hit['point'],'target':LABELS.get(key,key.replace('_',' '))}
        if item is not None:a['item']=LABELS.get(item,item)
        if code is not None:a['code']=str(code)
        return d.execute(a,'Observe the physical response')

    observe('s1_clue','Observe the four actual curved track pieces and the star station')
    for j,want in enumerate(SPEC['stages'][0]['target']):
        while g.states[0]['angles'][j]!=want:click('s1_control_'+str(j))
    click('s1_confirm')
    approach('s2_cover','Step back to the cargo drawer beneath the star station');click('s2_cover','open');d.append('Observe the flat small key in the cargo drawer',18);click('s2_tool','take')
    approach('s2_setup','Approach the mounted block display');click('s2_setup','use','s2_tool');click('s2_setup','open')
    observe('s2_net','Inspect the unfolded cube on the inside of the raised cover')
    observe('s2_clue','Infer the faces opposite the two shown shapes',stay=True)
    approach('s2_control_0','Use the cube net to find the opposite faces',stay=True)
    for j,want in enumerate(SPEC['stages'][1]['target']):
        while g.states[1]['angles'][j]!=want:click('s2_control_'+str(j))
    click('s2_confirm')
    approach('s2_reward','The green lamp marks the released drawer below the blocks',stay=True);click('s2_reward','open');d.append('The drawer contains the butterfly cover key',18);click('s3_tool','take')
    approach('s3_cover','Use the recovered key on the butterfly cover lock');click('s3_cover','use','s3_tool');click('s3_cover','open')
    observe('s3_clue','Reflect the fixed left wing across the centre line',stay=True)
    for slot,item in enumerate([1,0,3,2]):
        click('s3_item_'+str(item),'take');click('s3_slot_'+str(slot),'use','s3_item_'+str(item))
    click('s3_confirm');approach('key_box','Open the drawer directly below the completed butterfly',stay=True);click('key_box','open');d.append('Observe the flat brass door key on its supported pad',18);click('key','take')
    approach('exit','Return to the exit');click('exit','use','key');click('exit','open')
    if not exit_test(d.pos,g):raise RuntimeError('Open-door success was not reached')

def cpu_check():
    from easy88_core import stage_actions
    g=Game();checks=[]
    def act(kind,key,**kw):return g.act(dict(action=kind,_hit364=key,_validated364=True,**kw))
    assert not act('open','s2_reward')['ok'];checks.append('block reward locked before solution')
    assert not act('take','s3_tool')['ok'];checks.append('no key through closed reward drawer')
    for i in [0,1]:
        for kind,key,extra in stage_actions(g,i):assert act(kind,key,**extra)['ok'],(kind,key)
    assert not act('open','s3_cover')['ok'];checks.append('solved block flag alone cannot open next cabinet')
    assert act('open','s2_reward')['ok'];assert act('take','s3_tool')['ok']
    assert not act('use','s3_cover',item='s2_tool')['ok'];checks.append('old key cannot open butterfly cover')
    assert act('use','s3_cover',item='s3_tool')['ok']
    for kind,key,extra in stage_actions(g,2):assert act(kind,key,**extra)['ok'],(kind,key)
    assert g.solved[2];checks.append('physical mirrored wing arrangement accepted')
    g.states[2]['assignment']={0:1,1:3,2:0,3:2};assert g._check(2);checks.append('equal leaf pieces interchangeable')
    assert act('open','key_box')['ok'];assert act('take','key')['ok'];assert act('use','exit',item='key')['ok'];assert act('open','exit')['ok'];checks.append('separate take use open door success')
    return dict(level='R13',scope='CPU state fixtures, not native images',passed=len(checks),checks=checks)

_aff_build_last(Scene)
