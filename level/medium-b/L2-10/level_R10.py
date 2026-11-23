from easy88_core import make_level

SPEC = {'id': 'R10',
 'title': 'R10 · Parcel Packing Room / 包裹打包间',
 'theme': 'parcel_packing',
 'size': [4.0, 6.0],
 'door': {'side': 'north', 'start': 0.65, 'width': 1.04},
 'start': [1.25, 4.75, 1.35],
 'start_yaw': 270,
 'floor': 'concrete',
 'decor': ['fixed tape rolls', 'cardboard tubes', 'empty shipping boxes', 'packing paper stack'],
 'design_notes': 'Two adjacent devices share the west packing wall; the sealed-band case is on the side '
                 'rack. Cargo letters are author tile identities, not standalone player-facing answer '
                 'labels. Whole image is reference.',
 'stages': [{'kind': 'sliding_puzzle',
             'name': 'cargo picture slider',
             'wall': 'west',
             'centre': [0.15, 4.4],
             'view': [1.25, 4.25],
             'grid': [2, 3],
             'initial': ['D', 'A', 'C', 'B', '', 'E'],
             'target': ['A', 'B', 'C', 'D', 'E', ''],
             'auto': True,
             'solution_moves': ['B', 'D', 'A', 'B', 'E'],
             'visual': {'type': 'cargo_puzzle', 'reference_complete': True, 'show_author_tile_ids': False},
             'clue': {'reference': 'complete cargo loading picture', 'blank_cell': 'bottom_right'},
             'clue_text': ''},
            {'kind': 'label_index',
             'name': 'parcel label cabinet',
             'wall': 'west',
             'centre': [0.15, 2.65],
             'view': [1.25, 2.75],
             'answer': '8198',
             'digits': 4,
             'visual': {'type': 'label_positions',
                        'labels': ['681452', '374615', '129583', '546738'],
                        'indices': [2, 5, 3, 6],
                        'read_order': 'left_to_right'},
             'clue': {'labels': ['681452', '374615', '129583', '546738'],
                      'indices': [2, 5, 3, 6],
                      'read_order': 'left_to_right'},
             'clue_text': '681452\n374615\n129583\n546738'},
            {'kind': 'sequence',
             'name': 'sealed shipping case',
             'wall': 'east',
             'centre': [3.85, 2.15],
             'view': [2.75, 2.25],
             'options': ['circle', 'triangle', 'square', 'star', 'leaf', 'cross'],
             'answer': [5, 4, 3],
             'length': 3,
             'auto': False,
             'setup': {'kind': 'pluck',
                       'item': 'opening_pick',
                       'item_name': 'opening pick',
                       'target_name': 'sealed band protection cover',
                       'consume': False,
                       'open_after_use': True},
             'visual': {'type': 'symbol_strip',
                        'symbols': ['cross', 'leaf', 'star'],
                        'read_order': 'left_to_right'},
             'clue': {'symbols': ['cross', 'leaf', 'star'], 'read_order': 'left_to_right'},
             'clue_text': ''}]}

SPEC['start']=[2.75,5.0,1.35];SPEC['start_yaw']=180
for stage in SPEC['stages']:stage['clue_text']=''
SPEC['stages'][1].update(kind='label_index',name='combined parcel weights',answer='568',digits=3,
 visual={'type':'parcel_weight_relations'},clue={'pairs':[['red','blue',11],['blue','green',14],['red','green',13]],'unit':'kg'},clue_text='')
SPEC['stages'][2].update(kind='binary_pattern',name='shipping case retaining clasp',initial=[0],target=[1],auto=False,
 setup={'kind':'pluck','item':'opening_pick','item_name':'opening pick','target_name':'retaining clasp notch','consume':False,'gate':False},
 visual={'type':'physical_retaining_clasp'},clue={'type':'visible_clasp_and_notch'},clue_text='')
for field in ['options','answer','length']:SPEC['stages'][2].pop(field,None)
Game,_OriginalScene,_OriginalStandard,exit_test,cpu_check=make_level(SPEC)
TITLE=SPEC['title'];LEVEL_ID=SPEC['id'];START=SPEC['start'];START_YAW=SPEC['start_yaw']
CAP=150;OBSERVATION_SIZE=(640,360);VISUAL_ONLY=False;READ_ENABLED=True;READ_FEEDBACK_TEXT=True
Game.LABELS.update({'s1_clue':'complete cargo picture','s1_reset':'slider reset button','s2_cover':'shipping label drawer',
 's2_clue':'three paired parcel weight slips','s2_lock':'opening tool drawer lock','s3_cover':'opening tool drawer',
 's3_tool':'opening pick','s3_setup':'shipping band protection cover','s3_clue':'marks under the shipping band cover',
 's3_confirm':'screen check icon','s3_reset':'screen clear icon','key_box':'shipping case lid','key':'brass door key'})
LABELS=Game.LABELS
_original_act=Game.act
Game.stage_accessible=lambda self,index:0<=index<3
Game.stage_exposed=lambda self,index:0<=index<3 and bool(self.states[index]['setup_ready'])
def _packing_act(self,a):
    key=a.get('_hit364');kind=a.get('action')
    if a.get('_validated364') and key=='s3_tool' and kind=='take' and not self.opened['s3_cover']:
        from action_feedback import failure_for
        return {'ok':False,'text':failure_for(kind)}
    if a.get('_validated364') and key=='s3_setup':
        from action_feedback import failure_for,NO_ITEM
        if kind!='use':return {'ok':False,'text':failure_for(kind)}
        item=self._resolve_item(a.get('item'))
        if item is None:return {'ok':False,'text':NO_ITEM}
        if item!='s3_tool':return {'ok':False,'text':failure_for(kind)}
        self.states[2]['selected']=[1];self.states[2]['setup_used']=True;self.states[2]['setup_open']=True;self.solved[2]=True
        return {'ok':True,'text':''}
    if a.get('_validated364') and kind=='press' and str(key).startswith('s3_'):
        from action_feedback import failure_for
        return {'ok':False,'text':failure_for(kind)}
    result=_original_act(self,a)
    if a.get('_validated364') and kind=='unlock' and key=='s2_lock':self.states[1]['entered_code']=str(a.get('code',''))
    return result
Game.act=_packing_act
import math,hashlib
import numpy as np
from PIL import Image,ImageDraw
from easy88_scene import EasyScene
from easy88_clues import draw_symbol
from font_utils import load_font

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
        self.views={};self.focus={};self.labels={};self.drawers={};self.tiles={};self.tile_nodes={};self.expanded=[];self.screen_signature=None;self.lock_value='000'
    def palette(self):
        super().palette()
        for name,c in [('packing_paint',(.28,.36,.33)),('cardboard',(.52,.36,.20)),('packing_paper',(.71,.64,.49)),('tape_beige',(.65,.49,.27)),('concrete_floor',(.43,.46,.44)),('packing_felt',(.14,.22,.23)),('pick_steel',(.63,.68,.69))]:self.mat(name,c,rough=.90 if name!='pick_steel' else .28,metal=.65 if name=='pick_steel' else 0.)
    def reg_at(self,key,node,label,view,focus=None):
        self.reg(key,node);self.views[key]=list(view);self.labels[key]=label
        if focus is not None:self.focus[key]=list(focus)
        return node
    def flat(self,name,parent,pos,w,h,im,horizontal=False):
        p=self.tex/(name+'.png');im.save(p)
        return self.plane(name,pos,w,h,(1,0,0),(0,1,0) if horizontal else (0,0,1),None,parent,material=self.image_mat('r10_'+name,p))
    def text(self,name,parent,pos,w,h,value,bg=(211,204,180),ink=(34,48,43),horizontal=False):
        im=Image.new('RGB',(1000,240),bg);d=ImageDraw.Draw(im);size=160
        while size>12 and d.textbbox((0,0),str(value),font=load_font(size))[2]>940:size-=8
        d.text((500,120),str(value),font=load_font(size),fill=ink,anchor='mm');return self.flat(name,parent,pos,w,h,im,horizontal)
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

    def cargo_picture(self):
        im=Image.new('RGB',(900,600),(199,208,192));d=ImageDraw.Draw(im)
        d.rectangle((0,355,899,599),fill=(151,137,105));d.line((0,356,899,356),fill=(83,98,87),width=11)
        for x in [0,335,690]:d.rectangle((x,25,x+18,355),fill=(102,116,103))
        d.rectangle((0,55,899,77),fill=(114,92,64));d.rectangle((46,219,308,532),fill=(165,117,67),outline=(73,62,43),width=10)
        d.rectangle((50,224,304,270),fill=(196,147,83));d.line((178,222,178,530),fill=(224,200,144),width=26)
        d.line((51,381,306,381),fill=(224,200,144),width=22);d.polygon([(70,498),(285,284),(285,321),(105,498)],fill=(113,82,49))
        d.line([(385,515),(385,159),(468,159)],fill=(44,78,76),width=20);d.line((442,167,515,492),fill=(44,78,76),width=18)
        d.line((374,478,550,478),fill=(44,78,76),width=22);d.ellipse((364,476,425,539),fill=(37,43,39));d.ellipse((474,476,535,539),fill=(37,43,39))
        d.rectangle((618,121,849,281),fill=(172,128,78),outline=(79,69,47),width=9);d.line((735,123,735,279),fill=(223,197,141),width=22)
        d.polygon([(663,181),(697,147),(729,181),(712,181),(712,241),(681,241),(681,181)],fill=(51,72,61))
        d.rectangle((600,300,899,599),fill=(39,52,52));return im
    def label_picture(self,number,index):
        pairs=[('RED','BLUE',11),('BLUE','GREEN',14),('RED','GREEN',13)]
        a,b,total=pairs[int(index)];col={'RED':(166,64,43),'BLUE':(55,101,145),'GREEN':(65,115,75)}
        im=Image.new('RGB',(960,480),(227,219,192));d=ImageDraw.Draw(im)
        for x,name in [(70,a),(350,b)]:
            d.rectangle((x,60,x+180,250),fill=col[name],outline=(55,65,49),width=7)
            d.text((x+90,296),name,font=load_font(45),fill=(31,47,41),anchor='mm')
        d.text((306,150),'+',font=load_font(75),fill=(31,47,41),anchor='mm')
        d.text((735,170),'= '+str(total),font=load_font(90),fill=(31,47,41),anchor='mm')
        d.text((735,280),'kg',font=load_font(55),fill=(31,47,41),anchor='mm')
        return im
    def tape(self,name,parent,pos):
        n=self.group(name,pos,parent);count=32;pts=[]
        for z in [-.023,.023]:
            for radius in [.085,.045]:
                for j in range(count):
                    a=j*2*math.pi/count;pts.append([radius*math.cos(a),radius*math.sin(a),z])
        faces=[]
        for j in range(count):
            k=(j+1)%count;faces.extend([[j,k,count+k,count+j],[2*count+j,3*count+j,3*count+k,2*count+k],[j,2*count+j,2*count+k,k],[count+j,count+k,3*count+k,3*count+j]])
        self.mesh('tape_ring',pts,faces,'tape_beige',n);return n
    def opening_pick(self,parent):
        n=self.group('steel_opening_pick',[0,.22,.038],parent)
        self.box('pick_flat_shaft',[0,.022,.005],[.023,.19,.006],'pick_steel',n,bevel=.002)
        self.box('pick_wood_grip',[0,-.052,.015],[.044,.095,.025],'darkwood',n,bevel=.009)
        self.mesh('pick_prying_tip',[[-.025,.103,.002],[.025,.103,.002],[.028,.133,.014],[-.013,.133,.014],[-.025,.103,.008],[.025,.103,.008],[.028,.133,.020],[-.013,.133,.020]],[[0,1,2,3],[4,7,6,5],[0,4,5,1],[1,5,6,2],[2,6,7,3],[3,7,4,0]],'pick_steel',n)
        self.cylinder('grip_rivet',[0,-.054,.029],.006,.004,'brass','z',n,n=20);return n
    def screen_file(self,buffer,overflow=False,solved=False):
        im=Image.new('RGB',(1200,600),(23,37,38));d=ImageDraw.Draw(im)
        d.rounded_rectangle((4,4,1196,596),radius=18,outline=(75,119,97) if solved else (76,98,92),width=6)
        for j in range(3):
            x=360+j*205;d.rounded_rectangle((x-75,20,x+75,142),radius=12,fill=(36,54,51),outline=(99,119,104),width=3)
            if j<len(buffer):draw_symbol(d,SPEC['stages'][2]['options'][buffer[j]],(x-43,40,x+43,123),fill=(225,221,192),outline=(225,221,192))
            else:d.line((x-25,88,x+25,88),fill=(104,125,112),width=6)
        d.arc((70,48,144,122),35,306,fill=(213,218,190),width=9);d.polygon([(142,46),(148,80),(115,61)],fill=(213,218,190))
        d.line([(1030,77),(1065,114),(1140,35)],fill=(215,222,190),width=12)
        for j,symbol in enumerate(SPEC['stages'][2]['options']):
            x=(j%3)*400+200;y=180+(j//3)*210+105;d.rounded_rectangle((x-175,y-87,x+175,y+87),radius=15,fill=(36,52,50),outline=(85,109,100),width=3)
            draw_symbol(d,symbol,(x-57,y-57,x+57,y+57),fill=(225,219,189),outline=(225,219,189))
        path=self.tex/('shipping_lcd_'+(''.join(map(str,buffer)) or 'empty')+('_over' if overflow else '')+('_ok' if solved else '')+'.png');im.save(path);return path
    def screen_piece(self,key,rect,target=True):
        x0,y0,x1,y1=rect;points=[]
        for x,y in [(x0,y1),(x1,y1),(x1,y0),(x0,y0)]:points.append([(x/1200-.5)*.72,-.23+(.5-y/600)*.34,.0215])
        uv=[(x0/1200,1-y1/600),(x1/1200,1-y1/600),(x1/1200,1-y0/600),(x0/1200,1-y0/600)]
        n=self.mesh(key+'_glass',points,[[0,1,2,3]],self.screen_mat,self.key_lid,uv=uv)
        if target:self.reg_at(key,n,LABELS.get(key,key.replace('_',' ')),[2.5,2.25],[3.61,2.15,.823])
        return n
    def build(self,g):
        self.room_shell('packing_room',size=(4,6),openings={'north':[(.62,1.72)]})
        self.box('solid_subfloor',[2,3,-.075],[4.14,6.14,.10],'darkwood',bevel=.001)
        self.box('matte_concrete_floor',[2,3,.006],[4,6,.012],'concrete_floor',bevel=.001)
        self.bench=self.group('long_packing_bench',[.42,3.50,0]);self.transform(self.bench,rpy=[0,0,90])
        self.box('long_wood_top',[0,0,.72],[3.80,.68,.08],'wood',self.bench)
        for x in [-1.75,1.75]:
            for y in [-.25,.25]:self.box('bench_leg',[x,y,.35],[.075,.075,.70],'iron',self.bench)
        self.box('bench_lower_shelf',[0,0,.27],[3.64,.56,.045],'wood',self.bench);self.add_obstacle(.06,1.60,.78,5.40)
        self.slider=self.group('cargo_slider_board',[.70,-.05,.785],self.bench)
        self.box('slider_bottom',[0,0,0],[.94,.63,.035],'darkwood',self.slider);self.box('slider_well',[0,0,.019],[.89,.58,.007],'packing_felt',self.slider)
        for x in [-.465,.465]:self.box('slider_side_rail',[x,0,.040],[.035,.65,.065],'wood',self.slider)
        for y in [-.305,.305]:self.box('slider_end_rail',[0,y,.040],[.91,.035,.065],'wood',self.slider)
        picture=self.cargo_picture()
        for j,value in enumerate(['A','B','C','D','E']):
            r,c=divmod(j,3);n=self.group('cargo_tile_'+value,parent=self.slider);self.box('tile_wood',[0,0,0],[.282,.268,.027],'packing_paper',n,bevel=.004)
            self.flat('cargo_print_'+value,n,[0,0,.014],.275,.262,picture.crop((c*300,r*300,(c+1)*300,(r+1)*300)),True);self.tile_nodes[value]=n
        self.reference=self.group('cargo_reference',[.08,4.20,1.31]);self.transform(self.reference,rpy=[0,0,90]);self.box('reference_wood_frame',[0,0,0],[.48,.025,.34],'wood',self.reference)
        self.flat('reference_picture',self.reference,[0,-.014,0],.445,.300,picture);self.reg_at('s1_clue',self.reference,'complete cargo picture',[1.25,4.25],[.08,4.20,1.26])
        self.reset=self.group('slider_reset',[1.25,-.20,.80],self.bench);self.cylinder('reset_button',[0,0,0],.036,.022,'iron','z',self.reset,n=24)
        reset=Image.new('RGB',(160,160),(212,205,177));dr=ImageDraw.Draw(reset);dr.arc((30,30,130,130),30,306,fill=(45,68,53),width=13);dr.polygon([(130,25),(137,70),(96,49)],fill=(45,68,53));self.flat('reset_ink',self.reset,[0,0,.013],.061,.061,reset,True);self.reg_at('s1_reset',self.reset,'slider reset button',[1.25,4.25],[.62,4.75,.82])
        self.red=self.cylinder('slider_red',[.17,4.72,.87],.015,.012,'red_led','x',n=24);self.green=self.cylinder('slider_green',[.17,4.72,.87],.015,.012,'green','x',n=24)
        self.labeldrawer,label_face=self.drawer('label_drawer',self.bench,(.70,-.35),.54,width=1.30,depth=.44)
        self.reg_at('s2_cover',label_face,'shipping label drawer',[1.75,4.25],[.78,4.20,.56])
        self.box('label_support_plinth',[0,.22,-.0305],[1.19,.36,.14],'wood',self.labeldrawer)
        self.labelsheet=self.group('fixed_shipping_labels',[0,.22,.0415],self.labeldrawer)
        for j in range(3):self.flat('shipping_label_'+str(j),self.labelsheet,[(j-1)*.39,0,0],.365,.185,self.label_picture('',j),True)
        self.reg_at('s2_clue',self.labelsheet,'three paired parcel weight slips',[1.75,4.25],[.97,4.20,.5815])
        self.tooldrawer,tool_face=self.drawer('opening_tool_drawer',self.bench,(-.65,-.35),.54,width=.98,depth=.44)
        self.reg_at('s3_cover',tool_face,'opening tool drawer',[1.75,2.75],[.78,2.85,.56])
        self.lock=self.group('tool_drawer_code_lock',[.26,-.044,0],tool_face);self.box('code_lock_body',[0,0,0],[.30,.036,.14],'iron',self.lock)
        self.lock_display=self.text('tool_lock_lcd',self.lock,[0,-.020,.015],.258,.083,'000',bg=(48,68,56),ink=(224,228,190));self.lock_shader=self.S.Shader(self.stage.GetPrimAtPath(str(self.mats['r10_tool_lock_lcd'].GetPath())+'/texture'))
        self.reg_at('s2_lock',self.lock,'opening tool drawer lock',[1.75,2.75],[.80,3.11,.54])
        self.text('weight_lock_order',tool_face,[-.21,-.026,.090],.39,.062,'RED BLUE GREEN')
        self.box('tool_support_plinth',[0,.22,-.0305],[.87,.36,.14],'packing_felt',self.tooldrawer);self.pick=self.opening_pick(self.tooldrawer)
        self.reg_at('s3_tool',self.pick,'opening pick',[1.75,2.75],[.97,2.85,.59])
        self.tape('fixed_tape_roll_a',self.bench,[-1.43,-.08,.805]);self.tape('fixed_tape_roll_b',self.bench,[-1.58,.10,.805])
        self.box('packing_paper_stack',[-.12,.03,.79],[.28,.42,.055],'packing_paper',self.bench,bevel=.004)
        for j in range(3):self.cylinder('cardboard_tube',[-1.35+j*.17,0,.33],.045,.45,'cardboard','y',self.bench,n=28)
        self.case=self.group('shipping_case_stand',[3.61,2.15,0]);self.transform(self.case,rpy=[0,0,-90])
        self.box('case_cabinet_body',[0,0,.30],[1.16,.58,.55],'wood',self.case);self.box('case_counter',[0,0,.61],[1.23,.65,.055],'wood',self.case)
        for x in [-.28,.28]:
            self.box('cabinet_door',[x,-.297,.30],[.54,.035,.48],'paint',self.case);self.box('cabinet_handle',[x+(.17 if x<0 else -.17),-.33,.33],[.025,.045,.13],'brass',self.case)
        self.add_obstacle(3.26,1.52,3.96,2.78)
        self.box('case_floor',[0,0,.655],[.86,.48,.026],'darkwood',self.case);self.box('case_felt',[0,0,.674],[.79,.41,.010],'packing_felt',self.case)
        for x in [-.42,.42]:self.box('case_side',[x,0,.727],[.025,.48,.13],'wood',self.case)
        for y in [-.235,.235]:self.box('case_front_back',[0,y,.727],[.84,.025,.13],'wood',self.case)
        self.key_lid=self.group('shipping_case_hinge',[0,.235,.800],self.case)
        self.box('shipping_lid',[0,-.235,0],[.90,.50,.026],'wood',self.key_lid)
        lidtarget=self.group('shipping_lid_rim',parent=self.key_lid)
        for x in [-.43,.43]:self.box('lid_side_rim',[x,-.235,.015],[.035,.49,.009],'wood',lidtarget)
        for y in [-.46,-.01]:self.box('lid_end_rim',[0,y,.015],[.84,.035,.009],'wood',lidtarget)
        self.box('lid_pull',[0,-.50,0],[.17,.03,.035],'brass',lidtarget);self.reg_at('key_box',lidtarget,'shipping case lid',[2.5,2.25],[3.58,2.15,.81])
        self.guard=self.group('retaining_clasp_hinge',[0,-.267,.655],self.case)
        self.box('retaining_clasp',[0,0,.068],[.16,.030,.15],'steel',self.guard)
        self.box('clasp_catch',[0,-.025,.135],[.18,.035,.030],'iron',self.guard)
        self.box('prying_notch',[0,-.025,.018],[.040,.014,.026],'iron',self.guard)
        self.reg_at('s3_setup',self.guard,'retaining clasp notch',[2.5,2.25],[3.32,2.15,.724])
        _add_outline(self,'pick_outline',self.case,[.24,-.249,.727],'pick',.24,.08)
        self.key=self.tool('flat_brass_key',self.case,[0,0,.690],'key');self.target_nodes.pop('flat_brass_key',None);self.transform(self.key,rpy=[90,0,0]);self.reg_at('key',self.key,'brass door key',[2.5,2.25],[3.61,2.15,.690])
        for j in range(2):
            x=.95+j*.67;box=self.group('sealed_stock_carton_'+str(j),[x,.37,.225]);self.box('carton_body',[0,0,0],[.54,.52,.42],'cardboard',box)
            self.box('carton_top_tape',[0,0,.212],[.10,.52,.008],'tape_beige',box);self.box('carton_front_tape',[0,-.263,0],[.10,.006,.42],'tape_beige',box)
        self.add_obstacle(.66,.08,1.92,.66)
        rack=self.group('packing_stock_wall_rack',[3.73,4.55,0]);self.transform(rack,rpy=[0,0,-90])
        for x in [-.62,.62]:self.box('stock_rack_stile',[x,0,.58],[.045,.39,1.16],'darkwood',rack)
        self.box('stock_rack_back',[0,.17,.58],[1.28,.025,1.14],'paint',rack)
        for z in [.12,.64,1.14]:self.box('stock_rack_shelf',[0,0,z],[1.33,.42,.035],'wood',rack)
        for j in range(3):
            x=(j-1)*.36;self.box('flat_carton_stock',[x,.015,.25],[.29,.30,.23],'cardboard',rack)
            self.box('stock_carton_tape',[x,.015,.368],[.05,.30,.008],'tape_beige',rack)
        for j in range(3):self.box('folded_packing_paper',[0,-.01,.68+j*.012],[.62,.30,.011],'packing_paper',rack)
        self.tape('spare_tape_roll',rack,[.48,-.015,.694])
        self.add_obstacle(3.49,3.84,3.99,5.27)
        self.cylinder('wall_kraft_roll',[.15,2.35,1.62],.085,.66,'packing_paper','y',n=36)
        self.box('kraft_hanging_sheet',[.065,2.35,1.39],[.012,.58,.34],'packing_paper')
        for y in [1.98,2.72]:
            self.box('paper_roll_wall_bracket',[.07,y,1.61],[.12,.035,.17],'iron')
        self.mat('window_pale',(.52,.63,.62),rough=.9,emission=(.12,.16,.15));self.box('window_glass',[3.925,4.35,1.72],[.022,.74,.70],'window_pale')
        for y in [3.95,4.75]:self.box('window_jamb',[3.90,y,1.72],[.06,.035,.77],'darkwood')
        for z in [1.34,1.72,2.10]:self.box('window_rail',[3.90,4.35,z],[.06,.83,.035],'darkwood')
        self.exit_node=self.door('packing_exit',[1.69,5.94,0],1.04);self.door_angle=180;self.reg_at('exit',self.exit_node,'exit door',[1.25,5.0],[1.17,5.94,1.12]);self.door_view=[1.25,5.0]
        for x in [.63,1.71]:self.box('door_frame',[x,5.95,1.14],[.065,.17,2.30],'paint')
        self.box('door_top_frame',[1.17,5.95,2.29],[1.15,.17,.065],'paint')
        for x in [.64,1.70]:self.box('door_stop_jamb',[x,5.99,1.14],[.035,.026,2.28],'darkwood')
        self.box('door_stop_top',[1.17,5.99,2.28],[1.13,.026,.035],'darkwood')
        self.stage_views=[[1.25,4.25],[1.75,4.25],[2.5,2.25]];self.stage_centres=[[.47,4.20,.815],[.97,4.20,.582],[3.61,2.15,.82]]
        self.bases=[([.42,4.2],90),([.42,2.85],90),([3.61,2.15],-90)]
        self.sync(g)
    def visible(self,key,g):
        if key=='s2_clue':return bool(g.opened['s2_cover'])
        if key=='s3_tool':return bool(g.opened['s3_cover']) and key not in g.taken
        if key=='s3_clue':return False
        if key=='key':return bool(g.opened['key_box']) and key not in g.taken
        return key in self.target_nodes
    def sync(self,g):
        grid=g.states[0]['grid']
        for key in [k for k in self.target_nodes if k.startswith('s1_tile_')]:self.target_nodes.pop(key)
        for value,n in self.tile_nodes.items():
            j=grid.index(value);r,c=divmod(j,3);self.transform(n,[(c-1)*.294,(.5-r)*.282,.036]);self.reg_at('s1_tile_'+str(j),n,'sliding cargo picture tile',[1.25,4.25],[.47,4.20,.815])
        self.visibility(self.red,not g.solved[0]);self.visibility(self.green,g.solved[0])
        for name,flag in [('label_drawer',g.opened['s2_cover']),('opening_tool_drawer',g.opened['s3_cover'])]:
            n,p=self.drawers[name];self.transform(n,[p[0],p[1]-(.42 if flag else 0),p[2]])
        self.visibility(self.pick,'s3_tool' not in g.taken)
        code=g.states[1].get('entered_code','000')
        if code!=self.lock_value:
            im=Image.new('RGB',(1000,240),(48,68,56));dr=ImageDraw.Draw(im);size=160
            while size>12 and dr.textbbox((0,0),code,font=load_font(size))[2]>940:size-=8
            dr.text((500,120),code,font=load_font(size),fill=(224,228,190),anchor='mm');p=self.tex/('tool_code_'+hashlib.sha256(code.encode()).hexdigest()[:12]+'.png');im.save(p)
            with self.og.sim.editing_usd():self.lock_shader.GetInput('file').Set(str(p))
            self.lock_value=code
        self.transform(self.guard,rpy=[110 if g.states[2]['setup_open'] else 0,0,0])
        self.transform(self.key_lid,rpy=[-105 if g.opened['key_box'] else 0,0,0]);self.visibility(self.key,'key' not in g.taken)
        self.transform(self.exit_node,rpy=[0,0,180-(103 if g.opened['exit'] else 0)])
        self.expanded=[]
        for name,flag in [('label_drawer',g.opened['s2_cover']),('opening_tool_drawer',g.opened['s3_cover'])]:
            if flag:
                points=self.triangles(self.drawers[name][0]).reshape(-1,3);self.expanded.append((points.min(0)[:2]-.12,points.max(0)[:2]+.12))
        if g.states[2]['setup_open']:
            points=self.triangles(self.guard).reshape(-1,3);self.expanded.append((points.min(0)[:2]-.12,points.max(0)[:2]+.12))
        self.centres={}
        for key,n in self.target_nodes.items():
            points=self.triangles(n).reshape(-1,3)
            if points.size:self.centres[key]=((points.min(0)+points.max(0))/2).tolist()
    def candidates(self,g):return self.base_candidates([k for k in self.target_nodes if self.visible(k,g)])
    def blocked(self,x,y,g):return super().blocked(x,y,g) or any(lo[0]<x<hi[0] and lo[1]<y<hi[1] for lo,hi in self.expanded)
    def view_for(self,key):return self.views.get(key,[2.75,5.0])
    def focus_for(self,key):return self.focus.get(key,self.centres.get(key))
    def label_for(self,key):return self.labels.get(key,LABELS.get(key,key.replace('_',' ')))
    def animate(self,d,before):
        previous=before['states'][0]['grid'];now=d.game.states[0]['grid']
        for value,n in self.tile_nodes.items():
            a=previous.index(value);b=now.index(value)
            if a!=b:
                for t in [.33,.67]:
                    self.sync(d.game);r=a//3+(b//3-a//3)*t;c=a%3+(b%3-a%3)*t;self.transform(n,[(c-1)*.294,(.5-r)*.282,.036]);d.frame(warm=4);d.append('Picture tile slides into the empty slot',4)
        old=before.get('opened',{})
        for key,name in [('s2_cover','label_drawer'),('s3_cover','opening_tool_drawer')]:
            if bool(old.get(key))!=bool(d.game.opened[key]):
                n,p=self.drawers[name]
                for t in [.33,.67]:
                    q=float(bool(old.get(key)))+(float(bool(d.game.opened[key]))-float(bool(old.get(key))))*t;self.sync(d.game);self.transform(n,[p[0],p[1]-.42*q,p[2]]);d.frame(warm=4);d.append('Drawer opening',4)
        was=before['states'][2].get('setup_open',False);isopen=d.game.states[2]['setup_open']
        if was!=isopen:
            for t in [.33,.67]:
                q=float(bool(was))+(float(bool(isopen))-float(bool(was)))*t;self.sync(d.game);self.transform(self.guard,rpy=[110*q,0,0]);d.frame(warm=4);d.append('The retaining clasp releases; the case lid remains shut',4)
        if bool(old.get('key_box'))!=bool(d.game.opened['key_box']):
            for t in [.33,.67]:
                q=float(bool(old.get('key_box')))+(float(bool(d.game.opened['key_box']))-float(bool(old.get('key_box'))))*t;self.sync(d.game);self.transform(self.key_lid,rpy=[-105*q,0,0]);d.frame(warm=4);d.append('Case opening',4)
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

    observe('s1_clue','Observe the complete cargo loading picture')
    approach('s1_tile_0','Look down at the actual sliding picture')
    for value in ['B','D','A','B','E']:
        index=g.states[0]['grid'].index(value);click('s1_tile_'+str(index))
    if not g.solved[0]:raise RuntimeError('The five legal picture slides did not solve the cargo image')
    approach('s2_cover','Step back to the unlocked label drawer');click('s2_cover','open')
    observe('s2_clue','Compare the three combined parcel weights; infer each parcel weight',stay=True)
    approach('s2_lock','Walk along the same packing bench to the tool drawer');click('s2_lock','unlock',code='568')
    click('s3_cover','open');d.append('Observe the steel opening pick in its shallow drawer',18);click('s3_tool','take')
    approach('s3_setup','Use the narrow pry tip on the retaining clasp');click('s3_setup','use','s3_tool')
    d.append('The clasp is released; open the same case to reach its contents',18)
    click('key_box','open');d.append('Observe the flat brass key in the shallow case',18);click('key','take')
    approach('exit','Return to the exit door');click('exit','use','key');click('exit','open')
    if not exit_test(d.pos,g):raise RuntimeError('Open-door success was not reached')

def cpu_check():
    from easy88_core import stage_actions
    g=Game();checks=[]
    def act(kind,key,**kw):return g.act(dict(action=kind,_hit364=key,_validated364=True,**kw))
    assert not act('open','key_box')['ok'];checks.append('clasp blocks the case lid')
    assert not act('use','s3_setup',item='missing')['ok'];checks.append('no held tool rejected')
    for i in (0,1):
        for kind,key,extra in stage_actions(g,i):assert act(kind,key,**extra)['ok'],(i,kind,key)
    assert not act('take','s3_tool')['ok'];checks.append('closed tool drawer blocks take')
    assert act('open','s3_cover')['ok'];assert act('take','s3_tool')['ok']
    assert not act('press','s3_control_0')['ok'];checks.append('no hidden button solution')
    assert act('use','s3_setup',item='s3_tool')['ok'];assert g.solved[2] and not g.opened['key_box'];checks.append('pry releases only the clasp')
    assert act('open','key_box')['ok'];assert act('take','key')['ok'];assert act('use','exit',item='key')['ok'];assert act('open','exit')['ok'];checks.append('ordinary key/use/open wins')
    solutions=[(r,b,g) for r in range(1,15) for b in range(1,15) for g in range(1,15) if r+b==11 and b+g==14 and r+g==13]
    assert solutions==[(5,6,8)];checks.append('one parcel-weight solution: 5 6 8')
    return dict(level='R10',scope='CPU state fixtures; not native images',passed=len(checks),checks=checks)

_aff_build_last(Scene)
