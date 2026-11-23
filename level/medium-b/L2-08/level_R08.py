from easy88_core import make_level

SPEC = {'id': 'R08',
 'title': 'R08 · Archive Sorting Room / 档案整理室',
 'theme': 'archive',
 'size': [5.0, 5.5],
 'door': {'side': 'south', 'start': 1.75, 'width': 1.04},
 'start': [2.5, 1.25, 1.35],
 'start_yaw': 90,
 'floor': 'wood',
 'decor': ['fixed paper stacks', 'empty document trays', 'pencil cup', 'cardboard archive boxes'],
 'design_notes': 'Directory lookup opens the slider device and its cover key; true two-strip registration '
                 'reveals the code; three repeated rows form the final symbol sequence.',
 'stages': [{'kind': 'index_code',
             'name': 'archive index cabinet',
             'wall': 'north',
             'answer': '580',
             'digits': 3,
             'visual': {'type': 'index',
                        'rows': [['deer', '5'], ['leaf', '0'], ['bird', '3'], ['fish', '8']],
                        'query': ['deer', 'fish', 'leaf']},
             'clue': {'rows': [['deer', '5'], ['leaf', '0'], ['bird', '3'], ['fish', '8']],
                      'query': ['deer', 'fish', 'leaf']},
             'clue_text': 'Deer 5\nLeaf 0\nBird 3\nFish 8\nDeer / Fish / Leaf'},
            {'kind': 'slide_align',
             'name': 'registration slide viewer',
             'wall': 'east',
             'initial': [2, 4],
             'target': [3, 6],
             'moduli': [10, 10],
             'answer': '2437',
             'digits': 4,
             'auto': False,
             'code_after_alignment': True,
             'setup': {'kind': 'key',
                       'item': 'slide_cover_key',
                       'item_name': 'small slide-cover key',
                       'target_name': 'locked slider cover',
                       'consume': False},
             'visual': {'type': 'split_code',
                        'code': '2437',
                        'target': [3, 6],
                        'registration_marks': True,
                        'stops': 10},
             'clue': {'registration_marks': True, 'strips': 2, 'stops': 10, 'visible_complete_text': '2437'},
             'clue_text': ''},
            {'kind': 'sequence',
             'name': 'archive pattern lock',
             'wall': 'west',
             'options': ['circle', 'triangle', 'square', 'star', 'leaf', 'cross'],
             'answer': [2, 4, 1],
             'length': 3,
             'auto': False,
             'visual': {'type': 'repeat_rows',
                        'rows': [['circle', 'triangle', 'square', 'circle', 'triangle', None],
                                 ['star', 'square', 'leaf', 'star', 'square', None],
                                 ['cross', 'circle', 'triangle', 'cross', 'circle', None]]},
             'clue': {'rows': [['circle', 'triangle', 'square', 'circle', 'triangle', None],
                               ['star', 'square', 'leaf', 'star', 'square', None],
                               ['cross', 'circle', 'triangle', 'cross', 'circle', None]],
                      'read_order': 'top_to_bottom'},
             'clue_text': ''}]}
for _stage in SPEC['stages']:
    _stage.setdefault('graphic',_stage.get('visual',{}))
Game,Scene,standard,exit_test,cpu_check=make_level(SPEC)
TITLE=SPEC['title']
LEVEL_ID=SPEC['id']
LABELS=Game.LABELS
START=SPEC['start']
START_YAW=SPEC.get('start_yaw',90)
CAP=150
OBSERVATION_SIZE=(640,360)
VISUAL_ONLY=False
READ_ENABLED=True
READ_FEEDBACK_TEXT=True

from pathlib import Path
import math,json,hashlib
import numpy as np
from PIL import Image,ImageDraw
from easy88_scene import EasyScene
from easy88_clues import draw_symbol,render_clue
from font_utils import load_font

Game.LABELS['s2_tool']='key beside VIEWER tag'
_ArchiveGame=Game
class Game(_ArchiveGame):
    def __init__(self):
        super().__init__();self.entered_codes={}
    def act(self,a):
        result=super().act(a)
        key=a.get('_hit364')
        if a.get('_validated364') and a.get('action')=='unlock' and key in ('s1_lock','s2_lock'):
            self.entered_codes[key]=str(a.get('code','')).strip()
        return result
    def snapshot(self):
        state=super().snapshot();state['entered_codes']=dict(self.entered_codes);return state

class Scene(EasyScene):
    def __init__(self,og,run):
        super().__init__(og,run,SPEC)
        self.views={};self.focus={};self.labels={};self.drawers={};self.strip_nodes=[];self.buffer_nodes=[];self.lock_screens={};self.lock_values={}
    def palette(self):
        super().palette()
        self.mat('archive_card',(.61,.47,.29),rough=.96)
        self.mat('archive_blue',(.13,.24,.28),rough=.94)
        self.mat('archive_green',(.26,.34,.29),rough=.94)
        self.mat('archive_lining',(.66,.62,.49),rough=.97)
    def reg_at(self,key,node,label,view,focus=None):
        self.reg(key,node);self.labels[key]=label;self.views[key]=list(view)
        if focus is not None:self.focus[key]=list(focus)
        return node
    def flat(self,name,parent,pos,w,h,im,horizontal=False):
        p=self.tex/(name+'.png');im.save(p)
        return self.plane(name,pos,w,h,(1,0,0),(0,1,0) if horizontal else (0,0,1),None,parent,material=self.image_mat(name,p))
    def text(self,name,parent,pos,w,h,value,bg=(209,211,191),ink=(29,42,38),horizontal=False):
        im=Image.new('RGB',(800,240),bg);d=ImageDraw.Draw(im)
        d.text((400,120),value,font=load_font(146),fill=ink,anchor='mm')
        return self.flat(name,parent,pos,w,h,im,horizontal)
    def paper_stack(self,name,parent,pos,w=.27,d=.19,h=.07):
        n=self.group(name,pos,parent);self.box('paper_block',[0,0,h/2],[w,d,h],'paper',n,bevel=.001)
        for z in np.linspace(.008,h,6):self.box('paper_edges',[0,-d/2-.001,float(z)],[w*.95,.002,.001],'archive_lining',n,bevel=.0001)
        return n
    def archive_box(self,name,parent,pos,w=.25,d=.31,h=.24,colour='archive_card'):
        n=self.group(name,pos,parent)
        self.box('file_carton',[0,0,h/2],[w,d,h],colour,n,bevel=.006)
        self.box('carton_lid',[0,0,h+.008],[w+.012,d+.012,.022],colour,n,bevel=.003)
        self.box('label_holder',[0,-d/2-.004,h*.58],[w*.65,.008,.062],'paper',n,bevel=.001)
        self.box('label_mark',[0,-d/2-.009,h*.58],[w*.35,.002,.005],'archive_blue',n,bevel=.0001)
        self.cylinder('carton_finger_hole',[0,-d/2-.007,h*.26],.017,.004,'iron','y',n,n=20)
        return n
    def drawer(self,name,x,y,w=.90,depth=.49,z=.54):
        for xx in [x-w/2-.025,x+w/2+.025]:self.box(name+'_housing_side',[xx,y+depth/2,z],[.035,depth+.035,.23],'wood')
        self.box(name+'_housing_back',[x,y+depth,z],[w+.05,.03,.23],'wood')
        self.box(name+'_housing_bottom',[x,y+depth/2,z-.12],[w+.08,depth+.04,.027],'darkwood')
        for xx in [x-w/2,x+w/2]:self.box(name+'_fixed_slide',[xx,y+depth/2,z-.045],[.016,depth-.01,.025],'steel')
        n=self.group(name,[x,y,z]);self.box('drawer_bottom',[0,depth/2,-.095],[w,depth,.024],'wood',n)
        for xx in [-w/2,w/2]:self.box('drawer_side',[xx,depth/2,-.005],[.025,depth,.18],'wood',n)
        self.box('drawer_back',[0,depth,-.005],[w,.025,.18],'wood',n)
        self.box('drawer_lining',[0,depth/2,-.077],[w-.05,depth-.04,.012],'archive_lining',n)
        self.box('drawer_front',[0,0,0],[w+.05,.04,.21],'paint',n)
        handle=self.group(name+'_pull',[0,-.045,0],n);self.box('brass_handle',[0,0,0],[.18,.04,.025],'brass',handle)
        self.drawers[name]=(n,[x,y,z]);return n,handle
    def code_lock(self,key,parent,pos,digits,view,focus):
        n=self.group(key,pos,parent);self.box('lock_bezel',[0,0,0],[.32,.028,.095],'iron',n)
        self.text(key+'_digits',n,[0,-.016,0],.29,.068,'0'*digits,bg=(154,184,155))
        material=self.mats[key+'_digits']
        self.lock_screens[key]=(digits,self.S.Shader(self.stage.GetPrimAtPath(str(material.GetPath())+'/texture')))
        self.reg_at(key,n,'code lock',view,focus);return n
    def build(self,g):
        self.room_shell('archive_room',size=(5.0,5.5),openings={'south':[(1.72,2.84)]})
        self.box('solid_subfloor',[2.5,2.75,-.075],[5.14,5.64,.10],'darkwood',bevel=.001)
        self.table('archive_workbench',(2.5,5.10),(3.70,.66),height=.74)
        for x in [.73,4.27]:self.box('workbench_end_panel',[x,5.10,.37],[.075,.60,.67],'paint')
        self.leftdrawer,leftpull=self.drawer('index_drawer',1.40,4.79,w=1.00,z=.57)
        self.reg_at('s2_cover',leftpull,'index cabinet drawer',[1.4,3.9],[1.4,4.72,.57])
        self.code_lock('s1_lock',self.leftdrawer,[.30,-.025,0],3,[1.4,3.9],[1.7,4.75,.57])
        card=render_clue(SPEC['stages'][0],{},size=(1200,660))
        self.box('directory_clipboard',[1.40,5.35,1.22],[1.04,.045,.60],'darkwood')
        directory=self.flat('printed_archive_index',None,[1.40,5.322,1.22],1.00,.55,card)
        self.reg_at('s1_clue',directory,'archive directory',[1.4,4.0],[1.4,5.32,1.22])
        self.box('clipboard_clip',[1.4,5.30,1.52],[.14,.028,.045],'brass')
        self.smallkey=self.tool('s2_tool',self.leftdrawer,[-.20,.23,-.052],'key');self.transform(self.smallkey,rpy=[90,0,0])
        self.viewer_key_tag=self.text('viewer_key_tag',self.leftdrawer,[.12,.23,-.069],.22,.075,'VIEWER',horizontal=True)
        self.reg_at('s2_tool',self.smallkey,'key beside VIEWER tag',[1.4,3.9],[1.20,4.65,.53])
        self.viewer=self.group('registration_viewer',[3.40,5.05,.80])
        self.box('viewer_base',[0,0,0],[1.30,.58,.055],'archive_blue',self.viewer)
        for x in [-.65,.65]:self.box('viewer_end',[x,0,.065],[.035,.58,.13],'wood',self.viewer)
        self.box('viewer_back',[0,.28,.065],[1.30,.035,.13],'wood',self.viewer)
        self.viewer_lid=self.group('registration_cover',[0,.29,.14],self.viewer)
        self.box('protective_lid',[0,-.29,0],[1.35,.61,.035],'wood',self.viewer_lid)
        self.box('cover_pull',[0,-.615,0],[.18,.035,.025],'brass',self.viewer_lid)
        self.cylinder('cover_keyhole',[.47,-.606,0],.012,.010,'iron','y',self.viewer_lid)
        self.text('viewer_device_name',self.viewer_lid,[0,-.29,.020],.46,.13,'VIEWER',horizontal=True)
        self.reg_at('s2_setup',self.viewer_lid,'registration viewer cover',[3.4,4.0],[3.4,5.05,.95])
        full=Image.new('RGB',(800,200),(223,216,193));dr=ImageDraw.Draw(full)
        dr.text((400,100),'2437',font=load_font(205),fill=(0,0,0),stroke_width=5,stroke_fill=(0,0,0),anchor='mm')
        slit_pitch=.0204;slit_width=.0065
        ink=np.asarray(full).copy()
        xx=(np.arange(800)+.5)/1000.-.40
        phase=(xx+slit_pitch/2)%slit_pitch-slit_pitch/2
        ink[:,np.abs(phase)>slit_width/2,:]=(223,216,193)
        full=Image.fromarray(ink)
        self.strips=[]
        for j in range(2):
            y=.065 if j==0 else -.065
            strip=self.group('sliding_registration_strip_'+str(j),[0,y,.055],self.viewer)
            self.box('physical_strip',[0,0,0],[1.01,.125,.021],'paper',strip,bevel=.002)
            self.flat('half_number_'+str(j),strip,[0,0,.012],.80,.125,full.crop((0,j*100,800,(j+1)*100)),True)
            mark=Image.new('RGB',(100,100),(223,216,193));md=ImageDraw.Draw(mark);md.polygon([(17,50),(80,15),(80,85)],fill=(104,43,32))
            self.box('slider_thumb_grip',[-.552,0,.027],[.080,.105,.025],'archive_green',strip,bevel=.004)
            self.flat('moving_registration_mark_'+str(j),strip,[-.552,0,.041],.066,.078,mark,True)
            self.reg_at('s2_control_'+str(j),strip,'upper slider' if j==0 else 'lower slider',[3.4,4.0],[3.4,5.05,.87])
            self.strips.append(strip)
            self.box('strip_rail',[0,y,.039],[1.24,.13,.018],'iron',self.viewer)
            self.tube('fixed_registration_tick',[-.552,y-.085,.096],[-.552,y-.060,.096],.003,'red',self.viewer)
            windows=[]
            for k in range(-21,22):
                cx=k*slit_pitch
                if -.40<cx<.40:windows.append((cx-slit_width/2,cx+slit_width/2))
            edge=-.64
            for left,right in windows+[(.64,.64)]:
                if left>edge:self.box('fixed_registration_mask',[(edge+left)/2,y,.0685],[left-edge,.129,.001],'cream',self.viewer,bevel=.0001)
                edge=right
        reference_rim=self.box('registration_reference_rim',[0,.248,.067],[1.15,.018,.035],'archive_green',self.viewer)
        self.reg_at('s2_clue',reference_rim,'registration strips',[3.4,4.0],[3.4,5.05,.86])
        self.code_lock('s2_lock',self.viewer,[0,-.306,.035],4,[3.4,4.0],[3.4,4.74,.835])
        self.rightdrawer,rightpull=self.drawer('sample_drawer',3.40,4.79,w=1.02,z=.57)
        self.reg_at('s3_cover',rightpull,'sample drawer',[3.4,3.9],[3.4,4.72,.57])
        reference=render_clue(SPEC['stages'][2],{},size=(1200,660));rd=ImageDraw.Draw(reference)
        rd.text((600,40),'ARCHIVE',font=load_font(58),fill=(35,54,43),anchor='mm')
        for j,letter in enumerate(['A','B','C']):rd.text((34,180+j*160),letter,font=load_font(45),fill=(35,54,43),anchor='mm')
        self.box('sample_form_support_insert',[0,.25,.0115],[.94,.455,.165],'archive_lining',self.rightdrawer)
        sample=self.flat('file_pattern_reference',self.rightdrawer,[0,.25,.095],.90,.44,reference,True)
        self.reg_at('s3_clue',sample,'pattern sample',[3.4,3.9],[3.4,4.65,.665])
        self.finalcab=self.group('archive_card_cabinet',[.36,2.85,0]);self.transform(self.finalcab,rpy=[0,0,90])
        c=self.finalcab
        for xx in [-.65,.65]:self.box('card_cabinet_side',[xx,0,.36],[.035,.56,.66],'wood',c)
        self.box('card_cabinet_back',[0,.27,.36],[1.33,.035,.66],'paint',c)
        self.box('card_cabinet_floor',[0,0,.09],[1.33,.56,.035],'wood',c)
        self.box('fixed_lower_panel',[0,-.28,.20],[1.27,.035,.20],'paint',c)
        self.box('upper_panel_backing',[0,-.28,.635],[1.27,.025,.27],'paint',c)
        for xx in [-.59,.59]:self.box('key_drawer_rail',[xx,0,.35],[.025,.50,.03],'steel',c)
        self.box('card_cabinet_top',[0,0,.73],[1.41,.62,.065],'wood',c)
        self.text('archive_receiver_name',c,[0,.12,.7645],.56,.10,'ARCHIVE',horizontal=True)
        for j,letter in enumerate(['A','B','C']):self.text('archive_entry_row_'+str(j),c,[(j-1)*.155,-.20,.7645],.075,.055,letter,horizontal=True)
        for xx in [-.47,.47]:self.box('short_cabinet_foot',[xx,0,.055],[.10,.40,.10],'iron',c)
        self.box('symbol_screen_bezel',[0,-.292,.64],[1.19,.026,.28],'iron',c)
        for j,symbol in enumerate(SPEC['stages'][2]['options']):
            n=self.group('pattern_key_'+str(j),[(j-2.5)*.145,-.316,.605],c)
            self.box('symbol_key_cap',[0,0,0],[.13,.017,.105],'archive_green',n)
            im=Image.new('RGB',(180,150),(61,82,75));di=ImageDraw.Draw(im);draw_symbol(di,symbol,(35,20,145,130),fill=(220,220,196),outline=(220,220,196))
            self.flat('symbol_key_ink_'+str(j),n,[0,-.010,0],.116,.095,im)
            self.reg_at('s3_choice_'+str(j),n,symbol+' key',[1.4,2.85],[.68,2.85,.63])
        for j in range(3):
            n=self.group('input_slot_'+str(j),[(j-1)*.155,-.313,.713],c)
            self.box('input_blank',[0,0,0],[.135,.012,.075],'dark_panel',n);self.buffer_nodes.append(n)
        for key,x,label in [('s3_reset',-.51,'C'),('s3_confirm',.51,'OK')]:
            n=self.group(key,[x,-.316,.66],c);self.box('control_cap',[0,0,0],[.095,.018,.15],'archive_green',n)
            self.text(key+'_caption',n,[0,-.011,0],.083,.095,label,bg=(61,82,75),ink=(223,222,195))
            self.reg_at(key,n,'clear key' if key.endswith('reset') else 'check key',[1.4,2.85],[.68,2.85,.66])
        self.finaldrawer=self.group('key_card_drawer',[0,-.29,.40],c)
        self.box('key_drawer_floor',[0,.14,-.07],[1.12,.32,.026],'archive_lining',self.finaldrawer)
        for xx in [-.56,.56]:self.box('key_drawer_side',[xx,.14,0],[.025,.32,.16],'wood',self.finaldrawer)
        self.box('key_drawer_back',[0,.30,0],[1.12,.025,.16],'wood',self.finaldrawer)
        self.box('key_drawer_face',[0,0,0],[1.18,.045,.19],'paint',self.finaldrawer)
        handle=self.group('key_drawer_handle',[0,-.05,0],self.finaldrawer);self.box('key_drawer_pull',[0,0,0],[.20,.04,.025],'brass',handle)
        self.reg_at('key_box',handle,'archive cabinet drawer',[1.4,2.85],[.69,2.85,.40])
        self.key=self.tool('key',self.finaldrawer,[0,.14,-.045],'key');self.transform(self.key,rpy=[90,0,0])
        self.reg_at('key',self.key,'door key',[1.4,2.85],[.85,2.85,.36])
        self.add_obstacle(.06,2.13,.68,3.57)
        rack=self.group('document_shelving',[4.73,3.35,0]);self.transform(rack,rpy=[0,0,-90])
        for xx in [-.86,.86]:self.box('rack_upright',[xx,0,.77],[.05,.43,1.54],'darkwood',rack)
        self.box('rack_back',[0,.20,.77],[1.75,.035,1.54],'paint',rack)
        for z in [.16,.66,1.17]:self.box('rack_board',[0,0,z],[1.80,.47,.035],'wood',rack)
        for row,z in enumerate([.18,.68,1.19]):
            for j in range(4):self.archive_box('archive_box_%d_%d'%(row,j),rack,[(j-1.5)*.40,-.015,z],w=.30,d=.33,h=.27,colour='archive_card' if (j+row)%3 else 'archive_blue')
        self.add_obstacle(4.48,2.43,4.98,4.27)
        self.paper_stack('left_working_papers',None,[.98,5.05,.785],w=.33,d=.23,h=.085)
        tray=self.group('document_tray',[2.30,5.12,.81]);self.box('tray_floor',[0,0,0],[.38,.29,.018],'archive_blue',tray)
        for xx in [-.19,.19]:self.box('tray_side',[xx,0,.035],[.016,.29,.07],'archive_blue',tray)
        self.paper_stack('papers_in_tray',tray,[0,0,.015],w=.33,d=.24,h=.027)
        self.cylinder('pencil_cup',[2.68,5.13,.86],.045,.14,'archive_blue','z',n=24)
        for j in range(4):self.tube('pencil',[2.66+j*.012,5.13,.84],[2.65+j*.015,5.13,.99],.003,'wood')
        self.table('archive_packing_shelf',(4.03,.34),(1.30,.52),height=.69)
        self.archive_box('outgoing_file_box',None,[4.12,.35,.735],w=.36,d=.34,h=.24)
        self.paper_stack('packing_paper_stack',None,[3.61,.35,.735],w=.27,d=.28,h=.09)
        self.build_door()
        self.bases=[([1.40,5.10],0),([3.40,5.05],0),([.36,2.85],90)]
        self.stage_views=[[1.4,4.0],[3.4,4.0],[1.4,2.85]]
        self.stage_centres=[[1.4,5.32,1.22],[3.4,5.05,.86],[.68,2.85,.66]]
        self.sync(g)
    def visible(self,key,g):
        if key=='s2_tool':return bool(g.opened.get('s2_cover')) and key not in g.taken
        if key=='s3_clue':return bool(g.opened.get('s3_cover'))
        if key=='key':return bool(g.opened.get('key_box')) and key not in g.taken
        if key in ('s2_control_0','s2_control_1','s2_clue','s2_lock'):return bool(g.states[1]['setup_open'])
        return key in self.target_nodes
    def sync(self,g,blend=None):
        for key,(digits,shader) in self.lock_screens.items():
            value=getattr(g,'entered_codes',{}).get(key,'0'*digits)
            if self.lock_values.get(key)!=value:
                im=Image.new('RGB',(800,240),(154,184,155));draw=ImageDraw.Draw(im)
                font_size=146
                while font_size>12 and draw.textbbox((0,0),value,font=load_font(font_size))[2]>760:font_size-=8
                draw.text((400,120),value,font=load_font(font_size),fill=(29,42,38),anchor='mm')
                texture=self.tex/(key+'_entered_'+hashlib.sha256(value.encode()).hexdigest()[:12]+'.png');im.save(texture)
                with self.og.sim.editing_usd():shader.GetInput('file').Set(str(texture))
                self.lock_values[key]=value
        for key in ['index_drawer','sample_drawer']:
            n,p=self.drawers[key];opened=g.opened.get('s2_cover' if key=='index_drawer' else 's3_cover',False)
            self.transform(n,[p[0],p[1]-(.40 if opened else 0),p[2]])
        self.transform(self.viewer_lid,rpy=[-105 if g.states[1]['setup_open'] else 0,0,0])
        for j,node in enumerate(self.strips):
            self.transform(node,[(g.states[1]['angles'][j]-SPEC['stages'][1]['target'][j])*.034,.065 if j==0 else -.065,.055])
        self.transform(self.finaldrawer,[0,-.29-(.34 if g.opened.get('key_box') else 0),.40])
        for key in ['s2_tool','s3_clue','key','s2_control_0','s2_control_1','s2_clue','s2_lock']:self.visibility(self.target_nodes[key],self.visible(key,g))
        self.visibility(self.viewer,True)
        self.visibility(self.viewer_key_tag,bool(g.opened['s2_cover']))
        for j,n in enumerate(self.buffer_nodes):
            old=n.get('_symbol')
            if old is not None:self.visibility(old,False)
            buf=g.states[2]['buffer']
            if j<len(buf):
                name=SPEC['stages'][2]['options'][buf[j]];cache=n.setdefault('_symbols',{})
                if name not in cache:
                    im=Image.new('RGB',(160,100),(25,36,34));draw_symbol(ImageDraw.Draw(im),name,(40,10,120,90),fill=(221,222,191),outline=(221,222,191))
                    cache[name]=self.flat('entry_%d_%s'%(j,name),n,[0,-.007,0],.12,.066,im)
                n['_symbol']=cache[name];self.visibility(cache[name],True)
        self.transform(self.exit_node,rpy=[0,0,-103 if g.opened.get('exit') else 0])
        self.centres={}
        for key,node in self.target_nodes.items():
            tri=self.triangles(node)
            if tri.size:self.centres[key]=((tri.reshape(-1,3).min(0)+tri.reshape(-1,3).max(0))/2).tolist()
    def candidates(self,g):return self.base_candidates([k for k in self.target_nodes if self.visible(k,g)])
    def view_for(self,key):return self.views.get(key,self.door_view if key=='exit' else SPEC['start'][:2])
    def focus_for(self,key):return self.focus.get(key,self.centres.get(key))
    def label_for(self,key):return self.labels.get(key,Game.LABELS.get(key,key.replace('_',' ')))
    def animate(self,d,before):
        old=before.get('opened',{})
        for key,drawername in [('s2_cover','index_drawer'),('s3_cover','sample_drawer')]:
            if bool(old.get(key))!=bool(d.game.opened.get(key)):
                n,p=self.drawers[drawername]
                for t in [.33,.67]:
                    q=float(bool(old.get(key)))+(float(bool(d.game.opened.get(key)))-float(bool(old.get(key))))*t
                    self.sync(d.game);self.transform(n,[p[0],p[1]-.40*q,p[2]]);d.frame(warm=4);d.append('Drawer opening',4)
        prev=before['states'][1]['angles'];now=d.game.states[1]['angles']
        for j,(a,b) in enumerate(zip(prev,now)):
            if a!=b:
                for t in [.33,.67]:
                    self.sync(d.game);self.transform(self.strips[j],[((a+(b-a)*t)-SPEC['stages'][1]['target'][j])*.034,.065 if j==0 else -.065,.055]);d.frame(warm=3);d.append('Registration strip slides',3)
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
    observe('s1_clue','Read the actual archive directory and requested filing symbols')
    click('s1_lock','unlock',code='580')
    approach('s2_cover','Look down to the unlocked index drawer',stay=True)
    click('s2_cover','open');d.append('Observe the key in the actual drawer',18)
    click('s2_tool','take')
    approach('s2_setup','Walk along the workbench to the registration viewer')
    click('s2_setup','use','s2_tool');click('s2_setup','open')
    approach('s2_control_0','Keep both actual registration strips in view',stay=True)
    for j,target in enumerate(SPEC['stages'][1]['target']):
        while g.states[1]['angles'][j]!=target:click('s2_control_'+str(j))
    d.append('Observe the completed number on the physical strips',24)
    click('s2_lock','unlock',code='2437')
    approach('s3_cover','Look down to the unlocked sample drawer',stay=True)
    click('s3_cover','open')
    observe('s3_clue','Observe all three printed pattern rows in the drawer',stay=True)
    approach('s3_choice_2','Walk to the archive cabinet and its symbol lock')
    for j in SPEC['stages'][2]['answer']:click('s3_choice_'+str(j))
    click('s3_confirm')
    if not g.solved[2]:raise RuntimeError('Pattern sequence did not unlock the archive drawer')
    click('key_box','open');d.append('Observe the flat door key in the opened drawer',18)
    click('key','take')
    approach('exit','Return to the actual exit door')
    click('exit','use','key');click('exit','open')
    if not exit_test(d.pos,g):raise RuntimeError('Open-door success was not reached')

_archive_base_cpu=cpu_check
def cpu_check():
    from easy88_core import stage_actions
    result=_archive_base_cpu();g=Game()
    def act(kind,key,**kw):return g.act(dict(action=kind,_hit364=key,_validated364=True,**kw))
    for i in range(3):
        for kind,key,extra in stage_actions(g,i):assert act(kind,key,**extra)['ok'],(kind,key)
    assert g.entered_codes=={'s1_lock':'580','s2_lock':'2437'};result['checks'].append('actual subclass records entered codes with current public actions')
    assert 's2_tool' in g.taken and Game.LABELS['s2_tool']=='key beside VIEWER tag';result['checks'].append('inventory name matches visible VIEWER tag')
    assert g.solved[2];result['checks'].append('ARCHIVE completion remains solvable without invented install-card gate')
    result['passed']=len(result['checks']);return result
