from easy88_core import make_level

SPEC = {'id': 'R14', 'title': 'R14 · Sports Equipment Room / 运动器材室', 'theme': 'sports', 'size': [5.5, 4.5], 'door': {'side': 'west', 'start': 0.75, 'width': 1.04}, 'start': [1.0, 1.25, 1.35], 'start_yaw': 0, 'floor': 'wood', 'stages': [{'kind': 'read_code', 'name': 'scoreboard locker', 'wall': 'north', 'centre': [2.0, 4.17], 'view': [2.0, 3.25], 'board_height': 0.98, 'visual': {'type': 'score_rows', 'rows': [[5, None, 7], [3, None, 8]], 'operator': '+', 'row_order': 'top_to_bottom'}, 'clue': {'type': 'score_rows', 'rows': [[5, None, 7], [3, None, 8]], 'operator': '+', 'row_order': 'top_to_bottom'}, 'clue_text': '', 'furniture_style': 'low_wall_cabinet', 'answer': '25', 'digits': 2, 'lock_label': '00 ↓', 'design_notes': 'Only the printed facts5+?=7 and3+?=8; read does not calculate2 or5.'}, {'kind': 'sequence', 'name': 'sports bag display', 'wall': 'east', 'centre': [5.17, 2.5], 'view': [4.25, 2.5], 'board_height': 0.98, 'visual': {'type': 'bag_select', 'items': ['blue_double', 'blue_single', 'red_double', 'red_single'], 'query': ['blue_double', 'red_single'], 'query_order': 'top_to_bottom'}, 'clue': {'type': 'bag_select', 'items': ['blue_double', 'blue_single', 'red_double', 'red_single'], 'query': ['blue_double', 'red_single'], 'query_order': 'top_to_bottom'}, 'clue_text': '', 'furniture_style': 'low_wall_cabinet', 'options': ['blue_double', 'blue_single', 'red_double', 'red_single'], 'option_names': ['blue bag with two stripes', 'blue bag with one stripe', 'red bag with two stripes', 'red bag with one stripe'], 'answer': [0, 3], 'length': 2, 'distinct': True, 'confirm': True, 'design_notes': 'Reference card and bags appear only after prior cover opens. Choose a pair in order then confirm; all4 selection keys work, extra inputs invalidate the whole attempt, no per-bag correct light. Bags themselves are fixed display props, not loot containers.'}, {'kind': 'count', 'name': 'medal ribbon cabinet', 'wall': 'south', 'centre': [3.0, 0.33], 'view': [3.0, 1.25], 'board_height': 0.98, 'visual': {'type': 'count', 'counts': [3, 1, 4], 'symbol': 'ribbon_dot', 'order': 'left_to_right', 'medals': 3}, 'clue': {'type': 'count', 'counts': [3, 1, 4], 'symbol': 'ribbon_dot', 'order': 'left_to_right', 'medals': 3}, 'clue_text': '', 'furniture_style': 'low_wall_cabinet', 'answer': '314', 'digits': 3, 'lock_label': '000 →', 'design_notes': 'Count the actual dots on the3 fixed ribbons; no printed314 candidate answer.'}], 'decor': [{'kind': 'rackets', 'wall': 'south'}, {'kind': 'sports_balls', 'wall': 'east'}, {'kind': 'cones', 'wall': 'north'}, {'kind': 'folded_jersey', 'wall': 'west'}], 'design_notes': 'West side door, north scoreboard, east4-bag rack, south medal cabinet. Only2 arithmetic rows, the ordered pair and3-ribbon count are counted as the3 puzzles.'}


SPEC['stages'][1].update(kind='adjust',name='mechanical cabinet bolt',initial=[0,1,1],target=[2,0,2],moduli=[3,3,3],auto=False,
 visual={'type':'physical_sliding_bolt','grid':[4,4]},clue={'type':'collision_clearance','bolt_row':1,'exit':'right'},clue_text='',
 design_notes='Three reversible runners share a real4x4 clearance grid. The horizontal bolt opens only when its entire exit row is clear. No reference picture prints target coordinates.')
for field in ['options','option_names','answer','length','distinct']:SPEC['stages'][1].pop(field,None)
SPEC['design_notes']='Protective-cover score clue, reversible geometric bolt clearance, local handle drawer, square-peg handle fitted to medal cupboard, then ribbon count and exit key. No ordered bag selector or remote flag-only cupboard release.'
Game,_OriginalScene,_OriginalStandard,exit_test,cpu_check=make_level(SPEC)
TITLE=SPEC['title'];LEVEL_ID=SPEC['id'];START=SPEC['start'];START_YAW=SPEC['start_yaw']
CAP=150;OBSERVATION_SIZE=(640,360);VISUAL_ONLY=False;READ_ENABLED=True;READ_FEEDBACK_TEXT=True
Game.LABELS.update({'s1_clue':'two scoreboard rows','s1_lock':'bolt cabinet cover code lock','s2_cover':'bolt cabinet protective cover',
 's2_clue':'sliding bolt clearance board','s2_confirm':'sliding cabinet bolt','s2_reset':'unused reset site',
 's3_cover':'medal cupboard door','s3_clue':'three medal ribbons','s3_lock':'medal drawer code lock','key_box':'key drawer','key':'brass door key'})
Game.LABELS.update({'s2_reward':'handle drawer below the bolt board','s3_tool':'removable T handle'})
for j in range(3):
 for direction in (['up','down'] if j!=1 else ['left','right']):Game.LABELS['s2_move_'+str(j)+'_'+direction]=direction+' arrow on '+(['left vertical runner','horizontal runner','right vertical runner'][j])
LABELS=Game.LABELS
_sports_init=Game.__init__
def _initialise_bolt(self):
    _sports_init(self);self.states[1].update(bar_out=False,reward_open=False);self.states[2]['handle_installed']=False
Game.__init__=_initialise_bolt

def runner_cells(positions,j):
    q=int(positions[j])
    return {(q,2),(q+1,2)} if j==0 else {(2,q),(2,q+1)} if j==1 else {(q,3),(q+1,3)}
def runners_valid(positions,bar_out=False):
    if len(positions)!=3 or any(int(q)!=q or not 0<=q<=2 for q in positions):return False
    occupied=set() if bar_out else {(1,0),(1,1)}
    for j in range(3):
        cells=runner_cells(positions,j)
        if occupied & cells:return False
        occupied.update(cells)
    return True
def bolt_path_clear(positions):
    return runners_valid(positions) and not any(r==1 and c>=2 for j in range(3) for r,c in runner_cells(positions,j))
_base_sports_check=Game._check
def _bolt_check(self,index):return bolt_path_clear(self.states[1]['angles']) if index==1 else _base_sports_check(self,index)
Game._check=_bolt_check
_original_act=Game.act
Game.stage_accessible=lambda self,index:0<=index<3
Game.stage_exposed=lambda self,index:0<=index<3 and bool(self.states[index]['setup_ready'])
def _sports_act(self,a):
    key=a.get('_hit364');kind=a.get('action')
    if a.get('_validated364') and key=='s2_reward':
        from action_feedback import failure_for
        if kind not in ('open','close') or kind=='open' and not self.solved[1]:return {'ok':False,'text':failure_for(kind)}
        self.states[1]['reward_open']=kind=='open';return {'ok':True,'text':''}
    if a.get('_validated364') and key=='s3_tool':
        from action_feedback import failure_for
        if kind!='take' or not self.states[1]['reward_open'] or key in self.taken:return {'ok':False,'text':failure_for(kind)}
        self.taken.add(key);self.holding.append(key);return {'ok':True,'text':''}
    if a.get('_validated364') and key=='s3_cover':
        from action_feedback import failure_for,NO_ITEM
        if kind=='use':
            item=self._resolve_item(a.get('item'))
            if item is None:return {'ok':False,'text':NO_ITEM}
            if item!='s3_tool':return {'ok':False,'text':failure_for(kind)}
            self.holding.remove(item);self.states[2]['handle_installed']=True;return {'ok':True,'text':''}
        if kind=='open' and not self.states[2]['handle_installed']:return {'ok':False,'text':failure_for(kind)}
    if a.get('_validated364') and str(key).startswith('s2_move_'):
        from action_feedback import failure_for
        if kind!='press' or not self.opened['s2_cover']:return {'ok':False,'text':failure_for(kind)}
        _,_,j,direction=key.split('_');j=int(j)
        legal={0:('up','down'),1:('left','right'),2:('up','down')}
        if j not in legal or direction not in legal[j]:return {'ok':False,'text':failure_for(kind)}
        positions=list(self.states[1]['angles']);positions[j]+= -1 if direction in ('up','left') else 1
        if not runners_valid(positions,self.states[1]['bar_out']):return {'ok':False,'text':failure_for(kind)}
        self.states[1]['angles']=positions;return {'ok':True,'text':''}
    if a.get('_validated364') and key=='s2_confirm':
        from action_feedback import failure_for
        if kind not in ('open','close') or not self.opened['s2_cover'] or not self._check(1):return {'ok':False,'text':failure_for(kind)}
        self.states[1]['bar_out']=kind=='open'
        if kind=='open':self.solved[1]=True
        return {'ok':True,'text':''}
    if a.get('_validated364') and (str(key).startswith(('s2_choice_','s2_control_')) or key=='s2_reset'):
        from action_feedback import failure_for
        return {'ok':False,'text':failure_for(kind)}
    result=_original_act(self,a)
    if a.get('_validated364') and kind=='unlock' and key in ('s1_lock','s3_lock'):self.states[0 if key=='s1_lock' else 2]['entered_code']=str(a.get('code',''))
    return result
Game.act=_sports_act
import math,hashlib
import numpy as np
from PIL import Image,ImageDraw
from easy88_scene import EasyScene
from font_utils import load_font

class Scene(EasyScene):
    def __init__(self,og,run):
        super().__init__(og,run,SPEC)
        self.views={};self.focus={};self.labels={};self.drawers={};self.lock_screens={};self.lock_values={};self.expanded=[];self.screen_signature=None
    def palette(self):
        super().palette()
        for name,c in [('bag_blue',(.10,.23,.37)),('bag_red',(.46,.13,.09)),('strap_white',(.77,.74,.62)),('sports_green',(.19,.31,.25)),('cloth_blue',(.20,.34,.40)),('medal_felt',(.19,.29,.26)),('ball_orange',(.65,.32,.11)),('mat_blue',(.14,.29,.40))]:self.mat(name,c,rough=.91)
    def reg_at(self,key,node,label,view,focus=None):
        self.reg(key,node);self.views[key]=list(view);self.labels[key]=label
        if focus is not None:self.focus[key]=list(focus)
        return node
    def flat(self,name,parent,pos,w,h,im,horizontal=False):
        path=self.tex/(name+'.png');im.save(path)
        return self.plane(name,pos,w,h,(1,0,0),(0,1,0) if horizontal else (0,0,1),None,parent,material=self.image_mat('r14_'+name,path))
    def text(self,name,parent,pos,w,h,value,bg=(216,209,184),ink=(35,54,43)):
        ih=360;iw=max(180,int(ih*w/h));im=Image.new('RGB',(iw,ih),bg);d=ImageDraw.Draw(im);size=int(ih*.70)
        while size>12:
            b=d.textbbox((0,0),str(value),font=load_font(size))
            if b[2]-b[0]<iw*.85 and b[3]-b[1]<ih*.80:break
            size-=8
        d.text((iw/2,ih/2),str(value),font=load_font(size),fill=ink,anchor='mm');return self.flat(name,parent,pos,w,h,im)
    def lock(self,key,parent,pos,digits,view):
        n=self.group(key,pos,parent);self.box('numeric_lock_bezel',[0,0,0],[.30,.038,.14],'iron',n)
        self.text(key+'_display',n,[0,-.021,0],.26,.095,'0'*digits,bg=(47,67,55),ink=(224,229,191))
        self.lock_screens[key]=self.S.Shader(self.stage.GetPrimAtPath(str(self.mats['r14_'+key+'_display'].GetPath())+'/texture'));self.lock_values[key]='0'*digits
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

    def sports_bag(self,j,x):
        blue=j<2;stripes=2 if j%2==0 else 1;n=self.group('fixed_sports_bag_'+str(j),[x,-.025,.775],self.bagcase)
        self.box('soft_duffel_body',[0,0,.13],[.40,.25,.24],'bag_blue' if blue else 'bag_red',n,bevel=.042)
        for side in [-1,1]:
            self.tube('duffel_handle_side',[side*.075,0,.235],[side*.075,0,.33],.010,'iron',n)
        self.tube('duffel_handle_top',[-.075,0,.33],[.075,0,.33],.012,'iron',n)
        for k in range(stripes):self.box('woven_white_stripe',[(k-(stripes-1)/2)*.085,-.128,.13],[.026,.006,.195],'strap_white',n,bevel=.002)
        self.box('bag_zipper',[0,-.130,.223],[.32,.005,.008],'iron',n,bevel=.001)
        self.reg_at('fixed_bag_'+str(j),n,'fixed sports bag',[round((3.65+x)*4)/4,2.75]);return n
    def runner_position(self,j,positions):
        q=float(positions[j]);x=.15-.26+((2.5 if j==0 else q+1 if j==1 else 3.5)*.13)
        z=1.10+.26-((q+1 if j!=1 else 2.5)*.13)
        return [x,.150,z]
    def t_handle(self,name,parent,pos):
        node=self.group(name,pos,parent)
        self.cylinder('handle_shaft',[0,.01,0],.012,.12,'steel','y',node,n=20)
        self.cylinder('T_grip',[0,-.05,0],.016,.18,'steel','x',node,n=24)
        self.box('square_insertion_peg',[0,.083,0],[.025,.030,.025],'steel',node,bevel=.001)
        return node
    def build_bolt_board(self,g):
        self.runners=[]
        self.board=self.group('sliding_clearance_board',[.15,.20,1.10],self.bagcase)
        self.box('clearance_backing',[0,0,0],[.60,.040,.60],'sports_green',self.board)
        for j in range(5):
            q=(j-2)*.13
            self.box('horizontal_grid_recess',[0,-.021,q],[.52,.005,.006],'iron',self.board)
            self.box('vertical_grid_recess',[q,-.021,0],[.006,.005,.52],'iron',self.board)
        self.reg_at('s2_clue',self.board,'sliding bolt clearance board',[3.75,3.0],[3.80,4.25,1.10])
        for j in range(3):
            node=self.group('sliding_runner_'+str(j),self.runner_position(j,g.states[1]['angles']),self.bagcase)
            self.box('runner_body',[0,0,0],[.244,.032,.114] if j==1 else [.114,.032,.244],['bag_blue','sports_green','bag_red'][j],node,bevel=.006)
            self.cylinder('runner_carriage_pin',[0,.024,0],.018,.030,'steel','y',node,n=20)
            for direction,sign in ((('left',-1),('right',1)) if j==1 else (('up',1),('down',-1))):
                pos=[sign*.080,-.022,0] if j==1 else [0,-.022,sign*.080]
                arrow=self.group('runner_arrow_'+str(j)+'_'+direction,pos,node)
                self.box('arrow_cap',[0,0,0],[.063,.012,.063],'iron',arrow,bevel=.003)
                self.text('arrow_print',arrow,[0,-.007,0],.053,.053,{'left':'←','right':'→','up':'↑','down':'↓'}[direction])
                self.reg_at('s2_move_'+str(j)+'_'+direction,arrow,LABELS['s2_move_'+str(j)+'_'+direction],[3.75,3.0],[3.80,4.25,1.10])
            self.runners.append(node)
        self.bolt=self.group('sliding_latch_bolt',[.02,.145,1.165],self.bagcase)
        self.box('sliding_steel_bar',[0,0,0],[.244,.032,.087],'steel',self.bolt,bevel=.003)
        self.cylinder('bolt_pull_knob',[-.065,-.030,0],.027,.040,'brass','y',self.bolt,n=24)
        self.text('bolt_arrow',self.bolt,[.065,-.018,0],.055,.055,'→')
        self.reg_at('s2_confirm',self.bolt,'sliding cabinet bolt',[3.75,3.0],[3.80,4.25,1.10])
        for x in [-.075,.13,.50]:
            for z in [1.110,1.220]:self.box('bolt_guide_lip',[x,.159,z],[.08,.055,.014],'iron',self.bagcase)
            self.box('bolt_guide_back',[x,.183,1.165],[.08,.012,.11],'iron',self.bagcase)
        self.text('exit_arrow',self.bagcase,[.65,.234,1.165],.11,.09,'→')
        self.handledrawer,face=self.drawer('bolt_handle_drawer',None,(3.65,3.825),.54,width=1.10,depth=.44)
        self.reg_at('s2_reward',face,LABELS['s2_reward'],[3.75,3.0],[3.65,3.825,.54])
        self.box('handle_lining',[0,.21,-.021],[.94,.34,.158],'medal_felt',self.handledrawer)
        self.loose_handle=self.t_handle('removable_T_handle',self.handledrawer,[0,.21,.075]);self.reg_at('s3_tool',self.loose_handle,LABELS['s3_tool'],[3.75,3.0],[3.65,3.615,.61])
        self.reward_red=self.cylinder('handle_drawer_red',[.43,-.027,.025],.014,.010,'red_led','y',face,n=20)
        self.reward_green=self.cylinder('handle_drawer_green',[.43,-.027,.025],.014,.010,'green','y',face,n=20)
    def rounded_ball(self,parent,pos):
        n=self.group('basketball_'+str(self.count),pos,parent);pts=[[0,0,-.13],[0,0,.13]];faces=[];count=24;rings=9
        for j in range(1,rings+1):
            p=-math.pi/2+math.pi*j/(rings+1)
            for k in range(count):
                a=k*2*math.pi/count;pts.append([.13*math.cos(p)*math.cos(a),.13*math.cos(p)*math.sin(a),.13*math.sin(p)])
        for k in range(count):
            q=(k+1)%count;faces.extend([[0,2+q,2+k],[1,2+(rings-1)*count+k,2+(rings-1)*count+q]])
        for j in range(rings-1):
            for k in range(count):
                q=(k+1)%count;faces.append([2+j*count+k,2+j*count+q,2+(j+1)*count+q,2+(j+1)*count+k])
        self.mesh('orange_ball',pts,faces,'ball_orange',n)
        for plane in [0,1]:
            points=[]
            for a in np.linspace(0,2*math.pi,37):points.append([.131*math.cos(a),0,.131*math.sin(a)] if plane==0 else [0,.131*math.cos(a),.131*math.sin(a)])
            for a,b in zip(points,points[1:]):self.tube('ball_seam',a,b,.0025,'iron',n)
    def build(self,g):
        self.room_shell('sports_equipment_room',size=(5.5,4.5),openings={'west':[(.72,1.82)]});self.box('solid_subfloor',[2.75,2.25,-.075],[5.64,4.64,.10],'darkwood',bevel=.001)
        self.table('shared_equipment_cabinet',(2.75,4.15),(4.50,.65),height=.72)
        for y in [3.94,4.36]:self.box('middle_cabinet_support',[2.75,y,.36],[.075,.075,.72],'iron')
        self.bagcase=self.group('scoreboard_and_bag_compartment',[3.65,4.15,0])
        for x in [-1.13,1.13]:self.box('bag_compartment_side',[x,0,1.10],[.035,.57,.69],'wood',self.bagcase)
        self.box('bag_compartment_back',[0,.25,1.10],[2.28,.03,.69],'paint',self.bagcase);self.box('bag_compartment_floor',[0,0,.77],[2.30,.56,.03],'wood',self.bagcase);self.box('bag_compartment_top',[0,0,1.46],[2.32,.59,.035],'wood',self.bagcase)
        self.bag_cover=self.group('scoreboard_cover_hinge',[0,-.35,1.46],self.bagcase)
        cover=self.group('scoreboard_cover_face',parent=self.bag_cover);self.box('bag_protection_cover',[0,0,-.365],[2.32,.040,.73],'paint',cover)
        image=Image.new('RGB',(1200,520),(219,214,188));dr=ImageDraw.Draw(image)
        for j,(first,last) in enumerate([(5,7),(3,8)]):
            y=135+j*250;dr.text((230,y),str(first),font=load_font(162),fill=(33,50,42),anchor='mm');dr.text((430,y),'+',font=load_font(146),fill=(33,50,42),anchor='mm');dr.rectangle((550,y-83,695,y+83),outline=(61,77,59),width=7);dr.text((825,y),'=',font=load_font(146),fill=(33,50,42),anchor='mm');dr.text((1035,y),str(last),font=load_font(162),fill=(33,50,42),anchor='mm')
        facts=self.flat('scoreboard_facts',cover,[0,-.022,-.31],1.10,.39,image);self.reg_at('s1_clue',facts,'two scoreboard rows',[3.75,2.75],[3.65,3.78,1.15])
        self.text('score_order_arrow',cover,[.68,-.022,-.31],.10,.23,'↓')
        self.lock('s1_lock',cover,[0,-.044,-.62],2,[3.75,2.75]);self.reg_at('s2_cover',cover,'bolt cabinet protective cover',[3.75,2.75],[3.65,3.80,1.08])
        self.build_bolt_board(g)
        self.sports_bag(0,-.76)
        self.medals=self.group('medal_cupboard',[1.40,4.15,0])
        for x in [-.56,.56]:self.box('medal_case_side',[x,-.03,1.03],[.03,.53,.58],'wood',self.medals)
        self.box('medal_case_back',[0,.22,1.03],[1.15,.03,.58],'wood',self.medals);self.box('medal_case_top',[0,-.03,1.33],[1.18,.56,.035],'wood',self.medals);self.box('medal_case_floor',[0,-.03,.745],[1.15,.53,.025],'wood',self.medals)
        self.box('medal_dark_backing',[0,.19,1.03],[1.09,.025,.52],'medal_felt',self.medals)
        self.ribbon_group=self.group('three_fixed_medals',parent=self.medals)
        for j,count in enumerate([3,1,4]):
            x=(j-1)*.32;self.box('award_ribbon',[x,.165,1.055],[.115,.016,.27],'cloth_blue' if j!=1 else 'bag_red',self.ribbon_group,bevel=.002)
            for k in range(count):self.cylinder('ribbon_count_dot',[x,.155,1.055+(k-(count-1)/2)*.050],.013,.003,'strap_white','y',self.ribbon_group,n=24)
            self.tube('medal_connector',[x,.16,.925],[x,.16,.88],.008,'brass',self.ribbon_group);self.cylinder('fixed_award_medal',[x,.16,.84],.074,.014,'brass','y',self.ribbon_group,n=40);self.cylinder('medal_inner_disc',[x,.151,.84],.054,.005,'key_gold','y',self.ribbon_group,n=32)
        self.reg_at('s3_clue',self.ribbon_group,'three medal ribbons',[1.5,3.0],[1.4,4.305,1.04])
        self.medal_door=self.group('medal_door_hinge',[-.575,-.33,.765],self.medals)
        door=self.group('medal_door_leaf',parent=self.medal_door);self.box('medal_door',[.575,0,.28],[1.15,.035,.56],'paint',door)
        self.box('handle_socket_bezel',[1.05,-.022,.28],[.068,.012,.068],'steel',door)
        self.box('empty_square_socket',[1.05,-.030,.28],[.030,.008,.030],'iron',door)
        self.installed_handle=self.t_handle('installed_T_handle',door,[1.05,-.09,.28])
        self.reg_at('s3_cover',door,'medal cupboard door',[1.5,3.0],[1.4,3.80,1.05])
        self.medal_red=self.cylinder('medal_latch_red',[1.04,-.021,.48],.015,.009,'red_led','y',door,n=24);self.medal_green=self.cylinder('medal_latch_green',[1.04,-.021,.48],.015,.009,'green','y',door,n=24)
        self.keydrawer,keyfront=self.drawer('medal_key_drawer',None,(1.40,3.825),.54,width=1.08,depth=.44)
        self.reg_at('key_box',keyfront,'key drawer',[1.5,3.0],[1.4,3.825,.54]);self.lock('s3_lock',keyfront,[.28,-.043,0],3,[1.5,3.0])
        self.text('medal_count_arrow',keyfront,[0,-.027,0],.17,.070,'→')
        self.box('key_support_pad',[0,.21,-.021],[.85,.34,.158],'medal_felt',self.keydrawer)
        self.key=self.tool('flat_brass_key',self.keydrawer,[0,.21,.069],'key');self.target_nodes.pop('flat_brass_key',None);self.transform(self.key,rpy=[90,0,0]);self.reg_at('key',self.key,'brass door key',[1.5,3.0],[1.4,3.615,.609])
        balls=self.group('low_ball_rack',[4.50,.28,0])
        for x in [-.60,.60]:self.box('ball_rack_post',[x,0,.33],[.05,.40,.66],'darkwood',balls)
        self.box('ball_rack_shelf',[0,0,.18],[1.28,.42,.045],'wood',balls)
        for x in [-.28,.28]:self.rounded_ball(balls,[x,0,.333])
        self.add_obstacle(3.82,.04,5.18,.52)
        mats=self.group('rolled_training_mats',[1.17,.27,0]);self.box('mat_floor_cradle',[0,0,.025],[1.26,.39,.05],'wood',mats)
        for j in range(2):self.cylinder('rolled_exercise_mat',[0,(j-.5)*.18,.14],.090,1.10,'mat_blue' if j==0 else 'sports_green','x',mats,n=28)
        self.add_obstacle(.49,.04,1.85,.51)
        rack=self.group('racket_wall_mount',[5.39,2.31,0]);self.transform(rack,rpy=[0,0,-90]);self.box('racket_peg_rail',[0,0,1.42],[.90,.05,.10],'wood',rack)
        for j in range(2):
            x=(j-.5)*.42;points=[[x+.14*math.cos(a),-.045,1.58+.205*math.sin(a)] for a in np.linspace(0,2*math.pi,37)]
            for a,b in zip(points,points[1:]):self.tube('racket_oval_frame',a,b,.012,'steel',rack)
            self.tube('racket_shaft',[x,-.045,1.38],[x,-.045,1.16],.009,'steel',rack);self.tube('racket_grip',[x,-.045,1.18],[x,-.045,1.06],.018,'iron',rack)
            for z in np.linspace(1.43,1.73,6):
                w=.14*math.sqrt(max(0,1-((z-1.58)/.205)**2));self.tube('racket_string',[x-w,-.046,float(z)],[x+w,-.046,float(z)],.0012,'strap_white',rack)
        self.exit_node=self.door('sports_exit',[.06,1.79,0],1.04);self.door_angle=-90;self.reg_at('exit',self.exit_node,'exit door',[1.0,1.25],[.06,1.27,1.12]);self.door_view=[1.0,1.25]
        for y in [.73,1.81]:self.box('door_jamb',[.05,y,1.14],[.17,.065,2.30],'paint')
        self.box('door_lintel',[.05,1.27,2.29],[.17,1.15,.065],'paint')
        for y in [.74,1.80]:self.box('door_stop_jamb',[.01,y,1.14],[.026,.035,2.28],'darkwood')
        self.box('door_stop_top',[.01,1.27,2.28],[.026,1.13,.035],'darkwood')
        self.stage_views=[[3.75,2.75],[3.75,2.75],[1.5,3.0]];self.stage_centres=[[3.65,3.78,1.15],[3.65,4.0,1.14],[1.4,4.3,1.04]]
        self.bases=[([3.65,4.15],0),([3.65,4.15],0),([1.4,4.15],0)];self.sync(g)
    def visible(self,key,g):
        if key.startswith('fixed_bag_'):return bool(g.opened['s2_cover'])
        if key=='s2_reward':return True
        if key=='s3_tool':return bool(g.states[1]['reward_open']) and key not in g.taken
        if key=='s2_clue' or key.startswith('s2_move_') or key=='s2_confirm':return bool(g.opened['s2_cover'])
        if key=='s3_clue':return bool(g.opened['s3_cover'])
        if key=='key':return bool(g.opened['key_box']) and key not in g.taken
        return key in self.target_nodes
    def sync(self,g):
        self.transform(self.bag_cover,rpy=[-160 if g.opened['s2_cover'] else 0,0,0]);self.transform(self.medal_door,rpy=[0,0,-110 if g.opened['s3_cover'] else 0])
        for key,shader in self.lock_screens.items():
            value=g.states[0 if key=='s1_lock' else 2].get('entered_code','00' if key=='s1_lock' else '000')
            if value!=self.lock_values[key]:
                im=Image.new('RGB',(1000,300),(47,67,55));d=ImageDraw.Draw(im);size=190
                while size>12 and d.textbbox((0,0),value,font=load_font(size))[2]>930:size-=8
                d.text((500,150),value,font=load_font(size),fill=(224,229,191),anchor='mm');p=self.tex/(key+'_entered_'+hashlib.sha256(value.encode()).hexdigest()[:12]+'.png');im.save(p)
                with self.og.sim.editing_usd():shader.GetInput('file').Set(str(p))
                self.lock_values[key]=value
        for j,node in enumerate(self.runners):self.transform(node,self.runner_position(j,g.states[1]['angles']))
        self.transform(self.bolt,[.02+(.57 if g.states[1]['bar_out'] else 0),.145,1.165])
        n,p=self.drawers['bolt_handle_drawer'];self.transform(n,[p[0],p[1]-(.42 if g.states[1]['reward_open'] else 0),p[2]])
        self.visibility(self.loose_handle,'s3_tool' not in g.taken)
        self.visibility(self.installed_handle,g.states[2]['handle_installed'])
        self.visibility(self.reward_red,not g.solved[1]);self.visibility(self.reward_green,g.solved[1])
        self.visibility(self.medal_red,not g.states[2]['handle_installed']);self.visibility(self.medal_green,g.states[2]['handle_installed'])
        n,p=self.drawers['medal_key_drawer'];self.transform(n,[p[0],p[1]-(.42 if g.opened['key_box'] else 0),p[2]])
        self.visibility(self.key,'key' not in g.taken);self.transform(self.exit_node,rpy=[0,0,self.door_angle-(103 if g.opened['exit'] else 0)])
        self.expanded=[]
        for flag,node in [(g.opened['s2_cover'],self.bag_cover),(g.opened['s3_cover'],self.medal_door),(g.opened['key_box'],self.keydrawer),(g.states[1]['reward_open'],self.handledrawer)]:
            if flag:
                pts=self.triangles(node).reshape(-1,3);self.expanded.append((pts.min(0)[:2]-.12,pts.max(0)[:2]+.12))
        self.centres={}
        for key,node in self.target_nodes.items():
            pts=self.triangles(node).reshape(-1,3)
            if pts.size:self.centres[key]=((pts.min(0)+pts.max(0))/2).tolist()
    def candidates(self,g):return self.base_candidates([k for k in self.target_nodes if self.visible(k,g)])
    def blocked(self,x,y,g):return super().blocked(x,y,g) or any(lo[0]<x<hi[0] and lo[1]<y<hi[1] for lo,hi in self.expanded)
    def view_for(self,key):return self.views.get(key,[1.0,1.25])
    def focus_for(self,key):return self.focus.get(key,self.centres.get(key))
    def label_for(self,key):return self.labels.get(key,LABELS.get(key,key.replace('_',' ')))
    def animate(self,d,before):
        old=before.get('opened',{})
        for j,(a,b) in enumerate(zip(before['states'][1]['angles'],d.game.states[1]['angles'])):
            if a!=b:
                for q in [.33,.67]:
                    positions=list(d.game.states[1]['angles']);positions[j]=a+(b-a)*q;self.sync(d.game);self.transform(self.runners[j],self.runner_position(j,positions));d.frame(warm=4);d.append('Runner slides within its physical clearance',4)
        a=bool(before['states'][1].get('bar_out'));b=d.game.states[1]['bar_out']
        if a!=b:
            for q in [.33,.67]:
                self.sync(d.game);self.transform(self.bolt,[.02+.57*(float(a)+(float(b)-float(a))*q),.145,1.165]);d.frame(warm=4);d.append('The cleared bolt slides out and releases its own lower drawer',4)
        a=bool(before['states'][1].get('reward_open'));b=d.game.states[1]['reward_open']
        if a!=b:
            node,pos=self.drawers['bolt_handle_drawer']
            for q in [.33,.67]:
                t=float(a)+(float(b)-float(a))*q;self.sync(d.game);self.transform(node,[pos[0],pos[1]-.42*t,pos[2]]);d.frame(warm=4);d.append('Handle drawer opening',4)
        if bool(old.get('s2_cover'))!=bool(d.game.opened['s2_cover']):
            for q in [.33,.67]:
                t=float(bool(old.get('s2_cover')))+(float(bool(d.game.opened['s2_cover']))-float(bool(old.get('s2_cover'))))*q;self.sync(d.game);self.transform(self.bag_cover,rpy=[-160*t,0,0]);d.frame(warm=4);d.append('Sports bag cover opens',4)
        if bool(old.get('s3_cover'))!=bool(d.game.opened['s3_cover']):
            for q in [.33,.67]:
                t=float(bool(old.get('s3_cover')))+(float(bool(d.game.opened['s3_cover']))-float(bool(old.get('s3_cover'))))*q;self.sync(d.game);self.transform(self.medal_door,rpy=[0,0,-110*t]);d.frame(warm=4);d.append('Medal cupboard opens',4)
        if bool(old.get('key_box'))!=bool(d.game.opened['key_box']):
            n,p=self.drawers['medal_key_drawer']
            for q in [.33,.67]:
                t=float(bool(old.get('key_box')))+(float(bool(d.game.opened['key_box']))-float(bool(old.get('key_box'))))*q;self.sync(d.game);self.transform(n,[p[0],p[1]-.42*t,p[2]]);d.frame(warm=4);d.append('Key drawer opens',4)
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

    observe('s1_clue','Observe the two scoreboard rows and their downward order')
    click('s1_lock','unlock',code='25');click('s2_cover','open')
    observe('s2_clue','Find which runners obstruct the steel bolt path')
    click('s2_move_1_left')
    click('s2_move_0_down');click('s2_move_0_down');click('s2_move_2_down')
    click('s2_confirm','open')
    approach('s2_reward','Open the released drawer directly below the bolt board');click('s2_reward','open')
    d.append('Observe the removable T handle and its square peg',18);click('s3_tool','take')
    approach('s3_cover','Match the square peg to the medal cupboard socket');click('s3_cover','use','s3_tool');click('s3_cover','open')
    observe('s3_clue','Count the actual ribbon dots from left to right',stay=True)
    approach('s3_lock','Look down at the three-digit medal drawer lock',stay=True);click('s3_lock','unlock',code='314')
    click('key_box','open');d.append('Observe the flat brass key on the supported drawer pad',18);click('key','take')
    approach('exit','Return to the exit');click('exit','use','key');click('exit','open')
    if not exit_test(d.pos,g):raise RuntimeError('Open-door success was not reached')


def cpu_check():
    from easy88_core import stage_actions
    import collections
    g=Game();checks=[]
    def act(kind,key,**kw):return g.act(dict(action=kind,_hit364=key,_validated364=True,**kw))
    assert not act('press','s2_move_1_left')['ok'];checks.append('closed cover blocks slider controls')
    assert not act('take','s3_tool')['ok'];assert not act('open','s2_reward')['ok'];checks.append('handle cannot appear before its local bolt is released')
    for kind,key,extra in stage_actions(g,0):assert act(kind,key,**extra)['ok'],(kind,key)
    assert act('open','s2_cover')['ok']
    assert not act('open','s2_confirm')['ok'];checks.append('blocked bolt cannot open')
    assert not act('press','s2_move_0_down')['ok'];checks.append('real runner collision blocks premature vertical move')
    assert act('press','s2_move_1_left')['ok'];assert act('press','s2_move_1_right')['ok'];assert g.states[1]['angles']==[0,1,1];checks.append('legal moves reversible without reset or timing')
    assert not act('press','s2_control_0')['ok'];checks.append('old hidden counter controls cannot solve puzzle')
    for key in ['s2_move_1_left','s2_move_0_down','s2_move_0_down','s2_move_2_down']:assert act('press',key)['ok']
    assert act('open','s2_confirm')['ok'];assert g.solved[1] and not g.states[1]['reward_open'];checks.append('clear geometry releases same-cabinet drawer only')
    assert not act('open','s3_cover')['ok'];checks.append('solved flag alone cannot remotely open medal cupboard')
    assert act('open','s2_reward')['ok'];assert act('take','s3_tool')['ok']
    assert not act('use','s3_cover',item='missing')['ok'];assert act('use','s3_cover',item='s3_tool')['ok'];assert 's3_tool' not in g.holding;assert act('open','s3_cover')['ok'];checks.append('actual square-peg handle must be taken and fitted')
    for kind,key,extra in stage_actions(g,2):assert act(kind,key,**extra)['ok'],(kind,key)
    assert act('open','key_box')['ok'];assert act('take','key')['ok'];assert act('use','exit',item='key')['ok'];assert act('open','exit')['ok'];checks.append('full ordinary-action solution reaches open-door win')
    start=(0,1,1);queue=collections.deque([(start,0)]);seen={start};best=None
    while queue:
        pos,cost=queue.popleft()
        if bolt_path_clear(pos):best=cost;break
        for j in range(3):
            for delta in [-1,1]:
                nxt=list(pos);nxt[j]+=delta;nxt=tuple(nxt)
                if nxt not in seen and runners_valid(nxt):seen.add(nxt);queue.append((nxt,cost+1))
    assert best==4;checks.append('spatial clearance requires four runner moves, BFS proved')
    return dict(level='R14',scope='CPU collision/state fixtures only, no native pixels',passed=len(checks),checks=checks,minimum_runner_moves=best)
