from easy88_core import make_level

SPEC = {'id': 'R11', 'title': 'R11 · Laundry Room / 洗衣房', 'theme': 'laundry', 'size': [5.0, 4.8], 'door': {'side': 'south', 'start': 2.0, 'width': 1.04}, 'start': [2.5, 1.0, 1.35], 'start_yaw': 90, 'floor': 'tile', 'stages': [{'kind': 'window_align', 'name': 'filter inspection windows', 'wall': 'west', 'centre': [0.33, 2.75], 'view': [1.25, 2.75], 'board_height': 0.98, 'visual': {'type': 'window_align', 'layers': 2, 'positions': 4, 'reference': [3, 2], 'cutaway': True, 'handle_position': 2}, 'clue': {'type': 'window_align', 'layers': 2, 'positions': 4, 'reference': [3, 2], 'cutaway': True, 'handle_position': 2}, 'clue_text': '', 'furniture_style': 'low_wall_cabinet', 'initial': [0, 0], 'target': [2, 1], 'moduli': [4, 4], 'auto': True, 'control_names': ['front inspection window', 'rear inspection window'], 'design_notes': 'Both apertures and internal handle must align; real cutaway geometry, no per-layer correctness lamp.'}, {'kind': 'mirror', 'name': 'drain observation tank', 'wall': 'north', 'centre': [2.5, 4.47], 'view': [2.5, 3.5], 'board_height': 0.98, 'visual': {'type': 'mirror', 'text': '1420', 'water_tank': True, 'persist_after_drain': True, 'mirror_icon': True}, 'clue': {'type': 'mirror', 'text': '1420', 'water_tank': True, 'persist_after_drain': True, 'mirror_icon': True}, 'clue_text': '', 'furniture_style': 'low_wall_cabinet', 'answer': '1420', 'digits': 4, 'setup': {'kind': 'drain', 'item': None, 'target_name': 'drain button', 'gate': True}, 'design_notes': 'The unique drain button is a transition only. Water retreats to expose a physically mirrored label; read never corrects it.'}, {'kind': 'count', 'name': 'button collection box', 'wall': 'east', 'centre': [4.67, 2.25], 'view': [3.75, 2.25], 'board_height': 0.98, 'visual': {'type': 'count', 'counts': [3, 1, 2], 'symbol': 'button', 'order': 'top_to_bottom', 'rows': 3}, 'clue': {'type': 'count', 'counts': [3, 1, 2], 'symbol': 'button', 'order': 'top_to_bottom', 'rows': 3}, 'clue_text': '', 'furniture_style': 'low_wall_cabinet', 'answer': '312', 'digits': 3, 'lock_label': '000 ↓', 'design_notes': 'Three fixed physical rows, not a preprinted312 answer. No mandatory read.'}], 'decor': [{'kind': 'laundry_basket', 'wall': 'south'}, {'kind': 'folded_towels', 'wall': 'west'}, {'kind': 'detergent_bottles', 'wall': 'east'}, {'kind': 'washing_machine', 'wall': 'north'}], 'design_notes': 'U-shaped human-scale low equipment; each preceding solved/open cover exposes the next puzzle. Gate3 result is the real exit key. Solid grout backing and proper door frame.'}


Game,_OriginalScene,_OriginalStandard,exit_test,cpu_check=make_level(SPEC)
TITLE=SPEC['title'];LEVEL_ID=SPEC['id'];START=SPEC['start'];START_YAW=SPEC['start_yaw']
CAP=150;OBSERVATION_SIZE=(640,360);VISUAL_ONLY=False;READ_ENABLED=True;READ_FEEDBACK_TEXT=True
Game.LABELS.update({'s1_control_0':'front inspection slider button','s1_control_1':'rear inspection slider button',
 's1_clue':'two inspection apertures','s2_cover':'filter inspection hatch','s2_setup':'drain button',
 's2_clue':'mirrored plate inside the basin','s2_lock':'button cupboard code lock','s3_cover':'button cupboard door',
 's3_clue':'three rows of buttons','s3_lock':'button drawer code lock','key_box':'key drawer','key':'brass door key'})
LABELS=Game.LABELS
_original_act=Game.act
Game.stage_accessible=lambda self,index:0<=index<3
Game.stage_exposed=lambda self,index:0<=index<3 and bool(self.states[index]['setup_ready'])
def _laundry_act(self,a):
    key=a.get('_hit364');kind=a.get('action')
    if a.get('_validated364') and key=='filter_hatch_handle' and kind in ('open','close'):a=dict(a,_hit364='s2_cover');key='s2_cover'
    if a.get('_validated364') and key=='s2_setup' and kind=='press' and not self.opened['s2_cover']:
        from action_feedback import failure_for
        return {'ok':False,'text':failure_for(kind)}
    result=_original_act(self,a)
    if a.get('_validated364') and kind=='unlock' and key in ('s2_lock','s3_lock'):
        self.states[1 if key=='s2_lock' else 2]['entered_code']=str(a.get('code',''))
    return result
Game.act=_laundry_act
import math,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageOps
from easy88_scene import EasyScene
from font_utils import load_font

class Scene(EasyScene):
    def __init__(self,og,run):
        super().__init__(og,run,SPEC)
        self.views={};self.focus={};self.labels={};self.drawers={};self.lock_screens={};self.lock_values={};self.expanded=[];self.plates=[]
    def palette(self):
        super().palette()
        for name,c in [('laundry_enamel',(.62,.67,.63)),('laundry_blue',(.17,.30,.36)),('rear_plate',(.30,.43,.46)),('floor_tile',(.50,.53,.50)),('grout',(.30,.33,.31)),('clean_cloth',(.74,.72,.63)),('cloth_blue',(.25,.40,.43)),('laundry_felt',(.24,.35,.33))]:self.mat(name,c,rough=.91)
        self.mat('cloudy_soapy_water',(.17,.30,.32),rough=.24,opacity=1.)
        self.mat('basin_glass',(.29,.42,.43),rough=.12,opacity=.055)
    def reg_at(self,key,node,label,view,focus=None):
        self.reg(key,node);self.views[key]=list(view);self.labels[key]=label
        if focus is not None:self.focus[key]=list(focus)
        return node
    def flat(self,name,parent,pos,w,h,im,horizontal=False):
        path=self.tex/(name+'.png');im.save(path)
        return self.plane(name,pos,w,h,(1,0,0),(0,1,0) if horizontal else (0,0,1),None,parent,material=self.image_mat('r11_'+name,path))
    def text(self,name,parent,pos,w,h,value,bg=(211,208,184),ink=(34,48,42),horizontal=False):
        im=Image.new('RGB',(1000,240),bg);d=ImageDraw.Draw(im);size=160
        while size>12 and d.textbbox((0,0),str(value),font=load_font(size))[2]>940:size-=8
        d.text((500,120),str(value),font=load_font(size),fill=ink,anchor='mm');return self.flat(name,parent,pos,w,h,im,horizontal)
    def lock(self,key,parent,pos,digits,view,label=''):
        n=self.group(key,pos,parent);self.box('lcd_lock_bezel',[0,0,0],[.30,.038,.14],'iron',n)
        self.text(key+'_display',n,[0,-.021,.016],.26,.076,'0'*digits,bg=(48,67,56),ink=(224,228,191))
        self.lock_screens[key]=self.S.Shader(self.stage.GetPrimAtPath(str(self.mats['r11_'+key+'_display'].GetPath())+'/texture'));self.lock_values[key]='0'*digits
        if label:self.text(key+'_hint',n,[0,-.021,-.043],.25,.030,label)
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

    def aperture_plate(self,name,parent,depth,colour):
        n=self.group(name,[0,depth,-.25],parent)
        for x in [-.315,.315]:self.box('aperture_side',[x,0,0],[.47,.018,.36],colour,n)
        for z in [-.16,.16]:self.box('aperture_end',[0,0,z],[.16,.018,.04],colour,n)
        for x in [-.48,.48]:self.box('slider_tab',[x,-.012,0],[.045,.020,.11],'steel',n)
        return n
    def soap_bottle(self,name,parent,pos,colour):
        n=self.group(name,pos,parent);self.box('detergent_body',[0,0,.09],[.11,.075,.18],colour,n,bevel=.025)
        self.cylinder('detergent_neck',[0,0,.20],.022,.045,colour,'z',n,n=24);self.cylinder('bottle_cap',[0,0,.229],.027,.022,'laundry_enamel','z',n,n=24)
        self.box('detergent_label',[0,-.039,.09],[.075,.004,.073],'clean_cloth',n,bevel=.002);return n
    def build(self,g):
        self.room_shell('laundry_room',size=(5,4.8),openings={'south':[(1.97,3.07)]})
        self.box('solid_subfloor',[2.5,2.4,-.075],[5.14,4.94,.10],'darkwood',bevel=.001)
        self.box('matte_tile_floor',[2.5,2.4,.006],[5,4.8,.012],'floor_tile',bevel=.001)
        for x in np.arange(.5,5,.5):self.box('floor_grout',[float(x),2.4,.0125],[.005,4.8,.001],'grout',bevel=.0001)
        for y in np.arange(.5,4.8,.5):self.box('floor_grout',[2.5,float(y),.0125],[5,.005,.001],'grout',bevel=.0001)
        self.filter=self.group('laundry_filter_unit',[.38,2.20,0]);self.transform(self.filter,rpy=[0,0,90])
        self.box('filter_left_side',[-.88,-.06,.58],[.045,.64,1.04],'laundry_enamel',self.filter)
        self.box('filter_back',[0,.245,.58],[1.79,.045,1.04],'laundry_blue',self.filter)
        self.box('filter_base',[0,-.06,.08],[1.79,.64,.055],'steel',self.filter);self.box('filter_top',[0,-.06,1.10],[1.82,.67,.045],'laundry_enamel',self.filter)
        for z,h in [(.40,.64),(1.075,.05)]:self.box('cutaway_lower_upper',[.88,-.06,z],[.045,.64,h],'laundry_enamel',self.filter)
        for y in [-.36,.23]:self.box('cutaway_vertical_edge',[.88,y,.88],[.045,.05,.34],'laundry_enamel',self.filter)
        self.box('side_cutaway_glass',[.883,-.06,.88],[.012,.53,.32],'basin_glass',self.filter)
        self.add_obstacle(.04,1.28,.77,3.12)
        self.hatch=self.group('inspection_hatch_hinge',[0,-.40,1.12],self.filter)
        frame=self.group('inspection_hatch_frame',parent=self.hatch)
        for x in [-.635,.635]:self.box('hatch_side_frame',[x,-.045,-.275],[.45,.035,.55],'laundry_enamel',frame)
        self.box('hatch_top_frame',[0,-.045,-.04],[.82,.035,.08],'laundry_enamel',frame)
        self.box('hatch_lower_panel',[0,-.045,-.435],[.82,.035,.23],'laundry_enamel',frame)
        self.reg_at('s2_cover',frame,'filter inspection hatch',[1.75,2.25],[.82,2.2,.86])
        self.plates=[self.aperture_plate('front_aperture_plate',self.hatch,-.020,'steel'),self.aperture_plate('rear_aperture_plate',self.hatch,.040,'rear_plate')]
        for y in [-.025,.040]:
            for z in [-.438,-.062]:self.box('plate_guide_rail',[0,y,z],[1.70,.030,.020],'iron',self.hatch)
        self.handle=self.group('inside_filter_handle',[0,-.25,.87],self.filter)
        self.tube('handle_left',[-.04,0,-.062],[-.04,-.025,.062],.010,'brass',self.handle);self.tube('handle_right',[.04,0,-.062],[.04,-.025,.062],.010,'brass',self.handle)
        self.tube('handle_grip',[-.04,-.025,.062],[.04,-.025,.062],.012,'brass',self.handle)
        self.reg_at('filter_hatch_handle',self.handle,'inner filter handle',[1.75,2.25],[.65,2.2,.87])
        self.reg_at('s1_clue',frame,'two inspection apertures',[1.75,2.25],[.79,2.2,.87])
        for j,title in enumerate(['FRONT','REAR']):
            button=self.group('inspection_slider_button_'+str(j),[-.25+j*.50,-.085,-.47],self.hatch)
            self.cylinder('slider_button',[0,0,0],.048,.028,'iron','y',button,n=28)
            self.text('slider_button_mark_'+str(j),button,[0,-.015,0],.083,.052,'→')
            self.text('slider_layer_name_'+str(j),self.hatch,[-.25+j*.50,-.065,-.385],.26,.048,title)
            self.reg_at('s1_control_'+str(j),button,LABELS['s1_control_'+str(j)],[1.75,2.25],[.85,2.2,.66])
        self.drain=self.group('internal_drain_button',[.40,-.27,.66],self.filter)
        self.cylinder('drain_button_bezel',[0,0,0],.062,.040,'iron','y',self.drain,n=28);self.cylinder('drain_button_cap',[0,-.026,0],.049,.020,'laundry_blue','y',self.drain,n=28)
        self.text('drain_button_label',self.drain,[0,-.037,0],.080,.055,'↓');self.reg_at('s2_setup',self.drain,'drain button',[1.75,2.25],[.69,2.6,.66])
        self.tube('drain_hose_west',[.17,2.78,.24],[.17,4.55,.24],.025,'rubber');self.tube('drain_hose_north',[.17,4.55,.24],[3.35,4.55,.24],.025,'rubber')
        washer=self.group('front_loading_washer',[1.25,4.40,0]);self.box('washer_body',[0,0,.43],[.78,.64,.82],'laundry_enamel',washer,bevel=.025)
        self.box('washer_top',[0,0,.86],[.82,.67,.045],'laundry_enamel',washer)
        self.cylinder('washer_door_rim',[0,-.335,.44],.254,.035,'steel','y',washer,n=48);self.cylinder('washer_dark_window',[0,-.356,.44],.214,.015,'laundry_blue','y',washer,n=48)
        self.box('washer_handle',[.21,-.385,.46],[.045,.04,.12],'iron',washer);self.box('washer_controls',[0,-.326,.75],[.64,.018,.11],'laundry_blue',washer)
        self.cylinder('washer_dial',[-.23,-.349,.75],.037,.025,'steel','y',washer,n=28);self.text('washer_label',washer,[.10,-.339,.75],.30,.060,'WASH')
        self.soap_bottle('detergent_a',washer,[-.17,.03,.883],'laundry_blue');self.soap_bottle('detergent_b',washer,[.11,.03,.883],'rear_plate');self.add_obstacle(.83,4.06,1.67,4.75)
        self.table('laundry_basin_stand',(3.35,4.40),(1.45,.68),height=.61)
        self.basin=self.group('drain_observation_basin',[3.35,4.40,0])
        self.box('basin_bottom',[0,0,.673],[1.11,.48,.035],'steel',self.basin)
        for x in [-.555,.555]:self.box('basin_side',[x,0,.925],[.025,.48,.49],'basin_glass',self.basin)
        self.box('basin_rear',[0,.235,.925],[1.12,.022,.49],'laundry_enamel',self.basin)
        self.box('basin_front_glass',[0,-.235,.925],[1.12,.012,.49],'basin_glass',self.basin)
        for x in [-.56,.56]:self.box('basin_front_metal_edge',[x,-.246,.925],[.025,.022,.50],'steel',self.basin)
        for z in [.685,1.17]:self.box('basin_front_metal_edge',[0,-.246,z],[1.15,.022,.025],'steel',self.basin)
        self.box('inside_number_plate',[0,.214,.90],[.86,.018,.25],'clean_cloth',self.basin)
        image=Image.new('RGB',(1200,360),(222,217,194));dr=ImageDraw.Draw(image);dr.text((600,180),'1420',font=load_font(284),fill=(24,41,38),anchor='mm');image=ImageOps.mirror(image)
        codeface=self.flat('fixed_mirrored_plate',self.basin,[0,.202,.90],.83,.23,image);self.reg_at('s2_clue',codeface,'mirrored plate inside the basin',[3.25,3.5],[3.35,4.602,.90])
        self.water=self.group('actual_soapy_water',[0,-.025,.69],self.basin);self.box('soapy_water_volume',[0,0,.5],[1.055,.425,1.0],'cloudy_soapy_water',self.water)
        with self.og.sim.editing_usd():self.water_scale=self.G.Xformable(self.water['prim']).AddScaleOp()
        self.set_water(.445)
        self.buttons=self.group('laundry_button_cabinet',[4.62,2.35,0]);self.transform(self.buttons,rpy=[0,0,-90])
        for x in [-.68,.68]:self.box('button_cabinet_side',[x,0,.39],[.04,.55,.66],'wood',self.buttons)
        self.box('button_cabinet_back',[0,.245,.39],[1.40,.03,.66],'paint',self.buttons);self.box('button_cabinet_base',[0,0,.09],[1.42,.58,.05],'darkwood',self.buttons)
        self.box('folding_counter',[0,0,.72],[1.47,.62,.08],'wood',self.buttons);self.add_obstacle(4.29,1.60,4.96,3.10)
        self.button_case=self.group('button_sorting_case',[0,0,.1225],self.buttons)
        for x in [-.35,.35]:self.box('button_case_sides',[x,-.04,.90],[.025,.42,.50],'wood',self.button_case)
        self.box('button_case_back',[0,.16,.90],[.72,.025,.50],'wood',self.button_case);self.box('button_case_top',[0,-.04,1.16],[.74,.44,.035],'wood',self.button_case)
        self.box('button_case_base',[0,-.04,.65],[.72,.42,.025],'wood',self.button_case)
        self.box('button_cloth_board',[0,-.215,.91],[.63,.020,.43],'laundry_felt',self.button_case)
        self.button_rows=self.group('three_actual_button_rows',parent=self.button_case)
        for row,count in enumerate([3,1,2]):
            for j in range(count):
                x=(j-(count-1)/2)*.13;z=1.045-row*.135;self.cylinder('sewing_button',[x,-.243,z],.040,.018,'clean_cloth','y',self.button_rows,n=28)
                for dx in [-.011,.011]:
                    for dz in [-.011,.011]:self.cylinder('button_hole',[x+dx,-.253,z+dz],.0042,.002,'iron','y',self.button_rows,n=12)
        self.reg_at('s3_clue',self.button_rows,'three rows of buttons',[3.5,2.25],[4.37,2.35,1.03])
        self.button_door=self.group('button_case_hinge',[-.36,-.275,.65],self.button_case)
        door=self.group('button_cupboard_door',parent=self.button_door);self.box('button_case_door',[.36,0,.255],[.72,.035,.51],'paint',door);self.box('button_case_handle',[.65,-.045,.25],[.023,.045,.13],'brass',door)
        self.reg_at('s3_cover',door,'button cupboard door',[3.5,2.25],[4.33,2.35,1.03]);self.lock('s2_lock',door,[.25,-.028,.27],4,[3.5,2.25])
        icon=Image.new('RGB',(180,160),(213,208,183));dr=ImageDraw.Draw(icon);dr.rectangle((31,18,149,116),outline=(62,95,89),width=10);dr.line((90,118,90,142),fill=(62,95,89),width=8);dr.line((61,144,119,144),fill=(62,95,89),width=8)
        self.flat('mirror_lock_icon',door,[.52,-.022,.27],.11,.10,icon)
        self.flat('basin_mirror_icon',self.basin,[-.47,-.249,1.115],.09,.08,icon)
        self.keydrawer,keyfront=self.drawer('key_drawer',self.buttons,(0,-.30),.54,width=1.18,depth=.44)
        self.reg_at('key_box',keyfront,'key drawer',[3.5,2.25],[4.32,2.35,.54]);self.lock('s3_lock',keyfront,[.30,-.042,0],3,[3.5,2.25])
        self.box('key_support_pad',[0,.21,-.021],[.92,.34,.158],'laundry_felt',self.keydrawer)
        self.key=self.tool('flat_brass_key',self.keydrawer,[0,.21,.069],'key');self.target_nodes.pop('flat_brass_key',None);self.transform(self.key,rpy=[90,0,0]);self.reg_at('key',self.key,'brass door key',[3.5,2.25],[4.09,2.35,.609])
        shirt=Image.new('RGB',(260,180),(211,207,184));dr=ImageDraw.Draw(shirt);dr.polygon([(34,46),(73,21),(97,42),(121,21),(158,46),(139,77),(126,66),(126,150),(66,150),(66,66),(52,77)],outline=(43,67,56),width=7);dr.line((207,39,207,137),fill=(43,67,56),width=8);dr.polygon([(207,145),(187,120),(227,120)],fill=(43,67,56))
        self.flat('button_count_icon',keyfront,[-.43,-.027,0],.18,.11,shirt)
        shelf=self.group('folded_laundry_rack',[.87,.25,0]);self.transform(shelf,rpy=[0,0,180])
        for x in [-.63,.63]:self.box('laundry_rack_upright',[x,0,.67],[.055,.37,1.34],'darkwood',shelf)
        for z in [.16,.73,1.28]:self.box('laundry_shelf',[0,0,z],[1.33,.41,.04],'wood',shelf)
        self.box('laundry_rack_back',[0,.16,.67],[1.28,.035,1.30],'paint',shelf)
        for row,z in enumerate([.22,.79,1.34]):
            for j in [-1,1]:self.box('folded_towels',[j*.29,0,z],[.44,.30,.095],'clean_cloth' if row%2==0 else 'cloth_blue',shelf,bevel=.012)
        self.add_obstacle(.18,.04,1.56,.48)
        self.mat('laundry_window',(.50,.63,.63),rough=.9,emission=(.12,.16,.15));self.box('window_glass',[4.925,4.10,1.72],[.022,.72,.70],'laundry_window')
        for y in [3.71,4.49]:self.box('window_jamb',[4.90,y,1.72],[.06,.035,.77],'darkwood')
        for z in [1.34,1.72,2.10]:self.box('window_rail',[4.90,4.10,z],[.06,.81,.035],'darkwood')
        self.exit_node=self.door('laundry_exit',[2.0,.06,0],1.04);self.reg_at('exit',self.exit_node,'exit door',[2.5,1.0],[2.52,.06,1.12]);self.door_view=[2.5,1.0]
        for x in [1.98,3.06]:self.box('exit_jamb',[x,.05,1.14],[.065,.17,2.30],'paint')
        self.box('exit_lintel',[2.52,.05,2.29],[1.15,.17,.065],'paint')
        for x in [1.99,3.05]:self.box('exit_stop_jamb',[x,.01,1.14],[.035,.026,2.28],'darkwood')
        self.box('exit_stop_top',[2.52,.01,2.28],[1.13,.026,.035],'darkwood')
        self.stage_views=[[1.75,2.25],[3.25,3.5],[3.5,2.25]];self.stage_centres=[[.8,2.2,.87],[3.35,4.60,.90],[4.37,2.35,1.03]]
        self.bases=[([.38,2.2],90),([3.35,4.40],0),([4.62,2.35],-90)]
        self.sync(g)
    def set_water(self,height):
        with self.og.sim.editing_usd():self.water_scale.Set(self.F.Vec3f(1,1,float(height)))
    def visible(self,key,g):
        if key=='s2_setup':return bool(g.opened['s2_cover'])
        if key=='s3_clue':return bool(g.opened['s3_cover'])
        if key=='key':return bool(g.opened['key_box']) and key not in g.taken
        return key in self.target_nodes
    def sync(self,g):
        for j,n in enumerate(self.plates):self.transform(n,[(g.states[0]['angles'][j]-SPEC['stages'][0]['target'][j])*.12,[-.020,.040][j],-.25])
        self.transform(self.hatch,rpy=[-150 if g.opened['s2_cover'] else 0,0,0]);self.set_water(.035 if g.states[1]['setup_used'] else .445)
        self.transform(self.button_door,rpy=[0,0,-110 if g.opened['s3_cover'] else 0])
        n,pos=self.drawers['key_drawer'];self.transform(n,[pos[0],pos[1]-(.42 if g.opened['key_box'] else 0),pos[2]])
        for key,shader in self.lock_screens.items():
            index=1 if key=='s2_lock' else 2;value=g.states[index].get('entered_code','0000' if index==1 else '000')
            if self.lock_values[key]!=value:
                im=Image.new('RGB',(1000,240),(48,67,56));d=ImageDraw.Draw(im);size=160
                while size>12 and d.textbbox((0,0),value,font=load_font(size))[2]>940:size-=8
                d.text((500,120),value,font=load_font(size),fill=(224,228,191),anchor='mm');p=self.tex/(key+'_entered_'+hashlib.sha256(value.encode()).hexdigest()[:12]+'.png');im.save(p)
                with self.og.sim.editing_usd():shader.GetInput('file').Set(str(p))
                self.lock_values[key]=value
        self.visibility(self.key,'key' not in g.taken);self.transform(self.exit_node,rpy=[0,0,-103 if g.opened['exit'] else 0])
        self.expanded=[]
        for flag,node in [(g.opened['s2_cover'],self.hatch),(g.opened['s3_cover'],self.button_door),(g.opened['key_box'],self.keydrawer)]:
            if flag:
                points=self.triangles(node).reshape(-1,3);self.expanded.append((points.min(0)[:2]-.12,points.max(0)[:2]+.12))
        self.centres={}
        for key,node in self.target_nodes.items():
            pts=self.triangles(node).reshape(-1,3)
            if pts.size:self.centres[key]=((pts.min(0)+pts.max(0))/2).tolist()
    def candidates(self,g):return self.base_candidates([k for k in self.target_nodes if self.visible(k,g)])
    def blocked(self,x,y,g):return super().blocked(x,y,g) or any(lo[0]<x<hi[0] and lo[1]<y<hi[1] for lo,hi in self.expanded)
    def view_for(self,key):return self.views.get(key,[2.5,1.0])
    def focus_for(self,key):return self.focus.get(key,self.centres.get(key))
    def label_for(self,key):return self.labels.get(key,LABELS.get(key,key.replace('_',' ')))
    def animate(self,d,before):
        old=before.get('opened',{});prior=before['states'][0]['angles'];now=d.game.states[0]['angles']
        for j,(a,b) in enumerate(zip(prior,now)):
            if a!=b:
                for t in [.33,.67]:
                    self.sync(d.game);self.transform(self.plates[j],[((a+(b-a)*t)-SPEC['stages'][0]['target'][j])*.12,[-.020,.040][j],-.25]);d.frame(warm=4);d.append('Inspection aperture slides',4)
        if bool(old.get('s2_cover'))!=bool(d.game.opened['s2_cover']):
            for t in [.33,.67]:
                q=float(bool(old.get('s2_cover')))+(float(bool(d.game.opened['s2_cover']))-float(bool(old.get('s2_cover'))))*t;self.sync(d.game);self.transform(self.hatch,rpy=[-150*q,0,0]);d.frame(warm=4);d.append('Inspection hatch opens',4)
        if not before['states'][1].get('setup_used') and d.game.states[1]['setup_used']:
            for height in [.34,.23,.12,.035]:self.sync(d.game);self.set_water(height);d.frame(warm=5);d.append('Soapy water drains below the fixed mirrored plate',7)
        if bool(old.get('s3_cover'))!=bool(d.game.opened['s3_cover']):
            for t in [.33,.67]:
                q=float(bool(old.get('s3_cover')))+(float(bool(d.game.opened['s3_cover']))-float(bool(old.get('s3_cover'))))*t;self.sync(d.game);self.transform(self.button_door,rpy=[0,0,-110*q]);d.frame(warm=4);d.append('Button cupboard opens',4)
        if bool(old.get('key_box'))!=bool(d.game.opened['key_box']):
            n,p=self.drawers['key_drawer']
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

    observe('s1_clue','Observe the two real inspection holes and the inner handle')
    for _ in range(2):click('s1_control_0')
    click('s1_control_1');d.append('Both apertures now expose the inner handle',18)
    click('s2_cover','open');click('s2_setup')
    observe('s2_clue','Observe the fixed mirrored plate after the real water level falls')
    approach('s2_lock','Approach the button cupboard with the matching mirror-frame mark');click('s2_lock','unlock',code='1420')
    click('s3_cover','open');observe('s3_clue','Count the physical buttons from the upper row downward',stay=True)
    approach('s3_lock','Look at the three-digit button drawer lock',stay=True);click('s3_lock','unlock',code='312')
    click('key_box','open');d.append('Observe the flat key on the supported drawer lining',18);click('key','take')
    approach('exit','Return to the exit');click('exit','use','key');click('exit','open')
    if not exit_test(d.pos,g):raise RuntimeError('Open-door success was not reached')
