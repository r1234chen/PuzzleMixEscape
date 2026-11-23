import math
import numpy as np
from PIL import Image,ImageDraw,ImageOps
from easy88_core import make_level,reachable_approach
from easy88_scene import EasyScene
from font_utils import load_font

SPEC={
 'id':'R16','title':'Toiletry Store','chinese_title':'盥洗用品储藏间','theme':'bath',
 'size':[4.8,4.8],'door':{'side':'west','start':1.25,'width':1.04},
 'start':[1.0,1.75,1.35],'start_yaw':0,'floor':'tile',
 'stages':[
  {'kind':'mirror','name':'mirror-frame bottle cabinet','wall':'north',
   'answer':'0427','digits':4,'visual':{'type':'mirror','text':'0427'},'clue_text':''},
  {'kind':'read_code','name':'fixed bottle height cabinet','wall':'north',
   'answer':'364','digits':3,'visual':{'type':'bottle_heights','heights':[3,6,4],'levels':6},'clue_text':''},
  {'kind':'sequence','name':'comb direction box','wall':'north',
   'options':['left','up','right','down'],'answer':[3,2,1],'length':3,
   'visual':{'type':'comb_directions','directions':['down','right','up']},'clue_text':''}]}
SPEC['stages'][1]={'kind':'assign','name':'mixed-label cleaning bottles','wall':'north',
 'items':[{'id':'blue','name':'blue SOAP-labelled bottle'},{'id':'cream','name':'cream LOTION-labelled bottle'},{'id':'green','name':'green CLEANER-labelled bottle'}],
 'slots':1,'target':[0],'auto':False,'visual':{'type':'mislabelled_bottles'},
 'clue':{'all_labels_wrong':True,'blue_not':'lotion','bottle_labels':['soap','lotion','cleaner'],'recipient':'adhesive strip across comb-case cover'},
 'clue_text':'One soap, one lotion, one cleaner.\nEvery bottle label is wrong.\nThe blue bottle is not lotion.\nCLEANER → TAPE'}
Game,_OriginalScene,_OriginalStandard,exit_test,cpu_check=make_level(SPEC)
TITLE=SPEC['title'];LEVEL_ID=SPEC['id'];START=SPEC['start'];START_YAW=SPEC['start_yaw']
CAP=150;OBSERVATION_SIZE=(640,360);VISUAL_ONLY=False;READ_ENABLED=True;READ_FEEDBACK_TEXT=True
Game.LABELS.update({
 's1_clue':'fixed mirrored writing','s1_lock':'bottle cabinet code lock',
 's2_cover':'bottle cabinet cover','s2_clue':'three bottle tops and six-level ruler',
 's2_lock':'comb case code lock','s3_cover':'comb case cover','s3_clue':'three fixed combs',
 's3_confirm':'direction check icon','s3_reset':'direction clear icon',
 'key_box':'key drawer','key':'brass door key'})
Game.LABELS.update({'s2_clue':'bottle stock note','s2_slot_0':'adhesive strip on comb case',
 's2_item_0':'blue SOAP-labelled bottle','s2_item_1':'cream LOTION-labelled bottle','s2_item_2':'green CLEANER-labelled bottle'})
LABELS=Game.LABELS
_original_act=Game.act
Game.stage_accessible=lambda self,index:0<=index<3
Game.stage_exposed=lambda self,index:0<=index<3 and bool(self.states[index]['setup_ready'])
def _toiletry_act(self,a):
    key=a.get('_hit364');kind=a.get('action')
    if a.get('_validated364') and kind=='press' and (str(key).startswith('s3_choice_') or key in ('s3_confirm','s3_reset')) and not self.opened['s3_cover']:
        from action_feedback import failure_for
        return {'ok':False,'text':failure_for(kind)}
    result=_original_act(self,a)
    if a.get('_validated364') and kind=='unlock' and key in ('s1_lock','s2_lock'):
        self.states[0 if key=='s1_lock' else 1]['entered_code']=str(a.get('code',''))
    return result
Game.act=_toiletry_act
_toiletry_init=Game.__init__
def _cleaning_init(self):
    _toiletry_init(self);self.states[1]['cleaner_applied']=False
Game.__init__=_cleaning_init
_cleaning_base=Game.act
def _cleaning_act(self,a):
    key=str(a.get('_hit364',''));kind=a.get('action')
    if a.get('_validated364') and key.startswith('s2_item_'):
        from action_feedback import failure_for
        if kind=='read' and (self.opened['s2_cover'] or key in self.holding):return {'ok':True,'text':['SOAP','LOTION','CLEANER'][int(key[-1])]}
        if kind!='take' or not self.opened['s2_cover'] or key in self.holding:return {'ok':False,'text':failure_for(kind)}
        self.taken.add(key);self.holding.append(key);return {'ok':True,'text':''}
    if a.get('_validated364') and key=='s2_slot_0':
        from action_feedback import failure_for,NO_ITEM
        if kind=='read' and not self.states[1]['cleaner_applied']:return {'ok':True,'text':'TAPE'}
        if kind!='use':return {'ok':False,'text':failure_for(kind)}
        item=self._resolve_item(a.get('item'))
        if item is None:return {'ok':False,'text':NO_ITEM}
        if item!='s2_item_0':return {'ok':False,'text':failure_for(kind)}
        self.states[1]['cleaner_applied']=True;self.states[1]['setup_used']=True;self.states[1]['assignment']={0:0};self.solved[1]=True
        return {'ok':True,'text':''}
    if a.get('_validated364') and key in ('s2_lock','s2_confirm','s2_reset'):
        from action_feedback import failure_for
        return {'ok':False,'text':failure_for(kind)}
    return _cleaning_base(self,a)
Game.act=_cleaning_act

class Scene(EasyScene):
    def __init__(self,og,run):
        super().__init__(og,run,SPEC)
        self.views={};self.focus={};self.labels={};self.drawers={}
        self.lock_shaders={};self.lock_values={};self.expanded=[];self.screen_signature=None
    def palette(self):
        super().palette()
        for name,c in [
          ('bath_enamel',(.66,.71,.68)),('bath_green',(.26,.40,.35)),
          ('bath_blue',(.20,.37,.44)),('bath_cream',(.76,.73,.62)),
          ('bath_tile',(.53,.57,.55)),('tile_grout',(.34,.38,.36)),
          ('comb_ivory',(.78,.74,.61)),('comb_felt',(.21,.32,.29)),
          ('towel_blue',(.28,.43,.45)),('soap_white',(.73,.74,.65))]:
            self.mat(name,c,rough=.92)
        self.mat('frosted_mirror',(.44,.57,.57),rough=.18,metal=.35)
    def reg_at(self,key,node,label,view,focus=None):
        self.reg(key,node);self.views[key]=list(view);self.labels[key]=label
        if focus is not None:self.focus[key]=list(focus)
        return node
    def flat(self,name,parent,pos,w,h,im,horizontal=False):
        path=self.tex/(name+'.png');im.save(path)
        return self.plane(name,pos,w,h,(1,0,0),(0,1,0) if horizontal else (0,0,1),None,parent,material=self.image_mat('r16_'+name,path))
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
        mat=self.mats['r16_'+key+'_display']
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
    def fixed_bottle(self,j,level=3):
        x=(j-1)*.31;height=.22
        node=self.group('toiletry_bottle_'+str(j),[x,.09,.78],self.bottle_case)
        material=['bath_blue','bath_cream','bath_green'][j]
        self.cylinder('bottle_body',[0,0,.075],.060,.15,material,'z',node,n=32)
        self.cylinder('bottle_neck',[0,0,.172],.028,.045,material,'z',node,n=28)
        self.cylinder('bottle_cap',[0,0,.205],.034,.030,'bath_enamel','z',node,n=28)
        self.text('bottle_wrong_label_'+str(j),node,[0,-.061,.075],.103,.061,['SOAP','LOTION','CLEANER'][j])
        self.reg_at('s2_item_'+str(j),node,LABELS['s2_item_'+str(j)],[3.0,3.25]);return node
    def arrow(self,draw,direction,cx,cy,size,colour):
        points=[(.43,0),(.07,-.32),(.07,-.12),(-.42,-.12),(-.42,.12),(.07,.12),(.07,.32)]
        angle={'right':0,'down':math.pi/2,'left':math.pi,'up':-math.pi/2}[direction]
        c,s=math.cos(angle),math.sin(angle)
        draw.polygon([(cx+size*(x*c-y*s),cy+size*(x*s+y*c)) for x,y in points],fill=colour)
    def direction_screen(self,buffer,solved=False):
        im=Image.new('RGB',(1200,384),(29,45,41));d=ImageDraw.Draw(im)
        d.arc((38,38,112,112),35,306,fill=(216,224,191),width=9)
        d.polygon([(111,34),(117,73),(82,54)],fill=(216,224,191))
        for j in range(3):
            x=290+j*245
            d.rounded_rectangle((x-86,15,x+86,137),radius=12,fill=(43,62,52),outline=(110,140,114),width=3)
            if j<len(buffer):self.arrow(d,SPEC['stages'][2]['options'][buffer[j]],x,76,105,(225,221,191))
            else:d.line((x-28,79,x+28,79),fill=(124,148,124),width=7)
        d.line([(1062,74),(1093,108),(1161,34)],fill=(224,229,192),width=11)
        for j,direction in enumerate(SPEC['stages'][2]['options']):
            x=150+j*300
            d.rounded_rectangle((x-130,161,x+130,371),radius=14,fill=(43,63,52),outline=(99,130,106),width=3)
            self.arrow(d,direction,x,265,158,(226,221,188))
        d.rounded_rectangle((3,3,1197,381),radius=16,outline=(97,157,103) if solved else (94,124,103),width=5)
        path=self.tex/('comb_input_'+(''.join(map(str,buffer)) or 'empty')+('_ok' if solved else '')+'.png')
        im.save(path);return path
    def direction_piece(self,key,rect,target=True):
        x0,y0,x1,y1=rect
        points=[((x/1200-.5)*.80,-.20+(.5-y/384)*.256,.7875) for x,y in [(x0,y1),(x1,y1),(x1,y0),(x0,y0)]]
        uv=[(x0/1200,1-y1/384),(x1/1200,1-y1/384),(x1/1200,1-y0/384),(x0/1200,1-y0/384)]
        node=self.mesh(key+'_glass',points,[[0,1,2,3]],self.screen_mat,self.comb_case,uv=uv)
        if target:self.reg_at(key,node,LABELS.get(key,key.replace('_',' ')),[1.25,3.25],[1.30,4.20,.99])
        return node
    def real_comb(self,j,pose):
        node=self.group('fixed_comb_'+str(j),[(j-1)*.34,.070,.99],self.comb_case)
        self.box('comb_spine',[0,0,.040],[.24,.018,.030],'comb_ivory',node,bevel=.006)
        for k in range(9):
            self.box('actual_comb_tooth',[(k-4)*.024,0,-.020],[.009,.015,.090],'comb_ivory',node,bevel=.002)
        for x in [-.07,.07]:
            self.cylinder('comb_mounting_pin',[x,.017,.040],.006,.020,'brass','y',node,n=16)
        self.transform(node,rpy=pose)
        self.reg_at('fixed_comb_'+str(j),node,'fixed comb',[1.25,3.25])
        return node
    def soap_prop(self,name,parent,pos):
        node=self.group(name,pos,parent)
        self.cylinder('soap_body',[0,0,.09],.042,.18,'bath_green','z',node,n=24)
        self.cylinder('soap_cap',[0,0,.20],.030,.04,'bath_enamel','z',node,n=24)
        self.box('soap_label',[0,-.043,.09],[.055,.003,.072],'soap_white',node,bevel=.001)
        return node
    def build(self,g):
        self.room_shell('toiletry_store',size=(4.8,4.8),openings={'west':[(1.22,2.32)]})
        self.box('solid_subfloor',[2.4,2.4,-.075],[4.94,4.94,.10],'darkwood',bevel=.001)
        self.box('matte_bath_floor',[2.4,2.4,.006],[4.8,4.8,.012],'bath_tile',bevel=.001)
        for x in np.arange(.6,4.8,.6):
            self.box('floor_grout',[float(x),2.4,.0125],[.005,4.8,.001],'tile_grout',bevel=.0001)
        for y in np.arange(.6,4.8,.6):
            self.box('floor_grout',[2.4,float(y),.0125],[4.8,.005,.001],'tile_grout',bevel=.0001)

        self.table('shared_toiletry_vanity',(2.40,4.38),(3.35,.70),height=.72)
        for y in [4.15,4.61]:
            self.box('vanity_middle_support',[2.40,y,.36],[.075,.075,.72],'iron')

        self.mirror=self.group('fixed_wall_mirror',[1.30,4.70,1.58])
        self.box('mirror_frame',[0,0,0],[.90,.045,.64],'wood',self.mirror)
        self.box('frosted_mirror_panel',[0,-.024,0],[.83,.012,.57],'frosted_mirror',self.mirror)
        image=Image.new('RGB',(1200,900),(181,202,198));d=ImageDraw.Draw(image)
        d.text((600,450),'0427',font=load_font(365),fill=(28,47,43),anchor='mm')
        face=self.flat('fixed_mirror_writing',self.mirror,[0,-.031,0],.80,.50,ImageOps.mirror(image))
        self.reg_at('s1_clue',face,'fixed mirrored writing',[1.25,3.25],[1.30,4.669,1.58])
        for x in [-.43,.43]:
            self.box('mirror_wall_bracket',[x,.025,0],[.025,.055,.40],'steel',self.mirror)

        self.bottle_case=self.group('bottle_height_cabinet',[3.00,4.38,0])
        for x in [-.67,.67]:
            self.box('bottle_case_side',[x,-.02,1.10],[.035,.56,.66],'wood',self.bottle_case)
        self.box('bottle_case_back',[0,.245,1.10],[1.37,.03,.66],'paint',self.bottle_case)
        self.box('bottle_case_floor',[0,-.02,.770],[1.37,.56,.020],'wood',self.bottle_case)
        self.box('bottle_case_roof',[0,-.02,1.435],[1.40,.59,.030],'wood',self.bottle_case)
        self.bottles=[self.fixed_bottle(j) for j in range(3)]
        self.ruler=self.group('bottle_stock_note',[0,.159,1.235],self.bottle_case)
        im=Image.new('RGB',(1500,500),(225,218,191));ink=ImageDraw.Draw(im)
        ink.text((55,20),'One soap, one lotion, one cleaner.',font=load_font(54),fill=(37,53,44))
        ink.text((55,95),'Every bottle label is wrong.',font=load_font(60),fill=(37,53,44))
        ink.text((55,175),'The blue bottle is not lotion.',font=load_font(60),fill=(37,53,44))
        ink.text((95,355),'CLEANER',font=load_font(59),fill=(37,53,44))
        ink.line((575,389,845,389),fill=(37,53,44),width=12);ink.polygon([(845,389),(804,362),(804,416)],fill=(37,53,44))
        ink.rectangle((975,325,1290,465),fill=(171,141,88),outline=(83,71,46),width=5)
        ink.polygon([(1230,325),(1290,325),(1290,387)],fill=(224,215,185))
        ink.text((1132,395),'TAPE',font=load_font(47),fill=(48,53,41),anchor='mm')
        self.flat('stock_note_print',self.ruler,[0,-.003,0],1.15,.33,im)
        self.reg_at('s2_clue',self.ruler,'bottle stock note',[3.0,3.25],[3.0,4.44,1.24])
        self.bottle_cover=self.group('bottle_cover_hinge',[0,-.36,1.42],self.bottle_case)
        bottle_door=self.group('bottle_cover_face',parent=self.bottle_cover)
        self.box('opaque_bottle_cover',[0,0,-.33],[1.40,.036,.66],'paint',bottle_door)
        self.box('bottle_cover_pull',[0,-.045,-.58],[.19,.045,.030],'brass',bottle_door)
        self.reg_at('s2_cover',bottle_door,'bottle cabinet cover',[3.0,3.25],[3.0,4.02,1.10])
        self.numeric_lock('s1_lock',bottle_door,[0,-.028,-.39],4,[3.0,3.25])
        icon=Image.new('RGB',(200,190),(216,212,186));d=ImageDraw.Draw(icon)
        d.rectangle((36,21,164,132),outline=(57,88,80),width=11)
        d.line((100,135,100,163),fill=(57,88,80),width=8)
        d.line((71,166,129,166),fill=(57,88,80),width=8)
        self.flat('mirror_lock_mark',bottle_door,[.26,-.020,-.39],.10,.10,icon)

        self.comb_case=self.group('comb_pattern_case',[1.30,4.38,0])
        for x in [-.59,.59]:
            self.box('comb_case_side',[x,-.08,1.01],[.03,.62,.49],'wood',self.comb_case)
        self.box('comb_case_back',[0,.215,1.01],[1.21,.03,.49],'wood',self.comb_case)
        self.box('comb_case_floor',[0,-.08,.765],[1.21,.62,.010],'wood',self.comb_case)
        self.box('comb_case_roof',[0,-.08,1.255],[1.24,.63,.025],'wood',self.comb_case)
        self.box('comb_felt_backing',[0,.102,.99],[1.12,.020,.39],'comb_felt',self.comb_case)
        self.combs=[]
        for j,pose in enumerate([(0,0,0),(0,-90,0),(0,180,0)]):
            self.combs.append(self.real_comb(j,pose))
        self.reg_at('s3_clue',self.comb_case,'three actual comb tooth directions',[1.25,3.25],[1.30,4.45,.99])
        order=Image.new('RGB',(1200,90),(211,209,186));d=ImageDraw.Draw(order)
        d.line((70,45,1125,45),fill=(43,70,55),width=7)
        d.polygon([(1125,45),(1082,17),(1082,73)],fill=(43,70,55))
        self.flat('comb_read_order',self.comb_case,[0,.090,.82],.65,.048,order)
        self.box('comb_input_bezel',[0,-.20,.775],[.85,.30,.020],'iron',self.comb_case)
        self.screen_mat=self.image_mat('comb_direction_lcd',self.direction_screen([]))
        self.screen_shader=self.S.Shader(self.stage.GetPrimAtPath(str(self.screen_mat.GetPath())+'/texture'))
        self.direction_piece('s3_reset',(0,0,170,150))
        self.direction_piece('input_slots',(170,0,1030,150),False)
        self.direction_piece('s3_confirm',(1030,0,1200,150))
        for j in range(4):self.direction_piece('s3_choice_'+str(j),(j*300,150,(j+1)*300,384))
        self.comb_cover=self.group('comb_cover_hinge',[-.62,-.415,.775],self.comb_case)
        comb_door=self.group('comb_cover_face',parent=self.comb_cover)
        self.box('opaque_comb_cover',[.62,0,.24],[1.24,.036,.48],'paint',comb_door)
        self.box('comb_cover_pull',[.62,-.043,.08],[.18,.044,.030],'brass',comb_door)
        self.reg_at('s3_cover',comb_door,'comb case cover',[1.25,3.25],[1.30,3.965,1.02])
        self.box('seal_fixed_strike',[0,-.413,.756],[.26,.040,.035],'steel',self.comb_case)
        self.seal=self.group('adhesive_strip_hinge',[0,-.436,.740],self.comb_case)
        self.box('paper_adhesive_strip',[0,0,.085],[.18,.004,.17],'bath_cream',self.seal)
        self.text('adhesive_warning',self.seal,[0,-.003,.085],.15,.061,'TAPE')
        self.reg_at('s2_slot_0',self.seal,'adhesive strip on comb case',[1.25,3.25],[1.30,3.944,.825])
        self.keydrawer,keyfront=self.drawer('toiletry_key_drawer',None,(1.30,4.03),.54,width=1.10,depth=.44)
        self.reg_at('key_box',keyfront,'key drawer',[1.25,3.25],[1.30,4.03,.54])
        self.box('key_support_pad',[0,.21,-.021],[.90,.34,.158],'comb_felt',self.keydrawer)
        self.key=self.tool('flat_brass_key',self.keydrawer,[0,.21,.069],'key')
        self.target_nodes.pop('flat_brass_key',None)
        self.transform(self.key,rpy=[90,0,0])
        self.reg_at('key',self.key,'brass door key',[1.25,3.25],[1.30,3.82,.609])

        shelf=self.group('towel_and_soap_rack',[4.55,2.20,0])
        self.transform(shelf,rpy=[0,0,-90])
        for x in [-.61,.61]:
            self.box('towel_rack_post',[x,0,.70],[.055,.40,1.40],'darkwood',shelf)
        for z in [.15,.77,1.31]:
            self.box('towel_shelf',[0,0,z],[1.30,.43,.040],'wood',shelf)
        self.box('towel_rack_back',[0,.18,.70],[1.24,.035,1.37],'paint',shelf)
        for j in range(2):
            self.box('folded_hand_towels',[(j-.5)*.55,0,1.375],[.44,.31,.09],
                     'bath_cream' if j==0 else 'towel_blue',shelf,bevel=.012)
        for j in range(3):self.soap_prop('fixed_soap_'+str(j),shelf,[(j-1)*.32,0,.79])
        self.add_obstacle(4.30,1.53,4.78,2.87)
        basket=self.group('fixed_empty_storage_basket',[3.60,.30,0])
        self.box('basket_floor',[0,0,.035],[.68,.43,.050],'wood',basket)
        for x in [-.34,.34]:
            self.box('basket_side',[x,0,.19],[.025,.44,.31],'wood',basket)
        for y in [-.215,.215]:
            for z in [.09,.17,.25,.33]:
                self.box('basket_slatted_wall',[0,y,z],[.70,.018,.035],'darkwood',basket)
        self.add_obstacle(3.23,.04,3.97,.56)
        self.exit_node=self.door('toiletry_exit',[.06,2.29,0],1.04)
        self.door_angle=-90;self.door_view=[1.0,1.75]
        self.reg_at('exit',self.exit_node,'exit door',self.door_view,[.06,1.77,1.12])
        for y in [1.23,2.31]:
            self.box('door_jamb',[.05,y,1.14],[.17,.065,2.30],'paint')
        self.box('door_lintel',[.05,1.77,2.29],[.17,1.15,.065],'paint')
        for y in [1.24,2.30]:
            self.box('door_stop_jamb',[.01,y,1.14],[.026,.035,2.28],'darkwood')
        self.box('door_stop_top',[.01,1.77,2.28],[.026,1.13,.035],'darkwood')
        self.stage_views=[[1.25,3.25],[3.0,3.25],[1.25,3.25]]
        self.stage_centres=[[1.30,4.669,1.58],[3.0,4.44,1.06],[1.30,4.45,.99]]
        self.bases=[([1.30,4.70],0),([3.0,4.38],0),([1.30,4.38],0)]
        self.sync(g)
    def visible(self,key,g):
        if key=='s2_clue':return bool(g.opened['s2_cover'])
        if key.startswith('s2_item_'):return bool(g.opened['s2_cover']) and key not in g.holding
        if key=='s3_clue' or key.startswith('fixed_comb_') or key.startswith('s3_choice_') or key in ('s3_confirm','s3_reset'):
            return bool(g.opened['s3_cover'])
        if key=='key':return bool(g.opened['key_box']) and key not in g.taken
        return key in self.target_nodes
    def sync(self,g):
        for j,node in enumerate(self.bottles):self.visibility(node,'s2_item_'+str(j) not in g.holding)
        self.transform(self.seal,rpy=[180 if g.states[1].get('cleaner_applied') else 0,0,0])
        self.transform(self.bottle_cover,rpy=[-160 if g.opened['s2_cover'] else 0,0,0])
        self.transform(self.comb_cover,rpy=[0,0,-105 if g.opened['s3_cover'] else 0])
        for key,shader in self.lock_shaders.items():
            index=0 if key=='s1_lock' else 1
            value=g.states[index].get('entered_code','0000' if index==0 else '000')
            if self.lock_values[key]!=value:
                import hashlib
                image=self.text_image(value,.27,.088,(47,67,56),(224,228,191))
                path=self.tex/(key+'_entered_'+hashlib.sha256(value.encode()).hexdigest()[:12]+'.png')
                image.save(path)
                with self.og.sim.editing_usd():shader.GetInput('file').Set(str(path))
                self.lock_values[key]=value
        signature=(tuple(g.states[2]['buffer']),bool(g.solved[2]))
        if signature!=self.screen_signature:
            with self.og.sim.editing_usd():
                self.screen_shader.GetInput('file').Set(str(self.direction_screen(*signature)))
            self.screen_signature=signature
        node,pos=self.drawers['toiletry_key_drawer']
        self.transform(node,[pos[0],pos[1]-(.42 if g.opened['key_box'] else 0),pos[2]])
        self.visibility(self.key,'key' not in g.taken)
        self.transform(self.exit_node,rpy=[0,0,self.door_angle-(103 if g.opened['exit'] else 0)])
        self.expanded=[]
        for flag,node in [(g.opened['s2_cover'],self.bottle_cover),(g.opened['s3_cover'],self.comb_cover),(g.opened['key_box'],self.keydrawer)]:
            if flag:
                p=self.triangles(node).reshape(-1,3)
                self.expanded.append((p.min(0)[:2]-.12,p.max(0)[:2]+.12))
        self.centres={}
        for key,node in self.target_nodes.items():
            p=self.triangles(node).reshape(-1,3)
            if p.size:self.centres[key]=((p.min(0)+p.max(0))/2).tolist()
    def candidates(self,g):
        return self.base_candidates([k for k in self.target_nodes if self.visible(k,g)])
    def blocked(self,x,y,g):
        return super().blocked(x,y,g) or any(lo[0]<x<hi[0] and lo[1]<y<hi[1] for lo,hi in self.expanded)
    def view_for(self,key):return self.views.get(key,[1.0,1.75])
    def focus_for(self,key):return self.focus.get(key,self.centres.get(key))
    def label_for(self,key):return self.labels.get(key,LABELS.get(key,key.replace('_',' ')))
    def animate(self,d,before):
        if not before['states'][1].get('cleaner_applied') and d.game.states[1].get('cleaner_applied'):
            for q in [.33,.67]:
                self.sync(d.game);self.transform(self.seal,rpy=[180*q,0,0]);d.frame(warm=4);d.append('The adhesive strip peels away from the cover',4)
        old=before.get('opened',{})
        for key,node in [('s2_cover',self.bottle_cover),('s3_cover',self.comb_cover)]:
            if bool(old.get(key))!=bool(d.game.opened[key]):
                for q in [.33,.67]:
                    t=float(bool(old.get(key)))+(float(bool(d.game.opened[key]))-float(bool(old.get(key))))*q
                    self.sync(d.game);self.transform(node,rpy=[-160*t,0,0] if key=='s2_cover' else [0,0,-105*t])
                    d.frame(warm=4);d.append('Toiletry cover opens',4)
        if bool(old.get('key_box'))!=bool(d.game.opened['key_box']):
            node,p=self.drawers['toiletry_key_drawer']
            for q in [.33,.67]:
                t=float(bool(old.get('key_box')))+(float(bool(d.game.opened['key_box']))-float(bool(old.get('key_box'))))*q
                self.sync(d.game);self.transform(node,[p[0],p[1]-.42*t,p[2]])
                d.frame(warm=4);d.append('Key drawer opens',4)
        self.sync(d.game)

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
    observe('s1_clue','Observe the actual horizontally mirrored writing')
    approach('s1_lock','Approach the bottle cabinet lock with the matching mirror mark')
    click('s1_lock','unlock',code='0427');click('s2_cover','open')
    observe('s2_clue','Use the stock note and the three mismatched bottle labels',stay=True);click('s2_clue','read')
    approach('s2_item_0','Take the bottle whose content must be cleaner',stay=True);click('s2_item_0','take')
    approach('s2_slot_0','The cleaner diagram corresponds to the adhesive seal');click('s2_slot_0','use','s2_item_0')
    approach('s3_cover','Open the same comb cover after its adhesive strip releases',stay=True);click('s3_cover','open')
    observe('s3_clue','Observe the actual teeth of all three combs',stay=True)
    for j in [3,2,1]:click('s3_choice_'+str(j))
    click('s3_confirm')
    approach('key_box','Look down at the unlocked shallow key drawer',stay=True)
    click('key_box','open');d.append('Observe the flat key on its real drawer pad',18)
    click('key','take')
    approach('exit','Return to the exit')
    click('exit','use','key');click('exit','open')
    if not exit_test(d.pos,g):raise RuntimeError('Open-door success was not reached')


def cpu_check():
    import itertools
    checks=[];g=Game()
    def a(kind,key,**kw):return g.act(dict(action=kind,_hit364=key,_validated364=True,**kw))
    def ck(label,value):assert value,label;checks.append(label)
    ck('no bottle through closed cabinet',not a('take','s2_item_0')['ok'])
    ck('comb cover adhesive initially holds',not a('open','s3_cover')['ok'])
    ck('mirror code opens only first cabinet',a('unlock','s1_lock',code='0427')['ok'] and a('open','s2_cover')['ok'] and not g.solved[1])
    ck('stock note read is literal',a('read','s2_clue')['text']==SPEC['stages'][1]['clue_text'])
    labels=('soap','lotion','cleaner');solutions=[x for x in itertools.permutations(labels) if all(x[j]!=labels[j] for j in range(3)) and x[0]!='lotion']
    ck('self-contained bottle logic unique',solutions==[('cleaner','soap','lotion')])
    ck('take other labelled bottle',a('take','s2_item_2')['ok'])
    ck('wrong bottle leaves adhesive intact',not a('use','s2_slot_0',item='s2_item_2')['ok'] and not g.solved[1])
    ck('blue bottle can be taken',a('take','s2_item_0')['ok'])
    ck('cleaner releases actual adhesive only',a('use','s2_slot_0',item='s2_item_0')['ok'] and g.solved[1] and not g.opened['s3_cover'])
    ck('old bottle-height code removed',not a('unlock','s2_lock',code='364')['ok'])
    ck('open remains separate',a('open','s3_cover')['ok'])
    for j in [3,2,1]:ck('comb direction input '+str(j),a('press','s3_choice_'+str(j))['ok'])
    ck('comb pattern releases local key drawer',a('press','s3_confirm')['ok'])
    ck('open key drawer',a('open','key_box')['ok']);ck('take key',a('take','key')['ok']);ck('use exit key',a('use','exit',item='key')['ok']);ck('open exit completes',a('open','exit')['ok'] and g.exited)
    return {'level':'R16','scope':'CPU actual Game class; native visuals pending','passed':len(checks),'checks':checks}
