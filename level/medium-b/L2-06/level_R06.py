SPEC = {'id': 'R06',
 'title': 'R06 · Signal Display Workshop / 信号展示维护间',
 'theme': 'signal',
 'size': [5.0, 5.0],
 'door': {'side': 'south', 'start': 3.6, 'width': 1.04, 'view': [4.0, 1.0]},
 'start': [2.5, 1.75, 1.35],
 'start_yaw': 90,
 'floor': 'wood',
 'decor': [{'kind': 'conduit', 'wall': 'north', 'centre': [2.5, 4.85], 'fixed': True},
           {'kind': 'storage_boxes', 'wall': 'east', 'centre': [4.7, 3.2], 'fixed': True},
           {'kind': 'fixed_meter', 'wall': 'west', 'centre': [0.25, 1.75], 'fixed': True}],
 'furniture_group': 'signal_console',
 'design_notes': ['一体L形低柜；导线板、示例灯、比较板各与自己盖的锁舌可见关联。',
                  '全部插线都可take并放入任意空通用座，不能逐根拒绝或亮正确灯。',
                  '三位闪灯必须完整确认，错误不匹配流式子串；可无限重播。',
                  '六列比较不告知差异个数。'],
 'stages': [{'kind': 'assign',
             'name': 'signal lead patch panel',
             'wall': 'west',
             'centre': [0.42, 3.35],
             'view': [1.5, 3.25],
             'board_height': 0.96,
             'items': [{'id': 'circle_lead',
                        'name': 'round-tagged test lead',
                        'symbol': 'circle',
                        'colour': 'red'},
                       {'id': 'star_lead',
                        'name': 'star-tagged test lead',
                        'symbol': 'star',
                        'colour': 'blue'},
                       {'id': 'square_lead',
                        'name': 'square-tagged test lead',
                        'symbol': 'square',
                        'colour': 'yellow'}],
             'slots': 4,
             'target': [1, None, 2, 0],
             'auto': False,
             'clue': {'type': 'wire_trace',
                      'sources': ['circle', 'star', 'square'],
                      'ends': [4, 1, 3],
                      'terminal_count': 4},
             'visual': {'type': 'wire_trace',
                        'sources': ['circle', 'star', 'square'],
                        'ends': [4, 1, 3],
                        'terminal_count': 4,
                        'per_item_green': False,
                        'common_socket_shape': True},
             'clue_text': ''},
            {'kind': 'sequence',
             'name': 'signal lamp recorder',
             'wall': 'north',
             'centre': [1.65, 4.60],
             'view': [1.75, 3.5],
             'board_height': 0.96,
             'options': ['circle', 'triangle', 'square', 'star', 'leaf', 'cross'],
             'answer': [0, 1, 0],
             'length': 3,
             'auto': False,
             'clue': {'type': 'flash',
                      'sequence': ['circle', 'triangle', 'circle'],
                      'replay': True,
                      'audio_required': False},
             'visual': {'type': 'flash',
                        'sequence': ['circle', 'triangle', 'circle'],
                        'replay': True,
                        'flash_seconds': 0.8,
                        'gap_seconds': 0.3,
                        'audio_required': False},
             'clue_text': ''},
            {'kind': 'difference',
             'name': 'signal comparison panel',
             'wall': 'north',
             'centre': [3.45, 4.60],
             'view': [3.5, 3.5],
             'board_height': 0.96,
             'initial': [0, 0, 0, 0, 0, 0],
             'target': [1, 0, 0, 1, 0, 0],
             'rows': 1,
             'cols': 6,
             'auto': False,
             'clue': {'type': 'signal_compare',
                      'upper': [1, 0, 1, 0, 0, 1],
                      'lower': [0, 0, 1, 1, 0, 1]},
             'visual': {'type': 'signal_compare',
                        'upper': [1, 0, 1, 0, 0, 1],
                        'lower': [0, 0, 1, 1, 0, 1],
                        'marker': 'not_equal',
                        'different_count_hint': False},
             'clue_text': ''}],
 'author_solution': ['Trace round,star,square leads to terminals4,1,3; place all and confirm whole '
                     'panel.',
                     'Open recorder cover, replay the three slow lights circle,triangle,circle; submit '
                     'exactly3.',
                     'Open comparison cover, mark differing columns1,4 and confirm full row.',
                     'Open final compartment, take door key, use and open exit.']}
from easy88_core import make_level
Game, Scene, standard, exit_test, cpu_check = make_level(SPEC)
TITLE=SPEC['title']
LEVEL_ID=SPEC['id']
START=SPEC['start']
START_YAW=SPEC.get('start_yaw',90)
CAP=150
OBSERVATION_SIZE=(640,360)
VISUAL_ONLY=False
READ_ENABLED=True
READ_FEEDBACK_TEXT=True
LABELS=Game.LABELS

import math,json
import numpy as np
from PIL import Image,ImageDraw
from easy88_scene import EasyScene,icon
from easy88_clues import draw_symbol

_signal_init=Game.__init__;_signal_act=Game.act
Game.LABELS.update({'s3_record_cover':'recorder output hatch','s3_record':'recorded pulse card','s3_feed':'comparator record slot'})
LABELS=Game.LABELS
def _record_init(self):
    _signal_init(self);self.states[2].update(record_open=False,record_loaded=False)
Game.__init__=_record_init
def _record_act(self,a):
    key=a.get('_hit364');kind=a.get('action')
    if a.get('_validated364'):
        from action_feedback import failure_for,NO_ITEM
        st=self.states[2]
        if key=='s3_record_cover':
            if kind not in ('open','close') or kind=='open' and not self.solved[1]:return {'ok':False,'text':failure_for(kind)}
            st['record_open']=kind=='open';return {'ok':True,'text':''}
        if key=='s3_record':
            if kind!='take' or not self.solved[1] or not st['record_open'] or key in self.taken:return {'ok':False,'text':failure_for(kind)}
            self.taken.add(key);self.holding.append(key);return {'ok':True,'text':''}
        if key=='s3_feed':
            if kind!='use':return {'ok':False,'text':failure_for(kind)}
            item=self._resolve_item(a.get('item'))
            if item is None:return {'ok':False,'text':NO_ITEM}
            if item!='s3_record':return {'ok':False,'text':failure_for(kind)}
            self.holding.remove(item);st['record_loaded']=True;return {'ok':True,'text':''}
        if key=='s3_cover' and kind=='open' and not st['record_loaded']:return {'ok':False,'text':failure_for(kind)}
    return _signal_act(self,a)
Game.act=_record_act
from easy88_core import stage_actions as _plain_stage_actions
def _linked_stage_actions(game,index):
    if index==2 and not game.states[2]['record_loaded']:
        if 's3_record' not in game.holding:
            if not game.states[2]['record_open']:yield ('open','s3_record_cover',{})
            yield ('take','s3_record',{})
        yield ('use','s3_feed',{'item':'s3_record'})
    yield from _plain_stage_actions(game,index)
from types import FunctionType as _AuthorFunction
_base_signal_standard=standard
def standard(d):
    def routed_actions(game,index):
        for kind,key,fields in _linked_stage_actions(game,index):
            yield kind,key,fields
            if index==2 and key=='s3_feed' and kind=='use' and game.states[2]['record_loaded']:
                d.route([3.5,3.5],'Move to the clear front of the comparator before opening its cover')
                d.aim([3.45,4.43,1.17],'Keep the comparator controls and cover in view')
    runner=_AuthorFunction(_base_signal_standard.__code__,dict(_base_signal_standard.__globals__,stage_actions=routed_actions),_base_signal_standard.__name__,_base_signal_standard.__defaults__,_base_signal_standard.__closure__)
    return runner(d)
_record_cpu=_AuthorFunction(cpu_check.__code__,dict(cpu_check.__globals__,stage_actions=_linked_stage_actions),cpu_check.__name__,cpu_check.__defaults__,cpu_check.__closure__)
def cpu_check():
    result=_record_cpu();g=Game()
    act=lambda kind,key,**kw:g.act(dict(action=kind,_hit364=key,_validated364=True,**kw))
    assert not act('take','s3_record')['ok']
    assert not act('open','s3_record_cover')['ok']
    g.solved[0]=g.solved[1]=True
    assert not act('open','s3_cover')['ok']
    assert act('open','s3_record_cover')['ok'];assert act('take','s3_record')['ok']
    g.holding.append('s1_item_0');assert not act('use','s3_feed',item='s1_item_0')['ok']
    assert act('use','s3_feed',item='s3_record')['ok'];assert not g.opened['s3_cover']
    assert act('open','s3_cover')['ok']
    result['checks']+=['record cannot be taken through locked output hatch','recorder flag alone does not open comparator','wrong record-slot item rejected','actual record transferred and consumed','loading record does not auto-open comparator cover'];result['passed']=len(result['checks']);return result

class SignalWorkshopScene(EasyScene):
    def palette(self):
        super().palette()
        for name,c in [('lead_red',(.40,.10,.065)),('lead_blue',(.08,.22,.34)),('lead_yellow',(.55,.40,.08)),('enamel',(.15,.22,.22)),('lamp_dim',(.035,.065,.050)),('screen_ink',(.025,.038,.035))]:self.mat(name,c,rough=.88)
        self.mat('lamp_on',(.50,.68,.33),rough=.8,emission=(.42,.62,.22))
        self.mat('window_pale',(.56,.65,.63),rough=.9,emission=(.12,.15,.14))
    def station(self,i,s):
        c=s['centre'];a=90 if s['wall']=='west' else 0
        root=self.group('instrument_'+str(i),[c[0],c[1],0]);self.transform(root,rpy=[0,0,a]);self.roots.append(root);self.bases.append((c,a))
        self.stage_views.append(s['view']);self.stage_centres.append(self.world(i,[0,-.25,1.17]))
        self.box('steel_instrument_case',[0,.015,1.105],[1.15,.23,.65],'enamel',root,bevel=.018)
        self.box('dark_instrument_face',[0,-.112,1.11],[1.08,.02,.59],'dark_panel',root,bevel=.006)
        for x in [-.535,.535]:
            for z in [.825,1.39]:self.cylinder('case_screw',[x,-.13,z],.009,.006,'steel','y',root,n=12)
        cover=self.group('s%d_cover'%(i+1),[-.59,-.15,.78],root)
        self.box('hinged_dust_cover',[.59,0,.33],[1.18,.034,.66],'paint',cover)
        self.box('cover_grip',[1.04,-.032,.32],[.035,.06,.16],'steel',cover)
        for vent in range(5):self.box('cover_vent',[.18+vent*.075,-.019,.48],[.045,.008,.075],'dark_panel',cover)
        self.reg('s%d_cover'%(i+1),cover);self.covers.append(cover)
        self.status_nodes.append((self.cylinder('red_status',[.53,-.141,.80],.012,.013,'red_led','y',root),self.cylinder('green_status',[.53,-.141,.80],.012,.013,'green','y',root)))
        self.controls.append([]);self.choice_nodes.append([]);self.buffers.append([]);self.items.append([]);self.slots.append([]);self.tools.append([]);self.setups.append(None)
        return root
    def clue(self,i,s,root):
        p='s%d'%(i+1);n=self.group(p+'_clue',parent=root);self.clues.append(n);self.clue_mats.append(None);self.reg(p+'_clue',n)
        if i==0:
            for j,(source,end) in enumerate(zip(['circle','star','square'],[3,0,2])):
                x=(j-1)*.37;ex=(end-1.5)*.24;y=-.148-j*.013;colour=['lead_red','lead_blue','lead_yellow'][j]
                self.face('source_'+str(j),n,[x,-.197,1.38],.085,.085,icon(source))
                points=[[x,y,1.32],[x,y,1.27-j*.045],[ex,y,1.27-j*.045],[ex,y,1.11]]
                for a,b in zip(points,points[1:]):self.tube('fixed_circuit_wire',a,b,.009,colour,n)
                self.cylinder('wire_termination',[ex,y,1.10],.017,.013,'brass','y',n,n=16)
        elif i==1:
            self.signal_lamps=[]
            for j,name in enumerate(s['options']):
                x=(j-2.5)*.165
                self.cylinder('lamp_bezel',[x,-.16,1.315],.047,.025,'steel','y',n,n=24)
                off=self.cylinder('lamp_lens',[x,-.178,1.315],.038,.012,'lamp_dim','y',n,n=24)
                on=self.cylinder('lamp_illuminated',[x,-.187,1.315],.037,.009,'lamp_on','y',n,n=24)
                self.signal_lamps.append((off,on))
                self.face('lamp_symbol_'+str(j),n,[x,-.163,1.215],.085,.085,icon(name))
        else:
            self.label('comparison_mark','≠',[0,-.15,1.385],.07,.055,parent=n)
            for r,values in enumerate([s['visual']['upper'],s['visual']['lower']]):
                for j,v in enumerate(values):
                    x=(j-2.5)*.165;z=1.31-r*.15;level=.032 if v else -.032
                    self.tube('signal_baseline',[x-.063,-.15,z],[x+.063,-.15,z],.0035,'steel',n)
                    pts=[[x-.063,-.17,z-.032],[x-.030,-.17,z-.032],[x-.030,-.17,z+level],[x+.045,-.17,z+level],[x+.045,-.17,z-.032],[x+.063,-.17,z-.032]]
                    for a,b in zip(pts,pts[1:]):
                        if math.dist(a,b)>1e-7:self.tube('signal_trace',a,b,.007,'paper',n)
    def _push(self,key,root,pos,symbol,size=.085):
        n=self.group(key,pos,root);self.cylinder('button_rim',[0,0,0],size*.58,.025,'steel','y',n,n=24);self.cylinder('button_cap',[0,-.018,0],size*.49,.02,'paint','y',n,n=24)
        im=icon(symbol)
        if symbol in ('confirm','reset','play',''):
            im=Image.new('RGB',(200,200),(209,207,185));dr=ImageDraw.Draw(im)
            if symbol=='confirm':dr.line([(40,102),(85,145),(162,52)],fill=(40,60,50),width=13)
            elif symbol=='play':dr.polygon([(65,42),(163,100),(65,158)],fill=(40,60,50))
            elif symbol=='reset':
                dr.arc((42,42,158,158),35,310,fill=(40,60,50),width=11);dr.polygon([(150,40),(165,90),(119,65)],fill=(40,60,50))
        self.face(key+'_symbol',n,[0,-.030,0],size*.76,size*.76,im);self.reg(key,n);return n
    def controls_for(self,i,s,root):
        p='s%d'%(i+1)
        if i==0:
            for j,item in enumerate(s['items']):
                n=self.group(p+'_item_'+str(j),parent=root);col=['lead_red','lead_blue','lead_yellow'][j]
                pts=[[-.055,0,-.045],[-.055,0,.030],[-.035,0,.055],[.035,0,.055],[.055,0,.030],[.055,0,-.045]]
                for a,b in zip(pts,pts[1:]):self.tube('test_lead_cable',a,b,.009,col,n)
                for x in [-.055,.055]:
                    self.cylinder('insulated_plug',[x,0,-.048],.014,.040,'rubber','z',n,n=16);self.cylinder('metal_plug_pin',[x,0,-.076],.006,.024,'steel','z',n,n=12)
                self.face('lead_tag_'+str(j),n,[0,-.012,0],.045,.045,icon(item['symbol']));self.reg(p+'_item_'+str(j),n);self.items[i].append(n)
            for j in range(4):
                x=(j-1.5)*.24;n=self.group(p+'_slot_'+str(j),[x,-.175,1.025],root)
                self.cylinder('socket_bezel',[0,0,0],.041,.026,'steel','y',n,n=24);self.cylinder('socket_hole',[0,-.019,0],.026,.013,'rubber','y',n,n=24)
                self.label('socket_number_'+str(j),str(j+1),[0,-.025,-.075],.065,.045,parent=n);self.reg(p+'_slot_'+str(j),n);self.slots[i].append(n)
        elif i==1:
            for j,symbol in enumerate(s['options']):self.choice_nodes[i].append(self._push(p+'_choice_'+str(j),root,[(j-2.5)*.165,-.18,.925],symbol,.115))
            for j in range(3):
                n=self.group(p+'_buffer_'+str(j),[(j-1)*.20,-.155,1.075],root);self.box('input_window',[0,0,0],[.17,.025,.13],'screen_ink',n);self.buffers[i].append(n)
            self._push(p+'_play',root,[0,-.18,.81],'play',.085)
        else:
            for j in range(6):self.controls[i].append(self._push(p+'_control_'+str(j),root,[(j-2.5)*.165,-.18,.99],'',.11))
        self._push(p+'_confirm',root,[.41,-.18,.81],'confirm',.085)
        self._push(p+'_reset',root,[-.41,-.18,.81],'reset',.085)
    def _record_image(self,image):
        path=self.tex/'pulse_record.png';image.save(path);return path
    def visible(self,key,g):
        if key in ('s3_record_cover','s3_feed'):return True
        if key=='s3_record':return bool(g.solved[1] and g.states[2]['record_open']) and key not in g.taken
        return super().visible(key,g)
    def view_for(self,key):
        if key in ('s3_record_cover','s3_record'):return [1.75,3.5]
        if key=='s3_feed':return [3.5,3.5]
        return super().view_for(key)
    def focus_for(self,key):
        if key in ('s3_record_cover','s3_record'):return [1.65,4.20,.815]
        if key=='s3_feed':return [3.45,4.40,1.49]
        return self.centres.get(key)
    def label_for(self,key):
        if key in ('s3_record_cover','s3_record','s3_feed'):return LABELS[key]
        return super().label_for(key)
    def update_clue(self,i,g):
        if i!=1:return
        active=self.active_flash.get(i);answer=self.spec['stages'][1]['answer'];lit=answer[active] if active is not None else None
        for j,(off,on) in enumerate(self.signal_lamps):self.visibility(on,j==lit);self.visibility(off,j!=lit)
    def build(self,g):
        w,d=self.spec['size'];cfg=self.spec['door'];self.room_shell('signal_workroom',size=(w,d),openings={'south':[(cfg['start']-.03,cfg['start']+cfg['width']+.03)]})
        self.box('solid_subfloor',[w/2,d/2,-.075],[w+.14,d+.14,.10],'darkwood',bevel=.001);self.build_door()
        self.table('north_service_bench',(2.53,4.60),(4.38,.64),height=.73)
        self.table('west_patch_bench',(.40,3.25),(.66,1.65),height=.73)
        for i,s in enumerate(self.spec['stages']):r=self.station(i,s);self.clue(i,s,r);self.controls_for(i,s,r)
        r=self.roots[2];self.key_case=self.group('key_box',[.90,.40,.36],r);self.reg('key_box',self.key_case)
        for pos,size in [([0,-.40,.405],[.56,.34,.025]),([-.28,-.40,.47],[.025,.34,.13]),([.28,-.40,.47],[.025,.34,.13]),([0,-.57,.47],[.56,.025,.13]),([0,-.23,.47],[.56,.025,.13])]:self.box('key_case',pos,size,'paint',self.key_case)
        self.key_bolt=self.group('key_box_bolt',[0,-.605,.48],self.key_case);self.box('box_latch',[0,0,0],[.15,.03,.05],'steel',self.key_bolt)
        self.key_lid=self.group('key_box_lid',[0,-.22,.55],self.key_case);self.box('key_lid',[0,-.18,0],[.60,.38,.025],'paint',self.key_lid)
        self.key=self.tool('key',r,[.90,.01,.788],'key');self.transform(self.key,rpy=[90,0,0])
        writer=self.roots[1]
        self.box('record_tray_floor',[0,-.40,.7825],[.37,.23,.025],'steel',writer)
        for x in [-.18,.18]:self.box('record_tray_side',[x,-.40,.810],[.018,.23,.050],'enamel',writer)
        for y in [-.51,-.29]:self.box('record_tray_end',[0,y,.810],[.37,.018,.050],'enamel',writer)
        self.record_hatch=self.group('record_output_hinge',[0,-.285,.84],writer)
        self.box('record_output_cover',[0,-.1125,0],[.40,.235,.018],'enamel',self.record_hatch)
        self.box('record_cover_pull',[0,-.225,.014],[.11,.035,.025],'steel',self.record_hatch)
        self.reg('s3_record_cover',self.record_hatch)
        self.record_card=self.group('printed_pulse_record',[0,-.40,.800],writer)
        self.box('record_card_body',[0,0,0],[.285,.175,.010],'paper',self.record_card)
        im=Image.new('RGB',(900,420),(208,217,190));ink=ImageDraw.Draw(im)
        for j,v in enumerate(self.spec['stages'][2]['visual']['upper']):
            x=42+j*140;z=110 if v else 245
            ink.line([(x,290),(x+30,290),(x+30,z),(x+105,z),(x+105,290),(x+130,290)],fill=(30,65,59),width=11)
        for j in range(6):ink.rectangle((55+j*140,360,105+j*140,400),fill=(171,142,54))
        self.plane('pulse_record_print',[0,0,.006],.275,.165,(1,0,0),(0,1,0),None,self.record_card,material=self.image_mat('r06_record_print',self._record_image(im)))
        self.reg('s3_record',self.record_card)
        self.record_release_red=self.cylinder('record_hatch_red',[.235,-.32,.84],.013,.015,'red_led','z',writer,n=24)
        self.record_release_green=self.cylinder('record_hatch_green',[.235,-.32,.84],.013,.015,'green','z',writer,n=24)
        for x in [-.13,.13]:
            self.tube('reader_support_upright',[x,-.04,1.41],[x,-.04,1.45],.009,'steel',self.roots[2])
            self.tube('reader_support_arm',[x,-.04,1.45],[x,-.13,1.45],.009,'steel',self.roots[2])
        reader=self.group('comparator_record_reader',[0,-.12,1.49],self.roots[2]);self.box('record_reader_housing',[0,0,0],[.35,.15,.10],'enamel',reader)
        self.box('record_card_slot',[0,-.078,0],[.30,.014,.018],'rubber',reader)
        self.reg('s3_feed',reader);self.record_inserted=self.group('inserted_record_edge',[0,-.085,.002],reader)
        self.box('record_edge',[0,0,0],[.28,.055,.008],'paper',self.record_inserted)
        for j in range(6):self.box('record_contact',[(-2.5+j)*.039,-.02,.005],[.018,.025,.003],'brass',self.record_inserted)
        self.record_reader_lamp=self.cylinder('record_loaded_lamp',[.143,-.081,.027],.009,.008,'green','y',reader,n=20)
        self.decor();self.sync(g)
        (self.run/'ROOM_GEOMETRY.json').write_text(json.dumps({'id':'R06','size':[w,d],'camera_height':1.35,'stage_views':self.stage_views,'style':'wood workbench, grey-green storage, physical patch leads and lamps','input_size':[640,360]},indent=2),encoding='utf-8')
    def decor(self):
        shelf=self.group('spares_shelf',[4.73,2.80,0]);self.transform(shelf,rpy=[0,0,-90])
        for x in [-.65,.65]:self.box('upright',[x,0,.74],[.045,.40,1.48],'darkwood',shelf)
        for z in [.16,.73,1.30]:self.box('shelf_board',[0,0,z],[1.36,.42,.045],'wood',shelf)
        self.box('shelf_back',[0,.19,.75],[1.28,.025,1.45],'paint',shelf);self.add_obstacle(4.48,2.08,4.97,3.52)
        for j in range(3):
            x=(j-1)*.36;n=self.group('wire_reel_'+str(j),[x,0,.89],shelf)
            self.cylinder('cable_winding',[0,0,0],.11,.15,['lead_blue','rubber','lead_red'][j],'y',n,n=28)
            for y in [-.085,.085]:self.cylinder('reel_flange',[0,y,0],.13,.02,'wood','y',n,n=28)
            self.cylinder('reel_core',[0,-.098,0],.024,.015,'steel','y',n,n=16)
        for j in range(3):self.box('parts_tin',[(j-1)*.39,0,.275],[.30,.26,.16],'steel',shelf,bevel=.012)
        meter=self.group('fixed_analogue_meter',[.105,1.3,1.48]);self.transform(meter,rpy=[0,0,90]);self.box('meter_case',[0,0,0],[.34,.10,.29],'enamel',meter,bevel=.02)
        im=Image.new('RGB',(500,340),(213,209,184));ink=ImageDraw.Draw(im);ink.arc((70,65,430,390),190,350,fill=(45,55,50),width=6);ink.line((250,285,330,105),fill=(38,47,44),width=7)
        for angle in range(200,341,20):
            a=math.radians(angle);ink.line((250+165*math.cos(a),255+165*math.sin(a),250+144*math.cos(a),255+144*math.sin(a)),fill=(45,55,50),width=4)
        self.face('meter_face',meter,[0,-.057,0],.28,.22,im)
        self.box('window_glass',[2.6,4.925,1.92],[.90,.018,.46],'window_pale')
        for x in [2.13,2.60,3.07]:self.box('window_frame',[x,4.90,1.92],[.035,.045,.52],'darkwood')
        for z in [1.67,2.17]:self.box('window_frame',[2.6,4.90,z],[.97,.045,.035],'darkwood')
        for a,b in [([.12,3.85,1.53],[.12,4.86,1.53]),([.12,4.86,1.53],[1.65,4.86,1.53]),([1.65,4.86,1.53],[1.65,4.72,1.41])]:self.tube('power_conduit',a,b,.014,'steel')
    def sync(self,g,blend=None):
        super().sync(g,blend)
        assignment={int(k):int(v) for k,v in g.states[0].get('assignment',{}).items()}
        for j,n in enumerate(self.items[0]):
            slot=next((k for k,v in assignment.items() if v==j),None)
            pos=[(j-1)*.23,-.22,.795] if slot is None else [(slot-1.5)*.24,-.22,1.025]
            self.transform(n,pos,[-90,0,0] if slot is None else [0,0,0])
        self.transform(self.record_hatch,rpy=[-105 if g.states[2]['record_open'] else 0,0,0])
        self.visibility(self.record_card,'s3_record' not in g.taken)
        self.visibility(self.record_release_red,not g.solved[1]);self.visibility(self.record_release_green,g.solved[1])
        self.visibility(self.record_inserted,g.states[2]['record_loaded']);self.visibility(self.record_reader_lamp,g.states[2]['record_loaded'])
        self.stage_views[2]=[3.5,3.5] if g.states[2]['record_loaded'] else [1.75,3.5]
        self.stage_centres[2]=[3.45,4.43,1.17] if g.states[2]['record_loaded'] else [1.65,4.20,.815]
        self.update_clue(1,g)
        self.centres={}
        for key,n in self.target_nodes.items():
            tri=self.triangles(n)
            if tri.size:
                p=tri.reshape(-1,3);self.centres[key]=((p.min(0)+p.max(0))/2).tolist()
    def animate(self,d,before):
        prior=before.get('states',[{}, {}, {}])[1]
        if d.game.states[1].get('playback')!=prior.get('playback'):
            for j in range(3):
                self.active_flash[1]=j;self.sync(d.game);d.frame(warm=8);d.append('Watch the lamp',10);d.capture_feedback_frame()
                self.active_flash[1]=None;self.sync(d.game);d.frame(warm=4);d.append('',4)
        self.active_flash[1]=None;self.sync(d.game);d.frame(warm=8);d.append('Observe the instrument response',6)

class Scene(SignalWorkshopScene):
    def __init__(self,og,run):super().__init__(og,run,SPEC)