import math
import numpy as np
from PIL import Image,ImageDraw
from easy88_core import make_level,reachable_approach
from easy88_scene import EasyScene
from font_utils import load_font

FACTS="Window-side rack, level 1: striped box.\nRack away from the window, level 2: dotted box."
SPEC={
 'id':'R17','title':'Guest Linen Room','chinese_title':'客房布草间','theme':'linen',
 'size':[5.5,5.0],'cutout':{'corner':'north_east','size':[1.5,1.25]},
 'door':{'side':'south','start':1.25,'width':1.04},
 'start':[1.75,1.0,1.35],'start_yaw':90,'floor':'wood',
 'stages':[
  {'kind':'sequence','name':'two linen issue racks','wall':'west',
   'options':['window upper shelf','back upper shelf','window middle shelf','back middle shelf','window lower shelf','back lower shelf'],
   'answer':[4,3],'length':2,'distinct':True,
   'visual':{'type':'shelf_location','rows':3,'cols':2,'box_patterns':['plain','striped','dotted','dotted','striped','plain']},
   'clue_text':FACTS},
  {'kind':'measure','name':'cloth width measuring bench','wall':'north','answer':'0140',
   'setup':{'kind':'measure','item':'cloth_gauge','item_name':'cloth width gauge','target_name':'cloth strip','gate':True,'consume':False},
   'visual':{'type':'ruler','measurement':140,'unit':'mm','large_ticks':20},'clue_text':''},
  {'kind':'slide_align','name':'woven band linen case','wall':'north',
   'initial':[0,0],'target':[1,3],'moduli':[4,4],'auto':True,'code_after_alignment':False,
   'visual':{'type':'weave_align','target':[1,3],'levels':4,'fixed_side_anchors':True,'nonperiodic':True},'clue_text':''}]}
Game,_OriginalScene,_OriginalStandard,exit_test,cpu_check=make_level(SPEC)
TITLE=SPEC['title'];LEVEL_ID=SPEC['id'];START=SPEC['start'];START_YAW=SPEC['start_yaw']
CAP=150;OBSERVATION_SIZE=(640,360);VISUAL_ONLY=False;READ_ENABLED=True;READ_FEEDBACK_TEXT=True
Game.LABELS.update({
 's1_clue':'two printed linen rack facts','s1_confirm':'whole selection check icon','s1_reset':'selection clear icon',
 's2_cover':'central gauge drawer','s2_tool':'cloth width gauge','s2_setup':'cloth strip',
 's2_clue':'gauge own reading','s2_lock':'woven case millimetre lock','s3_cover':'woven band cover',
 's3_clue':'woven strips and fixed side anchors','s3_control_0':'upper woven strip button','s3_control_1':'lower woven strip button',
 'key_box':'linen key drawer','key':'brass door key'})
LABELS=Game.LABELS
_original_act=Game.act
Game.stage_accessible=lambda self,index:0<=index<3
Game.stage_exposed=lambda self,index:0<=index<3 and bool(self.states[index]['setup_ready'])
def _linen_act(self,a):
    key=a.get('_hit364');kind=a.get('action')
    if a.get('_validated364') and ((key=='s2_tool' and kind=='take' and not self.opened['s2_cover']) or (kind=='press' and str(key).startswith('s3_control_') and not self.opened['s3_cover'])):
        from action_feedback import failure_for
        return {'ok':False,'text':failure_for(kind)}
    result=_original_act(self,a)
    if a.get('_validated364') and kind=='unlock' and key=='s2_lock':
        self.states[1]['entered_code']=str(a.get('code',''))
    return result
Game.act=_linen_act

class Scene(EasyScene):
    def __init__(self,og,run):
        super().__init__(og,run,SPEC)
        self.views={};self.focus={};self.labels={};self.drawers={};self.expanded=[]
        self.selection_signature=None;self.number_value='0000';self.gauge_value=None;self.bands=[]
    def palette(self):
        super().palette()
        for name,c in [
          ('linen_cream',(.74,.70,.58)),('linen_blue',(.23,.36,.39)),
          ('linen_green',(.32,.40,.29)),('linen_felt',(.25,.34,.29)),
          ('cloth_strip_blue',(.18,.31,.35)),('basket_tan',(.53,.43,.28)),
          ('woven_backing',(.14,.23,.22))]:
            self.mat(name,c,rough=.94)
        self.mat('gauge_metal',(.58,.64,.65),rough=.30,metal=.70)
        self.mat('window_pale',(.54,.67,.67),rough=.9,emission=(.14,.19,.18))
    def reg_at(self,key,node,label,view,focus=None):
        self.reg(key,node);self.views[key]=list(view);self.labels[key]=label
        if focus is not None:self.focus[key]=list(focus)
        return node
    def flat(self,name,parent,pos,w,h,im,horizontal=False):
        path=self.tex/(name+'.png');im.save(path)
        return self.plane(name,pos,w,h,(1,0,0),(0,1,0) if horizontal else (0,0,1),None,parent,material=self.image_mat('r17_'+name,path))
    def text_image(self,text,w,h,bg=(219,213,188),ink=(35,54,43)):
        ih=360;iw=max(180,int(round(ih*w/h)));im=Image.new('RGB',(iw,ih),bg)
        d=ImageDraw.Draw(im);size=int(ih*.70)
        while size>12:
            b=d.textbbox((0,0),str(text),font=load_font(size))
            if b[2]-b[0]<iw*.85 and b[3]-b[1]<ih*.80:break
            size-=8
        d.text((iw/2,ih/2),str(text),font=load_font(size),fill=ink,anchor='mm')
        return im
    def text(self,name,parent,pos,w,h,value,horizontal=False):
        return self.flat(name,parent,pos,w,h,self.text_image(value,w,h),horizontal)
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
        self.box('drawer_pull',[0,-.055,.01],[min(.19,width*.45),.045,.028],'brass',face)
        self.drawers[key]=(node,[x,y,z]);return node,face
    def pattern_image(self,pattern):
        im=Image.new('RGB',(700,200),(217,209,181));d=ImageDraw.Draw(im)
        if pattern=='striped':
            for x in range(25,700,85):d.rectangle((x,6,x+31,194),fill=(65,94,87))
        elif pattern=='dotted':
            for x in range(50,700,100):
                for y in [50,150]:d.ellipse((x-17,y-17,x+17,y+17),fill=(65,94,87))
        d.rectangle((8,8,692,192),outline=(137,124,91),width=3)
        return im
    def issue_rack(self,key,y,window_side):
        root=self.group(key,[.30,y,0]);self.transform(root,rpy=[0,0,90])
        for x in [-.56,.56]:
            self.box('issue_rack_post',[x,0,.74],[.055,.40,1.48],'darkwood',root)
        self.box('issue_rack_back',[0,.18,.74],[1.12,.035,1.46],'paint',root)
        for level,z in enumerate([.16,.68,1.20],1):
            self.box('rack_shelf',[0,0,z],[1.18,.43,.040],'wood',root)
            box=self.group(key+'_fixed_box_'+str(level),[0,0,z+.12],root)
            self.box('fixed_reference_box',[0,0,0],[.80,.30,.20],'linen_cream',box,bevel=.012)
            self.box('reference_box_front_label',[0,-.153,0],[.74,.006,.18],'linen_cream',box,bevel=.001)
            row=3-level;index=row*2+(0 if window_side else 1)
            pattern=SPEC['stages'][0]['visual']['box_patterns'][index]
            self.flat(key+'_box_pattern_'+str(level),box,[0,-.157,0],.73,.175,self.pattern_image(pattern))
            self.reg_at('fixed_box_'+str(index),box,'fixed linen reference box',[1.5,round(y*4)/4])
            self.text(key+'_level_'+str(level),root,[-.49,-.217,z+.12],.065,.075,str(level))
            button=self.group('shelf_choice_'+str(index),[.48,-.215,z+.12],root)
            self.box('shelf_choice_bezel',[0,0,0],[.10,.024,.10],'iron',button)
            self.box('shelf_choice_cap',[0,-.016,0],[.075,.014,.075],'linen_cream',button)
            self.reg_at('s1_choice_'+str(index),button,LABELS['s1_choice_'+str(index)],[1.5,round(y*4)/4],[.53,y,.75])
        self.add_obstacle(.05,y-.61,.55,y+.61)
    def selection_screen(self,buffer,solved=False):
        im=Image.new('RGB',(1000,300),(30,46,41));d=ImageDraw.Draw(im)
        d.arc((25,100,101,176),35,306,fill=(218,225,189),width=9)
        d.polygon([(100,94),(105,131),(72,114)],fill=(218,225,189))
        for j in range(2):
            x=145+j*360
            d.rounded_rectangle((x,15,x+320,285),radius=15,outline=(112,145,111),width=4)
            if j<len(buffer):
                value=buffer[j];window=value%2==0;level=3-value//2
                if window:
                    d.rectangle((x+33,83,x+129,201),outline=(211,219,185),width=8)
                    d.line((x+81,85,x+81,200),fill=(211,219,185),width=5)
                    d.line((x+35,142,x+128,142),fill=(211,219,185),width=5)
                else:
                    d.rectangle((x+33,83,x+129,201),fill=(99,123,99),outline=(211,219,185),width=7)
                    for yy in [115,157]:d.line((x+35,yy,x+127,yy),fill=(211,219,185),width=5)
                d.text((x+239,150),str(level),font=load_font(167),fill=(226,225,190),anchor='mm')
            else:d.line((x+120,156,x+200,156),fill=(124,149,125),width=9)
        d.line([(875,139),(908,180),(977,87)],fill=(221,228,190),width=12)
        d.rounded_rectangle((3,3,997,297),radius=13,outline=(96,158,101) if solved else (92,125,98),width=5)
        path=self.tex/('linen_selection_'+(''.join(map(str,buffer)) or 'empty')+('_ok' if solved else '')+'.png')
        im.save(path);return path
    def selection_piece(self,key,x0,x1,target=True):
        points=[((x/1000-.5)*.58,-.30,.96+(.5-y/300)*.174) for x,y in [(x0,300),(x1,300),(x1,0),(x0,0)]]
        uv=[(x0/1000,0),(x1/1000,0),(x1/1000,1),(x0/1000,1)]
        node=self.mesh(key+'_display',points,[[0,1,2,3]],self.selection_mat,self.utility,uv=uv)
        if target:self.reg_at(key,node,LABELS[key],[1.5,3.0],[.65,2.95,.96])
    def gauge_model(self):
        node=self.group('actual_cloth_width_gauge')
        self.box('gauge_beam',[.045,.065,.014],[.28,.026,.018],'gauge_metal',node,bevel=.002)
        self.box('fixed_gauge_jaw',[-.075,.005,0],[.010,.13,.012],'gauge_metal',node,bevel=.001)
        self.moving_jaw=self.group('sliding_gauge_jaw',[-.025,0,0],node)
        self.box('moving_gauge_jaw',[0,.005,0],[.010,.13,.012],'gauge_metal',self.moving_jaw,bevel=.001)
        for k in range(11):
            x=-.070+k*.020
            self.box('twenty_mm_tick',[x,.065,.0235],[.0008,.022,.001],'iron',node,bevel=.0001)
        self.display_body=self.group('gauge_readout_case',[0,.075,.035],self.moving_jaw)
        self.box('gauge_lcd_body',[0,0,0],[.14,.070,.035],'iron',self.display_body,bevel=.003)
        self.gauge_screen=self.flat('gauge_own_lcd',self.display_body,[0,0,.020],.125,.052,self.gauge_display(False),True)
        mat=self.mats['r17_gauge_own_lcd']
        self.gauge_shader=self.S.Shader(self.stage.GetPrimAtPath(str(mat.GetPath())+'/texture'))
        return node
    def gauge_display(self,measured):
        im=Image.new('RGB',(1000,416),(49,70,58));d=ImageDraw.Draw(im)
        d.text((420,208),'140' if measured else '--',font=load_font(260),fill=(228,231,190),anchor='mm')
        d.text((877,278),'mm',font=load_font(104),fill=(220,228,186),anchor='mm')
        path=self.tex/('cloth_gauge_140mm.png' if measured else 'cloth_gauge_idle.png')
        im.save(path);return im
    def set_gauge(self,g,drawer_fraction=None,opening=None):
        measured=bool(g.states[1]['setup_used'])
        self.visibility(self.gauge,measured or 's2_tool' not in g.taken)
        if measured:self.transform(self.gauge,[2.10,4.50,.766],[0,0,0])
        else:
            q=float(g.opened['s2_cover']) if drawer_fraction is None else float(drawer_fraction)
            self.transform(self.gauge,[.46+.42*q,2.95,.515],[0,0,90])
        jaw=.075 if measured else -.025
        if opening is not None:jaw=float(opening)
        self.transform(self.moving_jaw,[jaw,0,0])
        if self.gauge_value!=measured:
            self.gauge_display(measured)
            path=self.tex/('cloth_gauge_140mm.png' if measured else 'cloth_gauge_idle.png')
            with self.og.sim.editing_usd():self.gauge_shader.GetInput('file').Set(str(path))
            self.gauge_value=measured
    def woven_pattern(self,row):
        im=Image.new('RGB',(1600,200),(220,213,183));d=ImageDraw.Draw(im)
        for x in range(0,1600,9):d.line((x,0,x,199),fill=(210,203,176),width=1)
        for y in range(0,200,9):d.line((0,y,1599,y),fill=(229,222,194),width=1)
        xs=[0,120,270,420,530,690,805,930,1040,1195,1340,1465,1599]
        ys=[100,95,40,135,65,155,35,115,55,148,83,121,60]
        if row:ys=[200-y for y in ys]
        d.line(list(zip(xs,ys)),fill=(44,91,66),width=10,joint='curve')
        d.line([(x,y-24 if not row else y+24) for x,y in zip(xs,ys)],fill=(147,89,50),width=8,joint='curve')
        return im
    def build(self,g):
        self.room_shell('guest_linen_room',size=(5.5,5),openings={'south':[(1.22,2.32)]})
        self.box('solid_subfloor',[2.75,2.5,-.075],[5.64,5.14,.10],'darkwood',bevel=.001)
        self.box('L_return_x',[4.0,4.375,1.4],[.12,1.25,2.8],'plaster')
        self.box('L_return_y',[4.75,3.75,1.4],[1.5,.12,2.8],'plaster')
        self.box('L_lower_x',[3.99,4.375,.51],[.14,1.25,1.02],'paint')
        self.box('L_lower_y',[4.75,3.74,.51],[1.5,.14,1.02],'paint')
        self.box('L_trim_x',[3.98,4.375,1.04],[.16,1.25,.045],'darkwood')
        self.box('L_trim_y',[4.75,3.73,1.04],[1.5,.16,.045],'darkwood')
        self.add_obstacle(3.94,3.69,5.56,5.06)

        self.issue_rack('window_side_rack',3.75,True)
        self.issue_rack('rack_away_from_window',2.15,False)
        self.box('real_window_glass',[.075,4.10,1.83],[.022,.65,.63],'window_pale')
        for y in [3.745,4.455]:
            self.box('window_jamb',[.10,y,1.83],[.07,.035,.70],'darkwood')
        for z in [1.48,1.83,2.18]:
            self.box('window_rail',[.10,4.10,z],[.07,.75,.035],'darkwood')

        sign=self.group('positive_location_facts',[.085,3.0,1.75])
        self.transform(sign,rpy=[0,0,90])
        self.box('facts_frame',[0,0,0],[1.34,.025,.38],'wood',sign)
        im=Image.new('RGB',(2000,560),(222,215,187));d=ImageDraw.Draw(im)
        lines=FACTS.split('\n');size=66
        while size>25 and max(d.textbbox((0,0),x,font=load_font(size))[2] for x in lines)>1900:size-=2
        for j,line in enumerate(lines):d.text((1000,155+j*245),line,font=load_font(size),fill=(35,55,42),anchor='mm')
        paper=self.flat('printed_location_facts',sign,[0,-.014,0],1.29,.34,im)
        self.reg_at('s1_clue',paper,'two printed linen rack facts',[1.5,3.0],[.10,3.0,1.75])

        self.utility=self.group('central_linen_tool_compartment',[.35,2.95,0])
        self.transform(self.utility,rpy=[0,0,90])
        self.box('utility_plinth',[0,0,.06],[.48,.48,.12],'darkwood',self.utility)
        for x in [-.25,.25]:
            self.box('utility_side',[x,0,.37],[.03,.48,.57],'wood',self.utility)
        self.box('utility_back',[0,.22,.37],[.53,.03,.57],'paint',self.utility)
        self.box('utility_top',[0,0,.66],[.58,.53,.08],'wood',self.utility)
        for x in [-.27,.27]:
            self.box('selection_display_support',[x,.02,.82],[.025,.035,.35],'wood',self.utility)
        self.box('selection_lcd_bezel',[0,-.275,.96],[.63,.045,.210],'iron',self.utility)
        self.selection_mat=self.image_mat('linen_selection_screen',self.selection_screen([]))
        self.selection_shader=self.S.Shader(self.stage.GetPrimAtPath(str(self.selection_mat.GetPath())+'/texture'))
        self.selection_piece('s1_reset',0,125)
        self.selection_piece('selection_slots',125,850,False)
        self.selection_piece('s1_confirm',850,1000)
        self.gaugedrawer,gaugefront=self.drawer('cloth_gauge_drawer',self.utility,(0,-.30),.48,width=.46,depth=.40)
        self.reg_at('s2_cover',gaugefront,'central gauge drawer',[1.5,3.0],[.66,2.95,.48])
        self.gauge_release=self.group('visible_gauge_drawer_bolt',[.25,-.342,.54],self.utility)
        self.box('gauge_latch_seat',[.025,0,0],[.065,.045,.070],'iron',self.gauge_release)
        self.gauge_pin=self.group('sliding_gauge_latch_pin',[-.045,-.026,0],self.gauge_release)
        self.box('gauge_latch_pin',[0,0,0],[.145,.025,.025],'brass',self.gauge_pin)
        self.gauge_release_lamps=[self.cylinder('gauge_drawer_red',[.19,-.337,.603],.011,.009,'red_led','y',self.utility,n=20),self.cylinder('gauge_drawer_green',[.19,-.337,.603],.011,.009,'green','y',self.utility,n=20)]
        self.tube('selector_release_conduit',[.27,-.304,.87],[.27,-.304,.58],.009,'steel',self.utility)

        self.box('gauge_support_pad',[0,.19,-.036],[.37,.32,.128],'linen_felt',self.gaugedrawer)
        self.gauge=self.gauge_model()
        self.reg_at('s2_tool',self.gauge,'cloth width gauge',[1.5,3.0],[.88,2.95,.55])
        self.add_obstacle(.06,2.64,.67,3.26)

        self.table('linen_measuring_bench',(2.50,4.58),(2.50,.65),height=.72)
        self.cloth=self.group('fixed_cloth_strip',[2.10,4.50,.763])
        self.box('cloth_strip',[0,0,0],[.140,.46,.006],'cloth_strip_blue',self.cloth,bevel=.001)
        self.reg_at('s2_setup',self.cloth,'cloth strip',[2.0,3.75],[2.10,4.50,.78])
        self.reg_at('s2_clue',self.gauge_screen,'gauge own display',[2.0,3.75],[2.145,4.575,.821])

        self.weave=self.group('woven_band_case',[3.0,4.55,0])
        for x in [-.705,.705]:
            self.box('woven_case_side',[x,-.01,1.08],[.030,.56,.64],'wood',self.weave)
        self.box('woven_case_back',[0,.25,1.08],[1.44,.03,.64],'paint',self.weave)
        self.box('woven_case_floor',[0,-.01,.77],[1.44,.56,.020],'wood',self.weave)
        self.box('woven_case_top',[0,-.01,1.415],[1.47,.59,.030],'wood',self.weave)
        self.box('weave_dark_backing',[0,-.18,1.06],[1.39,.020,.44],'woven_backing',self.weave)
        self.anchor_group=self.group('fixed_woven_side_anchors',parent=self.weave)
        for row,z in enumerate([1.16,.96]):
            image=self.woven_pattern(row)
            for side,x,crop in [('left',-.46,(220,0,460,200)),('right',.46,(1140,0,1380,200))]:
                anchor=self.group('fixed_'+side+'_anchor_'+str(row),[x,-.230,z],self.anchor_group)
                self.box('fixed_anchor_carrier',[0,0,0],[.24,.008,.17],'linen_cream',anchor)
                self.flat('fixed_anchor_print_'+side+'_'+str(row),anchor,[0,-.005,0],.24,.17,image.crop(crop))
            band=self.group('moving_woven_band_'+str(row),[0,-.220,z],self.weave)
            self.box('actual_cloth_slider',[0,0,0],[1.06,.006,.17],'linen_cream',band)
            self.flat('moving_woven_print_'+str(row),band,[0,-.0045,0],1.06,.17,image.crop((270,0,1330,200)))
            self.bands.append(band)
            self.tube('woven_button_mount',[-.65,-.245,z],[-.65,-.272,z],.012,'steel',self.weave)
            button=self.group('woven_band_button_'+str(row),[-.65,-.272,z],self.weave)
            self.cylinder('band_button_cap',[0,0,0],.035,.024,'iron','y',button,n=24)
            self.text('band_right_arrow_'+str(row),button,[0,-.0135,0],.061,.052,'→')
            self.reg_at('s3_control_'+str(row),button,LABELS['s3_control_'+str(row)],[3.0,3.5],[3.0,4.315,1.06])
        for x in [-.65,.65]:
            self.box('fixed_side_frame',[x,-.20,1.06],[.14,.10,.43],'wood',self.weave)
        for z,h in [(1.265,.035),(1.06,.020),(.855,.035)]:
            self.box('fixed_cross_frame',[0,-.20,z],[1.22,.10,h],'wood',self.weave)
        self.reg_at('s3_clue',self.anchor_group,'woven cloth and fixed endpoint anchors',[3.0,3.5],[3.0,4.315,1.06])
        self.case_cover=self.group('woven_case_cover_hinge',[0,-.335,1.40],self.weave)
        cover=self.group('woven_cover_face',parent=self.case_cover)
        self.box('woven_protective_cover',[0,0,-.32],[1.47,.036,.64],'paint',cover)
        self.box('woven_cover_pull',[0,-.043,-.55],[.19,.044,.030],'brass',cover)
        self.reg_at('s3_cover',cover,'woven band protective cover',[3.0,3.5],[3.0,4.20,1.06])
        self.number_lock=self.group('millimetre_code_lock',[0,-.028,-.40],cover)
        self.box('millimetre_lock_bezel',[0,0,0],[.31,.040,.15],'iron',self.number_lock)
        self.flat('millimetre_lock_display',self.number_lock,[0,-.022,.019],.265,.078,self.text_image('0000',.265,.078,(48,68,56),(225,229,191)))
        self.text('millimetre_unit',self.number_lock,[0,-.022,-.050],.11,.035,'mm')
        self.number_shader=self.S.Shader(self.stage.GetPrimAtPath(str(self.mats['r17_millimetre_lock_display'].GetPath())+'/texture'))
        self.reg_at('s2_lock',self.number_lock,'woven case millimetre lock',[3.0,3.5],[3.0,4.18,1.00])
        self.keydrawer,keyfront=self.drawer('linen_key_drawer',None,(3.0,4.255),.54,width=1.12,depth=.44)
        self.reg_at('key_box',keyfront,'linen key drawer',[3.0,3.5],[3.0,4.255,.54])
        self.box('door_key_pad',[0,.21,-.021],[.92,.34,.158],'linen_felt',self.keydrawer)
        self.key=self.tool('flat_brass_key',self.keydrawer,[0,.21,.069],'key')
        self.target_nodes.pop('flat_brass_key',None);self.transform(self.key,rpy=[90,0,0])
        self.reg_at('key',self.key,'brass door key',[3.0,3.5],[3.0,4.045,.609])

        rolls=self.group('fixed_linen_rolls',[5.10,2.45,0])
        self.transform(rolls,rpy=[0,0,-90])
        for x in [-.59,.59]:
            self.box('linen_roll_rack_post',[x,0,.63],[.055,.40,1.26],'darkwood',rolls)
        for z in [.14,.69,1.17]:
            self.box('linen_roll_shelf',[0,0,z],[1.25,.43,.040],'wood',rolls)
        self.box('linen_roll_rack_back',[0,.18,.63],[1.18,.035,1.23],'paint',rolls)
        for j in range(3):
            self.cylinder('stored_sheet_roll',[(j-1)*.34,0,1.27],.080,.28,'linen_cream','y',rolls,n=28)
        for j in range(2):
            self.box('folded_clean_linen',[(j-.5)*.53,0,.78],[.43,.30,.14],'linen_blue' if j else 'linen_cream',rolls,bevel=.010)
        self.add_obstacle(4.82,1.79,5.37,3.11)
        basket=self.group('fixed_linen_basket',[4.45,.31,0])
        self.box('basket_floor',[0,0,.035],[.67,.43,.07],'wood',basket)
        for x in [-.34,.34]:
            self.box('basket_side',[x,0,.20],[.025,.44,.33],'wood',basket)
        for y in [-.215,.215]:
            for z in [.10,.19,.28,.365]:
                self.box('basket_slatted_front',[0,y,z],[.70,.018,.035],'darkwood',basket)
        self.add_obstacle(4.07,.04,4.83,.56)

        self.exit_node=self.door('linen_room_exit',[1.25,.06,0],1.04)
        self.door_view=[1.75,1.0];self.door_angle=0
        self.reg_at('exit',self.exit_node,'exit door',self.door_view,[1.77,.06,1.12])
        for x in [1.23,2.31]:
            self.box('door_jamb',[x,.05,1.14],[.065,.17,2.30],'paint')
        self.box('door_lintel',[1.77,.05,2.29],[1.15,.17,.065],'paint')
        for x in [1.24,2.30]:
            self.box('door_stop_jamb',[x,.01,1.14],[.035,.026,2.28],'darkwood')
        self.box('door_stop_top',[1.77,.01,2.28],[1.13,.026,.035],'darkwood')
        self.stage_views=[[1.5,3.0],[2.0,3.75],[3.0,3.5]]
        self.stage_centres=[[.10,3.0,1.75],[2.10,4.50,.78],[3.0,4.315,1.06]]
        self.bases=[([.30,2.95],90),([2.10,4.50],0),([3.0,4.55],0)]
        self.sync(g)
    def visible(self,key,g):
        if key=='s2_tool':return bool(g.opened['s2_cover']) and 's2_tool' not in g.taken
        if key=='s2_clue':return bool(g.states[1]['setup_used'])
        if key=='s3_clue' or key in ('s3_control_0','s3_control_1'):return bool(g.opened['s3_cover'])
        if key=='key':return bool(g.opened['key_box']) and key not in g.taken
        return key in self.target_nodes
    def sync(self,g):
        self.transform(self.gauge_pin,[.115 if g.solved[0] else -.045,-.026,0])
        self.visibility(self.gauge_release_lamps[0],not g.solved[0]);self.visibility(self.gauge_release_lamps[1],g.solved[0])

        signature=(tuple(g.states[0]['buffer']),bool(g.solved[0]))
        if signature!=self.selection_signature:
            with self.og.sim.editing_usd():
                self.selection_shader.GetInput('file').Set(str(self.selection_screen(*signature)))
            self.selection_signature=signature
        node,p=self.drawers['cloth_gauge_drawer']
        self.transform(node,[p[0],p[1]-(.42 if g.opened['s2_cover'] else 0),p[2]])
        self.set_gauge(g)
        value=g.states[1].get('entered_code','0000')
        if value!=self.number_value:
            import hashlib
            image=self.text_image(value,.265,.078,(48,68,56),(225,229,191))
            path=self.tex/('millimetre_code_'+hashlib.sha256(value.encode()).hexdigest()[:12]+'.png')
            image.save(path)
            with self.og.sim.editing_usd():self.number_shader.GetInput('file').Set(str(path))
            self.number_value=value
        self.transform(self.case_cover,rpy=[-160 if g.opened['s3_cover'] else 0,0,0])
        for j,node in enumerate(self.bands):
            self.transform(node,[(g.states[2]['angles'][j]-SPEC['stages'][2]['target'][j])*.060,-.220,[1.16,.96][j]])
        node,p=self.drawers['linen_key_drawer']
        self.transform(node,[p[0],p[1]-(.42 if g.opened['key_box'] else 0),p[2]])
        self.visibility(self.key,'key' not in g.taken)
        self.transform(self.exit_node,rpy=[0,0,-103 if g.opened['exit'] else 0])
        self.expanded=[]
        for flag,node in [(g.opened['s2_cover'],self.gaugedrawer),(g.opened['s3_cover'],self.case_cover),(g.opened['key_box'],self.keydrawer)]:
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
    def view_for(self,key):return self.views.get(key,[1.75,1.0])
    def focus_for(self,key):return self.focus.get(key,self.centres.get(key))
    def label_for(self,key):return self.labels.get(key,LABELS.get(key,key.replace('_',' ')))
    def animate(self,d,before):
        old=before.get('opened',{})
        if bool(old.get('s2_cover'))!=bool(d.game.opened['s2_cover']):
            node,p=self.drawers['cloth_gauge_drawer']
            for q in [.33,.67]:
                t=float(bool(old.get('s2_cover')))+(float(bool(d.game.opened['s2_cover']))-float(bool(old.get('s2_cover'))))*q
                self.sync(d.game);self.transform(node,[p[0],p[1]-.42*t,p[2]])
                self.set_gauge(d.game,drawer_fraction=t)
                d.frame(warm=4);d.append('Gauge compartment opens',4)
        if not before['states'][1]['setup_used'] and d.game.states[1]['setup_used']:
            self.sync(d.game);d.frame(warm=8);d.append('Observe the140mm reading on the gauge itself',24)
        if bool(old.get('s3_cover'))!=bool(d.game.opened['s3_cover']):
            for q in [.33,.67]:
                t=float(bool(old.get('s3_cover')))+(float(bool(d.game.opened['s3_cover']))-float(bool(old.get('s3_cover'))))*q
                self.sync(d.game);self.transform(self.case_cover,rpy=[-160*t,0,0])
                d.frame(warm=4);d.append('Woven band cover opens',4)
        for j,(a,b) in enumerate(zip(before['states'][2]['angles'],d.game.states[2]['angles'])):
            if a!=b:
                for q in [.33,.67]:
                    self.sync(d.game)
                    self.transform(self.bands[j],[((a+(b-a)*q)-SPEC['stages'][2]['target'][j])*.060,-.220,[1.16,.96][j]])
                    d.frame(warm=4);d.append('The real woven strip slides between its fixed anchors',4)
        if bool(old.get('key_box'))!=bool(d.game.opened['key_box']):
            node,p=self.drawers['linen_key_drawer']
            for q in [.33,.67]:
                t=float(bool(old.get('key_box')))+(float(bool(d.game.opened['key_box']))-float(bool(old.get('key_box'))))*q
                self.sync(d.game);self.transform(node,[p[0],p[1]-.42*t,p[2]])
                d.frame(warm=4);d.append('Linen key drawer opens',4)
        self.sync(d.game)

def standard(d):
    import heapq
    from observation1280 import FX,FY,CX,CY
    from pixel355 import find_point
    from oracle355 import _edge_clear,_turn_actions,_wrap
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
        if blocked(*xy(start)) or blocked(*xy(goal)):raise ValueError('Blocked actual public route endpoint')
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
        while state in parents:state,a=parents[state];actions.append(a)
        actions=list(initial[state])+list(reversed(actions))
        if any(a['action'] in ('walk','side_step','step_back') for a in actions) and d.pitch<math.radians(-25):
            d._turn_vertical_to(math.radians(-20),'Look ahead while moving between the furniture')
        for a in actions:d.execute(a,purpose)
    def approach(key,purpose,stay=False):
        view=list(d.pos[:2]) if stay else [round(float(v)*4)/4 for v in sc.view_for(key)]
        p,k=axis_focus(key,view)
        if not stay:route_short(view,k,purpose)
        d.aim(p,purpose)
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
            route_short(view,axis_focus(key,view)[1],'Approach the actual visible surface')
            d.aim(centre(key),'Look at the reachable object')
            hit=find_point(key,d.pos,d.quat,d.depth,sc.candidates(g),fx=FX,fy=FY,cx=CX,cy=CY,actor_xy=d.pos[:2],tolerance=.05,mesh_tolerance=.04,grid=61,return_hit=True)
        if hit is None or float(hit['distance'])>reach:
            raise RuntimeError('No current visible native pixel within unchanged reach for '+key)
        a={'thought':'Use the clue and the actual room object.','action':kind,'point':hit['point'],'target':LABELS.get(key,key.replace('_',' '))}
        if item is not None:a['item']=LABELS.get(item,item)
        if code is not None:a['code']=str(code)
        return d.execute(a,'Observe the physical response')
    observe('s1_clue','Observe the two positive location facts beside the linen racks')
    approach('s1_choice_4','Inspect the window-side rack and its bottom striped box')
    click('s1_choice_4')
    approach('s1_choice_3','Inspect the other rack and its middle dotted box')
    click('s1_choice_3')
    approach('s1_confirm','Check the two observed locations together');click('s1_confirm')
    approach('s2_cover','Open the central utility compartment');click('s2_cover','open')
    d.append('Observe the actual width gauge on its supported pad',18);click('s2_tool','take')
    approach('s2_setup','Bring the gauge to the cloth strip');click('s2_setup','use','s2_tool')
    observe('s2_clue','Observe140mm on the gauge itself while both jaws touch the cloth',stay=True)
    approach('s2_lock','Approach the adjacent woven case millimetre lock')
    click('s2_lock','unlock',code='0140');click('s3_cover','open')
    observe('s3_clue','Compare each irregular woven strip with both fixed side endpoints',stay=True)
    click('s3_control_0')
    for _ in range(3):click('s3_control_1')
    if not g.solved[2]:raise RuntimeError('The two woven strips do not join their fixed anchors')
    approach('key_box','Look down at the unlocked linen key drawer',stay=True)
    click('key_box','open');d.append('Observe the flat door key on its actual drawer pad',18);click('key','take')
    approach('exit','Return to the exit');click('exit','use','key');click('exit','open')
    if not exit_test(d.pos,g):raise RuntimeError('Open-door success was not reached')
