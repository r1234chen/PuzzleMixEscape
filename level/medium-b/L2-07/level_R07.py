from easy88_core import make_level

SPEC = {'id': 'R07',
 'title': 'R07 · Art Studio / 画室',
 'theme': 'art_studio',
 'size': [5.5, 5.5],
 'layout': 'shallow_l',
 'cutout': {'corner': 'southeast', 'size': [1.5, 1.5]},
 'door': {'side': 'west', 'start': 0.65, 'width': 1.04},
 'start': [1.25, 1.25, 1.35],
 'start_yaw': 90,
 'floor': 'wood',
 'decor': ['fixed paint jars', 'rolled canvas', 'brush pot', 'small empty frames'],
 'design_notes': 'Three serial gates: physical easel support alignment, two textured colour windows, then '
                 'four kite heights. No painter identification or art-history knowledge.',
 'stages': [{'kind': 'support_align',
             'name': 'easel support adjusters',
             'wall': 'north',
             'initial': [0, 0],
             'target': [2, 0],
             'moduli': [4, 4],
             'auto': True,
             'visual': {'type': 'frame_align',
                        'bases': [0.45, 0.55],
                        'line': 0.6,
                        'step': 0.05,
                        'reference': 'a fixed horizontal paint mark on the easel'},
             'clue': {'support_bases': [0.45, 0.55], 'reference_height': 0.6, 'stop_count_each': 4},
             'clue_text': ''},
            {'kind': 'colour_windows',
             'name': 'colour sample windows',
             'wall': 'east',
             'initial': [0, 0],
             'target': [3, 4],
             'moduli': [6, 6],
             'options': ['red_circle',
                         'blue_stripe',
                         'yellow_dot',
                         'green_grid',
                         'purple_stripe',
                         'white_wave'],
             'auto': False,
             'setup': {'kind': 'key',
                       'item': 'colour_cover_key',
                       'item_name': 'small colour-cover key',
                       'target_name': 'locked colour control cover',
                       'consume': False},
             'visual': {'type': 'colour_windows',
                        'reference': ['green_grid', 'purple_stripe'],
                        'options': ['red_circle',
                                    'blue_stripe',
                                    'yellow_dot',
                                    'green_grid',
                                    'purple_stripe',
                                    'white_wave']},
             'clue': {'left_sample': 'green_grid', 'right_sample': 'purple_stripe'},
             'clue_text': ''},
            {'kind': 'sequence',
             'name': 'kite picture lock',
             'wall': 'west',
             'options': ['circle', 'star', 'leaf', 'triangle'],
             'answer': [0, 1, 2, 3],
             'length': 4,
             'distinct': True,
             'auto': False,
             'visual': {'type': 'kite_heights',
                        'symbols': ['leaf', 'circle', 'triangle', 'star'],
                        'heights': [3, 1, 4, 2],
                        'order': 'low_to_high'},
             'clue': {'order': 'lowest to highest',
                      'kites': [{'symbol': 'leaf', 'height': 3},
                                {'symbol': 'circle', 'height': 1},
                                {'symbol': 'triangle', 'height': 4},
                                {'symbol': 'star', 'height': 2}]},
             'clue_text': ''}]}

SPEC['theme']='painting'
SPEC['start']=[2.5,2.25,1.35]
SPEC['stages'][0].update(centre=[1.65,5.08],view=[1.75,4.0])
SPEC['stages'][1].update(centre=[3.95,5.08],view=[3.75,4.0])
SPEC['stages'][2].update(centre=[5.08,3.0],view=[4.0,3.0],wall='east')
for _stage in SPEC['stages']:_stage.setdefault('graphic',_stage.get('visual',{}))
Game,_GenericScene,standard,exit_test,cpu_check=make_level(SPEC)
TITLE=SPEC['title'];LEVEL_ID=SPEC['id'];LABELS=Game.LABELS
START=SPEC['start'];START_YAW=90;CAP=150;OBSERVATION_SIZE=(640,360)
VISUAL_ONLY=False;READ_ENABLED=True;READ_FEEDBACK_TEXT=True
LABELS.update({'s2_tool':'small paint-box key','s2_reward':'paint-sample tool drawer','s3_tool':'palette knife','s3_cover':'taped art cupboard door'})
_base_studio_init=Game.__init__;_base_studio_act=Game.act;_base_studio_cover=Game.cover_unlocked
def _studio_init(self):
    _base_studio_init(self);self.states[1]['tool_drawer_open']=False;self.states[2]['seal_cut']=False
Game.__init__=_studio_init
def _studio_cover(self,index):return self.states[2]['seal_cut'] if index==2 else _base_studio_cover(self,index)
Game.cover_unlocked=_studio_cover
def _studio_handoff(self,a):
    key=a.get('_hit364');kind=a.get('action')
    if a.get('_validated364'):
        from action_feedback import failure_for,NO_ITEM
        if key=='s2_reward':
            if kind not in ('open','close') or kind=='open' and not self.solved[1]:return {'ok':False,'text':failure_for(kind)}
            self.states[1]['tool_drawer_open']=kind=='open';return {'ok':True,'text':''}
        if key=='s3_tool':
            if kind!='take' or not self.states[1]['tool_drawer_open'] or key in self.taken:return {'ok':False,'text':failure_for(kind)}
            self.taken.add(key);self.holding.append(key);return {'ok':True,'text':''}
        if key=='s3_cover' and kind=='use':
            item=self._resolve_item(a.get('item'))
            if item is None:return {'ok':False,'text':NO_ITEM}
            if item!='s3_tool':return {'ok':False,'text':failure_for(kind)}
            self.states[2]['seal_cut']=True;return {'ok':True,'text':''}
    return _base_studio_act(self,a)
Game.act=_studio_handoff


import math,json
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
        self.views={};self.labels={};self.slider_nodes=[];self.colour_nodes=[];self.lamps=[]
    def palette(self):
        super().palette()
        for k,c in [('studio_green',(.26,.35,.31)),('canvas',(.76,.73,.64)),('ochre',(.57,.36,.11)),('paint_blue',(.10,.24,.37)),('paint_red',(.46,.16,.12))]:self.mat(k,c,rough=.94)
    def reg_at(self,key,node,view,label):
        self.reg(key,node);self.views[key]=view;self.labels[key]=label
        return node
    def image(self,key,parent,pos,w,h,im,right=(1,0,0),up=(0,0,1)):
        p=self.tex/(key+'.png');im.save(p)
        return self.plane(key,pos,w,h,right,up,None,parent,material=self.image_mat('print_'+key,p))
    def symbol(self,name,size=200):
        im=Image.new('RGB',(size,size),(219,210,184));d=ImageDraw.Draw(im)
        if name=='confirm':d.line([(42,104),(84,145),(157,51)],fill=(38,63,53),width=14)
        elif name=='reset':
            d.arc((39,38,161,161),35,303,fill=(38,63,53),width=13);d.polygon([(159,37),(166,84),(121,61)],fill=(38,63,53))
        else:draw_symbol(d,name,(32,32,size-32,size-32),fill=(40,65,57),outline=(40,65,57))
        return im
    def touch(self,key,parent,pos,name,view,size=.105):
        n=self.group(key,pos,parent);self.box('wood_button',[0,0,0],[size,.032,size],'darkwood',n)
        self.image(key+'_glyph',n,[0,-.017,0],size*.91,size*.91,self.symbol(name))
        self.reg_at(key,n,view,name+' button');return n
    def drawer(self,key,parent,pos,width=.52,depth=.34):
        n=self.group(key,pos,parent)
        self.box('drawer_bottom',[0,0,0],[width,depth,.025],'wood',n)
        for xx in [-width/2,width/2]:self.box('drawer_side',[xx,0,.07],[.025,depth,.15],'wood',n)
        for yy in [-depth/2,depth/2]:self.box('drawer_face',[0,yy,.07],[width,.025,.15],'wood',n)
        self.box('drawer_handle',[0,-depth/2-.035,.07],[.18,.045,.025],'brass',n)
        return n
    def framed(self,key,parent,pos,w,h,im):
        g=self.group(key,pos,parent)
        for x in [-w/2,w/2]:self.box('frame_side',[x,0,0],[.025,.035,h+.035],'darkwood',g)
        for z in [-h/2,h/2]:self.box('frame_rail',[0,0,z],[w+.035,.035,.025],'darkwood',g)
        self.box('canvas_back',[0,.008,0],[w,.014,h],'canvas',g)
        self.image(key+'_picture',g,[0,-.011,0],w-.012,h-.012,im)
        return g
    def landscape(self):
        im=Image.new('RGB',(700,490),(176,191,179));d=ImageDraw.Draw(im)
        d.ellipse((485,45,565,125),fill=(228,207,145))
        d.polygon([(0,310),(185,135),(338,300),(485,195),(700,320),(700,490),(0,490)],fill=(90,125,116))
        d.polygon([(0,380),(220,275),(490,340),(700,245),(700,490),(0,490)],fill=(68,100,83))
        d.line([(0,443),(160,410),(285,438),(470,394),(700,431)],fill=(171,164,120),width=17)
        return im
    def swatch(self,name):
        colours={'red_circle':(156,65,51),'blue_stripe':(45,95,132),'yellow_dot':(205,169,68),'green_grid':(68,124,78),'purple_stripe':(121,77,139),'white_wave':(218,213,191)}
        im=Image.new('RGB',(300,300),colours[name]);d=ImageDraw.Draw(im);ink=(226,220,189)
        if name.endswith('grid'):
            for x in range(15,300,42):d.line((x,0,x,300),fill=ink,width=5);d.line((0,x,300,x),fill=ink,width=5)
        elif name.endswith('stripe'):
            for x in range(-300,600,55):d.line((x,0,x-300,300),fill=ink,width=10)
        elif name.endswith('dot'):
            for x in range(35,300,70):
                for y in range(35,300,70):d.ellipse((x-8,y-8,x+8,y+8),fill=ink)
        elif name.endswith('circle'):d.ellipse((58,58,242,242),outline=ink,width=14)
        else:
            for y in [70,150,230]:d.line([(x,y+int(15*math.sin(x/23))) for x in range(300)],fill=(110,120,111),width=8)
        return im
    def build(self,g):
        self.room_shell('art_studio',size=(5.5,5.5),openings={'west':[(.62,1.72)]})
        self.box('continuous_subfloor',[2.75,2.75,-.074],[5.64,5.64,.10],'darkwood',bevel=.001)
        self.box('L_inner_x',[4.,.75,1.4],[.12,1.5,2.8],'plaster');self.box('L_inner_y',[4.75,1.5,1.4],[1.5,.12,2.8],'plaster')
        self.box('L_lower_x',[3.99,.75,.51],[.14,1.5,1.02],'studio_green');self.box('L_lower_y',[4.75,1.49,.51],[1.5,.14,1.02],'studio_green')
        self.add_obstacle(3.94,-.06,5.56,1.56)
        self.build_door()
        e=self.group('wooden_easel',[1.65,5.05,0])
        for x in [-.48,.48]:
            self.box('easel_upright',[x,.035,1.02],[.07,.08,2.04],'wood',e)
            self.box('easel_floor_foot',[x,-.14,.055],[.11,.59,.09],'darkwood',e)
        for z in [.35,.84,1.95]:self.box('easel_crossbar',[0,.06,z],[1.03,.07,.065],'wood',e)
        self.box('reference_rail',[0,-.058,1.12],[1.04,.045,.022],'red',e)
        for j,x in enumerate([-.35,.35]):
            self.box('fixed_jack_sleeve',[x,-.10,.81],[.075,.075,.40],'iron',e)
            n=self.group('moving_support_'+str(j),parent=e)
            self.cylinder('jack_steel_rod',[0,0,-.15],.021,.30,'steel','z',n)
            self.box('canvas_support_shoe',[0,-.025,0],[.16,.13,.035],'wood',n)
            self.slider_nodes.append(n)
            self.touch('s1_control_'+str(j),e,[x,-.155,.72],'up',[1.75,4.0],.11)
        self.frame=self.framed('working_landscape',e,[0,-.125,1.41],.78,.55,self.landscape())
        self.box('drawer_housing_top',[0,-.13,.64],[.69,.43,.04],'wood',e)
        for x in [-.345,.345]:self.box('drawer_housing_side',[x,-.13,.52],[.04,.43,.24],'wood',e)
        self.box('drawer_housing_base',[0,-.13,.40],[.69,.43,.04],'wood',e)
        self.easel_drawer=self.drawer('easel_key_drawer',e,[0,-.13,.425],.61,.36)
        self.reg_at('s2_cover',self.easel_drawer,[1.75,4.0],'easel drawer')
        self.cover_key=self.tool('s2_tool',self.easel_drawer,[0,-.02,.052],'key');self.transform(self.cover_key,rpy=[90,0,0])
        self.reg_at('s2_tool',self.cover_key,[1.75,4.0],'small paint-box key')
        self.lamps=[self.cylinder('easel_red',[.44,-.10,.91],.018,.018,'red_led','y',e),self.cylinder('easel_green',[.44,-.10,.91],.018,.018,'green','y',e)]
        self.table('colour_worktable',(3.95,5.05),(1.75,.67),height=.72)
        c=self.group('paint_sample_box',[3.95,5.03,.775])
        self.box('colour_box_base',[0,0,0],[.93,.44,.045],'wood',c)
        for x in [-.465,.465]:self.box('box_side',[x,0,.065],[.035,.44,.13],'wood',c)
        for y in [-.21,.21]:self.box('box_end',[0,y,.065],[.93,.035,.13],'wood',c)
        self.colour_lid=self.group('s2_setup',[0,.21,.15],c)
        self.box('paint_box_lid',[0,-.22,0],[.97,.46,.035],'wood',self.colour_lid)
        self.box('lid_lock',[0,-.446,-.035],[.12,.026,.08],'brass',self.colour_lid)
        self.reg_at('s2_setup',self.colour_lid,[3.75,4.0],'paint sample box lid')
        self.colour_face=self.group('colour_face',[0,-.05,.075],c);self.transform(self.colour_face,rpy=[-90,0,0])
        self.box('face_board',[0,0,0],[.83,.035,.25],'studio_green',self.colour_face)
        for j in range(2):
            n=self.group('colour_rotor_'+str(j),[(-.21 if j==0 else .21),-.03,0],self.colour_face)
            self.cylinder('colour_disc',[0,0,0],.095,.035,'darkwood','y',n,n=36)
            faces=[]
            for name in self.spec['stages'][1]['options']:
                f=self.group('swatch_'+name,parent=n);self.image('colour_'+str(j)+'_'+name,f,[0,-.020,0],.163,.163,self.swatch(name));faces.append(f)
            self.colour_nodes.append(faces);self.reg_at('s2_control_'+str(j),n,[3.75,4.0],'colour sample disc')
            _add_mark(self,'disc_turn_mark_'+str(j),self.colour_face,[(-.085 if j==0 else .085),-.0185,0],'turn',.035)
        self.touch('s2_confirm',self.colour_face,[.34,-.03,.04],'confirm',[3.75,4.0],.075)
        self.touch('s2_reset',self.colour_face,[-.34,-.03,.04],'reset',[3.75,4.0],.075)
        ref=Image.new('RGB',(700,260),(215,207,185));ref.paste(self.swatch('green_grid').resize((220,220)),(90,20));ref.paste(self.swatch('purple_stripe').resize((220,220)),(390,20))
        rn=self.framed('paint_sample_reference',None,[3.95,5.32,1.67],.60,.225,ref);self.reg_at('s2_clue',rn,[3.75,4.0],'two paint samples')
        for j,mat in enumerate(['paint_red','ochre','paint_blue']):
            n=self.group('fixed_paint_jar_'+str(j),[3.25,4.85+j*.20,.77])
            self.cylinder('paint_jar',[0,0,.035],.048,.09,mat,'z',n);self.cylinder('jar_cap',[0,0,.085],.05,.014,'steel','z',n)
        for x in [3.60,4.30]:self.box('knife_drawer_housing_side',[x,4.93,.545],[.035,.48,.22],'wood')
        self.box('knife_drawer_housing_back',[3.95,5.1775,.545],[.73,.025,.22],'wood');self.box('knife_drawer_housing_top',[3.95,4.93,.65],[.73,.48,.035],'wood');self.box('knife_drawer_housing_bottom',[3.95,4.93,.4225],[.73,.48,.025],'wood')
        self.knife_drawer=self.drawer('sample_palette_knife_drawer',None,[3.95,4.93,.45],.63,.42)
        self.reg_at('s2_reward',self.knife_drawer,[3.75,4.0],'paint-sample tool drawer')
        self.knife=self.group('palette_knife',[0,0,.015],self.knife_drawer)
        self.box('knife_wood_handle',[-.09,0,.007],[.15,.040,.018],'darkwood',self.knife,bevel=.007);self.box('knife_neck',[.010,0,.007],[.065,.015,.008],'steel',self.knife)
        pts=[[-.01,-.023,.003],[.13,-.037,.003],[.20,0,.003],[.13,.037,.003],[-.01,.023,.003],[-.01,-.023,.011],[.13,-.037,.011],[.20,0,.011],[.13,.037,.011],[-.01,.023,.011]]
        self.mesh('palette_knife_steel_blade',pts,[[0,4,3,2,1],[5,6,7,8,9],[0,1,6,5],[1,2,7,6],[2,3,8,7],[3,4,9,8],[4,0,5,9]],'steel',self.knife)
        self.reg_at('s3_tool',self.knife,[3.75,4.0],'palette knife')
        self.reward_red=self.cylinder('sample_drawer_red',[.25,-.2265,.075],.014,.008,'red_led','y',self.knife_drawer,n=24);self.reward_green=self.cylinder('sample_drawer_green',[.25,-.2265,.075],.014,.008,'green','y',self.knife_drawer,n=24)

        k=self.group('art_storage_cupboard',[5.12,3.15,0]);self.transform(k,rpy=[0,0,-90])
        for x in [-.69,.69]:self.box('cabinet_side',[x,0,.76],[.045,.52,1.35],'wood',k)
        self.box('cabinet_back',[0,.24,.76],[1.38,.035,1.35],'studio_green',k)
        for z in [.10,.62,1.42]:self.box('cabinet_shelf',[0,0,z],[1.42,.54,.045],'wood',k)
        self.cabinet_door=self.group('s3_cover',[-.71,-.29,.08],k)
        self.box('cupboard_door',[.71,0,.68],[1.42,.045,1.36],'studio_green',self.cabinet_door)
        self.box('cupboard_handle',[1.32,-.04,.71],[.025,.05,.17],'brass',self.cabinet_door)
        self.reg_at('s3_cover',self.cabinet_door,[4.0,3.25],'taped art cupboard door')
        self.seal_tape=self.group('cupboard_paper_seal',[1.32,-.068,.71],self.cabinet_door)
        self.box('tape_across_handle',[0,0,0],[.16,.014,.29],'canvas',self.seal_tape)
        for z in [-.10,.10]:self.box('tape_torn_edge',[0,-.008,z],[.14,.003,.015],'ochre',self.seal_tape)
        self.cut_seal_ends=self.group('cut_tape_ends',[1.32,-.068,.71],self.cabinet_door)
        for z in [-.108,.108]:self.box('remaining_tape_end',[0,0,z],[.16,.014,.075],'canvas',self.cut_seal_ends)

        kite=Image.new('RGB',(900,560),(205,216,202));d=ImageDraw.Draw(kite)
        d.polygon([(0,530),(0,440),(210,410),(470,450),(690,405),(900,445),(900,560),(0,560)],fill=(118,145,116))
        for j,(name,y) in enumerate([('leaf',215),('circle',355),('triangle',120),('star',285)]):
            x=130+j*210;d.line((x,y+53,x-14,500),fill=(98,97,73),width=3)
            d.polygon([(x,y-54),(x+47,y),(x,y+54),(x-47,y)],fill=[(149,118,66),(96,132,137),(177,130,97),(115,125,103)][j],outline=(56,75,67),width=4)
            draw_symbol(d,name,(x-22,y-22,x+22,y+22),fill=(239,226,188),outline=(239,226,188))
        self.kite_picture=self.framed('stored_kite_painting',k,[0,.20,1.035],1.20,.70,kite)
        self.reg_at('s3_clue',self.kite_picture,[4.0,3.25],'kite painting')
        arrow=Image.new('RGB',(120,300),(216,209,185));ad=ImageDraw.Draw(arrow);ad.line((60,255,60,50),fill=(48,70,60),width=14);ad.polygon([(60,25),(27,75),(93,75)],fill=(48,70,60))
        self.image('height_order',k,[.61,-.02,1.04],.075,.25,arrow)
        panel=self.group('kite_touch_panel',[0,-.02,.670],k);self.transform(panel,rpy=[-90,0,0]);self.box('panel_back',[0,0,0],[1.20,.055,.40],'dark_panel',panel)
        for j,name in enumerate(self.spec['stages'][2]['options']):self.touch('s3_choice_'+str(j),panel,[(j-1.5)*.22,-.044,-.10],name,[4.0,3.25],.13)
        self.touch('s3_confirm',panel,[.52,-.044,-.10],'confirm',[4.0,3.25],.10)
        self.touch('s3_reset',panel,[-.52,-.044,-.10],'reset',[4.0,3.25],.10)
        self.input_slots=[]
        for j in range(4):
            n=self.group('input_slot_'+str(j),[(j-1.5)*.15,-.035,.10],panel);self.box('input_dark',[0,0,0],[.13,.015,.10],'dark_panel',n)
            faces=[]
            for name in self.spec['stages'][2]['options']:
                f=self.group('input_'+name,parent=n);self.image('input_'+str(j)+name,f,[0,-.009,0],.095,.09,self.symbol(name));faces.append(f)
            self.input_slots.append(faces)
        self.final_drawer=self.drawer('key_drawer',k,[0,0,.15],1.24,.42)
        self.reg_at('key_box',self.final_drawer,[4.0,3.25],'bottom art cupboard drawer')
        self.key=self.tool('key',self.final_drawer,[0,-.01,.050],'key');self.transform(self.key,rpy=[90,0,0]);self.reg_at('key',self.key,[4.0,3.25],'brass door key')
        rack=self.group('canvas_storage_rack',[.30,3.70,0]);self.transform(rack,rpy=[0,0,90])
        for x in [-.73,.73]:self.box('rack_upright',[x,0,.77],[.055,.45,1.54],'darkwood',rack)
        for z in [.12,.80,1.48]:self.box('rack_board',[0,0,z],[1.53,.45,.045],'wood',rack)
        self.box('rack_back',[0,.20,.78],[1.47,.035,1.40],'studio_green',rack);self.add_obstacle(.08,2.94,.56,4.46)
        for j in range(4):
            f=self.group('stored_canvas_'+str(j),[-.50+j*.25,0,.41],rack)
            self.box('canvas_frame',[0,0,0],[.075,.30,.53],'wood',f);self.box('canvas_side',[.040,0,0],[.012,.28,.50],'canvas',f)
        for j,mat in enumerate(['paint_blue','paint_red','ochre']):
            self.cylinder('rolled_canvas',[.30,3.18+j*.30,1.00],.065,.31,'canvas','z')
        self.table('painting_preparation_table',(2.55,.43),(1.80,.64),height=.72)
        pp=self.group('palette',[2.40,.40,.773]);self.cylinder('wooden_palette',[0,0,0],.19,.018,'wood','z',pp,n=40)
        for j,mat in enumerate(['paint_red','ochre','paint_blue','leaf_green']):self.cylinder('palette_paint',[.11*math.cos(j*1.5),.11*math.sin(j*1.5),.013],.027,.005,mat,'z',pp)
        pot=self.group('brush_pot',[3.12,.46,.82]);self.cylinder('pot',[0,0,0],.055,.13,'cream','z',pot)
        for j in range(5):
            x=(j-2)*.016;self.tube('brush_handle',[x,0,.015],[x+.025,0,.25],.004,'wood',pot);self.tube('brush_tip',[x+.025,0,.25],[x+.029,0,.29],.011,'bristle',pot)
        self.mat('pale_window',(.53,.64,.63),rough=.9,emission=(.17,.22,.21))
        self.box('window_pane',[.077,4.86,1.93],[.018,.62,.58],'pale_window')
        for y in [4.52,5.20]:self.box('window_frame',[.10,y,1.93],[.06,.04,.66],'darkwood')
        for z in [1.61,1.93,2.25]:self.box('window_cross',[.10,4.86,z],[.06,.72,.035],'darkwood')
        self.add_obstacle(4.83,2.41,5.43,3.89)
        self.add_obstacle(1.10,4.69,2.20,5.42)
        self.bases=[([1.65,5.05],0),([3.95,5.03],0),([5.12,3.15],-90)]
        self.stage_views=[[1.75,4.0],[3.75,4.0],[4.0,3.25]]
        self.stage_centres=[[1.65,5.0,1.12],[3.95,4.95,.95],[5.12,3.15,1.0]]
        self.sync(g)
        (self.run/'ROOM_GEOMETRY.json').write_text(json.dumps({'id':'R07','camera_height':1.35,'size':[5.5,5.5],'style_reference':'approved R03 material primitives','furniture':['wooden easel with supported drawer','low paint worktable','art storage cupboard','canvas rack','palette workbench'],'stage_views':self.stage_views,'input_size':[640,360]},ensure_ascii=False,indent=2),encoding='utf-8')
    def visible(self,key,g):
        if key=='s2_cover':return True
        if key=='s2_tool':return bool(g.opened['s2_cover']) and key not in g.taken
        if key=='s2_setup':return True
        if key.startswith('s2_') and key!='s2_clue':return bool(g.states[1]['setup_open'])
        if key=='s2_reward':return True
        if key=='s3_tool':return bool(g.states[1]['tool_drawer_open']) and key not in g.taken
        if key=='s3_cover':return True
        if key.startswith('s3_') or key in ('key','key_box'):
            if not g.opened['s3_cover']:return False
            return key!='key' or bool(g.opened['key_box']) and key not in g.taken
        return key in self.target_nodes
    def sync(self,g):
        a=g.states[0]['angles'];heights=[.97+.05*(a[0]+1),1.07+.05*(a[1]+1)]
        for j,n in enumerate(self.slider_nodes):self.transform(n,[(-.35 if j==0 else .35),-.11,heights[j]])
        self.transform(self.frame,[0,-.125,(sum(heights)/2)+.275],[0,-math.degrees(math.atan2(heights[1]-heights[0],.70)),0])
        self.visibility(self.lamps[0],not g.solved[0]);self.visibility(self.lamps[1],g.solved[0])
        self.transform(self.easel_drawer,[0,-.53 if g.opened['s2_cover'] else -.13,.425])
        self.visibility(self.cover_key,self.visible('s2_tool',g))
        self.transform(self.colour_lid,rpy=[-105 if g.states[1]['setup_open'] else 0,0,0])
        for j,faces in enumerate(self.colour_nodes):
            for q,n in enumerate(faces):self.visibility(n,q==g.states[1]['angles'][j])
        self.visibility(self.colour_face,True)
        self.transform(self.knife_drawer,[3.95,4.55 if g.states[1]['tool_drawer_open'] else 4.93,.45])
        self.visibility(self.knife,self.visible('s3_tool',g));self.visibility(self.reward_red,not g.solved[1]);self.visibility(self.reward_green,g.solved[1])
        self.visibility(self.seal_tape,not g.states[2]['seal_cut']);self.visibility(self.cut_seal_ends,g.states[2]['seal_cut'])
        self.transform(self.cabinet_door,rpy=[0,0,-105 if g.opened['s3_cover'] else 0])
        self.visibility(self.kite_picture,bool(g.opened['s3_cover']))
        for j,faces in enumerate(self.input_slots):
            buffer=g.states[2]['buffer']
            for q,n in enumerate(faces):self.visibility(n,j<len(buffer) and q==buffer[j])
        self.transform(self.final_drawer,[0,-.34 if g.opened['key_box'] else 0,.15]);self.visibility(self.key,self.visible('key',g))
        self.transform(self.exit_node,rpy=[0,0,self.door_angle-(103 if g.opened['exit'] else 0)])
        self.centres={}
        for key,node in self.target_nodes.items():
            tri=self.triangles(node)
            if tri.size:self.centres[key]=((tri.reshape(-1,3).min(0)+tri.reshape(-1,3).max(0))/2).tolist()
    def candidates(self,g):return self.base_candidates([k for k in self.target_nodes if self.visible(k,g)])
    def blocked(self,x,y,g):
        return super().blocked(x,y,g) or bool(g.states[1]['tool_drawer_open']) and 3.57<x<4.33 and 4.30<y<5.18
    def view_for(self,key):return self.views.get(key,self.door_view if key=='exit' else self.spec['start'][:2])
    def label_for(self,key):return self.labels.get(key,super().label_for(key))
    def focus_for(self,key):return self.centres.get(key)
    def animate(self,d,before):return


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
        view=list(d.pos[:2]) if stay else sc.view_for(key)
        if view is None:raise RuntimeError('No physical approach for '+key)
        point,k=axis_focus(key,view)
        if not stay:route_short(view,k,purpose)
        d.aim(point,purpose)
    def observe(key,purpose,stay=False):approach(key,purpose,stay);d.append(purpose,18)
    def click(key,kind='press',item=None):
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
        a={'thought':'Use the clue and the actual room object.','action':kind,'point':hit['point'],'target':sc.label_for(key)}
        if item is not None:a['item']=LABELS.get(item,item)
        return d.execute(a,'Observe the physical response')
    route_short(sc.view_for('s1_control_0'),1,'Approach the actual wooden easel')
    d.aim([d.pos[0],5.05,1.29],'Keep the whole easel and its fixed alignment rail in view')
    d.append('Observe both real support shoes and the fixed horizontal rail',18)
    for j,target in enumerate(SPEC['stages'][0]['target']):
        while g.states[0]['angles'][j]!=target:click('s1_control_'+str(j))
    if not g.solved[0]:raise RuntimeError('Aligned canvas did not release the easel drawer')
    approach('s2_cover','Look down at the drawer under this easel',stay=True)
    click('s2_cover','open');d.append('Observe the small key in the open easel drawer',18)
    click('s2_tool','take')
    observe('s2_clue','Walk along the wall and observe the two paint samples')
    approach('s2_setup','Look at the keyed paint sample box',stay=True)
    click('s2_setup','use','s2_tool');click('s2_setup','open')
    approach('s2_control_0','Keep both paint sample discs in view',stay=True)
    for j,target in enumerate(SPEC['stages'][1]['target']):
        while g.states[1]['angles'][j]!=target:click('s2_control_'+str(j))
    click('s2_confirm')
    if not g.solved[1]:raise RuntimeError('The two matching swatches did not release the art cupboard')
    approach('s2_reward','The green lamp marks the tool drawer beneath the paint samples',stay=True);click('s2_reward','open');d.append('Observe the flat palette knife',18);click('s3_tool','take')
    approach('s3_cover','Bring the palette knife to the visible cupboard sealing tape');click('s3_cover','use','s3_tool');d.append('The seal is cut; the cupboard door remains shut',18)
    click('s3_cover','open')
    observe('s3_clue','Observe the actual kite painting inside the cupboard',stay=True)
    approach('s3_choice_1','Look down at the cupboard symbol lock',stay=True)
    for j in SPEC['stages'][2]['answer']:click('s3_choice_'+str(j))
    click('s3_confirm')
    if not g.solved[2]:raise RuntimeError('The complete kite sequence did not release the bottom drawer')
    approach('key_box','Look down to the bottom drawer',stay=True)
    click('key_box','open');d.append('Observe the flat brass key in the open drawer',18)
    click('key','take')
    approach('exit','Return to the actual exit door')
    click('exit','use','key');click('exit','open')
    if not exit_test(d.pos,g):raise RuntimeError('Open-door success was not reached')

def cpu_check():
    from easy88_core import stage_actions
    g=Game();checks=[]
    def act(kind,key,**kw):return g.act(dict(action=kind,_hit364=key,_validated364=True,**kw))
    assert not act('open','s2_reward')['ok'];checks.append('tool drawer locked before sample solution')
    for i in [0,1]:
        for kind,key,extra in stage_actions(g,i):assert act(kind,key,**extra)['ok'],(i,kind,key)
    assert not act('open','s3_cover')['ok'];checks.append('sample solved alone cannot open distant cupboard')
    assert not act('take','s3_tool')['ok'];checks.append('closed local drawer blocks knife take')
    assert act('open','s2_reward')['ok'];assert act('take','s3_tool')['ok']
    assert not act('use','s3_cover',item='s2_tool')['ok'];checks.append('paint-box key does not cut tape')
    assert act('use','s3_cover',item='s3_tool')['ok'];assert g.states[2]['seal_cut'] and not g.opened['s3_cover'];checks.append('knife cuts seal but does not open door')
    for kind,key,extra in stage_actions(g,2):assert act(kind,key,**extra)['ok'],(kind,key)
    assert act('open','key_box')['ok'];assert act('take','key')['ok'];assert act('use','exit',item='key')['ok'];assert act('open','exit')['ok'];checks.append('ordinary key/use/open wins')
    return dict(level='R07',scope='CPU game-state fixtures only; native visual review pending',passed=len(checks),checks=checks)

_aff_build_last(Scene)
