SPEC = {'id': 'R05',
 'title': 'R05 · Tea Packing Room / 茶叶备货间',
 'theme': 'tea',
 'size': [5.0, 4.5],
 'door': {'side': 'east', 'start': 0.7, 'width': 1.04, 'view': [4.0, 1.25]},
 'start': [3.75, 1.25, 1.35],
 'start_yaw': 90,
 'floor': 'wood',
 'decor': [{'kind': 'tea_tins', 'wall': 'east', 'centre': [4.7, 3.25], 'fixed': True},
           {'kind': 'teaware', 'wall': 'north', 'centre': [1.4, 4.15], 'fixed': True},
           {'kind': 'paper_packs', 'wall': 'west', 'centre': [0.25, 1.5], 'fixed': True}],
 'design_notes': ['唯一相关茶样罐没有重量标签，173g必须由实际秤屏观测。',
                  '柜内分装单提供四条位置约束，五只可拿放茶罐按整组检查；不逐罐提示正确。',
                  '三枚茶牌叶片数由视觉计数，read不能自动给213。'],
 'stages': [{'kind': 'weigh',
             'name': 'tea sample scale',
             'wall': 'north',
             'centre': [3.75, 4.15],
             'view': [3.75, 3.25],
             'board_height': 0.96,
             'answer': '0173',
             'auto': False,
             'setup': {'kind': 'weigh',
                       'item': 'tea_tin',
                       'item_name': 'tea sample tin',
                       'target_name': 'scale pan',
                       'consume': True,
                       'gate': True},
             'clue': {'type': 'scale',
                      'reading': 173,
                      'unit': 'g',
                      'lock_label': 'g / 0000',
                      'sample_weight_label': False},
             'visual': {'type': 'scale',
                        'reading': 173,
                        'unit': 'g',
                        'lock_label': 'g / 0000',
                        'sample_weight_label': False},
             'clue_text': '173 g'},
            {'kind': 'assign',
             'name': 'tea packing order',
             'wall': 'west',
             'centre': [0.3, 2.05],
             'view': [1.25, 2.25],
             'board_height': 0.96,
             'items': [{'id': 'white', 'name': 'white-lidded tea tin'},
                       {'id': 'red', 'name': 'red-lidded tea tin'},
                       {'id': 'blue', 'name': 'blue-lidded tea tin'},
                       {'id': 'green', 'name': 'green-lidded tea tin'},
                       {'id': 'black', 'name': 'black-lidded tea tin'}],
             'slots': 5,
             'target': [0, 4, 3, 1, 2],
             'auto': False,
             'clue': {'type': 'packing_order', 'source': 'packing note inside the sample cupboard'},
             'visual': {'type': 'physical_tin_rack'},
             'clue_text': 'White sits at an end.\n'
                          'Blue is immediately right of red.\n'
                          'One tin separates white and green.\n'
                          'Green is left of red.',
             'standard_read': True},
            {'kind': 'count',
             'name': 'tea badge chest',
             'wall': 'south',
             'centre': [2.0, 0.35],
             'view': [2.0, 1.25],
             'board_height': 0.96,
             'answer': '213',
             'auto': False,
             'clue': {'type': 'count',
                      'counts': [2, 1, 3],
                      'symbol': 'leaf',
                      'order': 'left_to_right',
                      'lock_label': '000'},
             'visual': {'type': 'count',
                        'counts': [2, 1, 3],
                        'symbol': 'leaf',
                        'order': 'left_to_right',
                        'separate_plaques': True,
                        'lock_label': '000'},
             'clue_text': ''}],
 'author_solution': ['Take sample tin, put it on actual scale, observe173g; unlock0173.',
                     'Read the packing note; arrange all five actual tins by its four constraints; test the complete rack.',
                     'Count leaves on three badges from left:2,1,3; unlock213.',
                     'Open final chest, take door key, use on door, open door.']}

SPEC['start']=[2.75,1.5,1.35]
SPEC['stages'][0].update(centre=[3.40,4.10],view=[3.5,3.25],clue_text='')
SPEC['stages'][1].update(centre=[.30,2.05],view=[1.75,2.25])
SPEC['stages'][2].update(centre=[3.35,.35],view=[3.25,1.25])
from easy88_core import make_level
Game,_BaseScene,standard,exit_test,cpu_check=make_level(SPEC)
TITLE=SPEC['title'];LEVEL_ID=SPEC['id'];START=SPEC['start'];START_YAW=90
CAP=150;OBSERVATION_SIZE=(640,360);VISUAL_ONLY=False;READ_ENABLED=True;READ_FEEDBACK_TEXT=True
Game.LABELS.update({'s1_tool':'tea sample tin','s1_setup':'scale pan','s1_clue':'scale display',
 's1_lock':'sample cupboard code lock','s2_cover':'sample cupboard door','s2_clue':'packing note inside the cupboard',
 's2_confirm':'packing rack check lever','s3_cover':'tea tag drawer','s3_clue':'tea leaf tags',
 's3_lock':'tea chest code lock','key_box':'tea chest lid','key':'door key'})
LABELS=Game.LABELS
_tea_act=Game.act
def _record_unlock(self,a):
    result=_tea_act(self,a)
    key=a.get('_hit364')
    if a.get('_validated364') and a.get('action')=='unlock' and key in ('s1_lock','s3_lock'):
        self.states[0 if key=='s1_lock' else 2]['entered_code']=str(a.get('code',''))
    return result
Game.act=_record_unlock

_base_tea_check=Game._check
def _packing_order_valid(self,index):
    if index!=1:return _base_tea_check(self,index)
    placed={int(k):int(v) for k,v in self.states[1]['assignment'].items()}
    if set(placed)!=set(range(5)) or set(placed.values())!=set(range(5)):return False
    colours=[self.SPEC['stages'][1]['items'][placed[k]]['id'] for k in range(5)]
    pos={colour:colours.index(colour) for colour in colours}
    return (pos['white'] in (0,4) and pos['blue']==pos['red']+1
            and abs(pos['white']-pos['green'])==2 and pos['green']<pos['red'])
Game._check=_packing_order_valid
import math,hashlib
import numpy as np
from PIL import Image,ImageDraw
from easy88_scene import EasyScene
from easy88_clues import draw_symbol
from font_utils import load_font

class Scene(EasyScene):
    def __init__(self,og,run):
        super().__init__(og,run,SPEC)
        self._views={};self._labels={};self._screen_signature=None;self.lock_screens={};self.lock_values={}
    def palette(self):
        super().palette()
        self.mat('tea_green',(.16,.25,.19),rough=.9)
        self.mat('tea_paper',(.60,.50,.32),rough=.98)
        self.mat('tea_cream',(.75,.71,.59),rough=.98)
        self.mat('selection_amber',(.76,.44,.07),rough=.7,emission=(.12,.05,.005))
    def _reg(self,key,node,label,view):
        self.reg(key,node);self._labels[key]=label;self._views[key]=list(view);return node
    def _print(self,key,parent,pos,w,h,im,horizontal=False):
        p=self.tex/(key+'.png');im.save(p)
        return self.plane(key,pos,w,h,(1,0,0),(0,1,0) if horizontal else (0,0,1),None,parent,material=self.image_mat('r05_'+key,p))
    def _tin(self,key,parent,pos,col='tea_green',size=.065):
        n=self.group(key,pos,parent)
        self.cylinder('round_tea_tin',[0,0,0],size,.17,col,'z',n,n=28)
        self.cylinder('fitted_tin_lid',[0,0,.087],size+.004,.014,'brass','z',n,n=28)
        self.cylinder('lid_knob',[0,0,.103],.014,.018,'brass','z',n)
        self.box('tin_paper_label',[0,-size-.001,-.005],[size*.95,.003,.068],'tea_cream',n,bevel=.001)
        return n
    def _shelf(self):
        n=self.group('tea_stock_shelf',[1.15,4.23,0])
        for x in [-.8,.8]:self.box('rack_upright',[x,0,.75],[.055,.40,1.50],'darkwood',n)
        self.box('rack_back',[0,.18,.75],[1.60,.035,1.48],'paint',n)
        for z in [.14,.72,1.34]:self.box('stock_shelf_board',[0,0,z],[1.68,.42,.045],'wood',n)
        for j in range(5):self._tin('stock_tea_tin_'+str(j),n,[-.58+j*.29,-.04,1.45],['tea_green','red','tea_green','tea_paper','tea_green'][j])
        for j in range(4):
            self.box('sealed_tea_pouch',[-.55+j*.36,0,.84],[.22,.22,.20],'tea_paper',n,bevel=.018)
            self.box('folded_pouch_top',[-.55+j*.36,0,.95],[.22,.22,.025],'tea_cream',n,bevel=.004)
        self.box('paper_wrapping_stack',[-.36,0,.20],[.60,.31,.07],'tea_cream',n,bevel=.006)
        self.box('empty_packing_tray',[.48,0,.23],[.35,.31,.13],'wood',n,bevel=.01)
        self.add_obstacle(.29,4.0,2.01,4.46)
    def _code_lock(self,key,parent,pos,digits,label,view):
        n=self.group(key,pos,parent);self.box('lock_housing',[0,0,0],[.29,.043,.13],'iron',n)
        face=self.label(key+'_display',digits,[0,-.023,.014],.23,.065,parent=n)
        self.lock_screens[key]=self.S.Shader(self.stage.GetPrimAtPath(str(self.mats['label_'+key+'_display'].GetPath())+'/texture'));self.lock_values[key]=digits
        self.label(key+'_hint',label,[0,-.024,-.040],.24,.033,parent=n)
        self._reg(key,n,Game.LABELS[key],view);return n
    def build(self,g):
        self.room_shell('tea_packing_room',size=(5,4.5),openings={'east':[(.67,1.77)]})
        self.box('continuous_subfloor',[2.5,2.25,-.076],[5.14,4.64,.10],'darkwood',bevel=.001)
        self._shelf()
        self.table('tea_weighing_bench',(3.40,4.10),(2.15,.62),height=.72)
        self.scale=self.group('bench_scale',[3.60,4.05,.79])
        self.box('scale_enamel_body',[0,0,.035],[.54,.37,.11],'tea_green',self.scale,bevel=.018)
        self.cylinder('scale_pan_stalk',[0,0,.13],.035,.12,'steel','z',self.scale)
        pan=self.group('scale_pan_target',[0,0,.20],self.scale);self.cylinder('stainless_weighing_pan',[0,0,0],.205,.024,'steel','z',pan,n=36)
        self._reg('s1_setup',pan,'scale pan',[3.5,3.25])
        self.box('scale_lcd_bezel',[0,-.188,.042],[.33,.018,.085],'iron',self.scale)
        self.scale_empty=self._print('scale_zero',self.scale,[0,-.200,.045],.296,.064,self._lcd('0 g'))
        self.scale_loaded=self._print('scale_reading',self.scale,[0,-.201,.045],.296,.064,self._lcd('173 g'))
        self._reg('s1_clue',self.scale_loaded,'scale display',[3.5,3.25])
        self.sample=self._tin('sample_tea_tin',None,[2.80,4.04,.85])
        self._reg('s1_tool',self.sample,'tea sample tin',[3.0,3.25])
        self.sample_on_scale=self._tin('sample_tin_on_pan',self.scale,[0,0,.298])
        c=self.group('tea_sample_cupboard',[.18,2.05,0]);self.transform(c,rpy=[0,0,90]);self.cupboard=c
        for x in [-.75,.75]:self.box('cupboard_side',[x,-.12,.78],[.035,.52,1.31],'wood',c)
        self.box('cupboard_back',[0,.12,.78],[1.52,.035,1.31],'paint',c)
        self.box('cupboard_top',[0,-.12,1.45],[1.60,.57,.055],'wood',c)
        self.box('cupboard_base',[0,-.12,.12],[1.56,.54,.06],'darkwood',c)
        self.box('drawer_separator',[0,-.12,.51],[1.52,.52,.04],'wood',c)
        self.selected=[];self.tin_nodes=[];self.tin_source_positions=[];self.tin_slot_positions=[]
        self.box('packing_shelf',[0,-.10,.5325],[1.42,.45,.035],'wood',c)
        self.mat('tin_white',(.78,.77,.70),rough=.65)
        self.mat('tin_red',(.56,.075,.035),rough=.65)
        self.mat('tin_blue',(.07,.22,.48),rough=.65)
        self.mat('tin_green',(.075,.36,.13),rough=.65)
        self.mat('tin_black',(.055,.065,.06),rough=.65)
        self.mat('packing_wait',(.48,.045,.025),rough=.8,emission=(.12,.008,.004))
        self.mat('packing_pass',(.08,.48,.12),rough=.8,emission=(.02,.16,.03))
        paper=Image.new('RGB',(1200,650),(229,221,196));ink=ImageDraw.Draw(paper)
        ink.text((65,24),'PACKING ORDER',font=load_font(72),fill=(35,51,40))
        for j,line in enumerate(SPEC['stages'][1]['clue_text'].splitlines()):
            ink.text((65,142+j*112),line,font=load_font(49),fill=(35,51,40))
        self.note=self.group('packing_note',[0,.075,1.16],c)
        self._print('actual_packing_note',self.note,[0,-.004,0],.70,.36,paper)
        self._reg('s2_clue',self.note,'packing note',[1.25,2.25])
        for j,item in enumerate(SPEC['stages'][1]['items']):
            x=(j-2)*.28
            source=[x,.025,.635];slot=[x,-.25,.638]
            self.tin_source_positions.append(source);self.tin_slot_positions.append(slot)
            tin=self._tin('packing_tin_'+str(j),c,source,size=.065)
            self.cylinder('coloured_tin_lid',[0,0,.100],.066,.007,'tin_'+item['id'],'z',tin,n=28)
            self._reg('s2_item_'+str(j),tin,item['name'],[1.25,2.25]);self.tin_nodes.append(tin)
            bay=self.group('packing_bay_'+str(j),[x,-.25,.551],c)
            self.cylinder('felt_bay',[0,0,0],.090,.004,'dark_panel','z',bay,n=28)
            self._reg('s2_slot_'+str(j),bay,'packing shelf position',[1.25,2.25])
        check=self.group('packing_check_lever',[.69,-.22,.79],c)
        self.box('lever_mount',[0,0,0],[.10,.035,.10],'iron',check)
        self.tube('lever_grip',[0,-.02,0],[0,-.11,.035],.017,'brass',check)
        self._reg('s2_confirm',check,'packing check lever',[1.4,2.25])
        self.wait_lamp=self.cylinder('packing_red_lamp',[.69,-.245,.885],.019,.010,'packing_wait','y',c)
        self.pass_lamp=self.cylinder('packing_green_lamp',[.69,-.245,.885],.019,.010,'packing_pass','y',c)
        self.tube('visible_drawer_lock_link',[.70,-.25,.79],[.70,-.25,.46],.006,'steel',c)
        self.tube('drawer_link_end',[.70,-.25,.46],[.60,-.43,.45],.006,'steel',c)
        self.drawer_bolt=self.group('packing_drawer_bolt',[.60,-.43,.45],c)
        self.box('retracting_latch',[0,0,0],[.12,.023,.024],'brass',self.drawer_bolt)
        self.cupboard_door=self.group('sample_cupboard_hinge',[-.75,-.40,.53],c)
        self.box('cupboard_door_leaf',[.75,0,.445],[1.50,.045,.89],'paint',self.cupboard_door)
        self.box('cupboard_door_handle',[1.37,-.06,.43],[.025,.055,.18],'brass',self.cupboard_door)
        self._reg('s2_cover',self.cupboard_door,'sample cupboard door',[1.75,2.25])
        self._code_lock('s1_lock',self.cupboard_door,[1.07,-.045,.43],'0000','g',[1.75,2.25])
        self.drawer=self.group('tea_tag_drawer',[0,-.40,.31],c)
        self.drawer_face=self.group('tag_drawer_front',parent=self.drawer)
        self.box('drawer_front',[0,0,0],[1.45,.045,.28],'wood',self.drawer_face)
        self.box('drawer_pull',[0,-.055,0],[.22,.05,.03],'brass',self.drawer_face)
        self._reg('s3_cover',self.drawer_face,'tea tag drawer',[1.75,2.25])
        self.box('drawer_bottom',[0,.23,-.12],[1.37,.47,.023],'wood',self.drawer)
        for x in [-.69,.69]:
            self.box('drawer_side',[x,.23,-.005],[.025,.47,.25],'wood',self.drawer)
            self.box('drawer_slide',[x,.25,-.035],[.012,.48,.025],'steel',self.drawer)
        self.box('drawer_rear',[0,.455,-.005],[1.40,.025,.25],'wood',self.drawer)
        self.tags=self.group('three_tea_tags',[0,.20,-.100],self.drawer)
        for j,count in enumerate([2,1,3]):
            im=Image.new('RGB',(300,360),(223,214,184));di=ImageDraw.Draw(im)
            di.polygon([(12,35),(35,12),(265,12),(288,35),(288,344),(12,344)],outline=(113,102,77),width=5)
            for k in range(count):
                cy=180+(k-(count-1)/2)*75;draw_symbol(di,'leaf',(107,cy-30,193,cy+30),fill=(32,70,47),outline=(32,70,47))
            self._print('tea_leaf_tag_'+str(j),self.tags,[(j-1)*.36,0,.002],.30,.34,im,horizontal=True)
        self._reg('s3_clue',self.tags,'tea leaf tags',[1.5,2.25])
        self.add_obstacle(.05,1.26,.72,2.84)
        self.table('tea_chest_stand',(3.35,.39),(1.42,.61),height=.62)
        self.chest=self.group('small_tea_chest',[3.35,.39,.68]);self.transform(self.chest,rpy=[0,0,180])
        self.box('tea_chest_floor',[0,0,0],[.81,.45,.025],'darkwood',self.chest)
        for x in [-.40,.40]:self.box('tea_chest_side',[x,0,.065],[.025,.45,.13],'wood',self.chest)
        for y in [-.22,.22]:self.box('tea_chest_edge',[0,y,.065],[.80,.025,.13],'wood',self.chest)
        self.box('tea_chest_lining',[0,0,.018],[.75,.39,.01],'tea_cream',self.chest)
        self.chest_lid=self.group('tea_chest_lid_hinge',[0,.22,.135],self.chest)
        lid=self.group('tea_chest_lid',parent=self.chest_lid);self.box('tea_chest_lid_wood',[0,-.22,0],[.85,.48,.025],'wood',lid)
        self.box('lid_pull',[0,-.47,0],[.15,.035,.03],'brass',lid);self._reg('key_box',lid,'tea chest lid',[3.25,1.25])
        self._code_lock('s3_lock',self.chest,[0,-.246,.067],'000','',[3.25,1.25])
        leaf=Image.new('RGB',(240,110),(222,214,185));di=ImageDraw.Draw(leaf);draw_symbol(di,'leaf',(18,15,80,95),fill=(34,67,45),outline=(34,67,45));di.line((112,55,205,55),fill=(46,61,45),width=7);di.polygon([(205,55),(180,38),(180,72)],fill=(46,61,45))
        self._print('chest_leaf_order',self.chest,[.29,-.237,.065],.15,.07,leaf)
        self.key=self.tool('flat_door_key',self.chest,[0,0,.044],'key');self.target_nodes.pop('flat_door_key',None);self.transform(self.key,rpy=[90,0,0]);self._reg('key',self.key,'door key',[3.25,1.25])
        self.mat('window_pale',(.48,.60,.58),rough=.9,emission=(.12,.16,.15))
        self.box('window_glass',[4.925,3.20,1.68],[.025,.67,.70],'window_pale')
        for y in [2.84,3.56]:self.box('window_jamb',[4.90,y,1.68],[.065,.035,.77],'darkwood')
        for z in [1.30,1.68,2.06]:self.box('window_rail',[4.90,3.20,z],[.065,.76,.035],'darkwood')
        self.box('packing_paper_stack',[4.12,4.05,.80],[.31,.33,.07],'tea_cream',bevel=.006)
        self.exit_node=self.door('exit_door',[4.94,.70,0],1.04);self.door_angle=90
        self._reg('exit',self.exit_node,'exit door',[4.0,1.25]);self.door_view=[4.0,1.25]
        for y in [.68,1.76]:self.box('door_frame',[4.95,y,1.14],[.17,.065,2.30],'paint')
        self.box('door_top_frame',[4.95,1.22,2.29],[.17,1.15,.065],'paint')
        for y in [.69,1.75]:self.box('door_stop_jamb',[4.99,y,1.14],[.026,.035,2.28],'darkwood')
        self.box('door_stop_top',[4.99,1.22,2.28],[.026,1.13,.035],'darkwood')
        self.stage_views=[[3.5,3.25],[1.75,2.25],[1.5,2.25]]
        self.bases=[([3.40,4.10],0),([.18,2.05],90),([.18,2.05],90)]
        self.stage_centres=[[3.40,4.04,.94],[.55,2.05,.86],[.85,2.05,.35]]
        self.sync(g)
    def _lcd(self,text):
        im=Image.new('RGB',(600,160),(49,68,55));d=ImageDraw.Draw(im);d.text((300,80),text,font=load_font(108),fill=(220,228,184),anchor='mm');return im
    def visible(self,key,g):
        if key=='s1_tool':return key not in g.taken
        if key=='s1_clue':return bool(g.states[0]['setup_ready'])
        if key.startswith('s2_item_'):
            j=int(key.rsplit('_',1)[1]);placed={int(k):int(v) for k,v in g.states[1]['assignment'].items()}
            return bool(g.opened['s2_cover']) and key not in g.holding and (key not in g.taken or j in placed.values())
        if key.startswith('s2_slot_') or key in ('s2_clue','s2_confirm'):return bool(g.opened['s2_cover'])
        if key=='s3_clue':return bool(g.opened['s3_cover'])
        if key=='key':return bool(g.opened['key_box']) and key not in g.taken
        return key in self.target_nodes
    def sync(self,g):
        for key,shader in self.lock_screens.items():
            text=g.states[0 if key=='s1_lock' else 2].get('entered_code','0000' if key=='s1_lock' else '000')
            if self.lock_values[key]!=text:
                path=self.label_image(key+'_entered_'+hashlib.sha256(text.encode()).hexdigest()[:12],text,1200,340)
                with self.og.sim.editing_usd():shader.GetInput('file').Set(str(path))
                self.lock_values[key]=text
        loaded=bool(g.states[0]['setup_ready']);self.visibility(self.scale_empty,not loaded);self.visibility(self.scale_loaded,loaded)
        self.visibility(self.sample,self.visible('s1_tool',g));self.visibility(self.sample_on_scale,loaded)
        self.transform(self.cupboard_door,rpy=[0,0,-103 if g.opened['s2_cover'] else 0])
        placed={int(k):int(v) for k,v in g.states[1]['assignment'].items()}
        for j,tin in enumerate(self.tin_nodes):
            slot=next((k for k,v in placed.items() if v==j),None)
            self.transform(tin,self.tin_source_positions[j] if slot is None else self.tin_slot_positions[slot])
            self.visibility(tin,self.visible('s2_item_'+str(j),g))
        self.visibility(self.note,bool(g.opened['s2_cover']))
        self.visibility(self.target_nodes['s2_confirm'],bool(g.opened['s2_cover']))
        for j in range(5):self.visibility(self.target_nodes['s2_slot_'+str(j)],bool(g.opened['s2_cover']))
        self.visibility(self.wait_lamp,bool(g.opened['s2_cover']) and not g.solved[1])
        self.visibility(self.pass_lamp,bool(g.opened['s2_cover']) and g.solved[1])
        self.transform(self.drawer_bolt,[.72 if g.solved[1] else .60,-.43,.45])
        self.transform(self.drawer,[0,-.40-(.40 if g.opened['s3_cover'] else 0),.31])
        self.visibility(self.tags,bool(g.opened['s3_cover']))
        self.transform(self.chest_lid,rpy=[-105 if g.opened['key_box'] else 0,0,0]);self.visibility(self.key,self.visible('key',g))
        self.transform(self.exit_node,rpy=[0,0,self.door_angle-(103 if g.opened['exit'] else 0)])
        self.centres={}
        for key,node in self.target_nodes.items():
            tri=self.triangles(node)
            if tri.size:self.centres[key]=((tri.reshape(-1,3).min(0)+tri.reshape(-1,3).max(0))/2).tolist()
    def candidates(self,g):return self.base_candidates([k for k in self.target_nodes if self.visible(k,g)])
    def view_for(self,key):
        if key in ('key','key_box','s3_lock'):return [3.25,1.25]
        if key=='exit':return self.door_view
        return self._views.get(key,[2.75,1.5])
    def label_for(self,key):return self._labels.get(key,Game.LABELS.get(key,key.replace('_',' ')))
    def animate(self,d,before):
        old=before.get('opened',{});current=d.game.opened
        for key,node in [('s2_cover',self.cupboard_door),('key_box',self.chest_lid)]:
            if bool(old.get(key))!=bool(current[key]):
                for t in [.33,.66]:
                    amount=float(bool(old.get(key)))+(float(bool(current[key]))-float(bool(old.get(key))))*t
                    self.sync(d.game);self.transform(node,rpy=[0,0,-103*amount] if key=='s2_cover' else [-105*amount,0,0]);d.frame(warm=4);d.append('Observe the container opening',4)
        if bool(old.get('s3_cover'))!=bool(current['s3_cover']):
            for t in [.33,.66]:
                amount=float(bool(old.get('s3_cover')))+(float(bool(current['s3_cover']))-float(bool(old.get('s3_cover'))))*t
                self.sync(d.game);self.transform(self.drawer,[0,-.40-.40*amount,.31]);d.frame(warm=4);d.append('Observe the drawer opening',4)
        self.sync(d.game)

_tea_standard=standard
def standard(d):
    previous=d.prepare_reference
    def reference(index):
        if index==1:
            if __import__('math').dist(d.pos[:2],[1.5,2.25])>.08:d.route([1.5,2.25],'Stand back enough to see the tins and drawer response')
            return d.aim(d.scene.stage_centres[1],'Keep the packing rack and its drawer latch in view')
        return previous(index)
    d.prepare_reference=reference
    try:return _tea_standard(d)
    finally:d.prepare_reference=previous
