SPEC = {'id': 'R04',
 'title': 'R04 · Garden Store / 园艺储藏室',
 'theme': 'gardening',
 'size': [4.6, 6.0],
 'door': {'side': 'south', 'start': 3.15, 'width': 1.04, 'view': [3.5, 1.0]},
 'start': [2.25, 1.5, 1.35],
 'start_yaw': 90,
 'floor': 'tile',
 'decor': [{'kind': 'plant_pots', 'wall': 'north', 'centre': [3.1, 5.65], 'fixed': True},
           {'kind': 'seed_packets', 'wall': 'west', 'centre': [0.25, 4.65], 'fixed': True},
           {'kind': 'watering_tools', 'wall': 'east', 'centre': [4.25, 1.75], 'fixed': True}],
 'design_notes': ['四有效管格，另外两格为实心空位；按实际IN到OUT连通接受。',
                  '壶、龙头、窄筒与软木环提供日常物理提示，不加浮力说明牌。',
                  '注水浮起不自动take；小钥匙必须take并use下一盖，最后仍有三叶方向题。'],
 'stages': [{'kind': 'rotate_pipes',
             'name': 'irrigation connection board',
             'wall': 'north',
             'centre': [1.25, 5.65],
             'view': [1.25, 4.75],
             'board_height': 0.96,
             'grid': [2, 3],
             'cells': [[0, 0], [0, 1], [1, 1], [1, 2]],
             'ports': [[3, 1], [0, 1], [0, 1], [3, 1]],
             'initial': [1, 1, 3, 1],
             'target': [2, 2, 0, 2],
             'inlet': [0, 0, 3],
             'outlet': [1, 2, 1],
             'auto': True,
             'clue': {'type': 'pipes',
                      'rows': 2,
                      'cols': 3,
                      'cells': [[0, 0], [0, 1], [1, 1], [1, 2]],
                      'in': [0, 0, 'W'],
                      'out': [1, 2, 'E']},
             'visual': {'type': 'pipes',
                        'rows': 2,
                        'cols': 3,
                        'cells': [[0, 0], [0, 1], [1, 1], [1, 2]],
                        'in': [0, 0, 'W'],
                        'out': [1, 2, 'E'],
                        'water_colour': 'blue',
                        'inactive_cells': [[0, 2], [1, 0]]},
             'clue_text': 'IN / OUT'},
            {'kind': 'float_key',
             'name': 'watering bench',
             'wall': 'east',
             'centre': [4.25, 3.75],
             'view': [3.25, 3.75],
             'board_height': 0.96,
             'auto': False,
             'clue': {'type': 'float_key',
                      'key_on_cork_ring': True,
                      'narrow_cylinder': True,
                      'tap': 'left'},
             'visual': {'type': 'float_key',
                        'key_on_cork_ring': True,
                        'narrow_cylinder': True,
                        'tap': 'left',
                        'water_start': 0.04,
                        'water_end': 0.43,
                        'key_start': 0.07,
                        'key_end': 0.46,
                        'cylinder_height': 0.52},
             'tool_name': 'small watering jug',
             'float_key_name': 'seed cabinet key',
             'clue_text': ''},
            {'kind': 'sequence',
             'name': 'seed cabinet leaf lock',
             'wall': 'west',
             'centre': [0.35, 3.25],
             'view': [1.25, 3.25],
             'board_height': 0.96,
             'options': ['left', 'up', 'right', 'down'],
             'answer': [0, 1, 1],
             'length': 3,
             'auto': False,
             'clue': {'type': 'leaf_directions',
                      'directions': ['left', 'up', 'up'],
                      'order': 'left_to_right'},
             'visual': {'type': 'leaf_directions',
                        'directions': ['left', 'up', 'up'],
                        'order': 'left_to_right',
                        'show_leaf_stems': True},
             'clue_text': ''}],
 'author_solution': ['Rotate the four active pipe tiles until actual IN-to-OUT connectivity.',
                     'Open the watering compartment, take jug; use it at faucet, then at narrow '
                     'cylinder.',
                     'Take the floated small key and use it on the seed cabinet cover; open cover.',
                     'Read leaf-tip directions left,up,up; input exactly3 and confirm.',
                     'Open final box, take door key, use and open exit.']}

from easy88_core import make_level,stage_actions
SPEC['stages'][2].update(kind='assign',name='seed germination trays',items=[
 {'id':'sun_moist','name':'sun/moist seed packet','conditions':[1,1]},
 {'id':'sun_dry','name':'sun/dry seed packet','conditions':[1,0]},
 {'id':'shade_moist','name':'shade/moist seed packet','conditions':[0,1]},
 {'id':'decoy_shade_dry','name':'shade/dry seed packet','conditions':[0,0],'decoy':True}],
 slots=3,target=[1,2,0],auto=False,clue={'type':'growth_compatibility','tray_conditions':[[1,0],[0,1],[1,1]],'self_contained':True},visual={'type':'physical_seed_packets_and_trays'},clue_text='')
for field in ['options','answer','length']:SPEC['stages'][2].pop(field,None)
Game,_OriginalScene,_original_standard,exit_test,cpu_check=make_level(SPEC)
TITLE=SPEC['title'];LEVEL_ID='R04';START=SPEC['start'];START_YAW=90
CAP=150;OBSERVATION_SIZE=(640,360);VISUAL_ONLY=False;READ_ENABLED=True;READ_FEEDBACK_TEXT=True
Game.LABELS.update({'s2_cover':'watering bench drawer','s2_tool':'small water jug','s3_cover':'seed cupboard door','key_box':'seed cupboard lower drawer','key':'brass door key'})
Game.LABELS.update({'s2_float_key':'leaf-bow brass key','s3_clue':'germination tray conditions','s3_confirm':'seed tray check lever'})
LABELS=Game.LABELS
_garden_check=Game._check;_garden_act=Game.act
def _growth_check(self,index):
    if index!=2:return _garden_check(self,index)
    placed={int(k):int(v) for k,v in self.states[2]['assignment'].items()}
    if set(placed)!=set(range(3)) or len(set(placed.values()))!=3:return False
    conditions=self.SPEC['stages'][2]['clue']['tray_conditions'];items=self.SPEC['stages'][2]['items']
    return all(items[placed[j]]['conditions']==conditions[j] for j in range(3))
Game._check=_growth_check
def _read_packet(self,a):
    key=str(a.get('_hit364',''))
    if a.get('_validated364') and a.get('action')=='read' and key.startswith('s3_item_'):
        from action_feedback import failure_for
        try:j=int(key.rsplit('_',1)[1]);sun,moist=self.SPEC['stages'][2]['items'][j]['conditions']
        except (ValueError,IndexError):return {'ok':False,'text':failure_for('read')}
        if not self.opened['s3_cover']:return {'ok':False,'text':failure_for('read')}
        return {'ok':True,'text':('Sunlight' if sun else 'Shade')+'; '+('moist soil.' if moist else 'dry soil.')}
    return _garden_act(self,a)
Game.act=_read_packet


import math,json,re
import numpy as np
from PIL import Image,ImageDraw
from easy88_scene import EasyScene
from easy88_clues import draw_symbol

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


class GardenRoom(EasyScene):
    def __init__(self,og,run):
        super().__init__(og,run,SPEC);self.labels={};self.views={};self.focus={};self.rotors=[];self.seed_packets=[];self.seed_slots=[]
    def palette(self):
        super().palette()
        for n,c in [('terracotta',(.48,.25,.13)),('soil',(.10,.075,.045)),('sage',(.29,.40,.31)),('plant_light',(.26,.43,.18)),('darkgreen',(.08,.22,.12)),('cork',(.51,.37,.19)),('porcelain',(.68,.71,.65))]:self.mat(n,c,rough=.92)
        self.mat('clear_tube',(.78,.86,.85),rough=.025,opacity=.08)
    def reg_at(self,key,node,label,view,focus=None):
        self.reg(key,node);self.labels[key]=label;self.views[key]=view
        if focus is not None:self.focus[key]=focus
        return node
    def flat(self,key,parent,pos,w,h,im,right=(1,0,0),up=(0,0,1)):
        p=self.tex/(key+'.png');im.save(p);return self.plane(key,pos,w,h,right,up,None,parent,material=self.image_mat(key,p))
    def conditions_image(self,conditions,seed=False):
        im=Image.new('RGB',(520,300),(222,216,190));d=ImageDraw.Draw(im);sun,moist=conditions
        if seed:d.ellipse((215,20,290,60),fill=(101,70,39));d.line((230,50,268,30),fill=(185,157,92),width=5)
        colour=(195,148,43) if sun else (76,88,83)
        if sun:
            d.ellipse((63,83,137,157),fill=colour)
            for a in range(0,360,45):
                t=math.radians(a);d.line((100+48*math.cos(t),120+48*math.sin(t),100+68*math.cos(t),120+68*math.sin(t)),fill=colour,width=7)
        else:
            d.polygon([(35,97),(165,97),(146,66),(54,66)],fill=colour);d.line((48,98,48,160),fill=colour,width=7);d.line((152,98,152,160),fill=colour,width=7)
        if moist:
            for x in [343,404]:d.polygon([(x,69),(x-24,123),(x-16,149),(x+16,149),(x+24,123)],fill=(50,111,134))
        else:
            d.rectangle((322,105,436,153),fill=(135,99,59));d.line((335,113,357,128,349,148),fill=(221,210,177),width=6);d.line((401,107,391,132,414,149),fill=(221,210,177),width=6)
        from font_utils import load_font
        d.text((100,222),'SUN' if sun else 'SHADE',font=load_font(42),fill=(38,55,42),anchor='mm');d.text((380,222),'MOIST' if moist else 'DRY',font=load_font(42),fill=(38,55,42),anchor='mm')
        return im
    def pot(self,key,parent,pos,scale=1.):
        n=self.group(key,pos,parent);r=.095*scale;h=.15*scale
        self.cylinder('earthen_pot',[0,0,h/2],r,h,'terracotta','z',n,n=28)
        self.cylinder('pot_lip',[0,0,h-.008*scale],r*1.12,.026*scale,'terracotta','z',n,n=28)
        self.cylinder('visible_soil',[0,0,h+.006*scale],r*.91,.010*scale,'soil','z',n,n=28)
        for j in range(5):
            a=j*2.4;tip=[.09*scale*math.cos(a),.09*scale*math.sin(a),h+(.15+.02*j)*scale]
            self.tube('stem',[0,0,h],tip,.004*scale,'darkgreen',n)
            mid=np.array(tip)*.75+np.array([0,0,h])*.25;side=np.array([-.035*math.sin(a),.035*math.cos(a),.01])*scale
            leaf=[mid.tolist(),(np.array(tip)+np.array([.07*math.cos(a),.07*math.sin(a),.05])*scale).tolist(),(mid+side).tolist(),(mid-side).tolist()]
            self.mesh('broad_green_leaf',leaf,[[0,2,1,3]],'plant_light' if j%2 else 'leaf_green',n)
        return n
    def shelf(self):
        n=self.group('plant_and_pot_rack',[.31,3.6,0]);self.transform(n,rpy=[0,0,90])
        for x in [-.77,.77]:self.box('rack_upright',[x,0,.77],[.05,.48,1.54],'darkwood',n)
        self.box('rack_back',[0,.22,.77],[1.54,.028,1.54],'sage',n)
        for z in [.15,.73,1.31]:self.box('rack_shelf',[0,0,z],[1.6,.48,.035],'wood',n)
        for j,x in enumerate([-.5,0,.5]):self.pot('growing_seedling_'+str(j),n,[x,0,.75],.80 if j!=1 else 1.)
        for x in [-.5,-.22,.1,.43]:
            self.cylinder('spare_flowerpot',[x,0,1.42],.085,.18,'terracotta','z',n,n=24)
            self.cylinder('empty_pot_dark_inside',[x,0,1.511],.071,.003,'soil','z',n,n=24)
        self.box('soil_sack',[.1,0,.36],[.63,.35,.34],'cloth',n,bevel=.055)
        self.add_obstacle(.06,2.78,.56,4.42)
        self.box('tool_pegboard',[.085,1.72,1.42],[.06,.64,.40],'wood')
        for y in [1.53,1.87]:
            self.cylinder('trowel_grip',[.15,y,1.51],.021,.18,'wood','z')
            self.mesh('trowel_spade',[[.13,y-.045,1.42],[.13,y+.045,1.42],[.19,y+.055,1.33],[.19,y,1.27],[.19,y-.055,1.33]],[[0,1,2,3,4]],'steel')
    def drawer(self,key,parent,centre,width=.78,depth=.40):
        n=self.group(key,centre,parent)
        self.box('drawer_base',[0,depth/2,0],[width,depth,.025],'darkwood',n)
        for x in [-width/2,width/2]:self.box('drawer_side',[x,depth/2,.065],[.025,depth,.15],'wood',n)
        self.box('drawer_back',[0,depth,.065],[width,.025,.15],'wood',n)
        self.box('drawer_front',[0,-.012,.055],[width+.045,.045,.19],'wood',n)
        self.box('drawer_handle',[0,-.052,.055],[.20,.04,.025],'brass',n)
        return n
    def build(self,g):
        self.room_shell('garden_room',size=(4.6,6.),openings={'south':[(3.12,4.22)]})
        self.box('continuous_subfloor',[2.3,3.,-.075],[4.74,6.14,.10],'darkwood',bevel=.001)
        self.box('pale_workroom_tile',[2.3,3.,.003],[4.48,5.88,.012],'cream',bevel=.001)
        for x in np.arange(.55,4.5,.6):self.box('grout_x',[float(x),3.,.010],[.006,5.87,.001],'plaster',bevel=.0001)
        for y in np.arange(.55,5.9,.6):self.box('grout_y',[2.3,float(y),.010],[4.47,.006,.001],'plaster',bevel=.0001)
        self.build_door();self.reg_at('exit',self.exit_node,'exit door',[3.5,1.0],[3.67,.075,1.05])
        self.table('long_potting_bench',(2.3,5.53),(3.35,.70),height=.70)
        self.box('wetbench_enamel_surface',[2.3,5.53,.749],[3.28,.65,.025],'porcelain',bevel=.012)
        self.box('bench_splashback',[2.3,5.87,.87],[3.35,.035,.28],'sage')
        root=self.group('irrigation_manifold',[1.28,5.76,1.21]);self.box('manifold_mount',[0,0,0],[1.04,.07,.73],'sage',root)
        self.stage_views=[[1.25,4.5],[2.75,4.5],[3.25,3.25]]
        self.stage_centres=[[1.28,5.68,1.21],[2.72,5.48,1.02],[4.30,3.3,1.02]]
        self.bases=[([1.28,5.76],0),([2.72,5.48],0),([4.30,3.3],-90)]
        spacing=.30
        for j,(r,c) in enumerate(SPEC['stages'][0]['cells']):
            x=(c-1)*spacing;z=(.5-r)*spacing;n=self.group('turnable_pipe_'+str(j),[x,-.055,z],root)
            self.box('pipe_rotor_plate',[0,0,0],[.286,.025,.286],'dark_panel',n)
            for port in SPEC['stages'][0]['ports'][j]:
                dx,dz={0:(0,.15),1:(.15,0),2:(0,-.15),3:(-.15,0)}[port]
                self.tube('brass_pipe',[0,-.035,0],[dx,-.035,dz],.025,'brass',n)
            self.cylinder('pipe_junction',[0,-.035,0],.030,.04,'brass','y',n,n=20)
            self.reg_at('s1_control_'+str(j),n,'turnable irrigation pipe',[1.25,4.5],[1.28,5.68,1.21]);self.rotors.append(n)
            _add_mark(self,'pipe_turn_mark_'+str(j),n,[.11,-.0135,.11],'turn',.05)
        self.tube('water_feed',[.70,5.67,.75],[.70,5.67,1.36],.026,'steel')
        self.tube('inlet_pipe',[.70,5.67,1.36],[.83,5.67,1.36],.026,'steel')
        self.label('inlet_label','IN',[.73,5.63,1.52],.12,.06)
        self.tube('outlet_pipe',[1.73,5.67,1.06],[1.90,5.67,1.06],.026,'steel')
        self.tube('outlet_drop',[1.90,5.67,1.06],[1.90,5.67,.86],.026,'steel')
        self.tube('outlet_to_faucet',[1.90,5.67,.86],[2.32,5.67,.86],.026,'steel')
        self.tube('faucet_supply_elbow',[2.32,5.67,.86],[2.32,5.76,.86],.026,'steel')
        self.label('outlet_label','OUT',[1.83,5.63,.98],.14,.06)
        self.water_flow=self.tube('connected_water_stream',[2.32,5.60,1.04],[2.32,5.60,.775],.014,'water')
        self.red=self.cylinder('irrigation_red',[1.83,5.69,1.48],.025,.018,'red_led','y');self.green=self.cylinder('irrigation_green',[1.83,5.69,1.48],.025,.018,'green','y')
        for x in [.83,1.73]:self.box('drawer_housing_side',[x,5.51,.545],[.035,.54,.28],'wood')
        self.box('drawer_housing_floor',[1.28,5.51,.41],[.94,.54,.025],'darkwood')
        self.box('drawer_housing_back',[1.28,5.77,.545],[.94,.025,.28],'wood')
        self.jug_drawer=self.drawer('watering_jug_drawer',None,[1.28,5.23,.47],.86,.48)
        self.reg_at('s2_cover',self.jug_drawer,'watering bench drawer',[1.25,4.5],[1.28,5.20,.55])
        self.jug=self.tool('s2_tool',self.jug_drawer,[0,.24,.14],'small water jug')
        self.reg_at('s2_tool',self.jug,'small water jug',[1.25,4.5])
        self.box('sink_dark_cavity',[2.32,5.49,.768],[.57,.43,.014],'dark_panel')
        for x in [2.02,2.62]:self.box('sink_side_rim',[x,5.49,.79],[.035,.46,.045],'steel')
        for y in [5.26,5.72]:self.box('sink_front_back_rim',[2.32,y,.79],[.63,.035,.045],'steel')
        tap=self.group('water_tap',[2.32,5.76,.80]);self.tube('tap_vertical',[0,0,0],[0,0,.29],.022,'steel',tap);self.tube('tap_neck',[0,0,.29],[0,-.16,.29],.022,'steel',tap);self.tube('tap_spout',[0,-.16,.29],[0,-.16,.24],.023,'steel',tap)
        self.cylinder('tap_valve',[.08,0,.10],.030,.045,'brass','x',tap);self.tube('tap_handle',[.10,0,.10],[.10,0,.18],.012,'steel',tap)
        self.reg_at('s2_tap',tap,'water tap',[2.25,4.5],[2.32,5.65,1.04])
        cyl=self.group('clear_propagation_cylinder',[3.14,5.35,.77])
        self.cylinder('cup_bottom',[0,0,.009],.12,.012,'clear_tube','z',cyl,n=48)
        count=64;points=[]
        for radius,z in [(.12,.012),(.12,.26),(.116,.012),(.116,.26)]:
            for j in range(count):
                a=2*math.pi*j/count;points.append([radius*math.cos(a),radius*math.sin(a),z])
        faces=[]
        for j in range(count):
            k=(j+1)%count
            faces.extend([[j,k,count+k,count+j],[2*count+j,3*count+j,3*count+k,2*count+k],[count+j,count+k,3*count+k,3*count+j]])
        self.mesh('thin_open_glass_cup',points,faces,'clear_tube',cyl)
        self.reg_at('s2_setup',cyl,'short clear water cup',[3.25,5.0],[3.14,5.35,.92])
        self.mat('cup_water',(.08,.34,.41),rough=.12,opacity=.20)
        self.water=self.group('cylinder_water',[0,0,.015],cyl)
        self.cylinder('water_volume',[0,0,.5],.114,1.,'cup_water','z',self.water,n=48)
        with self.og.sim.editing_usd():self.water_scale=self.G.Xformable(self.water['prim']).AddScaleOp()
        self.float=self.group('floating_cork_key',parent=cyl);self.transform(self.float,rpy=[0,0,90])
        self.cylinder('small_cork_raft',[0,0,0],.099,.018,'cork','z',self.float,n=48)
        self.floatkey=self.group('s2_float_key',[0,0,.014],self.float)
        outline=[(0,.100),(.015,.083),(.025,.060),(.019,.036),(0,.018),(-.019,.036),(-.025,.060),(-.015,.083)]
        points=[[x,y,z] for y in [-.005,.005] for x,z in outline];n=len(outline)
        faces=[list(reversed(range(n))),list(range(n,2*n))]+[[j,(j+1)%n,(j+1)%n+n,j+n] for j in range(n)]
        self.mesh('leaf_shaped_brass_key_bow',points,faces,'brass',self.floatkey)
        self.tube('leaf_key_vein',[0,.006,.028],[0,.006,.090],.0014,'darkgreen',self.floatkey)
        self.tube('leaf_key_vein_branch_a',[0,.006,.050],[.015,.006,.064],.0011,'darkgreen',self.floatkey)
        self.tube('leaf_key_vein_branch_b',[0,.006,.065],[-.016,.006,.079],.0011,'darkgreen',self.floatkey)
        self.box('brass_key_shaft',[0,0,-.034],[.012,.010,.13],'key_gold',self.floatkey,bevel=.002)
        self.box('brass_key_teeth',[.018,0,-.079],[.040,.010,.027],'key_gold',self.floatkey,bevel=.002)
        self.transform(self.floatkey,rpy=[90,0,0])
        self.reg_at('s2_float_key',self.floatkey,'leaf-bow brass key',[3.25,5.0],[3.14,5.35,.96])
        self.cab=self.group('seed_cupboard',[4.29,3.3,0]);self.transform(self.cab,rpy=[0,0,-90])
        for x in [-.64,.64]:self.box('cupboard_side',[x,0,.68],[.045,.53,1.34],'wood',self.cab)
        self.box('cupboard_back',[0,.25,.68],[1.29,.035,1.34],'sage',self.cab)
        for z in [.08,.58,1.34]:self.box('cupboard_board',[0,0,z],[1.3,.53,.04],'wood',self.cab)
        self.cabdoor=self.group('seed_cupboard_outer_door',[-.65,-.29,.68],self.cab);self.box('seed_door_panel',[.65,0,.30],[1.29,.045,.72],'sage',self.cabdoor);self.box('seed_door_handle',[1.17,-.045,.30],[.035,.05,.14],'brass',self.cabdoor)
        self.cylinder('seed_door_keyhole',[1.16,-.03,.15],.015,.009,'iron','y',self.cabdoor)
        self.mesh('seed_cupboard_leaf_emblem',[[1.10,-.026,.52],[1.15,-.026,.46],[1.14,-.026,.39],[1.10,-.026,.36],[1.06,-.026,.39],[1.05,-.026,.46]],[[0,1,2,3,4,5]],'darkgreen',self.cabdoor)
        self.reg_at('s3_cover',self.cabdoor,'seed cupboard door',[3.25,3.25],[4.01,3.3,.98])
        self.box('packet_rest_shelf',[0,.10,1.01],[1.27,.27,.025],'wood',self.cab)
        self.seed_reference=self.group('growth_conditions_reference',parent=self.cab)
        for j,conditions in enumerate(SPEC['stages'][2]['clue']['tray_conditions']):
            x=(j-1)*.37;tray=self.group('germination_tray_'+str(j),[x,-.10,.606],self.cab)
            self.box('seed_bed',[0,0,.012],[.29,.27,.035],'darkwood',tray);self.box('soil_bed',[0,0,.031],[.26,.24,.004],'soil',tray)
            self.reg_at('s3_slot_'+str(j),tray,'germination tray',[3.5,3.25],[4.18,3.3,.68]);self.seed_slots.append([x,-.10,.645])
            sign=self.group('tray_conditions_'+str(j),[x,.105,.80],self.seed_reference)
            self.box('condition_sign_post',[0,0,-.10],[.015,.022,.20],'wood',sign);self.box('condition_sign_back',[0,0,0],[.29,.015,.12],'darkwood',sign)
            self.flat('condition_sign_'+str(j),sign,[0,-.009,0],.28,.115,self.conditions_image(conditions))
        for j,item in enumerate(SPEC['stages'][2]['items']):
            packet=self.group('seed_packet_'+str(j),[(j-1.5)*.28,.12,1.1125],self.cab)
            self.box('paper_seed_packet',[0,0,0],[.20,.012,.18],'paper',packet);self.flat('seed_packet_print_'+str(j),packet,[0,-.0065,0],.19,.17,self.conditions_image(item['conditions'],True))
            self.reg_at('s3_item_'+str(j),packet,item['name'],[3.5,3.25],[4.25,3.3,1.11]);self.seed_packets.append(packet)
        self.reg_at('s3_clue',self.seed_reference,'germination tray conditions',[3.5,3.25],[4.28,3.3,.80])
        self.box('seed_validation_apron',[0,-.255,.53],[1.26,.04,.10],'sage',self.cab)
        self.confirm=self.group('s3_confirm',[.50,-.292,.53],self.cab);self.box('tray_check_lever',[0,0,0],[.10,.034,.10],'cream',self.confirm)
        tick=Image.new('RGB',(160,160),(220,215,192));td=ImageDraw.Draw(tick);td.line([(35,85),(68,117),(128,40)],fill=(35,70,43),width=13);self.flat('tray_check_mark',self.confirm,[0,-.018,0],.09,.09,tick)
        self.reg_at('s3_confirm',self.confirm,'seed tray check lever',[3.5,3.25],[4.0,3.3,.53])
        self.leaf_red=self.cylinder('seed_latch_red',[.33,-.278,.53],.018,.012,'red_led','y',self.cab);self.leaf_green=self.cylinder('seed_latch_green',[.33,-.278,.53],.018,.012,'green','y',self.cab)
        self.keydrawer=self.drawer('seed_cupboard_key_drawer',self.cab,[0,-.29,.30],1.16,.43)
        self.reg_at('key_box',self.keydrawer,'seed cupboard lower drawer',[3.25,3.25],[4.0,3.3,.36])
        self.key=self.tool('key',self.keydrawer,[0,.21,.055],'brass key');self.transform(self.key,rpy=[90,0,0]);self.reg_at('key',self.key,'brass door key',[3.25,3.25])
        self.shelf()
        self.table('short_potting_table',(1.05,.40),(1.65,.55),height=.70)
        self.pot('potted_herb',None,[.62,.4,.75],1.2)
        self.box('seed_tray',[1.25,.4,.79],[.55,.34,.07],'darkwood')
        for x in [1.06,1.24,1.42]:
            for y in [.31,.48]:self.cylinder('seed_tray_soil',[x,y,.83],.055,.015,'soil','z')
        self.sync(g)
        (self.run/'ROOM_GEOMETRY.json').write_text(json.dumps({'id':'R04','size':SPEC['size'],'camera_height':1.35,'furniture':['long_potting_bench','supported_jug_drawer','sink','clear_cylinder','seed_cupboard','plant_rack','short_potting_table'],'central_walkway_clear':True,'stage_views':self.stage_views,'input_size':[640,360]},ensure_ascii=False,indent=2),encoding='utf-8')
    def visible(self,key,g):
        if key=='s2_tool':return g.opened['s2_cover'] and key not in g.taken
        if key=='s2_float_key':return g.states[1]['floated'] and key not in g.taken
        if key=='key':return g.opened['key_box'] and key not in g.taken
        if key.startswith('s3_item_'):return bool(g.opened['s3_cover']) and key not in g.holding
        if key.startswith('s3_') and key!='s3_cover':return g.opened['s3_cover']
        return key in self.target_nodes
    def sync(self,g):
        for n,a in zip(self.rotors,g.states[0]['angles']):self.transform(n,rpy=[0,int(a)*90,0])
        self.visibility(self.red,not g.solved[0]);self.visibility(self.green,g.solved[0]);self.visibility(self.water_flow,g.solved[0])
        self.transform(self.jug_drawer,[1.28,4.80 if g.opened['s2_cover'] else 5.23,.47]);self.visibility(self.jug,self.visible('s2_tool',g))
        z=.245 if g.states[1]['floated'] else .055;self.transform(self.float,[0,0,z+.012])
        with self.og.sim.editing_usd():self.water_scale.Set(self.F.Vec3f(1,1,z-.015))
        self.visibility(self.floatkey,'s2_float_key' not in g.taken)
        self.transform(self.cabdoor,rpy=[0,0,-110 if g.opened['s3_cover'] else 0])
        assignment={int(k):int(v) for k,v in g.states[2]['assignment'].items()}
        for j,node in enumerate(self.seed_packets):
            slot=next((k for k,v in assignment.items() if v==j),None)
            self.transform(node,[(j-1.5)*.28,.12,1.1125] if slot is None else self.seed_slots[slot],rpy=[0,0,0] if slot is None else [-90,0,0]);self.visibility(node,self.visible('s3_item_'+str(j),g))
        self.visibility(self.leaf_red,not g.solved[2]);self.visibility(self.leaf_green,g.solved[2])
        self.transform(self.keydrawer,[0,-.70 if g.opened['key_box'] else -.29,.30]);self.visibility(self.key,self.visible('key',g))
        self.transform(self.exit_node,rpy=[0,0,-103 if g.opened['exit'] else 0])
        self.centres={}
        for key,n in self.target_nodes.items():
            pts=self.triangles(n).reshape(-1,3)
            if pts.size:self.centres[key]=((pts.min(0)+pts.max(0))/2).tolist()
    def candidates(self,g):return self.base_candidates([k for k in self.target_nodes if self.visible(k,g)])
    def view_for(self,key):return self.views.get(key,START[:2])
    def focus_for(self,key):return self.focus.get(key,self.centres.get(key))
    def label_for(self,key):return self.labels.get(key,LABELS.get(key,key.replace('_',' ')))
    def animate(self,d,before):
        old=before.get('states',[{}, {}, {}])[1]
        if not old.get('floated') and d.game.states[1]['floated']:
            for t in [.2,.4,.6,.8]:
                self.sync(d.game);z=.055+.19*t
                with self.og.sim.editing_usd():self.water_scale.Set(self.F.Vec3f(1,1,z-.015))
                self.transform(self.float,[0,0,z+.012]);d.frame(warm=4);d.append('Water lifts the cork and key',5)
        self.sync(d.game)

Scene=GardenRoom

def standard(d):
    from observation1280 import FX,FY,CX,CY
    from pixel355 import find_point
    g=d.game;s=d.scene
    def click(key,kind='press',fields=None):
        view=s.view_for(key)
        if math.dist(d.pos[:2],view)>.01:d.route(view,'Approach the room furniture')
        focus=s.focus_for(key)
        if focus is not None:d.aim(focus,'Observe the object and its response')
        cs=s.candidates(g)
        hit=find_point(key,d.pos,d.quat,d.depth,cs,fx=FX,fy=FY,cx=CX,cy=CY,actor_xy=d.pos[:2],tolerance=.05,mesh_tolerance=.04,grid=51,return_hit=True)
        if hit is None:
            d.aim(s.centres[key],'Look at the visible object');hit=find_point(key,d.pos,d.quat,d.depth,s.candidates(g),fx=FX,fy=FY,cx=CX,cy=CY,actor_xy=d.pos[:2],tolerance=.05,mesh_tolerance=.04,grid=61,return_hit=True)
        if hit is None:raise RuntimeError('No native visible point for '+key)
        fields=dict(fields or {})
        if 'item' in fields:fields['item']=LABELS[fields['item']]
        return d.execute(dict(thought='Follow the visible room clue.',action=kind,point=hit['point'],target=s.label_for(key),**fields),'Observe the result')
    for i in range(3):
        for kind,key,fields in stage_actions(g,i):click(key,kind,fields)
        if not g.solved[i]:raise RuntimeError('Stage not solved')
    click('key_box','open');click('key','take');click('exit','use',{'item':'key'});click('exit','open')
    assert exit_test(d.pos,g)

_garden_base_cpu=cpu_check
def cpu_check():
    import itertools
    result=_garden_base_cpu();g=Game();valid=[]
    for arrangement in itertools.permutations(range(4),3):
        g.states[2]['assignment']=dict(enumerate(arrangement))
        if g._check(2):valid.append(arrangement)
    assert valid==[(1,2,0)];result['checks'].append('24 packet assignments: only one compatible full allocation, unused decoy not required')
    g=Game();g.solved[:2]=[True,True];g.opened['s3_cover']=True
    def act(kind,key,**kw):return g.act(dict(action=kind,_hit364=key,_validated364=True,**kw))
    assert act('read','s3_item_0')['text']=='Sunlight; moist soil.';result['checks'].append('packet requirements self-contained in literal read feedback')
    assert act('take','s3_item_0')['ok'];assert act('use','s3_slot_0',item='s3_item_0')['ok'];assert not act('press','s3_confirm')['ok'];assert not g.solved[2]
    assert act('take','s3_item_0')['ok'] and not g.states[2]['assignment'];result['checks'].append('wrong placement remains recoverable, no per-slot correctness hint')
    assets=[GardenRoom.conditions_image(None,item['conditions'],True).tobytes() for item in SPEC['stages'][2]['items']]
    assert len(set(assets))==4;result['checks'].append('four actual printed packet condition images are distinct')
    result['passed']=len(result['checks']);return result

_aff_build_last(Scene)
