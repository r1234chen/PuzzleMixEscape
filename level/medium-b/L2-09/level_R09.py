from easy88_core import make_level

SPEC = {'id': 'R09',
 'title': 'R09 · Pantry / 家庭食品储藏间',
 'theme': 'pantry',
 'size': [4.5, 5.0],
 'door': {'side': 'east', 'start': 0.65, 'width': 1.04},
 'start': [3.25, 1.25, 1.35],
 'start_yaw': 180,
 'floor': 'tile',
 'decor': ['sealed food jars', 'flour sacks', 'empty basket', 'fixed wooden spoons'],
 'design_notes': 'Net mass is180 minus tray20. Pack one ready fruit, grain and drink without repeated ingredients; any three pockets and any card order are legal. All facts are printed/readable on the cards. The local latch releases the clock drawer; use its time at the HHMM recipe case.',
 'stages': [{'kind': 'net_weigh',
             'lock_label': 'NET g / 0000',
             'name': 'pantry weighing station',
             'wall': 'north',
             'answer': '0160',
             'digits': 4,
             'setup': {'kind': 'weigh',
                       'item': 'sample_tin',
                       'item_name': 'plain food tin',
                       'target_name': 'scale pan',
                       'consume': False},
             'visual': {'type': 'scale',
                        'reading': 180,
                        'tare': 20,
                        'unit': 'g',
                        'display_on_scale': True,
                        'lock_label': 'NET g / 0000'},
             'clue': {'reading': 180, 'tare': 20, 'unit': 'g', 'required_quantity': 'net_weight'},
             'clue_text': 'Tray: 20 g\n180 g'},
            {'kind': 'assign',
             'name': 'food classification rack',
             'wall': 'west',
             'items': [{'id': 'apple_card', 'name': 'apple picture card', 'symbol': 'apple'},
                       {'id': 'rice_card', 'name': 'rice-bag picture card', 'symbol': 'rice_bag'},
                       {'id': 'water_card', 'name': 'water-bottle picture card', 'symbol': 'bottle'}],
             'slots': 4,
             'target': [0, None, 2, 1],
             'auto': False,
             'visual': {'type': 'food_classify',
                        'classes': ['fruit', 'vegetable', 'drink', 'staple'],
                        'items': ['apple', 'rice_bag', 'bottle']},
             'clue': {'classes': ['fruit', 'vegetable', 'drink', 'staple'],
                      'examples': [['pear', 'banana'],
                                   ['carrot', 'cabbage'],
                                   ['glass_of_water', 'juice'],
                                   ['bread', 'wheat']]},
             'clue_text': ''},
            {'kind': 'clock',
             'name': 'recipe case time lock',
             'wall': 'east',
             'answer': '1645',
             'digits': 4,
             'visual': {'type': 'clock', 'hour': 4, 'minute': 45, 'period': 'PM', 'format': '24h'},
             'clue': {'hour': 4, 'minute': 45, 'period': 'PM', 'format': '24h/HHMM'},
             'clue_text': 'PM\n24h / HHMM'}]}

SPEC['start_yaw']=90
SPEC['stages'][0]['setup']['consume']=True
SPEC['stages'][0]['clue_text']=''
SPEC['stages'][2]['clue_text']=''
from easy88_core import make_level,_assignment
from action_feedback import failure_for
SPEC['stages'][1].update(name='picnic lunch packing',items=[
 {'id':'apple','name':'apple ingredient card','symbol':'apple','category':'FRUIT','ready':True,'ingredients':['APPLE']},
 {'id':'rice','name':'uncooked rice ingredient card','symbol':'rice_bag','category':'GRAIN','ready':False,'ingredients':['RICE']},
 {'id':'water','name':'water ingredient card','symbol':'bottle','category':'DRINK','ready':True,'ingredients':['WATER']},
 {'id':'crackers','name':'cracker ingredient card','symbol':'crackers','category':'GRAIN','ready':True,'ingredients':['WHEAT']},
 {'id':'juice','name':'apple juice ingredient card','symbol':'bottle','category':'DRINK','ready':True,'ingredients':['APPLE']}],
 target=[0,3,2,None],slots=4,visual={'type':'physical_lunch_cards'},
 clue={'type':'ingredient_set_constraints','one_each':['FRUIT','GRAIN','DRINK'],'no_cooking':True,'no_repeated_ingredients':True},
 clue_text='One fruit, one grain, one drink.\nNo cooking.\nNo repeated ingredients.',standard_read=True)
Game,_OldScene,_OldStandard,exit_test,cpu_check=make_level(SPEC)
TITLE=SPEC['title'];LEVEL_ID=SPEC['id'];START=SPEC['start'];START_YAW=90
CAP=150;OBSERVATION_SIZE=(640,360);VISUAL_ONLY=False;READ_ENABLED=True;READ_FEEDBACK_TEXT=True
Game.LABELS.update({'s1_tool':'plain food tin','s1_setup':'scale tray','s1_clue':'scale display',
 's1_lock':'net weight drawer lock','s2_cover':'food card drawer','s2_clue':'picnic packing list',
 's2_confirm':'stock check button','s3_cover':'clock drawer','s3_clue':'clock face',
 's3_lock':'recipe box time lock','key_box':'recipe box lid','key':'brass door key'})
for _i,_label in enumerate(['lunch tray pocket','lunch tray pocket','lunch tray pocket','lunch tray pocket']):Game.LABELS['s2_slot_'+str(_i)]=_label
LABELS=Game.LABELS
_original_act=Game.act
Game.stage_accessible=lambda self,index:0<=index<3
Game.stage_exposed=lambda self,index:0<=index<3 and bool(self.states[index]['setup_ready'])
def _pantry_act(self,a):
    key=a.get('_hit364');kind=a.get('action')
    if a.get('_validated364') and kind=='take' and str(key).startswith('s2_item_'):
        j=int(key.rsplit('_',1)[1]);placed=j in _assignment(self.states[1]).values()
        if not placed and not self.opened['s2_cover']:return {'ok':False,'text':failure_for(kind)}
    if a.get('_validated364') and kind=='read' and str(key).startswith('s2_item_'):
        j=int(key.rsplit('_',1)[1]);placed=j in _assignment(self.states[1]).values()
        if not (self.opened['s2_cover'] or placed or key in self.holding):return {'ok':False,'text':failure_for(kind)}
        item=self.SPEC['stages'][1]['items'][j]
        return {'ok':True,'text':item['category']+' / '+('READY' if item['ready'] else 'COOK')+' / '+' + '.join(item['ingredients'])}
    result=_original_act(self,a)
    if a.get('_validated364') and kind=='unlock' and key in ('s1_lock','s3_lock'):
        self.states[0 if key=='s1_lock' else 2]['entered_code']=str(a.get('code',''))
    return result
Game.act=_pantry_act
_base_pantry_check=Game._check
def _lunch_check(self,index):
    if index!=1:return _base_pantry_check(self,index)
    values=list(_assignment(self.states[1]).values());items=self.SPEC['stages'][1]['items']
    if len(values)!=3 or len(set(values))!=3 or any(not 0<=int(v)<len(items) for v in values):return False
    selected=[items[int(v)] for v in values]
    if sorted(x['category'] for x in selected)!=['DRINK','FRUIT','GRAIN'] or not all(x['ready'] for x in selected):return False
    seen=set()
    for item in selected:
        ingredients=set(item['ingredients'])
        if seen & ingredients:return False
        seen.update(ingredients)
    return True
Game._check=_lunch_check

import math,hashlib
import numpy as np
from PIL import Image,ImageDraw
from easy88_scene import EasyScene
from easy88_clues import draw_symbol
from font_utils import load_font

class Scene(EasyScene):
    def __init__(self,og,run):
        super().__init__(og,run,SPEC)
        self.views={};self.focus={};self.labels={};self.drawers={};self.lock_screens={};self.lock_values={};self.cards=[];self.slot_positions=[];self.expanded=[]
    def palette(self):
        super().palette()
        for name,c in [('pantry_enamel',(.20,.30,.27)),('pantry_tile',(.50,.52,.48)),('tile_joint',(.26,.29,.26)),('sack',(.60,.50,.34)),('food_red',(.48,.12,.075)),('food_green',(.23,.36,.17)),('bottle_blue',(.20,.38,.42)),('card_cream',(.75,.71,.60)),('basket_lining',(.45,.36,.24))]:self.mat(name,c,rough=.91)
    def reg_at(self,key,node,label,view,focus=None):
        self.reg(key,node);self.labels[key]=label;self.views[key]=list(view)
        if focus is not None:self.focus[key]=list(focus)
        return node
    def flat(self,name,parent,pos,w,h,im,horizontal=False):
        p=self.tex/(name+'.png');im.save(p)
        return self.plane(name,pos,w,h,(1,0,0),(0,1,0) if horizontal else (0,0,1),None,parent,material=self.image_mat('r09_'+name,p))
    def text(self,name,parent,pos,w,h,value,bg=(49,68,55),ink=(222,227,190),horizontal=False):
        im=Image.new('RGB',(1000,240),bg);d=ImageDraw.Draw(im);size=160
        while size>12 and d.textbbox((0,0),str(value),font=load_font(size))[2]>940:size-=8
        d.text((500,120),str(value),font=load_font(size),fill=ink,anchor='mm')
        return self.flat(name,parent,pos,w,h,im,horizontal)
    def lock(self,key,parent,pos,label,view):
        n=self.group(key,pos,parent);self.box('code_lock_case',[0,0,0],[.32,.036,.145],'iron',n)
        plane=self.text(key+'_lcd',n,[0,-.020,.025],.268,.076,'0000')
        self.lock_screens[key]=self.S.Shader(self.stage.GetPrimAtPath(str(self.mats['r09_'+key+'_lcd'].GetPath())+'/texture'));self.lock_values[key]='0000'
        self.text(key+'_label',n,[0,-.020,-.043],.285,.030,label,bg=(207,201,177),ink=(38,48,40))
        self.reg_at(key,n,LABELS[key],view);return n
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
    def tin(self,name,parent,pos):
        n=self.group(name,pos,parent);self.cylinder('food_tin_body',[0,0,0],.062,.16,'pantry_enamel','z',n,n=28)
        for z in [-.081,.081]:self.cylinder('tin_rim',[0,0,z],.065,.012,'steel','z',n,n=28)
        self.box('tin_paper_band',[0,-.063,0],[.075,.003,.067],'card_cream',n,bevel=.001);return n
    def bottle(self,name,parent,pos):
        n=self.group(name,pos,parent);self.cylinder('water_bottle_body',[0,0,.10],.042,.19,'bottle_blue','z',n,n=24)
        self.cylinder('bottle_neck',[0,0,.215],.023,.07,'bottle_blue','z',n,n=24);self.cylinder('bottle_cap',[0,0,.253],.026,.022,'pantry_enamel','z',n,n=24)
        self.cylinder('bottle_paper_label',[0,0,.105],.043,.067,'card_cream','z',n,n=24);return n
    def fruit(self,name,parent,pos,col='food_red'):
        n=self.group(name,pos,parent);pts=[[0,0,-.06],[0,0,.06]];faces=[];rings=7;segments=20
        for j in range(1,rings+1):
            p=-math.pi/2+math.pi*j/(rings+1)
            for k in range(segments):
                a=k*2*math.pi/segments;pts.append([.065*math.cos(p)*math.cos(a),.065*math.cos(p)*math.sin(a),.06*math.sin(p)])
        for k in range(segments):
            q=(k+1)%segments;faces.append([0,2+q,2+k]);faces.append([1,2+(rings-1)*segments+k,2+(rings-1)*segments+q])
        for j in range(rings-1):
            for k in range(segments):
                q=(k+1)%segments;faces.append([2+j*segments+k,2+j*segments+q,2+(j+1)*segments+q,2+(j+1)*segments+k])
        self.mesh('rounded_fruit',pts,faces,col,n);self.tube('fruit_stem',[0,0,.046],[.006,0,.084],.006,'darkwood',n)
        self.box('fruit_leaf',[.018,0,.073],[.036,.014,.006],'food_green',n,bevel=.003);return n
    def ingredient_card_image(self,item):
        im=Image.new('RGB',(500,650),(226,219,194));d=ImageDraw.Draw(im)
        d.rectangle((10,10,489,639),outline=(147,137,109),width=5)
        if item['symbol']=='crackers':
            for dx,dy in [(0,0),(70,35)]:
                d.rounded_rectangle((115+dx,70+dy,315+dx,265+dy),radius=15,fill=(191,149,82),outline=(95,76,45),width=7)
                for x in [155,215,275]:
                    for y in [115,175,235]:d.ellipse((x+dx-5,y+dy-5,x+dx+5,y+dy+5),fill=(106,81,44))
        else:draw_symbol(d,item['symbol'],(100,45,400,320))
        lines=[item['category'],'READY' if item['ready'] else 'COOK',' + '.join(item['ingredients'])]
        for j,line in enumerate(lines):d.text((250,390+j*90),line,font=load_font(49),fill=(34,50,40),anchor='mm')
        return im
    def packing_list_image(self):
        im=Image.new('RGB',(1400,470),(226,219,194));d=ImageDraw.Draw(im)
        for j,line in enumerate(['PICNIC LUNCH']+SPEC['stages'][1]['clue_text'].splitlines()):d.text((35,20+j*112),line,font=load_font(67 if j==0 else 54),fill=(34,50,40))
        return im
    def clock_image(self):
        im=Image.new('RGB',(800,800),(223,216,190));d=ImageDraw.Draw(im);d.ellipse((20,20,780,780),fill=(231,225,204),outline=(43,53,49),width=12)
        for j in range(60):
            a=math.radians(j*6-90);r=336 if j%5 else 318
            d.line((400+r*math.cos(a),400+r*math.sin(a),400+357*math.cos(a),400+357*math.sin(a)),fill=(50,57,49),width=6 if j%5 else 10)
        for number in range(1,13):
            a=math.radians(number*30-90);d.text((400+277*math.cos(a),400+277*math.sin(a)),str(number),font=load_font(63),fill=(36,46,43),anchor='mm')
        for angle,length,width in [(4.75*30-90,180,20),(45*6-90,286,13)]:
            a=math.radians(angle);d.line((400,400,400+length*math.cos(a),400+length*math.sin(a)),fill=(32,45,43),width=width)
        d.ellipse((382,382,418,418),fill=(131,83,45));return im
    def build(self,g):
        self.room_shell('pantry_room',size=(4.5,5),openings={'east':[(.62,1.72)]})
        self.box('continuous_subfloor',[2.25,2.5,-.075],[4.64,5.14,.10],'darkwood',bevel=.001)
        self.box('matte_tile_floor',[2.25,2.5,.006],[4.5,5,.012],'pantry_tile',bevel=.001)
        for x in np.arange(.5,4.5,.5):self.box('tile_grout',[float(x),2.5,.0125],[.005,5,.001],'tile_joint',bevel=.0001)
        for y in np.arange(.5,5,.5):self.box('tile_grout',[2.25,float(y),.0125],[4.5,.005,.001],'tile_joint',bevel=.0001)
        self.table('weighing_bench',(2.85,4.58),(2.30,.65),height=.72)
        self.scale=self.group('kitchen_scale',[3.30,4.53,.79]);self.box('scale_body',[0,0,.018],[.48,.34,.10],'pantry_enamel',self.scale,bevel=.015)
        self.cylinder('pan_support',[0,0,.105],.028,.09,'steel','z',self.scale)
        self.pan=self.group('scale_tray_target',[0,0,.16],self.scale);self.box('tray_bottom',[0,0,0],[.31,.25,.019],'steel',self.pan)
        for x in [-.155,.155]:self.box('tray_side',[x,0,.02],[.009,.26,.05],'steel',self.pan,bevel=.002)
        for y in [-.125,.125]:self.box('tray_rim',[0,y,.02],[.31,.009,.05],'steel',self.pan,bevel=.002)
        self.text('tray_weight',self.pan,[0,-.133,.020],.25,.045,'TRAY 20 g',bg=(218,213,192),ink=(36,47,41))
        self.reg_at('s1_setup',self.pan,'scale tray',[3.25,3.5],[3.30,4.53,.96])
        self.box('scale_lcd_bezel',[0,-.177,.018],[.33,.017,.082],'iron',self.scale)
        self.scale_empty=self.text('scale_20',self.scale,[0,-.188,.019],.30,.064,'20 g')
        self.scale_loaded=self.text('scale_180',self.scale,[0,-.189,.019],.30,.064,'180 g')
        self.reg_at('s1_clue',self.scale_loaded,'scale display',[3.25,3.5],[3.3,4.53,.90])
        self.sample=self.tin('plain_food_tin',None,[2.15,4.53,.85]);self.reg_at('s1_tool',self.sample,'plain food tin',[2.25,3.5],[2.15,4.53,.88])
        self.carddrawer,face=self.drawer('card_drawer',None,(2.80,4.25),.54,width=1.14,depth=.43)
        self.reg_at('s2_cover',face,'food card drawer',[2.75,3.25],[2.80,4.25,.54])
        self.box('ingredient_card_insert',[0,.20,-.0185],[1.05,.36,.165],'wood',self.carddrawer,bevel=.002)
        self.lock('s1_lock',face,[.30,-.040,0],'NET g',[3.25,3.5])
        self.box('packing_list_paper',[2.62,4.55,.763],[.60,.29,.006],'card_cream')
        note=self.flat('packing_list_print',None,[2.62,4.55,.767],.59,.28,self.packing_list_image(),True)
        self.reg_at('s2_clue',note,'picnic packing list',[2.75,3.5],[2.62,4.55,.77])
        for j,item in enumerate(SPEC['stages'][1]['items']):
            n=self.group('food_picture_card_'+str(j));self.box('card_stock',[0,0,0],[.185,.012,.26],'card_cream',n,bevel=.002)
            self.flat('card_picture_'+str(j),n,[0,-.0065,0],.181,.256,self.ingredient_card_image(item))
            self.reg_at('s2_item_'+str(j),n,LABELS['s2_item_'+str(j)],[2.75,3.25],[2.80+(j-2)*.20,4.03,.610]);self.cards.append(n)
        self.rack=self.group('food_stock_cabinet',[.26,2.70,0]);self.transform(self.rack,rpy=[0,0,90])
        for x in [-.91,.91]:self.box('cabinet_side',[x,0,.40],[.04,.49,.70],'wood',self.rack)
        self.box('cabinet_back',[0,.22,.40],[1.84,.03,.70],'paint',self.rack)
        self.box('cabinet_base',[0,0,.08],[1.87,.52,.055],'darkwood',self.rack)
        self.box('cabinet_counter',[0,0,.74],[1.94,.57,.06],'wood',self.rack)
        self.add_obstacle(.05,1.73,.57,3.67)
        classes=['LUNCH','LUNCH','LUNCH','LUNCH'];centres=[-.69,-.23,.23,.69]
        label_group=self.group('category_labels',parent=self.rack)
        for j,x in enumerate(centres):
            basket=self.group('food_basket_'+str(j),[x,0,.79],self.rack)
            self.box('basket_floor',[0,0,0],[.40,.41,.025],'basket_lining',basket)
            for xx in [-.20,.20]:self.box('basket_side',[xx,0,.14],[.018,.42,.28],'wood',basket)
            self.box('basket_front',[0,-.205,.14],[.40,.02,.28],'wood',basket);self.box('basket_rear',[0,.205,.14],[.40,.02,.28],'wood',basket)
            for z in [.045,.12,.20]:self.box('basket_weave_strip',[0,-.218,z],[.395,.005,.012],'basket_lining',basket,bevel=.002)
            slot=self.group('category_card_holder_'+str(j),[x,-.242,.94],self.rack)
            self.box('card_holder_back',[0,0,0],[.263,.014,.29],'darkwood',slot,bevel=.003)
            for xx in [-.13,.13]:self.box('card_holder_edge',[xx,-.013,0],[.012,.021,.285],'brass',slot,bevel=.002)
            self.box('card_holder_lower_edge',[0,-.013,-.143],[.264,.021,.012],'brass',slot,bevel=.002)
            world=[.26+.262,2.70+x,.94];self.slot_positions.append(world)
            self.reg_at('s2_slot_'+str(j),slot,LABELS['s2_slot_'+str(j)],[1.5,round((2.70+x)*4)/4],world)
        self.box('lunch_case_label',[0,-.273,.66],[.48,.02,.10],'wood',self.rack)
        self.text('lunch_case_ink',self.rack,[0,-.286,.66],.44,.075,'LUNCH',bg=(214,207,183),ink=(37,49,42))
        self.check=self.group('stock_check',[-.35,-.287,.66],self.rack);self.box('check_body',[0,0,0],[.12,.035,.085],'iron',self.check)
        self.text('check_ink',self.check,[0,-.020,0],.108,.068,'CHECK',bg=(203,205,180),ink=(31,48,39));self.reg_at('s2_confirm',self.check,'stock check button',[1.5,2.75],[.55,2.70,.66])
        self.red=self.cylinder('stock_check_red',[-.49,-.31,.66],.014,.008,'red_led','y',self.rack,n=24)
        self.green=self.cylinder('stock_check_green',[-.49,-.31,.66],.014,.008,'green','y',self.rack,n=24)
        self.clockdrawer,clockfront=self.drawer('clock_drawer',self.rack,(0,-.28),.44,width=1.52,depth=.40)
        self.reg_at('s3_cover',clockfront,'clock drawer',[1.5,2.75],[.56,2.70,.46])
        self.box('clock_support_plinth',[0,.20,-.021],[1.17,.35,.158],'wood',self.clockdrawer)
        self.packing_bolt=self.group('local_packing_drawer_bolt',[.78,-.315,.56],self.rack)
        self.box('drawer_bolt',[0,0,0],[.26,.025,.025],'brass',self.packing_bolt)
        self.box('bolt_guide',[.78,-.29,.56],[.045,.04,.10],'iron',self.rack)
        self.clock=self.group('stored_kitchen_clock',[0,.20,.072],self.clockdrawer)
        self.cylinder('clock_metal_rim',[0,0,0],.153,.026,'steel','z',self.clock,n=48)
        clockface=self.flat('clock_face',self.clock,[0,0,.014],.282,.282,self.clock_image(),True)
        self.reg_at('s3_clue',clockface,'clock face',[1.5,2.75],[.76,2.70,.526])
        self.text('clock_period',self.clockdrawer,[-.39,.20,.059],.19,.10,'PM',bg=(218,211,183),ink=(33,48,41),horizontal=True)
        self.text('clock_format',self.clockdrawer,[.40,.20,.059],.24,.10,'24h',bg=(218,211,183),ink=(33,48,41),horizontal=True)
        self.table('recipe_box_stand',(3.0,.38),(1.20,.60),height=.61)
        self.recipe=self.group('wooden_recipe_box',[3.0,.38,.67]);self.transform(self.recipe,rpy=[0,0,180])
        self.box('box_floor',[0,0,0],[.80,.45,.025],'darkwood',self.recipe);self.box('box_felt',[0,0,.018],[.74,.39,.01],'card_cream',self.recipe)
        for x in [-.40,.40]:self.box('box_side',[x,0,.066],[.025,.45,.13],'wood',self.recipe)
        for y in [-.22,.22]:self.box('box_front_back',[0,y,.066],[.80,.025,.13],'wood',self.recipe)
        self.key_lid=self.group('recipe_box_hinge',[0,.22,.138],self.recipe)
        lid=self.group('recipe_box_lid',parent=self.key_lid);self.box('recipe_lid_wood',[0,-.22,0],[.84,.48,.026],'wood',lid);self.box('lid_pull',[0,-.475,0],[.15,.035,.03],'brass',lid)
        self.reg_at('key_box',lid,'recipe box lid',[3.0,1.25],[3.0,.38,.81]);self.lock('s3_lock',self.recipe,[0,-.245,.067],'24h / HHMM',[3.0,1.25])
        self.key=self.tool('flat_brass_key',self.recipe,[0,0,.034],'key');self.target_nodes.pop('flat_brass_key',None);self.transform(self.key,rpy=[90,0,0]);self.reg_at('key',self.key,'brass door key',[3.0,1.25],[3.0,.38,.704])
        shelf=self.group('dry_goods_shelf',[.95,.25,0]);self.transform(shelf,rpy=[0,0,180])
        for x in [-.64,.64]:self.box('shelf_upright',[x,0,.69],[.055,.36,1.38],'darkwood',shelf)
        for z in [.14,.72,1.29]:self.box('shelf_board',[0,0,z],[1.34,.40,.04],'wood',shelf)
        self.box('shelf_back',[0,.16,.69],[1.26,.035,1.34],'paint',shelf)
        for j in range(4):self.box('sealed_flour_bag',[-.45+j*.30,0,.88],[.23,.27,.27],'sack',shelf,bevel=.018)
        for j in range(3):self.tin('sealed_food_can_'+str(j),shelf,[-.36+j*.36,0,1.40])
        self.add_obstacle(.25,.05,1.65,.49)
        self.mat('pantry_window',(.51,.62,.60),rough=.9,emission=(.12,.16,.15))
        self.box('window_glass',[4.425,3.50,1.72],[.023,.74,.70],'pantry_window')
        for y in [3.10,3.90]:self.box('window_jamb',[4.40,y,1.72],[.065,.035,.77],'darkwood')
        for z in [1.34,1.72,2.10]:self.box('window_rail',[4.40,3.5,z],[.065,.83,.035],'darkwood')
        self.box('spoon_pegboard',[3.72,4.90,1.60],[.55,.045,.32],'wood')
        for j in range(3):
            x=3.56+j*.16;self.tube('wooden_spoon_handle',[x,4.85,1.68],[x,4.85,1.49],.008,'darkwood');self.cylinder('spoon_bowl',[x,4.85,1.45],.033,.014,'wood','y',n=24)
        self.exit_node=self.door('pantry_exit',[4.44,.65,0],1.04);self.door_angle=90;self.reg_at('exit',self.exit_node,'exit door',[3.75,1.25],[4.44,1.17,1.12]);self.door_view=[3.75,1.25]
        for y in [.63,1.71]:self.box('door_frame',[4.45,y,1.14],[.17,.065,2.30],'paint')
        self.box('door_top_frame',[4.45,1.17,2.29],[.17,1.15,.065],'paint')
        for y in [.64,1.70]:self.box('door_stop_jamb',[4.49,y,1.14],[.026,.035,2.28],'darkwood')
        self.box('door_stop_top',[4.49,1.17,2.28],[.026,1.13,.035],'darkwood')
        self.stage_views=[[3.25,3.5],[1.5,2.75],[3.0,1.25]];self.stage_centres=[[3.3,4.53,.94],[.52,2.7,1.0],[3,.38,.75]]
        self.bases=[([3.3,4.53],0),([.26,2.7],90),([3,.38],180)]
        self.sync(g)
    def visible(self,key,g):
        if key=='s1_tool':return 's1_tool' not in g.holding
        if key.startswith('s2_item_'):
            j=int(key.rsplit('_',1)[1]);placed=j in _assignment(g.states[1]).values()
            return key not in g.holding and (placed or g.opened['s2_cover'] and key not in g.taken)
        if key=='s3_clue':return bool(g.opened['s3_cover'])
        if key=='key':return bool(g.opened['key_box']) and key not in g.taken
        return key in self.target_nodes
    def sync(self,g):
        for key,shader in self.lock_screens.items():
            value=g.states[0 if key=='s1_lock' else 2].get('entered_code','0000')
            if self.lock_values[key]!=value:
                im=Image.new('RGB',(1000,240),(49,68,55));d=ImageDraw.Draw(im);size=160
                while size>12 and d.textbbox((0,0),value,font=load_font(size))[2]>940:size-=8
                d.text((500,120),value,font=load_font(size),fill=(222,227,190),anchor='mm');p=self.tex/(key+'_entered_'+hashlib.sha256(value.encode()).hexdigest()[:12]+'.png');im.save(p)
                with self.og.sim.editing_usd():shader.GetInput('file').Set(str(p))
                self.lock_values[key]=value
        placed_tin=bool(g.states[0]['setup_used']);self.visibility(self.sample,'s1_tool' not in g.holding)
        self.transform(self.sample,[3.30,4.53,1.047] if placed_tin else [2.15,4.53,.85])
        self.visibility(self.scale_empty,not placed_tin);self.visibility(self.scale_loaded,placed_tin)
        for key,opened in [('card_drawer',g.opened['s2_cover']),('clock_drawer',g.opened['s3_cover'])]:
            n,p=self.drawers[key];self.transform(n,[p[0],p[1]-(.42 if opened else 0),p[2]])
        assignments=_assignment(g.states[1])
        for j,n in enumerate(self.cards):
            slot=next((k for k,v in assignments.items() if v==j),None)
            if slot is not None:self.transform(n,self.slot_positions[slot],[0,0,90])
            else:self.transform(n,[2.80+(j-2)*.20,4.45-(.42 if g.opened['s2_cover'] else 0),.610],[-90,0,0])
            self.visibility(n,'s2_item_'+str(j) not in g.holding)
        self.visibility(self.red,not g.solved[1]);self.visibility(self.green,g.solved[1])
        self.transform(self.packing_bolt,[.78+(.13 if g.solved[1] else 0),-.315,.56])
        self.transform(self.key_lid,rpy=[-105 if g.opened['key_box'] else 0,0,0]);self.visibility(self.key,'key' not in g.taken)
        self.transform(self.exit_node,rpy=[0,0,90-(103 if g.opened['exit'] else 0)])
        self.expanded=[]
        for key,flag in [('card_drawer',g.opened['s2_cover']),('clock_drawer',g.opened['s3_cover'])]:
            if flag:
                points=self.triangles(self.drawers[key][0]).reshape(-1,3);self.expanded.append((points.min(0)[:2]-.12,points.max(0)[:2]+.12))
        self.centres={}
        for key,n in self.target_nodes.items():
            points=self.triangles(n).reshape(-1,3)
            if points.size:self.centres[key]=((points.min(0)+points.max(0))/2).tolist()
    def candidates(self,g):return self.base_candidates([k for k in self.target_nodes if self.visible(k,g)])
    def blocked(self,x,y,g):return super().blocked(x,y,g) or any(lo[0]<x<hi[0] and lo[1]<y<hi[1] for lo,hi in self.expanded)
    def view_for(self,key):return self.views.get(key,[3.25,1.25])
    def focus_for(self,key):return self.focus.get(key,self.centres.get(key))
    def label_for(self,key):return self.labels.get(key,LABELS.get(key,key.replace('_',' ')))
    def animate(self,d,before):
        old=before.get('opened',{})
        for key,name in [('s2_cover','card_drawer'),('s3_cover','clock_drawer')]:
            if bool(old.get(key))!=bool(d.game.opened[key]):
                n,p=self.drawers[name]
                for t in [.33,.67]:
                    q=float(bool(old.get(key)))+(float(bool(d.game.opened[key]))-float(bool(old.get(key))))*t
                    self.sync(d.game);self.transform(n,[p[0],p[1]-.42*q,p[2]])
                    if name=='card_drawer':
                        for j,card in enumerate(self.cards):
                            if j not in _assignment(d.game.states[1]).values() and 's2_item_'+str(j) not in d.game.holding:self.transform(card,[2.80+(j-2)*.20,4.45-.42*q,.610],[-90,0,0])
                    d.frame(warm=4);d.append('Drawer opening',4)
        if bool(old.get('key_box'))!=bool(d.game.opened['key_box']):
            for t in [.33,.67]:
                q=float(bool(old.get('key_box')))+(float(bool(d.game.opened['key_box']))-float(bool(old.get('key_box'))))*t
                self.sync(d.game);self.transform(self.key_lid,rpy=[-105*q,0,0]);d.frame(warm=4);d.append('Box opening',4)
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

    approach('s1_tool','Approach the food sample on the weighing bench');click('s1_tool','take')
    approach('s1_setup','Place the food sample on the real scale tray');click('s1_setup','use','s1_tool')
    observe('s1_clue','Observe180g on the scale and20g on its tray',stay=True)
    observe('s1_lock','Read the NET g requirement beside the drawer code input')
    click('s1_lock','unlock',code='0160')
    approach('s2_cover','Look into the unlocked ingredient-card drawer');click('s2_cover','open')
    observe('s2_clue','Read the packing list on the same workbench');click('s2_clue','read')
    observe('s2_item_2','Look down into the supported ingredient cards and their complete printed labels')
    for j in range(5):click('s2_item_'+str(j),'read')
    for j in [0,3,2]:click('s2_item_'+str(j),'take')
    for slot,item in [(0,0),(1,3),(2,2)]:
        approach('s2_slot_'+str(slot),'Pack a complete meal without cooking or repeating ingredients');click('s2_slot_'+str(slot),'use','s2_item_'+str(item))
    approach('s2_confirm','Release the same cabinet drawer by checking the complete meal');click('s2_confirm')
    approach('s3_cover','Open the unlocked clock drawer',stay=True);click('s3_cover','open')
    observe('s3_clue','Observe the actual clock hands andPM marking in the drawer',stay=True)
    approach('s3_lock','Walk to the recipe box and its24-hour time lock');click('s3_lock','unlock',code='1645')
    click('key_box','open');d.append('Observe the flat key inside the shallow box',18);click('key','take')
    approach('exit','Return to the exit door');click('exit','use','key');click('exit','open')
    if not exit_test(d.pos,g):raise RuntimeError('Open-door success was not reached')


def cpu_check():
    from easy88_core import stage_actions
    import itertools
    g=Game();checks=[]
    def act(kind,key,**kw):return g.act(dict(action=kind,_hit364=key,_validated364=True,**kw))
    assert not act('take','s2_item_0')['ok'];checks.append('closed source drawer blocks card take')
    assert not act('read','s2_item_0')['ok'];checks.append('closed source drawer blocks card read')
    for kind,key,extra in stage_actions(g,0):assert act(kind,key,**extra)['ok'],(kind,key)
    assert act('open','s2_cover')['ok'];assert act('read','s2_clue')['text']==SPEC['stages'][1]['clue_text']
    for j in range(5):assert act('read','s2_item_'+str(j))['ok']
    checks.append('all cooking/category/ingredient facts printed and readable, no answer text')
    valid=[]
    for combination in itertools.combinations(range(5),3):
        h=Game();h.states[1]['assignment']={j:v for j,v in enumerate(combination)}
        if h._check(1):valid.append(combination)
    assert valid==[(0,2,3)];checks.append('set constraints derive exactly apple water crackers from five cards')
    for perm in itertools.permutations([0,2,3]):
        for slots in itertools.combinations(range(4),3):
            h=Game();h.states[1]['assignment']=dict(zip(slots,perm));assert h._check(1)
    checks.append('all24 order/pocket-equivalent valid packings accepted')
    h=Game();h.states[1]['assignment']={0:0,1:1,2:2};assert not h._check(1);checks.append('uncooked rice rejected')
    h.states[1]['assignment']={0:0,1:3,2:4};assert not h._check(1);checks.append('apple and apple juice conflict by repeated ingredient')
    h.SPEC=__import__('copy').deepcopy(h.SPEC);h.SPEC['stages'][1]['items'][4]['ingredients']=['ORANGE'];assert h._check(1);checks.append('checker uses visible properties, not a secret allowed item set')
    for j in [0,3,2]:assert act('take','s2_item_'+str(j))['ok']
    for slot,item in [(3,0),(0,3),(2,2)]:assert act('use','s2_slot_'+str(slot),item='s2_item_'+str(item))['ok']
    assert act('take','s2_item_3')['ok'];assert act('use','s2_slot_1',item='s2_item_3')['ok'];checks.append('misplaced cards can be removed and repacked')
    assert act('press','s2_confirm')['ok'];assert g.solved[1] and not g.opened['s3_cover'];checks.append('complete meal releases local drawer without auto-opening')
    for kind,key,extra in stage_actions(g,2):assert act(kind,key,**extra)['ok'],(kind,key)
    assert act('open','key_box')['ok'];assert act('take','key')['ok'];assert act('use','exit',item='key')['ok'];assert act('open','exit')['ok'];checks.append('full public-action key/use/open chain succeeds')
    assert abs((.54-.0185+.165/2)+.012/2-.610)<1e-9
    assert .610+.012/2 < .54+.1275-.025/2
    eye_y,eye_z=3.25,1.35
    near_y=4.45-.42-.26/2
    line_z=eye_z+(.610+.006-eye_z)*(4.25-.42-eye_y)/(near_y-eye_y)
    assert line_z>.54+.25/2+.02
    checks.append('supported source cards clear original drawer front and closed housing; geometry only')
    return dict(level='R09',scope='CPU state/constraint fixture only, no native pixels',passed=len(checks),checks=checks)
