from easy88_core import make_level

SPEC = {'id': 'R12', 'title': 'R12 · Music Practice Room / 音乐练习室', 'theme': 'music', 'size': [5.0, 5.0], 'door': {'side': 'west', 'start': 0.75, 'width': 1.04}, 'start': [1.0, 1.25, 1.35], 'start_yaw': 0, 'floor': 'wood', 'stages': [{'kind': 'sequence', 'name': 'practice light box', 'wall': 'north', 'centre': [1.5, 4.67], 'view': [1.5, 3.75], 'board_height': 0.98, 'visual': {'type': 'flash', 'sequence': ['square', 'circle', 'triangle'], 'slow': True, 'replayable': True}, 'clue': {'type': 'flash', 'sequence': ['square', 'circle', 'triangle'], 'slow': True, 'replayable': True}, 'clue_text': '', 'furniture_style': 'low_wall_cabinet', 'options': ['circle', 'triangle', 'square', 'star', 'leaf', 'cross'], 'answer': [2, 0, 1], 'length': 3, 'playback': True, 'distinct': False, 'confirm': True, 'design_notes': 'Six pictorial keys, exactly3 slots, whole-input confirm; playback is unlimited and uses visible lamps, not audio.'}, {'kind': 'read_code', 'name': 'hand-cranked paper roll', 'wall': 'east', 'centre': [4.67, 3.5], 'view': [3.75, 3.5], 'board_height': 0.98, 'visual': {'type': 'punch_rows', 'rows': 6, 'holes': [2, 5, 2], 'order': 'left_to_right', 'reference_ticks': [1, 2, 3, 4, 5, 6]}, 'clue': {'type': 'punch_rows', 'rows': 6, 'holes': [2, 5, 2], 'order': 'left_to_right', 'reference_ticks': [1, 2, 3, 4, 5, 6]}, 'clue_text': '', 'furniture_style': 'low_wall_cabinet', 'answer': '252', 'digits': 3, 'setup': {'kind': 'crank', 'item': 'crank', 'item_name': 'crank handle', 'target_name': 'paper roll socket', 'gate': True}, 'lock_label': '000', 'design_notes': 'The crank is supplied after opening the first cover. One use feeds the real roll to its stop and exposes3 holes against6 labelled rows; read does not return252.'}, {'kind': 'adjust', 'name': 'paired organ pipes', 'wall': 'south', 'centre': [3.0, 0.33], 'view': [3.0, 1.25], 'board_height': 0.98, 'visual': {'type': 'organ_heights', 'reference': [2, 4], 'levels': 4, 'units': 'detents'}, 'clue': {'type': 'organ_heights', 'reference': [2, 4], 'levels': 4, 'units': 'detents'}, 'clue_text': '', 'furniture_style': 'low_wall_cabinet', 'initial': [0, 0], 'target': [1, 3], 'moduli': [4, 4], 'auto': False, 'confirm': True, 'control_names': ['left organ pipe', 'right organ pipe'], 'design_notes': 'Pipe geometry visibly telescopes at4 wide detents; compare to the native reference outline. Only whole-pair confirm opens key compartment.'}], 'decor': [{'kind': 'music_stand', 'wall': 'west'}, {'kind': 'metronome', 'wall': 'south'}, {'kind': 'instrument_case', 'wall': 'east'}, {'kind': 'stacked_music_books', 'wall': 'north'}], 'design_notes': 'Short lamp sequence, row reading and physical height matching; no musical notation, hearing requirement or motor action.'}


TOGGLE_MASKS=((0,1,3),(1,2,4),(0,2,5),(3,4))
SPEC['stages'][0].update(kind='binary_pattern',name='practice keyboard lamp test',initial=[0,0,1,0,1,0],target=[1]*6,
 auto=False,clue_text='Each key flips the lamps marked above it. Light all six lamps.',
 clue={'type':'overlapping_key_lamps','layout':[2,3],'masks':[list(x) for x in TOGGLE_MASKS],'goal':'all_on'},
 visual={'type':'physical_practice_keys'},control_names=['practice key A','practice key B','practice key C','practice key D'])
for name in ['answer','length','playback','distinct','options']:SPEC['stages'][0].pop(name,None)
SPEC['stages'][1]['setup'].update(consume=True,post_take=True)
SPEC['stages'][1].update(kind='binary_pattern',initial=[0],target=[1],auto=False,semantic_kind='punched_strip_transfer',name='punched music roll feed',clue_text='',clue={'type':'removable_music_roll','recipient':'organ reader slot'},visual={'type':'physical_punched_music_roll'})

for name in ['answer','digits','lock_label']:SPEC['stages'][1].pop(name,None)
Game,_OriginalScene,_OriginalStandard,exit_test,cpu_check=make_level(SPEC)
TITLE=SPEC['title'];LEVEL_ID=SPEC['id'];START=SPEC['start'];START_YAW=SPEC['start_yaw']
CAP=150;OBSERVATION_SIZE=(640,360);VISUAL_ONLY=False;READ_ENABLED=True;READ_FEEDBACK_TEXT=True
Game.LABELS.update({'s1_clue':'lamp test and key diagrams','s1_play':'play symbol','s1_reset':'clear symbol','s1_confirm':'check symbol',
 's2_cover':'crank handle drawer','s2_tool':'crank handle','s2_setup':'paper roll crank socket','s2_clue':'music roll feeder label',
 's2_lock':'organ paper reader slot','s2_card':'punched music strip','s3_cover':'organ pipe protective door','s3_clue':'fixed organ pipe height outlines',
 's3_control_0':'left pipe adjustment button','s3_control_1':'right pipe adjustment button','s3_confirm':'pipe pair check button',
 'key_box':'key drawer','key':'brass door key'})
LABELS=Game.LABELS
_original_act=Game.act
Game.stage_accessible=lambda self,index:0<=index<3
Game.stage_exposed=lambda self,index:0<=index<3 and bool(self.states[index]['setup_ready'])
def _music_act(self,a):
    key=a.get('_hit364');kind=a.get('action')
    if not a.get('_validated364'):return _original_act(self,a)
    from action_feedback import failure_for,NO_ITEM
    if str(key).startswith('s1_control_'):
        try:j=int(str(key).rsplit('_',1)[1])
        except ValueError:return {'ok':False,'text':failure_for(kind)}
        if kind!='press' or not 0<=j<len(TOGGLE_MASKS):return {'ok':False,'text':failure_for(kind)}
        for lamp in TOGGLE_MASKS[j]:self.states[0]['selected'][lamp]^=1
        if all(self.states[0]['selected']):self.solved[0]=True
        return {'ok':True,'text':''}
    if key in ('s1_play','s1_confirm','s1_reset') or str(key).startswith('s1_choice_'):
        return {'ok':False,'text':failure_for(kind)}
    if key=='s2_tool' and kind=='take' and not self.opened['s2_cover']:return {'ok':False,'text':failure_for(kind)}
    if str(key).startswith('s2_control_') or key in ('s2_confirm','s2_reset'):return {'ok':False,'text':failure_for(kind)}
    if key=='s2_lock':
        if kind!='use':return {'ok':False,'text':failure_for(kind)}
        item=self._resolve_item(a.get('item'))
        if item is None:return {'ok':False,'text':NO_ITEM}
        if item!='s2_card':return {'ok':False,'text':failure_for(kind)}
        self.holding.remove(item);self.states[1]['strip_inserted']=True;self.states[1]['selected']=[1];self.solved[1]=True
        return {'ok':True,'text':''}
    if key=='s3_cover' and kind=='open' and not self.states[1].get('strip_inserted'):return {'ok':False,'text':failure_for(kind)}
    if kind=='press' and (str(key).startswith('s3_control_') or key=='s3_confirm') and not self.opened['s3_cover']:
        return {'ok':False,'text':failure_for(kind)}
    return _original_act(self,a)
Game.act=_music_act
LABELS.update({'s1_control_'+str(j):'practice key '+chr(65+j) for j in range(4)})
import math,hashlib
import numpy as np
from PIL import Image,ImageDraw
from easy88_scene import EasyScene
from easy88_clues import draw_symbol
from font_utils import load_font

class Scene(EasyScene):
    def __init__(self,og,run):
        super().__init__(og,run,SPEC)
        self.views={};self.focus={};self.labels={};self.drawers={};self.expanded=[];self.lamp_nodes=[];self.flash_index=None;self.screen_signature=None;self.lock_value='000';self.pipe_nodes=[]
    def palette(self):
        super().palette()
        for name,c in [('music_blue',(.13,.25,.28)),('music_green',(.22,.33,.28)),('cream_paper',(.74,.70,.57)),('pipe_steel',(.42,.49,.48)),('dark_pipe_bore',(.025,.035,.035)),('instrument_lining',(.24,.32,.27))]:self.mat(name,c,rough=.88 if name!='pipe_steel' else .30,metal=.60 if name=='pipe_steel' else 0.)
    def reg_at(self,key,node,label,view,focus=None):
        self.reg(key,node);self.views[key]=list(view);self.labels[key]=label
        if focus is not None:self.focus[key]=list(focus)
        return node
    def flat(self,name,parent,pos,w,h,im,horizontal=False):
        path=self.tex/(name+'.png');im.save(path)
        return self.plane(name,pos,w,h,(1,0,0),(0,1,0) if horizontal else (0,0,1),None,parent,material=self.image_mat('r12_'+name,path))
    def text(self,name,parent,pos,w,h,value,bg=(214,208,181),ink=(34,48,42),horizontal=False):
        short=len(str(value))==1
        iw,ih=(max(200,int(round(400*w/h))),400) if short else (1000,240)
        im=Image.new('RGB',(iw,ih),bg);d=ImageDraw.Draw(im);size=int(ih*.72) if short else 160
        while size>12:
            box=d.textbbox((0,0),str(value),font=load_font(size))
            if box[2]-box[0]<=iw*.84 and box[3]-box[1]<=ih*.78:break
            size-=8
        d.text((iw/2,ih/2),str(value),font=load_font(size),fill=ink,anchor='mm');return self.flat(name,parent,pos,w,h,im,horizontal)
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

    def hollow_pipe(self,name,parent,pos,radius=.045,inner=.033,height=1.):
        n=self.group(name,pos,parent);count=32;pts=[]
        for z in [0,1]:
            for r in [radius,inner]:
                for j in range(count):
                    a=j*2*math.pi/count;pts.append([r*math.cos(a),r*math.sin(a),z])
        faces=[]
        for j in range(count):
            k=(j+1)%count;faces.extend([[j,k,2*count+k,2*count+j],[count+j,3*count+j,3*count+k,count+k],[2*count+j,2*count+k,3*count+k,3*count+j],[j,count+j,count+k,k]])
        self.mesh('hollow_metal_tube',pts,faces,'pipe_steel',n)
        with self.og.sim.editing_usd():n['_height']=self.G.Xformable(n['prim']).AddScaleOp();n['_height'].Set(self.F.Vec3f(1,1,height))
        return n
    def crank_handle(self):
        n=self.group('actual_crank_handle')
        self.cylinder('crank_shaft',[0,0,0],.014,.060,'steel','y',n,n=24)
        self.tube('crank_arm',[0,-.024,0],[.13,-.024,.050],.012,'steel',n)
        self.cylinder('wooden_crank_grip',[.13,-.05,.050],.026,.035,'darkwood','y',n,n=28)
        return n
    def paper_strip(self,parent):
        n=self.group('actual_perforated_paper',[0,-.245,.60],parent)
        holes=[(-.09,.070),(0,-.070),(.09,.070)]
        xs=sorted(set([-.15,.15]+[x+d for x,z in holes for d in [-.016,.016]]));zs=sorted(set([-.15,.15]+[z+d for x,z in holes for d in [-.012,.012]]))
        for x0,x1 in zip(xs,xs[1:]):
            for z0,z1 in zip(zs,zs[1:]):
                x=(x0+x1)/2;z=(z0+z1)/2
                if any(abs(x-hx)<.016 and abs(z-hz)<.012 for hx,hz in holes):continue
                self.box('paper_between_perforations',[x,0,z],[x1-x0,.003,z1-z0],'cream_paper',n,bevel=.0001)
        return n
    def set_paper(self,fraction):self.transform(self.paper,[0,-.245,.60+.42*float(fraction)])
    def set_crank(self,g,drawer_fraction=None,rotation=0):
        installed=bool(g.states[1]['setup_used']);self.visibility(self.crank,'s2_tool' not in g.holding)
        if installed:self.transform(self.crank,[4.37,3.12,.78],[0,rotation,-90])
        else:
            q=float(g.opened['s2_cover']) if drawer_fraction is None else float(drawer_fraction);self.transform(self.crank,[1.5,4.45-.42*q,.58],[-90,0,0])
    def build(self,g):
        self.room_shell('music_practice_room',size=(5,5),openings={'west':[(.72,1.82)]})
        self.box('continuous_subfloor',[2.5,2.5,-.075],[5.14,5.14,.10],'darkwood',bevel=.001)
        self.table('practice_console_stand',(1.50,4.50),(1.70,.72),height=.70)
        self.lamp_base=self.group('practice_lamp_console',[1.50,4.50,0])
        self.box('lamp_box_back',[0,.17,1.12],[1.10,.16,.69],'music_blue',self.lamp_base)
        self.lamp_board=self.group('six_practice_lamps',parent=self.lamp_base)
        self.mat('practice_lamp_on',(.22,.57,.19),rough=.55,emission=(.07,.22,.04))
        self.mat('practice_lamp_off',(.075,.11,.085),rough=.85)
        for j in range(6):
            x=(j%3-1)*.30;z=1.30-(j//3)*.23;cell=self.group('practice_lamp_'+str(j),[x,.077,z],self.lamp_board)
            self.cylinder('lamp_rim',[0,0,0],.078,.030,'iron','y',cell,n=32)
            off=self.cylinder('lamp_unlit',[0,-.018,0],.064,.008,'practice_lamp_off','y',cell,n=32)
            on=self.cylinder('lamp_lit',[0,-.018,0],.064,.008,'practice_lamp_on','y',cell,n=32)
            self.lamp_nodes.append((off,on))
        self.box('lamp_goal_backing',[0,.105,1.42],[.59,.04,.084],'music_blue',self.lamp_board)
        self.text('lamp_goal',self.lamp_board,[0,.084,1.42],.55,.072,'ALL ON')
        self.reg_at('s1_clue',self.lamp_board,'lamp test and key diagrams',[1.5,3.5],[1.5,4.4,1.10])
        self.practice_keys=[]
        for j,mask in enumerate(TOGGLE_MASKS):
            x=(j-1.5)*.21
            key=self.group('physical_practice_key_'+str(j),[x,-.19,.786],self.lamp_base)
            self.box('ivory_practice_key',[0,0,0],[.185,.31,.033],'cream_paper',key,bevel=.008)
            self.reg_at('s1_control_'+str(j),key,LABELS['s1_control_'+str(j)],[1.5,3.5],[1.5,4.4,1.05]);self.practice_keys.append(key)
            im=Image.new('RGB',(240,180),(218,211,180));dr=ImageDraw.Draw(im)
            for k in range(6):
                cx=55+(k%3)*65;cy=48+(k//3)*75
                dr.ellipse((cx-19,cy-19,cx+19,cy+19),fill=(43,78,54) if k in mask else (203,201,174),outline=(76,94,74),width=4)
            self.box('effect_diagram_backing',[x,.075,.86],[.18,.072,.14],'music_blue',self.lamp_board)
            self.flat('key_effect_diagram_'+str(j),self.lamp_board,[x,.0385,.86],.17,.13,im)
        self.practice_latch=self.group('practice_drawer_latch',[.48,-.285,.57],self.lamp_base)
        self.box('drawer_latch_body',[0,0,0],[.055,.035,.15],'brass',self.practice_latch)
        self.cylinder('latch_upper_stem',[0,0,.085],.006,.10,'steel','z',self.practice_latch,n=20)
        self.tube('local_test_linkage',[.48,.06,1.03],[.48,.06,.56],.012,'steel',self.lamp_base)
        self.crankdrawer,front=self.drawer('crank_drawer',None,(1.5,4.25),.54,width=1.06,depth=.44)
        self.reg_at('s2_cover',front,'crank handle drawer',[1.5,3.25],[1.5,4.25,.54]);self.box('crank_support_pad',[0,.22,-.0455],[.92,.34,.11],'instrument_lining',self.crankdrawer)
        self.crank=self.crank_handle();self.reg_at('s2_tool',self.crank,'crank handle',[1.5,3.25],[1.56,4.03,.60])
        self.reader=self.group('paper_roll_reader',[4.65,3.50,0]);self.transform(self.reader,rpy=[0,0,-90])
        for x in [-.58,.58]:self.box('reader_side',[x,0,.85],[.04,.58,1.34],'wood',self.reader)
        self.box('reader_back',[0,.26,.85],[1.20,.04,1.34],'music_green',self.reader);self.box('reader_floor',[0,0,.17],[1.22,.60,.04],'wood',self.reader)
        self.box('reader_top',[0,0,1.53],[1.22,.60,.04],'wood',self.reader)
        for x in [-.48,.48]:
            for y in [-.22,.22]:self.box('reader_short_foot',[x,y,.075],[.085,.085,.15],'darkwood',self.reader)
        self.box('reader_front_lower',[0,-.27,.53],[1.20,.045,.70],'wood',self.reader);self.box('reader_front_upper',[0,-.27,1.385],[1.20,.045,.29],'wood',self.reader)
        for x in [-.495,.495]:self.box('reader_window_side',[x,-.27,1.06],[.21,.045,.36],'wood',self.reader)
        self.box('dark_paper_backing',[0,-.18,1.06],[.77,.025,.37],'dark_pipe_bore',self.reader)
        self.paper=self.paper_strip(self.reader);self.reg_at('s2_card',self.paper,'punched music strip',[3.5,3.5],[4.40,3.50,1.06])
        for z in [.835,1.285]:
            self.cylinder('paper_feed_roller',[0,-.21,z],.044,.83,'darkwood','x',self.reader,n=28)
            for x in [-.44,.44]:self.cylinder('roller_bearing',[x,-.21,z],.052,.04,'brass','x',self.reader,n=24)
        feed_label=self.text('roll_feed_label',self.reader,[0,-.299,.795],.38,.055,'MUSIC ROLL')
        self.reg_at('s2_clue',feed_label,'music roll feeder label',[3.5,3.5],[4.35,3.50,.795])
        socket=self.group('paper_crank_socket',[.38,-.28,.78],self.reader)
        self.cylinder('socket_bezel',[0,0,0],.037,.025,'steel','y',socket,n=28);self.cylinder('socket_recess',[0,-.014,0],.018,.003,'iron','y',socket,n=24)
        self.reg_at('s2_setup',socket,'paper roll crank socket',[3.5,3.5],[4.36,3.12,.78]);self.add_obstacle(4.32,2.88,4.98,4.12)
        self.pipe_base=self.group('organ_pipe_cabinet',[3.0,.34,0]);self.transform(self.pipe_base,rpy=[0,0,180])
        for x in [-.71,.71]:self.box('pipe_cabinet_side',[x,0,.36],[.04,.56,.60],'wood',self.pipe_base)
        self.box('pipe_cabinet_back',[0,.24,.36],[1.46,.04,.60],'paint',self.pipe_base);self.box('pipe_cabinet_floor',[0,0,.08],[1.48,.58,.045],'darkwood',self.pipe_base)
        self.box('pipe_cabinet_top',[0,0,.68],[1.50,.62,.08],'wood',self.pipe_base);self.add_obstacle(2.23,.04,3.77,.67)
        for x in [-.70,.70]:self.box('pipe_protective_side',[x,-.12,1.0],[.03,.44,.64],'wood',self.pipe_base)
        self.box('pipe_protective_back',[0,.105,1.0],[1.44,.03,.64],'paint',self.pipe_base)
        self.box('pipe_protective_top',[0,-.12,1.335],[1.44,.47,.03],'wood',self.pipe_base)
        self.box('outline_board',[0,.07,1.00],[1.15,.035,.61],'music_blue',self.pipe_base)
        self.references=self.group('two_fixed_height_outlines',parent=self.pipe_base)
        for j,level in enumerate([2,4]):
            x=(j-.5)*.51;top=.72+.12*level
            for side in [-1,1]:self.tube('outline_side',[x+side*.078,.043,.72],[x+side*.078,.043,top],.006,'cream_paper',self.references)
            self.tube('outline_top',[x-.078,.043,top],[x+.078,.043,top],.006,'cream_paper',self.references)
            self.cylinder('fixed_pipe_sleeve',[x,-.045,.77],.058,.10,'brass','z',self.pipe_base,n=32)
            pipe=self.hollow_pipe('telescoping_pipe_'+str(j),self.pipe_base,[x,-.045,.72],height=.12);self.pipe_nodes.append(pipe)
            self.box('pipe_foot',[x,-.045,.718],[.20,.20,.024],'iron',self.pipe_base)
            button=self.group('pipe_adjustment_button_'+str(j),[x,-.27,.76],self.pipe_base);self.cylinder('pipe_button',[0,0,0],.042,.023,'iron','y',button,n=28);self.text('pipe_arrow_'+str(j),button,[0,-.013,0],.073,.062,'↑')
            self.reg_at('s3_control_'+str(j),button,LABELS['s3_control_'+str(j)],[3.0,1.5],[3.0,.61,1.0])
        self.reg_at('s3_clue',self.references,'fixed pipe height outlines',[3.0,1.5],[3.0,.39,1.02])
        self.check=self.group('pipe_pair_check',[0,-.28,.76],self.pipe_base);self.box('pipe_check_body',[0,0,0],[.13,.027,.076],'iron',self.check);self.text('pipe_check_mark',self.check,[0,-.015,0],.116,.063,'✓')
        self.reg_at('s3_confirm',self.check,'pipe pair check button',[3.0,1.5],[3.0,.62,.76])
        self.red=self.cylinder('pipe_pair_red',[.12,-.293,.76],.013,.010,'red_led','y',self.pipe_base,n=24);self.green=self.cylinder('pipe_pair_green',[.12,-.293,.76],.013,.010,'green','y',self.pipe_base,n=24)
        self.pipe_cover=self.group('pipe_protective_door',[-.70,-.34,.69],self.pipe_base)
        cover=self.group('pipe_door_leaf',parent=self.pipe_cover);self.box('protective_door',[.70,0,.32],[1.40,.04,.64],'paint',cover);self.box('protective_door_handle',[1.28,-.050,.30],[.025,.05,.16],'brass',cover)
        self.reg_at('s3_cover',cover,'organ pipe protective door',[3.0,1.5],[3.0,.69,1.0])
        self.code_lock=self.group('organ_music_reader_slot',[.84,-.036,.32],cover)
        self.box('paper_reader_body',[0,0,0],[.38,.048,.13],'iron',self.code_lock)
        self.box('paper_reader_opening',[0,-.025,.012],[.32,.005,.025],'dark_pipe_bore',self.code_lock)
        self.text('reader_roll_label',self.code_lock,[0,-.026,-.036],.32,.034,'MUSIC ROLL')
        self.reg_at('s2_lock',self.code_lock,'organ paper reader slot',[3.0,1.5],[2.86,.72,1.01])
        self.inserted_strip=self.group('inserted_music_strip',[0,-.032,.012],self.code_lock)
        self.box('supported_strip_tail',[0,-.074,0],[.30,.15,.003],'cream_paper',self.inserted_strip)
        for j in range(3):self.box('punched_strip_tail_hole',[(j-1)*.09,-.06,.002],[.027,.020,.001],'dark_pipe_bore',self.inserted_strip,bevel=.0001)
        self.keydrawer,keyfront=self.drawer('organ_key_drawer',self.pipe_base,(0,-.30),.50,width=1.16,depth=.44)
        self.reg_at('key_box',keyfront,'key drawer',[3.0,1.5],[3.0,.64,.50]);self.box('key_support_pad',[0,.21,-.021],[.94,.34,.158],'instrument_lining',self.keydrawer)
        self.key=self.tool('flat_brass_key',self.keydrawer,[0,.21,.069],'key');self.target_nodes.pop('flat_brass_key',None);self.transform(self.key,rpy=[90,0,0]);self.reg_at('key',self.key,'brass door key',[3.0,1.5],[3.0,.85,.569])
        stand=self.group('music_stand',[.35,2.75,0]);self.transform(stand,rpy=[0,0,90])
        self.cylinder('stand_pole',[0,0,.56],.016,1.10,'iron','z',stand)
        for a in [0,120,240]:
            r=math.radians(a);self.tube('stand_foot',[0,0,.12],[.27*math.cos(r),.27*math.sin(r),.025],.012,'iron',stand)
        tray=self.group('music_tray',[0,0,1.20],stand);self.transform(tray,rpy=[-16,0,0]);self.box('tray_back',[0,0,0],[.56,.025,.39],'darkwood',tray)
        sheet=Image.new('RGB',(600,400),(223,216,190));dr=ImageDraw.Draw(sheet)
        for group in range(3):
            for line in range(5):dr.line((45,70+group*100+line*11,555,70+group*100+line*11),fill=(112,121,102),width=2)
        self.flat('fixed_score_page',tray,[0,-.014,0],.51,.34,sheet);self.add_obstacle(.07,2.43,.70,3.08)
        case=self.group('fixed_instrument_case',[3.12,4.62,.14]);self.box('instrument_case_body',[0,0,0],[1.12,.36,.22],'music_blue',case,bevel=.045);self.box('case_lid_seam',[0,0,.045],[1.13,.37,.012],'iron',case,bevel=.01)
        for x in [-.35,.35]:self.box('case_latch',[x,-.19,.04],[.07,.025,.055],'brass',case)
        self.box('case_handle',[0,-.23,.03],[.23,.035,.033],'iron',case);self.add_obstacle(2.54,4.40,3.70,4.84)
        met=self.group('fixed_metronome',[.79,4.55,.742]);self.mesh('metronome_wood',[[-.075,-.075,0],[.075,-.075,0],[.075,.075,0],[-.075,.075,0],[0,0,.24]],[[0,1,4],[1,2,4],[2,3,4],[3,0,4],[0,3,2,1]],'wood',met);self.tube('metronome_pendulum',[0,-.070,.055],[.025,-.025,.20],.005,'steel',met)
        for j in range(3):self.box('stacked_music_book',[2.20,4.55,.758+j*.025],[.25,.30,.023],'cream_paper' if j%2 else 'music_green',bevel=.003)
        self.exit_node=self.door('music_room_exit',[.06,1.79,0],1.04);self.door_angle=-90;self.reg_at('exit',self.exit_node,'exit door',[1.0,1.25],[.06,1.27,1.12]);self.door_view=[1.0,1.25]
        for y in [.73,1.81]:self.box('door_jamb',[.05,y,1.14],[.17,.065,2.30],'paint')
        self.box('door_lintel',[.05,1.27,2.29],[.17,1.15,.065],'paint')
        for y in [.74,1.80]:self.box('door_stop_jamb',[.01,y,1.14],[.026,.035,2.28],'darkwood')
        self.box('door_stop_top',[.01,1.27,2.28],[.026,1.13,.035],'darkwood')
        self.stage_views=[[1.5,3.5],[3.5,3.5],[3.0,1.5]];self.stage_centres=[[1.5,4.5,1.15],[4.4,3.5,1.06],[3.0,.39,1.02]]
        self.bases=[([1.5,4.5],0),([4.65,3.5],-90),([3.0,.34],180)]
        self.sync(g)
    def visible(self,key,g):
        if key in ('s2_card','s2_clue'):return bool(g.states[1]['setup_used']) and 's2_card' not in g.taken
        if key=='s2_tool':return bool(g.opened['s2_cover']) and key not in g.taken
        if key in ('s3_clue','s3_control_0','s3_control_1','s3_confirm'):return bool(g.opened['s3_cover'])
        if key=='key':return bool(g.opened['key_box']) and key not in g.taken
        return key in self.target_nodes
    def sync(self,g):
        for j,(off,on) in enumerate(self.lamp_nodes):self.visibility(off,not g.states[0]['selected'][j]);self.visibility(on,bool(g.states[0]['selected'][j]))
        self.transform(self.practice_latch,[.48,-.285,.57+(.18 if g.solved[0] else 0)])
        n,p=self.drawers['crank_drawer'];self.transform(n,[p[0],p[1]-(.42 if g.opened['s2_cover'] else 0),p[2]])
        self.set_crank(g);self.set_paper(1 if g.states[1]['setup_used'] else 0)
        self.visibility(self.paper,'s2_card' not in g.taken)
        self.visibility(self.inserted_strip,bool(g.states[1].get('strip_inserted')))
        self.transform(self.pipe_cover,rpy=[0,0,-110 if g.opened['s3_cover'] else 0])
        for j,node in enumerate(self.pipe_nodes):
            with self.og.sim.editing_usd():node['_height'].Set(self.F.Vec3f(1,1,.12*(g.states[2]['angles'][j]+1)))
        self.visibility(self.red,not g.solved[2]);self.visibility(self.green,g.solved[2])
        n,p=self.drawers['organ_key_drawer'];self.transform(n,[p[0],p[1]-(.42 if g.opened['key_box'] else 0),p[2]])
        self.visibility(self.key,'key' not in g.taken);self.transform(self.exit_node,rpy=[0,0,self.door_angle-(103 if g.opened['exit'] else 0)])
        self.expanded=[]
        for flag,node in [(g.opened['s2_cover'],self.crankdrawer),(g.opened['s3_cover'],self.pipe_cover),(g.opened['key_box'],self.keydrawer)]:
            if flag:
                points=self.triangles(node).reshape(-1,3);self.expanded.append((points.min(0)[:2]-.12,points.max(0)[:2]+.12))
        self.centres={}
        for key,node in self.target_nodes.items():
            points=self.triangles(node).reshape(-1,3)
            if points.size:self.centres[key]=((points.min(0)+points.max(0))/2).tolist()
    def candidates(self,g):return self.base_candidates([k for k in self.target_nodes if self.visible(k,g)])
    def blocked(self,x,y,g):return super().blocked(x,y,g) or any(lo[0]<x<hi[0] and lo[1]<y<hi[1] for lo,hi in self.expanded)
    def view_for(self,key):return self.views.get(key,[1.0,1.25])
    def focus_for(self,key):return self.focus.get(key,self.centres.get(key))
    def label_for(self,key):return self.labels.get(key,LABELS.get(key,key.replace('_',' ')))
    def animate(self,d,before):
        changed=before['states'][0]['selected']!=d.game.states[0]['selected']
        if changed:
            action=getattr(d,'current_action',{}) or {};key=action.get('_hit364')
            delta={j for j,(a,b) in enumerate(zip(before['states'][0]['selected'],d.game.states[0]['selected'])) if a!=b}
            index=next((j for j,m in enumerate(TOGGLE_MASKS) if set(m)==delta),None)
            if index is not None:
                node=self.practice_keys[index];x=(index-1.5)*.21
                self.sync(d.game);self.transform(node,[x,-.19,.774]);d.frame(warm=4);d.append('The key changes its marked lamp group',5)
                self.transform(node,[x,-.19,.786])
        old=before.get('opened',{})
        if bool(old.get('s2_cover'))!=bool(d.game.opened['s2_cover']):
            n,p=self.drawers['crank_drawer']
            for t in [.33,.67]:
                q=float(bool(old.get('s2_cover')))+(float(bool(d.game.opened['s2_cover']))-float(bool(old.get('s2_cover'))))*t;self.sync(d.game);self.transform(n,[p[0],p[1]-.42*q,p[2]]);self.set_crank(d.game,q);d.frame(warm=4);d.append('Crank drawer opens',4)
        if not before['states'][1]['setup_used'] and d.game.states[1]['setup_used']:
            for q in [.25,.50,.75,1.0]:self.sync(d.game);self.set_crank(d.game,rotation=-360*q);self.set_paper(q);d.frame(warm=4);d.append('The crank feeds the same perforated paper to its stop',5)
        if bool(old.get('s3_cover'))!=bool(d.game.opened['s3_cover']):
            for t in [.33,.67]:
                q=float(bool(old.get('s3_cover')))+(float(bool(d.game.opened['s3_cover']))-float(bool(old.get('s3_cover'))))*t;self.sync(d.game);self.transform(self.pipe_cover,rpy=[0,0,-110*q]);d.frame(warm=4);d.append('Pipe protective door opens',4)
        for j,(a,b) in enumerate(zip(before['states'][2]['angles'],d.game.states[2]['angles'])):
            if a!=b:
                for t in [.33,.67]:
                    self.sync(d.game)
                    with self.og.sim.editing_usd():self.pipe_nodes[j]['_height'].Set(self.F.Vec3f(1,1,.12*(a+1+(b-a)*t)))
                    d.frame(warm=4);d.append('The organ pipe changes its real height',4)
        if bool(old.get('key_box'))!=bool(d.game.opened['key_box']):
            n,p=self.drawers['organ_key_drawer']
            for t in [.33,.67]:
                q=float(bool(old.get('key_box')))+(float(bool(d.game.opened['key_box']))-float(bool(old.get('key_box'))))*t;self.sync(d.game);self.transform(n,[p[0],p[1]-.42*q,p[2]]);d.frame(warm=4);d.append('Key drawer opens',4)
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

    observe('s1_clue','Compare the key effect diagrams with the currently lit lamps')
    approach('s1_control_1','Keep the lamps and practice keys together in view',stay=True)
    for j in [1,2,3]:click('s1_control_'+str(j))
    if not g.solved[0]:raise RuntimeError('The overlapping lamp groups did not reach the all-on goal')
    approach('s2_cover','Open the locally released crank drawer');click('s2_cover','open');d.append('Observe the crank resting inside the shallow drawer',18);click('s2_tool','take')
    approach('s2_setup','Use the crank on the paper feed socket');click('s2_setup','use','s2_tool')
    observe('s2_card','Observe the actual punched strip that has fed into view',stay=True);click('s2_card','take')
    approach('s2_lock','Insert the punched strip into the matching-width organ reader');click('s2_lock','use','s2_card');click('s3_cover','open')
    observe('s3_clue','Compare the two real pipe heights with their fixed outline',stay=True)
    click('s3_control_0')
    for _ in range(3):click('s3_control_1')
    click('s3_confirm');approach('key_box','Look down at the unlocked key drawer',stay=True);click('key_box','open');d.append('Observe the flat brass key on the supported drawer pad',18);click('key','take')
    approach('exit','Return to the exit');click('exit','use','key');click('exit','open')
    if not exit_test(d.pos,g):raise RuntimeError('Open-door success was not reached')

def cpu_check():
    import itertools
    from easy88_core import stage_actions
    checks=[];g=Game()
    def act(kind,key,**kw):return g.act(dict(action=kind,_validated364=True,_hit364=key,**kw))
    assert not act('open','s2_cover')['ok'];checks.append('local crank drawer locked before lamp goal')
    assert not act('press','s1_choice_0')['ok'];checks.append('obsolete sequence input unavailable')
    solutions=[]
    for bits in itertools.product([0,1],repeat=4):
        v=list(SPEC['stages'][0]['initial'])
        for on,mask in zip(bits,TOGGLE_MASKS):
            if on:
                for j in mask:v[j]^=1
        if v==[1]*6:solutions.append(bits)
    assert solutions==[(0,1,1,1)];checks.append('one reversible switch subset among16')
    assert act('press','s1_control_0')['ok'];assert act('press','s1_control_0')['ok'];assert g.states[0]['selected']==SPEC['stages'][0]['initial'];checks.append('key press is a reversible group toggle')
    for j in [3,1,2]:assert act('press','s1_control_'+str(j))['ok']
    assert g.solved[0] and not g.opened['s2_cover'];checks.append('order-independent all-on result releases only its drawer')
    assert act('open','s2_cover')['ok'];assert act('take','s2_tool')['ok'];assert not act('take','s2_card')['ok'];checks.append('strip cannot be taken before feeding')
    assert act('use','s2_setup',item='s2_tool')['ok'];assert act('take','s2_card')['ok'];assert not g.solved[1];checks.append('crank produces real takeable strip without remote unlock')
    assert not act('unlock','s2_lock',code='252')['ok'];assert not act('open','s3_cover')['ok'];checks.append('old code and stage flag do not replace paper insertion')
    assert act('use','s2_lock',item='s2_card')['ok'];assert g.states[1]['strip_inserted'] and g.solved[1];assert 's2_card' not in g.holding;checks.append('paper is physically transferred to organ reader')
    for kind,key,extra in stage_actions(g,2):assert act(kind,key,**extra)['ok'],(kind,key)
    for kind,key,extra in [('open','key_box',{}),('take','key',{}),('use','exit',{'item':'key'}),('open','exit',{})]:assert act(kind,key,**extra)['ok']
    assert g.exited;checks.append('manual take/use/open door completes')
    return dict(level='R12',scope='CPU state-machine and constraint checks, no SDK/native pixels/API',passed=len(checks),checks=checks)
