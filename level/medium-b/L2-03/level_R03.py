SPEC = {
 'id':'R03','title':'R03 · Sewing Workroom / 缝纫工作间','theme':'sewing',
 'size':[4.8,5.4],'door':{'side':'south','start':3.3,'width':1.04,'view':[3.75,1.0]},
 'start':[3.0,1.25,1.35],'start_yaw':90,'floor':'wood',
 'decor':[{'kind':'sewing_machine','wall':'north','centre':[2.9,5.0],'fixed':True},
          {'kind':'fabric_shelf','wall':'west','centre':[0.25,3.8],'fixed':True},
          {'kind':'thread_spools','wall':'north','centre':[3.65,5.1],'fixed':True},
          {'kind':'cutting_table','centre':[2.45,2.65],'fixed':True},
          {'kind':'ironing_board','wall':'east','centre':[4.45,4.65],'fixed':True}],
 'design_notes':['真实缝纫台、布卷架、针线盒和布料柜，不使用三台通用答题站。',
                 '抽屉中的线迹布样提供针线盒的图序；针线盒中的剪刀用来剪开布包。',
                 '图案按钮可以正常试按，信息和工具构成自然依赖，不设隐藏read或阶段门禁。'],
 'stages':[
  {'kind':'rotate_picture','name':'sewing table fabric mounts','wall':'north','centre':[1.45,5.0],
   'view':[1.5,4.0],'initial':[3,1,0],'target':[0,0,0],'auto':True,
   'visual':{'type':'fabric','pattern':'branch_stripe','panels':3,'cross_panel_features':['flowering_branch','two_horizontal_threads'],'rotation_asymmetric':True},
   'clue':{'type':'fabric','reference':'join the continuous branch and threads'},'clue_text':''},
  {'kind':'sequence','name':'wooden sewing box','wall':'east','centre':[4.4,3.4],'view':[3.5,3.5],
   'options':['circle','triangle','square','star','leaf','cross'],'answer':[0,3,0],'length':3,'auto':True,
   'visual':{'type':'line_trace','start':'spool','symbols':['circle','star','circle'],'crossings':False,'line_colour':'white','other_symbols':['triangle','square','leaf']},
   'clue':{'type':'line_trace','source':'cloth sample inside the sewing table drawer'},'clue_text':''},
  {'kind':'binary_pattern','name':'linen cabinet patchwork latch','wall':'west','centre':[0.12,1.9],
   'view':[1.25,2.0],'initial':[0,0,0,0],'target':[1,0,1,1],'rows':2,'cols':2,'auto':True,
   'setup':{'kind':'cut','item':'scissors','item_name':'sewing scissors','target_name':'temporary white stitching','consume':False,'gate':True},
   'visual':{'type':'binary_swatch','reference':[1,0,1,1],'rows':2,'cols':2,'cover':'stitched_cloth_bundle','seam_colour':'white'},
   'clue':{'type':'binary_swatch','source':'inside the cut cloth bundle on the fabric shelf'},'clue_text':''}],
 'author_solution':['Join the three fabric mounts on the sewing table.',
                    'Open the unlocked table drawer and observe the stitched sample.',
                    'Trace its thread from the spool: circle, star, circle. Enter it on the wooden sewing box.',
                    'Open the sewing box, take the scissors, and cut the white temporary stitching on the cloth bundle.',
                    'Match the four real cabinet-door cloth patches to the revealed sample.',
                    'Open the linen cabinet, take the brass key, use it on the exit, and open the exit.']}


import copy,math,re
from easy88_core import EasyGame,reachable_approach
from action_feedback import failure_for,NO_OBJECT,NO_ITEM

class Game(EasyGame):
    SPEC=SPEC
    LABELS={
      'exit':'exit door','key':'brass door key','key_box':'linen cabinet door',
      's2_cover':'sewing table drawer','s2_clue':'stitched cloth sample',
      'scissors_box':'wooden sewing box lid','s3_tool':'sewing scissors',
      's3_setup':'white temporary stitching','s3_clue':'black and white cloth sample',
      's2_reset':'touchscreen clear icon',
      's1_tile_0':'left fabric mount','s1_tile_1':'middle fabric mount','s1_tile_2':'right fabric mount',
      's3_control_0':'upper left cloth patch','s3_control_1':'upper right cloth patch',
      's3_control_2':'lower left cloth patch','s3_control_3':'lower right cloth patch',
      'room_shell':'wall','floor':'floor'}
    for _j,_name in enumerate(SPEC['stages'][1]['options']):LABELS['s2_choice_'+str(_j)]=_name+' touchscreen symbol'
    def __init__(self):
        super().__init__()
        self.opened={'s2_cover':False,'scissors_box':False,'key_box':False,'exit':False}
    def stage_accessible(self,index):
        return index==0 or index==1 and self.opened['s2_cover'] or index==2 and self.states[2]['setup_open']
    def stage_exposed(self,index):return self.stage_accessible(index)
    def act(self,a):
        kind=a.get('action');key=a.get('_hit364')
        def out(ok,text=''):
            return {'ok':bool(ok),'text':str(text) if kind=='read' and ok else '' if ok else str(text or failure_for(kind))}
        if not a.get('_validated364') or not isinstance(key,str):return out(False,NO_OBJECT)
        if key=='exit':
            if kind=='use':
                item=self._resolve_item(a.get('item'))
                if item is None:return out(False,NO_ITEM)
                if item!='key':return out(False)
                self.exit_unlocked=True;return out(True)
            if kind in ('open','close'):
                if kind=='open' and not self.exit_unlocked:return out(False)
                self.opened['exit']=kind=='open';self.exited=kind=='open' and self.exit_unlocked;return out(True)
            return out(False)
        if key in ('s2_cover','scissors_box','key_box'):
            solved_index={'s2_cover':0,'scissors_box':1,'key_box':2}[key]
            if kind not in ('open','close') or kind=='open' and not self.solved[solved_index]:return out(False)
            self.opened[key]=kind=='open';return out(True)
        if key=='s3_tool':
            if kind!='take' or not self.opened['scissors_box'] or key in self.taken:return out(False)
            self.taken.add(key);self.holding.append(key);return out(True)
        if key=='key':
            if kind!='take' or not self.opened['key_box'] or key in self.taken:return out(False)
            self.taken.add(key);self.holding.append(key);return out(True)
        if key=='s3_setup':
            state=self.states[2]
            if kind=='use':
                item=self._resolve_item(a.get('item'))
                if item is None:return out(False,NO_ITEM)
                if item!='s3_tool' or state['setup_used']:return out(False)
                state.update(setup_used=True,setup_open=True,setup_ready=True);return out(True)
            if kind in ('open','close') and state['setup_used']:
                state['setup_open']=kind=='open';state['setup_ready']=state['setup_open'];return out(True)
            return out(False)
        m=re.fullmatch(r's1_tile_([0-2])',key)
        if m:
            if kind!='press':return out(False)
            values=self.states[0]['angles'];j=int(m[1]);values[j]=(values[j]+1)%4
            if values==SPEC['stages'][0]['target']:self.solved[0]=True
            return out(True)
        m=re.fullmatch(r's2_choice_([0-5])',key)
        if m:
            if kind!='press':return out(False)
            state=self.states[1]
            if len(state['buffer'])>=3:state['buffer']=[]
            state['buffer'].append(int(m[1]));state['overflow']=False
            if len(state['buffer'])<3:return out(True)
            if state['buffer']==SPEC['stages'][1]['answer']:
                self.solved[1]=True;return out(True)
            state['buffer']=[];return out(False)
        if key=='s2_reset':
            if kind!='press':return out(False)
            self.states[1]['buffer']=[];self.states[1]['overflow']=False;return out(True)
        m=re.fullmatch(r's3_control_([0-3])',key)
        if m:
            if kind!='press':return out(False)
            state=self.states[2];j=int(m[1]);state['selected'][j]=1-int(state['selected'][j])
            if state['selected']==SPEC['stages'][2]['target']:self.solved[2]=True
            return out(True)
        return out(False)


TITLE=SPEC['title'];LEVEL_ID=SPEC['id'];START=SPEC['start'];START_YAW=SPEC['start_yaw']
CAP=80;OBSERVATION_SIZE=(1280,640);VISUAL_ONLY=False;READ_ENABLED=True;READ_FEEDBACK_TEXT=True;LABELS=Game.LABELS

def exit_test(pos,g):return bool(g.exit_unlocked and g.opened['exit'])

def standard(d):
    import heapq,numpy as np
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
        view=list(d.pos[:2]) if stay else sc.view_for(key)
        if view is None:raise RuntimeError('No physical approach for '+key)
        point,k=axis_focus(key,view)
        if not stay:route_short(view,k,purpose)
        d.aim(point,purpose)
    def observe(key,purpose,stay=False):approach(key,purpose,stay);d.append(purpose,18)
    def click(key,kind='press',item=None):
        c=candidate(key)
        if c is None:raise RuntimeError('Physical object not currently exposed: '+key)
        hit=find_point(key,d.pos,d.quat,d.depth,sc.candidates(g),fx=640.,fy=640.,cx=640.,cy=320.,actor_xy=d.pos[:2],tolerance=.05,mesh_tolerance=.04,grid=41,return_hit=True)
        if hit is None:
            d.aim(centre(key),'Look at the actual visible object')
            hit=find_point(key,d.pos,d.quat,d.depth,sc.candidates(g),fx=640.,fy=640.,cx=640.,cy=320.,actor_xy=d.pos[:2],tolerance=.05,mesh_tolerance=.04,grid=61,return_hit=True)
        reach=1.5 if key=='exit' else 1.2
        if hit is not None and float(hit['distance'])>reach:
            view=reachable_approach(d.pos[:2],d.yaw,hit,lambda x,y:sc.blocked(x,y,g),SPEC['size'],reach)
            route_short(view,axis_focus(key,view)[1],'Approach the actual visible surface');d.aim(centre(key),'Look at the reachable object')
            hit=find_point(key,d.pos,d.quat,d.depth,sc.candidates(g),fx=640.,fy=640.,cx=640.,cy=320.,actor_xy=d.pos[:2],tolerance=.05,mesh_tolerance=.04,grid=61,return_hit=True)
        if hit is None or float(hit['distance'])>reach:raise RuntimeError('No current visible native pixel within unchanged reach for '+key)
        a={'thought':'Use the clue and the actual room object.','action':kind,'point':hit['point'],'target':LABELS.get(key,key.replace('_',' '))}
        if item is not None:a['item']=LABELS.get(item,item)
        return d.execute(a,'Observe the physical response')
    observe('s1_tile_1','Look over the sewing table and joined cloth pattern')
    for j,target in enumerate(SPEC['stages'][0]['target']):
        while g.states[0]['angles'][j]!=target:click('s1_tile_'+str(j))
    if not g.solved[0]:raise RuntimeError('Cloth pattern did not release the table drawer')
    approach('s2_cover','Look down to the actual sewing-table drawer',stay=True);click('s2_cover','open')
    d.append('Observe the complete stitched sample in the open drawer',24)
    approach('scissors_box','Walk to the wooden sewing box')
    for j in SPEC['stages'][1]['answer']:click('s2_choice_'+str(j))
    if not g.solved[1]:raise RuntimeError('The complete touchscreen sequence did not release the sewing box latch')
    click('scissors_box','open');d.append('Observe the sewing scissors in the opened box',18);click('s3_tool','take')
    approach('s3_setup','Approach the temporary stitching on the cloth bundle');click('s3_setup','use','s3_tool')
    observe('s3_clue','Observe the black and white sample after cutting the stitching',stay=True)
    approach('s3_control_0','Face the linen cabinet and its four actual cloth patches')
    for j,target in enumerate(SPEC['stages'][2]['target']):
        if g.states[2]['selected'][j]!=target:click('s3_control_'+str(j))
    if not g.solved[2]:raise RuntimeError('Patchwork pattern did not release the linen cabinet')
    click('key_box','open');d.append('Observe the brass key in the opened linen cabinet',18);click('key','take')
    approach('exit','Return to the actual exit door');click('exit','use','key');click('exit','open')
    if not exit_test(d.pos,g):raise RuntimeError('Open-door success was not reached')



def cpu_check():
    g=Game();checks=[];trace=[]
    def ck(name,condition):
        assert condition,name;checks.append(name)
    def a(kind,key,**fields):
        before=g.snapshot();r=g.act(dict(action=kind,_hit364=key,_validated364=True,**fields));trace.append({'action':kind,'target':key,'fields':fields,'result':r,'before':before,'after':g.snapshot()});return r
    def ok(kind,key,**fields):
        r=a(kind,key,**fields);ck(kind+' '+key,r['ok']);ck('successful '+kind+' stays silent',r['text']=='');return r
    pristine=g.snapshot();ck('unvalidated world action rejected',not g.act({'action':'open','_hit364':'s2_cover'})['ok']);ck('unvalidated action no mutation',g.snapshot()==pristine)
    for key in ['s2_cover','scissors_box','key_box','exit']:ck(key+' initially locked',not a('open',key)['ok'])
    ck('closed sewing box hides scissors',not a('take','s3_tool')['ok']);ck('closed cabinet hides key',not a('take','key')['ok'])
    for key in ['s2_clue','s3_clue','sewing_machine','fabric_shelf']:ck('fixed '+key+' cannot take',not a('take',key)['ok'])
    ok('press','s2_choice_1');ck('visible input has no previous-stage hidden gate',g.states[1]['buffer']==[1]);ok('press','s2_reset')
    for j,t in enumerate(SPEC['stages'][0]['target']):
        while g.states[0]['angles'][j]!=t:ok('press','s1_tile_'+str(j))
    ck('joined cloth releases only drawer latch',g.solved==[True,False,False] and not g.opened['s2_cover']);ok('open','s2_cover')
    ck('graphical trace is not transcribed to answer',not a('read','s2_clue')['ok']);ck('cloth stays fixed',not a('take','s2_clue')['ok'])
    for j in [0,3]:ok('press','s2_choice_'+str(j))
    ck('first two touch entries give no solved feedback',g.states[1]['buffer']==[0,3] and not g.solved[1])
    ck('wrong complete group rejected',not a('press','s2_choice_2')['ok'] and not g.solved[1]);ck('wrong group clears all3 entries',not g.states[1]['buffer'] and not g.states[1]['overflow'])
    for j in SPEC['stages'][1]['answer']:ok('press','s2_choice_'+str(j))
    ck('third correct touch unlocks box without confirm',g.solved[1] and g.states[1]['buffer']==SPEC['stages'][1]['answer'])
    ck('correct group does not auto open or take',not g.opened['scissors_box'] and 's3_tool' not in g.holding)
    ck('no separate confirm target accepted',not a('press','s2_confirm')['ok'])
    grouped=Game()
    for j in [1,0,3,0]:grouped.act({'action':'press','_hit364':'s2_choice_'+str(j),'_validated364':True})
    ck('rolling substring is not accepted',not grouped.solved[1] and grouped.states[1]['buffer']==[0])
    for j in [3,0]:grouped.act({'action':'press','_hit364':'s2_choice_'+str(j),'_validated364':True})
    ck('next complete disjoint group can unlock',grouped.solved[1])
    ok('open','scissors_box');ok('take','s3_tool');ck('scissors enter inventory',g.holding==['s3_tool']);ck('no duplicate scissors',not a('take','s3_tool')['ok'])
    before=g.snapshot();ck('wrong held tool rejected',not a('use','s3_setup',item='wrong tool')['ok']);ck('wrong tool no mutation',g.snapshot()==before)
    ok('use','s3_setup',item='sewing scissors');ck('cut opens cloth bundle, not cabinet',g.states[2]['setup_open'] and not g.opened['key_box']);ok('close','s3_setup');ok('open','s3_setup')
    for j,t in enumerate(SPEC['stages'][2]['target']):
        if g.states[2]['selected'][j]!=t:ok('press','s3_control_'+str(j))
    ck('whole patch pattern unlocks cabinet automatically',g.solved==[True,True,True]);ck('key still requires physical cabinet open',not a('take','key')['ok']);ok('open','key_box');ok('take','key')
    ck('key enters inventory only once',g.holding==['s3_tool','key'] and not a('take','key')['ok']);ok('use','exit',item='brass door key');ck('using key alone does not win',not exit_test(START,g));ok('open','exit');ck('opening unlocked exit wins without walking out',exit_test(START,g))
    restored=Game()
    for k,v in g.snapshot().items():setattr(restored,k,set(v) if k=='taken' else copy.deepcopy(v))
    ck('human snapshot schema roundtrip',restored.snapshot()==g.snapshot());ck('no artificial stage3 cover',set(g.opened)=={'s2_cover','scissors_box','key_box','exit'})
    return {'level':'R03','scope':'CPU public state machine only; not native RGB/video acceptance','passed':len(checks),'checks':checks,'trace':trace,'final':g.snapshot()}




from pathlib import Path
import math,json
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


class R03WorkroomScene(EasyScene):
    def __init__(self,og,run,spec):
        super().__init__(og,run,spec)
        self._labels={};self._views={};self._focus={};self.patch_nodes=[];self.rotor_nodes=[];self.input_nodes=[]
    def palette(self):
        super().palette()
        for name,c in [('linen',(.68,.62,.49)),('cloth_blue',(.13,.27,.34)),('cloth_red',(.43,.19,.16)),('cloth_gold',(.56,.43,.20)),('cloth_white',(.76,.74,.64)),('cloth_black',(.035,.045,.047)),('sewing_enamel',(.075,.10,.095)),('drawer_inner',(.42,.29,.16))]:self.mat(name,c,rough=.93)
    def _reg(self,key,node,label,view,focus=None):
        self.reg(key,node);self._labels[key]=label;self._views[key]=list(view)
        if focus is not None:self._focus[key]=list(focus)
        return node
    def _image(self,name,im):
        p=self.tex/(name+'.png');im.save(p);return self.image_mat(name,p)
    def _flat(self,key,parent,pos,w,h,im,right=(1,0,0),up=(0,0,1)):
        return self.plane(key,pos,w,h,right,up,None,parent,material=self._image(key,im))
    @staticmethod
    def _cloth(size=(900,300),colour=(225,216,190)):
        w,h=size;x,y=np.meshgrid(np.arange(w),np.arange(h));a=np.empty((h,w,3),dtype=np.uint8)
        stripe=((x%5==0)|(y%5==0)).astype(float)*-5+((x+y)%7==0).astype(float)*2
        for k,v in enumerate(colour):a[:,:,k]=np.clip(v+stripe,0,255)
        return Image.fromarray(a)
    def _pattern(self):
        im=self._cloth();d=ImageDraw.Draw(im)
        d.line([(0,188),(110,167),(265,179),(388,125),(550,143),(680,98),(900,115)],fill=(56,100,58),width=10)
        for x,y in [(115,164),(460,134),(780,106)]:
            d.line((x,y,x+15,y-44),fill=(63,103,63),width=6)
            for dx,dy in [(-14,-4),(14,-4),(0,-18),(0,10)]:d.ellipse((x+dx-10,y-44+dy-10,x+dx+10,y-44+dy+10),fill=(156,91,71))
            d.ellipse((x-8,y-52,x+8,y-36),fill=(191,155,72))
        for yy in [70,249]:
            for xx in range(0,900,14):d.line((xx,yy,xx+8,yy),fill=(116,134,118),width=3)
        return im
    def _trace(self):
        im=self._cloth((960,480),(43,65,71));d=ImageDraw.Draw(im)
        d.rounded_rectangle((12,12,948,468),radius=18,outline=(128,106,76),width=5)
        path=[(85,340),(180,340),(180,150),(390,150),(390,295),(630,295),(630,110),(830,110)]
        for a,b in zip(path,path[1:]):
            n=max(1,int(math.dist(a,b)/15))
            for i in range(n):
                t=i/n;u=min(1,t+.55/n);d.line((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[0]+(b[0]-a[0])*u,a[1]+(b[1]-a[1])*u),fill=(231,222,192),width=7)
        d.rectangle((40,305,100,375),fill=(135,81,48));d.rectangle((30,300,110,310),fill=(94,56,36));d.rectangle((30,370,110,380),fill=(94,56,36))
        for yy in range(315,370,7):d.line((41,yy,99,yy),fill=(211,195,146),width=3)
        for symbol,x,y in [('circle',180,150),('star',390,295),('circle',830,110),('triangle',520,100),('square',805,330),('leaf',240,365)]:
            d.ellipse((x-42,y-42,x+42,y+42),fill=(43,65,71));draw_symbol(d,symbol,(x-34,y-34,x+34,y+34),fill=(229,221,193),outline=(225,218,190))
        return im
    def _binary(self):
        im=self._cloth((500,500));d=ImageDraw.Draw(im)
        for j,v in enumerate([1,0,1,1]):
            x=25+(j%2)*240;y=25+(j//2)*240;d.rectangle((x,y,x+220,y+220),fill=(32,40,39) if v else (229,223,202))
            for t in range(6,215,13):d.line((x+t,y+6,x+t+6,y+6),fill=(152,144,120),width=2);d.line((x+t,y+214,x+t+6,y+214),fill=(152,144,120),width=2)
        return im
    def _symbol(self,name,size=200):
        im=self._cloth((size,size),(217,202,171));d=ImageDraw.Draw(im)
        if name=='confirm':d.line([(48,105),(90,144),(156,55)],fill=(42,57,43),width=13)
        elif name=='reset':
            d.arc((40,40,160,160),35,305,fill=(69,60,43),width=12);d.polygon([(155,42),(164,87),(121,65)],fill=(69,60,43))
        else:draw_symbol(d,name,(30,30,size-30,size-30),fill=(45,62,55),outline=(40,53,45))
        return im
    def _press_button(self,key,parent,pos,symbol,size=.085):
        node=self.group(key,pos,parent);self.cylinder('wood_button',[0,0,0],size*.53,.025,'darkwood','y',node,n=24)
        self._flat(key+'_ink',node,[0,-.014,0],size*.88,size*.88,self._symbol(symbol))
        return node
    def _shelf(self,key,x,y,width=1.45,depth=.42,height=1.5,angle=90):
        g=self.group(key,[x,y,0]);self.transform(g,rpy=[0,0,angle])
        for xx in [-width/2,width/2]:self.box(key+'_upright',[xx,.0,height/2],[.055,depth,height],'darkwood',g)
        for zz in [.16,.78,1.38]:self.box(key+'_board',[0,0,zz],[width+.07,depth,.04],'wood',g)
        self.box(key+'_back',[0,depth/2-.025,height/2],[width,.035,height],'paint',g)
        pts=[]
        for xx in [-width/2-.04,width/2+.04]:
            for yy in [-depth/2,depth/2]:
                a=math.radians(angle);pts.append([x+xx*math.cos(a)-yy*math.sin(a),y+xx*math.sin(a)+yy*math.cos(a)])
        self.add_obstacle(min(q[0] for q in pts),min(q[1] for q in pts),max(q[0] for q in pts),max(q[1] for q in pts))
        return g
    def _fabric_roll(self,key,parent,pos,colour='cloth_blue',length=.28,radius=.065,axis='x'):
        n=self.group(key,pos,parent);self.cylinder(key+'_cloth',[0,0,0],radius,length,colour,axis,n,n=28)
        ax={'x':0,'y':1,'z':2}[axis];p=[0.,0.,0.];p[ax]=length/2+.001
        self.cylinder(key+'_card',p,radius*.30,.005,'paper',axis,n,n=20)
        for shift in [-.012,.012]:
            pp=list(p);pp[ax]+=shift*.1;self.cylinder(key+'_edge',pp,radius*.92,.002,colour,axis,n,n=30)
        return n
    def _sewing_machine(self):
        n=self.group('cast_iron_sewing_machine',[2.96,5.00,.79])
        self.box('machine_bed',[0,0,0],[.62,.32,.055],'sewing_enamel',n,bevel=.02)
        self.box('machine_upright',[.20,.0,.18],[.14,.18,.34],'sewing_enamel',n,bevel=.04)
        self.box('machine_arm',[-.015,0,.34],[.50,.18,.12],'sewing_enamel',n,bevel=.045)
        self.box('machine_head',[-.24,0,.25],[.105,.16,.21],'sewing_enamel',n,bevel=.025)
        self.cylinder('handwheel',[.31,.0,.20],.12,.04,'iron','x',n,n=32)
        self.cylinder('wheel_centre',[.334,.0,.20],.038,.012,'brass','x',n)
        self.cylinder('spool_pin',[.03,0,.44],.008,.14,'steel','z',n)
        self.cylinder('upper_thread_spool',[.03,0,.43],.035,.10,'cloth_red','z',n)
        for z in [.375,.485]:self.cylinder('spool_end',[.03,0,z],.042,.012,'wood','z',n)
        self.tube('thread_route',[.03,-.02,.47],[-.24,-.02,.36],.0024,'paper',n)
        self.cylinder('needle',[-.24,-.025,.105],.003,.16,'steel','z',n)
        self.box('needle_plate',[-.23,-.02,.037],[.12,.13,.007],'steel',n)
        self.tube('foot_arm',[-.20,-.05,.13],[-.20,-.05,.05],.007,'steel',n)
        self.box('presser_foot',[-.20,-.07,.047],[.05,.07,.008],'steel',n)
        self._reg('fixed_sewing_machine',n,'sewing machine',[3.5,4.0])
        self.box('foot_pedal',[2.96,5.0,.07],[.25,.35,.055],'iron');self.tube('pedal_belt',[3.15,5.05,.15],[3.19,5.05,.78],.007,'rubber')
    def _decor_room(self):
        self._sewing_machine()
        peg=self.group('thread_rack',[4.70,4.72,1.49]);self.transform(peg,rpy=[0,0,-90]);self.box('rack_back',[0,0,0],[.65,.06,.42],'wood',peg)
        for j in range(8):
            x=(j%4-1.5)*.14;z=(j//4-.5)*.18;self.cylinder('thread_spindle',[x,-.10,z],.011,.18,'wood','y',peg)
            self.cylinder('thread_coil',[x,-.11,z],.044,.09,['cloth_red','cloth_blue','cloth_gold','cloth_white'][j%4],'y',peg)
            for yy in [-.165,-.055]:self.cylinder('thread_end',[x,yy,z],.049,.009,'wood','y',peg)
        paper=self._cloth((440,600),(225,218,196));d=ImageDraw.Draw(paper);d.line([(100,100),(180,75),(210,155),(300,75),(360,110),(310,245),(330,500),(115,500),(135,245),(100,100)],fill=(95,106,94),width=4)
        d.line((220,170,220,485),fill=(135,135,113),width=2)
        self._flat('paper_dress_pattern',None,[3.70,5.315,1.68],.38,.52,paper)
        for x,z in [(3.53,1.91),(3.87,1.91)]:self.cylinder('paper_pin',[x,5.30,z],.009,.01,'brass','y')
        self.mat('window_pale',(.55,.66,.66),rough=.9,emission=(.20,.25,.24))
        self.box('window_glass',[.075,4.95,1.75],[.02,.54,.62],'window_pale')
        for y in [4.65,5.25]:self.box('window_jamb',[.10,y,1.75],[.07,.035,.69],'darkwood')
        for z in [1.42,1.75,2.08]:self.box('window_rail',[.10,4.95,z],[.07,.65,.035],'darkwood')
        cut=self.table('small_cutting_table',(2.45,2.65),(1.10,.65),height=.72)
        self.box('cloth_on_cutting_table',[2.35,2.66,.775],[.68,.44,.016],'cloth_blue',bevel=.005)
        self.box('folded_offcut',[2.70,2.74,.79],[.25,.18,.055],'linen',bevel=.009)
        ruler=self.group('fixed_tailor_ruler',[2.40,2.45,.792]);self.box('ruler_wood',[0,0,0],[.57,.045,.012],'paper',ruler)
        for x in np.linspace(-.26,.26,27):self.box('ruler_tick',[float(x),-.01,.007],[.002,.018,.002],'darkwood',ruler,bevel=.0001)
        self._reg('fixed_tailor_ruler',ruler,'tailor ruler',[2.5,1.75])
        ironboard=self.table('ironing_board',(1.30,.40),(1.43,.48),height=.70)
        self.box('ironing_cloth',[1.30,.40,.75],[1.34,.45,.025],'cloth_white',bevel=.018)
        iron=self.group('fixed_iron',[1.05,.40,.80]);self.mesh('iron_sole',[[-.12,-.10,0],[.12,-.10,0],[.04,.17,0],[-.04,.17,0],[-.10,-.08,.07],[.10,-.08,.07],[.025,.14,.07],[-.025,.14,.07]],[[0,1,2,3],[0,4,5,1],[1,5,6,2],[2,6,7,3],[3,7,4,0],[4,7,6,5]],'steel',iron)
        self.tube('iron_handle_a',[-.06,-.04,.08],[-.06,-.04,.16],.018,'iron',iron);self.tube('iron_handle_b',[.06,-.04,.08],[.06,-.04,.16],.018,'iron',iron);self.tube('iron_grip',[-.06,-.04,.16],[.06,-.04,.16],.024,'iron',iron)
        self._reg('fixed_iron',iron,'iron',[1.25,1.25])
    def _screen_file(self,buffer,solved=False):
        from font_utils import load_font
        im=Image.new('RGB',(1200,600),(24,37,39));d=ImageDraw.Draw(im)
        d.rounded_rectangle((5,5,1195,595),radius=25,outline=(72,113,103) if solved else (79,92,91),width=7)
        options=self.spec['stages'][1]['options']
        for j in range(3):
            x=180+j*270;d.rounded_rectangle((x-90,23,x+90,153),radius=14,fill=(37,53,54),outline=(93,113,108),width=3)
            if j<len(buffer):draw_symbol(d,options[int(buffer[j])],(x-46,44,x+46,135),fill=(225,219,192),outline=(225,219,192))
            else:d.line((x-25,95,x+25,95),fill=(121,139,132),width=8)
        d.arc((1055,44,1135,124),35,308,fill=(194,205,188),width=8);d.polygon([(1136,42),(1140,78),(1107,60)],fill=(194,205,188))
        for j,name in enumerate(options):
            x=(j%3)*400+200;y=180+(j//3)*210+105
            d.rounded_rectangle((x-175,y-87,x+175,y+87),radius=17,fill=(36,52,52),outline=(91,111,105),width=3)
            draw_symbol(d,name,(x-58,y-58,x+58,y+58),fill=(224,218,188),outline=(224,218,188))
        signature=''.join(map(str,buffer)) or 'empty';p=self.tex/('single_lcd_'+signature+('_ok' if solved else '')+'.png');im.save(p);return p
    def _screen_piece(self,key,rect,target):
        x0,y0,x1,y1=rect;points=[]
        for x,y in [(x0,y1),(x1,y1),(x1,y0),(x0,y0)]:points.append([(x/1200-.5)*.78,-.22+(.5-y/600)*.34,.0185])
        uv=[(x0/1200,1-y1/600),(x1/1200,1-y1/600),(x1/1200,1-y0/600),(x0/1200,1-y0/600)]
        n=self.mesh(key+'_glass',points,[[0,1,2,3]],self.screen_mat,self.box_lid,uv=uv)
        if target:
            label='clear touch icon' if key=='s2_reset' else self.spec['stages'][1]['options'][int(key.rsplit('_',1)[1])]+' touch icon'
            self._reg(key,n,label,[3.5,3.5],[4.40,3.4,.7835])
        return n
    def _real_scissors(self,parent,pos):
        self.mat('scissor_real_steel',(.64,.69,.72),rough=.23,metal=.88)
        self.mat('scissor_cutting_edge',(.79,.82,.83),rough=.15,metal=.92)
        self.mat('scissor_dark_handles',(.025,.030,.029),rough=.48)
        n=self.group('real_steel_scissors',pos,parent)
        def prism(key,poly,z,h,mat):
            pts=[[x,y,z] for x,y in poly]+[[x,y,z+h] for x,y in poly];m=len(poly)
            faces=[list(range(m-1,-1,-1)),list(range(m,m*2))]+[[i,(i+1)%m,(i+1)%m+m,i+m] for i in range(m)]
            return self.mesh(key,pts,faces,mat,n)
        for sign,z in [(-1,0.),(1,.0045)]:
            prism('pointed_steel_blade',[(sign*-.010,-.014),(sign*.013,-.006),(sign*.030,.133)],z,.0038,'scissor_real_steel')
            prism('polished_cutting_bevel',[(sign*.008,-.003),(sign*.030,.133),(sign*.023,.105)],z+.0039,.0006,'scissor_cutting_edge')
            prism('steel_handle_shank',[(sign*.007,.004),(sign*.017,-.006),(sign*.049,-.058),(sign*.031,-.064)],z,.005,'scissor_real_steel')
            cx=sign*.037;cy=-.072;count=48;pts=[]
            for zz in [0.,.010]:
                for rx,ry in [(.028,.035),(.018,.024)]:
                    for j in range(count):
                        a=2*math.pi*j/count;pts.append([cx+rx*math.cos(a),cy+ry*math.sin(a),zz])
            faces=[]
            for j in range(count):
                k=(j+1)%count;faces.extend([[j,k,count+k,count+j],[2*count+j,3*count+j,3*count+k,2*count+k],[j,2*count+j,2*count+k,k],[count+j,count+k,3*count+k,3*count+j]])
            self.mesh('hollow_finger_ring',pts,faces,'scissor_dark_handles',n)
        self.cylinder('scissor_pivot_rivet',[0,0,.009],.011,.009,'steel','z',n,n=28)
        self.box('rivet_slot',[0,0,.014],[.012,.0015,.001],'iron',n,bevel=.0001)
        return n
    def build(self,g):
        self.room_shell('sewing_room',size=(4.8,5.4),openings={'south':[(3.27,4.37)]})
        self.box('solid_subfloor',[2.4,2.7,-.075],[4.94,5.54,.10],'darkwood',bevel=.001)
        self.table('sewing_workbench',(2.40,5.02),(2.90,.65),height=.74)
        for x in [.94,1.98]:self.box('drawer_housing_side',[x,4.97,.565],[.035,.55,.27],'wood')
        self.box('drawer_housing_back',[1.46,5.235,.565],[1.075,.035,.27],'wood')
        self.box('drawer_housing_floor',[1.46,4.97,.438],[1.075,.55,.025],'darkwood')
        self.box('drawer_front_upper_frame',[1.46,4.70,.661],[1.075,.045,.078],'wood')
        self.box('drawer_front_lower_frame',[1.46,4.70,.446],[1.075,.045,.027],'wood')
        for x in [.94,1.98]:self.box('drawer_front_side_frame',[x,4.70,.555],[.035,.052,.245],'wood')
        for x in [1.46-.468,1.46+.468]:
            self.box('fixed_drawer_slide',[x,4.96,.515],[.016,.52,.026],'steel')
            self.box('slide_mount',[x,4.96,.495],[.070,.50,.014],'iron')
        self.rotor_nodes=[];pattern=self._pattern()
        for j in range(3):
            x=1.17+j*.29;n=self.group('cloth_mount_'+str(j),[x,4.98,1.05]);self.box('hoop_wood',[0,0,0],[.278,.026,.278],'darkwood',n)
            self._flat('embroidery_panel_'+str(j),n,[0,-.014,0],.258,.258,pattern.crop((j*300,0,(j+1)*300,300)))
            self.cylinder('cloth_pivot',[x,5.03,1.05],.027,.09,'brass','y')
            self._reg('s1_tile_'+str(j),n,'rotating cloth sample',[1.5,4.0],[1.46,4.98,1.05]);self.rotor_nodes.append(n)
            _add_mark(self,'mount_turn_mark_'+str(j),n,[.105,-.0155,-.105],'turn',.045)
        for x in [1.0,1.93]:self.box('sample_stand_post',[x,5.045,.92],[.035,.05,.35],'wood')
        self.box('sample_stand_crossbar',[1.46,5.045,1.05],[.98,.035,.035],'wood')
        self.sample_lamp=self.group('sample_status_lamp',[2.01,4.98,1.05]);self.cylinder('sample_lamp_socket',[0,0,0],.033,.045,'iron','y',self.sample_lamp)
        self.sample_red=self.cylinder('sample_red_light',[0,-.026,0],.025,.009,'red_led','y',self.sample_lamp,n=28)
        self.sample_green=self.cylinder('sample_green_light',[0,-.026,0],.025,.009,'green','y',self.sample_lamp,n=28)
        self.drawer=self.group('sample_drawer',[1.46,4.70,.54]);
        for x in [-.460,.460]:self.box('moving_telescopic_slide',[x,.22,-.025],[.014,.465,.021],'steel',self.drawer)
        self.drawer_face=self.group('drawer_front',parent=self.drawer)
        self.box('drawer_front_wood',[0,0,-.005],[.96,.045,.17],'wood',self.drawer_face);self.box('drawer_pull',[0,-.050,0],[.20,.045,.025],'brass',self.drawer_face)
        self.drawer_bolt=self.group('drawer_lock_bolt',[.38,-.034,.015],self.drawer_face);self.box('drawer_bolt',[0,0,0],[.065,.018,.045],'brass',self.drawer_bolt)
        self.box('drawer_bottom',[0,.22,-.071],[.89,.45,.024],'drawer_inner',self.drawer)
        for x in [-.445,.445]:self.box('drawer_side',[x,.22,-.004],[.022,.45,.15],'wood',self.drawer)
        self.box('drawer_back',[0,.435,-.004],[.90,.025,.15],'wood',self.drawer)
        self._reg('s2_cover',self.drawer_face,'sewing table drawer',[1.5,3.75],[1.46,4.52,.57])
        self.box('folded_blue_cloth_padding',[0,.22,-.04],[.76,.39,.06],'cloth_blue',self.drawer)
        clothnode=self.group('stitched_cloth_sample',[0,.22,-.008],self.drawer)
        cloth=self._flat('stitched_sample_print',clothnode,[0,0,0],.73,.365,self._trace(),up=(0,1,0))
        self._reg('s2_clue',cloth,'stitched cloth sample',[1.5,4.0],[1.46,4.49,.532])
        self.box_root=self.group('notions_workstand',[4.40,3.40,0]);self.transform(self.box_root,rpy=[0,0,-90])
        self.box('notions_cabinet_body',[0,.03,.30],[1.10,.62,.56],'wood',self.box_root)
        self.box('notions_cabinet_top',[0,-.01,.61],[1.17,.68,.05],'wood',self.box_root)
        for x in [-.27,.27]:
            self.box('lower_storage_door',[x,-.29,.30],[.52,.035,.51],'paint',self.box_root);self.box('lower_storage_handle',[x+(.16 if x<0 else -.16),-.32,.32],[.025,.025,.13],'brass',self.box_root)
        self.add_obstacle(4.05,2.81,4.76,3.99)
        self.box('notions_box_bottom',[0,0,.650],[.87,.46,.025],'darkwood',self.box_root)
        self.box('light_velvet_lining',[0,0,.668],[.80,.395,.009],'linen',self.box_root)
        for x in [-.42,.42]:self.box('notions_box_side',[x,0,.705],[.035,.46,.10],'wood',self.box_root)
        self.box('notions_box_back',[0,.21,.705],[.84,.035,.10],'wood',self.box_root)
        self.box('notions_box_front',[0,-.22,.700],[.84,.035,.09],'wood',self.box_root)
        self.box_lid=self.group('notions_box_lid',[0,.22,.765],self.box_root)
        self.box('wooden_lid',[0,-.22,0],[.90,.48,.025],'wood',self.box_lid)
        lidtarget=self.group('lid_rim_and_pull',parent=self.box_lid)
        for x in [-.424,.424]:self.box('lid_side_rim',[x,-.22,.013],[.040,.475,.006],'wood',lidtarget)
        for y in [-.445,.005]:self.box('lid_end_rim',[0,y,.013],[.82,.025,.006],'wood',lidtarget)
        self.box('front_lid_pull',[0,-.465,.0],[.18,.025,.034],'brass',lidtarget)
        self._reg('scissors_box',lidtarget,'wooden sewing box lid',[3.5,3.5],[4.32,3.40,.735])
        self.box('single_lcd_bezel',[0,-.22,.015],[.82,.38,.006],'iron',self.box_lid)
        self.screen_sig=None;self.screen_mat=self.image_mat('r03_sewing_lcd',self._screen_file([]));self.screen_shader=self.S.Shader(self.stage.GetPrimAtPath(str(self.screen_mat.GetPath())+'/texture'))
        self._screen_piece('screen_input_display',(0,0,990,180),False)
        self._screen_piece('s2_reset',(990,0,1200,180),True)
        for j in range(6):
            c=j%3;r=j//3;self._screen_piece('s2_choice_'+str(j),(c*400,180+r*210,(c+1)*400,390+r*210),True)
        self.scissors=self._real_scissors(self.box_root,[-.16,-.01,.674]);self._reg('s3_tool',self.scissors,'steel sewing scissors',[3.5,3.5],[4.39,3.56,.682])
        shelf=self._shelf('fabric_storage_rack',.22,3.80,width=1.47,depth=.38,height=1.55,angle=90)
        for j,col in enumerate(['cloth_blue','cloth_red','cloth_gold','cloth_white']):self._fabric_roll('upper_fabric_roll_'+str(j),shelf,[(j-1.5)*.30,-.025,1.47],col,length=.22,radius=.075,axis='y')
        for j,col in enumerate(['cloth_red','cloth_blue','cloth_white']):self.box('folded_fabric_stack',[(j-1)*.32,0,.245],[.27,.30,.13],col,shelf,bevel=.014)
        self.pouch=self.group('stitched_fabric_pouch',[0,-.05,.95],shelf)
        self.box('pouch_back',[0,.035,0],[.51,.12,.27],'cloth_red',self.pouch,bevel=.02)
        self.pouch_flap=self.group('stitched_flap',[0,-.036,.14],self.pouch);self.box('pouch_fold',[0,-.035,-.14],[.51,.025,.28],'linen',self.pouch_flap,bevel=.014)
        self.stitches=self.group('temporary_white_stitches',parent=self.pouch_flap)
        for j in range(15):
            x=-.23+j*.033;self.tube('white_tack',[x,-.051,-.13],[x+.016,-.051,-.15],.0028,'cloth_white',self.stitches)
        self._reg('s3_setup',self.pouch_flap,'temporary stitching on fabric pouch',[1.0,3.75],[.45,3.80,.97])
        self.binary_sample=self._flat('inside_black_white_swatch',self.pouch,[0,-.027,-.002],.24,.24,self._binary())
        self._reg('s3_clue',self.binary_sample,'black and white cloth sample',[1.0,3.75],[.325,3.80,.95])
        self.cabinet=self.group('linen_cupboard',[.12,1.90,0]);self.transform(self.cabinet,rpy=[0,0,90])
        for x in [-.51,.51]:self.box('cupboard_side',[x,-.20,.40],[.035,.48,.68],'wood',self.cabinet)
        self.box('cupboard_back',[0,.035,.40],[1.05,.03,.68],'paint',self.cabinet)
        self.box('cupboard_base',[0,-.20,.10],[1.08,.50,.05],'darkwood',self.cabinet);self.box('cupboard_top',[0,-.20,.75],[1.13,.54,.06],'wood',self.cabinet)
        self.box('cupboard_inside_shelf',[0,-.18,.32],[.98,.40,.025],'wood',self.cabinet)
        for j,col in enumerate(['cloth_white','cloth_blue','cloth_red']):self.box('inside_folded_cloth',[(j-1)*.28,-.02,.56],[.24,.20,.15],col,self.cabinet,bevel=.012)
        self.cabinet_door=self.group('linen_cupboard_hinge',[-.52,-.455,.11],self.cabinet)
        doorface=self.group('linen_door_leaf',parent=self.cabinet_door);self.box('linen_cupboard_door',[.52,0,.295],[1.04,.045,.59],'paint',doorface);self.box('cupboard_handle',[.94,-.05,.295],[.025,.055,.16],'brass',doorface)
        self._reg('key_box',doorface,'linen cupboard door',[1.25,2.0],[.56,1.9,.43])
        self.patch_nodes=[]
        for j in range(4):
            px=.36+(j%2)*.28;pz=.435-(j//2)*.28;n=self.group('fabric_flip_patch_'+str(j),[px,-.036,pz],self.cabinet_door)
            self.box('stitched_patch_edge',[0,0,0],[.25,.028,.25],'darkwood',n)
            for bit,(yy,right,col) in enumerate([(-.016,(1,0,0),(229,223,202)),(.016,(-1,0,0),(31,39,38))]):
                self._flat('patch_face_%d_%d'%(j,bit),n,[0,yy,0],.232,.232,self._cloth((220,220),col),right=right)
            self._reg('s3_control_'+str(j),n,'cloth insert on cupboard',[1.25,2.0],[.60,1.9,.45]);self.patch_nodes.append(n)
            _add_mark(self,'patch_flip_mark_a_'+str(j),n,[.085,-.0175,-.085],'flip',.04)
            _add_mark(self,'patch_flip_mark_b_'+str(j),n,[-.085,.0175,-.085],'flip',.04,right=(-1,0,0))
        self.key=self.tool('door_key',self.cabinet,[0,-.19,.343],'key');self.target_nodes.pop('door_key',None);self.transform(self.key,rpy=[90,0,0]);self._reg('key',self.key,'door key',[1.0,2.0],[.33,1.9,.35])
        self.add_obstacle(.10,1.30,.64,2.50)
        self.door_angle=0;self.exit_node=self.door('workroom_exit',(3.30,.075,0),1.04);self._reg('exit',self.exit_node,'exit door',[3.75,1.0],[3.82,.13,1.05]);self.door_view=[3.75,1.0]
        for x in [3.27,4.37]:self.box('door_jamb',[x,.03,1.1675],[.06,.24,2.335],'paint');self.box('door_stop',[x,.10,1.135],[.10,.025,2.27],'darkwood')
        self.box('door_header',[3.82,.03,2.29],[1.22,.24,.09],'paint')
        self._decor_room()
        self.stage_views=[[1.5,4.0],[3.5,3.5],[1.25,2.0]];self.stage_centres=[[1.46,4.98,1.05],[4.15,3.4,.87],[.60,1.9,.45]]
        self.sync(g)
        (self.run/'ROOM_GEOMETRY.json').write_text(json.dumps({'id':'R03','size':[4.8,5.4],'camera_height':1.35,'solid_subfloor':True,'stage_views':self.stage_views,'theme_furniture':['sewing_machine','real_workbench_drawer','wooden_notions_box','fabric_roll_shelf','linen_cupboard','cutting_table','ironing_board','thread_rack'],'no_generic_stage_covers':True,'input_size':[1280,640]},ensure_ascii=False,indent=2),encoding='utf-8')
    def visible(self,key,g):
        if key=='s2_clue':return bool(g.opened.get('s2_cover'))
        if key=='s3_tool':return bool(g.opened.get('scissors_box')) and 's3_tool' not in g.taken
        if key=='s3_clue':return bool(g.states[2].get('setup_open'))
        if key=='key':return bool(g.opened.get('key_box')) and 'key' not in g.taken
        return key in self.target_nodes
    def sync(self,g):
        for n,q in zip(self.rotor_nodes,g.states[0]['angles']):self.transform(n,rpy=[0,int(q)*90,0])
        aligned=list(g.states[0]['angles'])==list(self.spec['stages'][0]['target']);self.visibility(self.sample_red,not aligned);self.visibility(self.sample_green,aligned)
        self.transform(self.drawer,[1.46,4.27 if g.opened.get('s2_cover') else 4.70,.54]);self.transform(self.drawer_bolt,[.31 if g.solved[0] else .38,-.034,.015])
        self.transform(self.box_lid,rpy=[-105 if g.opened.get('scissors_box') else 0,0,0])
        buffer=g.states[1].get('buffer',[]);sig=(tuple(buffer),bool(g.solved[1]))
        if sig!=self.screen_sig:
            with self.og.sim.editing_usd():
                self.screen_shader.GetInput('file').Set(str(self._screen_file(buffer,bool(g.solved[1]))))
            self.screen_sig=sig
        self.visibility(self.scissors,self.visible('s3_tool',g))
        bagopen=bool(g.states[2].get('setup_open'));self.transform(self.pouch_flap,rpy=[-105 if bagopen else 0,0,0]);self.visibility(self.stitches,not bagopen);self.visibility(self.binary_sample,bagopen)
        self.visibility(self.target_nodes['s2_clue'],self.visible('s2_clue',g))
        self.transform(self.cabinet_door,rpy=[0,0,-103 if g.opened.get('key_box') else 0])
        for j,n in enumerate(self.patch_nodes):self.transform(n,rpy=[0,0,180*int(g.states[2]['selected'][j])])
        self.visibility(self.key,self.visible('key',g));self.transform(self.exit_node,rpy=[0,0,-103 if g.opened.get('exit') else 0])
        self.centres={}
        for key,node in self.target_nodes.items():
            tri=self.triangles(node)
            if tri.size:self.centres[key]=((tri.reshape(-1,3).min(0)+tri.reshape(-1,3).max(0))/2).tolist()
    def candidates(self,g):return self.base_candidates([k for k in self.target_nodes if self.visible(k,g)])
    def blocked(self,x,y,g):
        if not(.18<=x<=4.62 and .18<=y<=5.22):return not(bool(g.opened.get('exit')) and 3.43<x<4.20 and -.8<y<.25)
        if self.static_blocked(x,y):return True
        if g.opened.get('s2_cover') and 1.0<x<1.94 and 4.20<y<4.72:return True
        return False
    def view_for(self,key):return self._views.get(key,[3.0,1.25])
    def focus_for(self,key):return self._focus.get(key,self.centres.get(key))
    def label_for(self,key):return self._labels.get(key,key.replace('_',' '))
    def animate(self,d,before):
        old=before.get('opened',{})
        changes=[]
        if old.get('s2_cover')!=d.game.opened.get('s2_cover'):changes.append(('drawer',old.get('s2_cover'),d.game.opened.get('s2_cover')))
        if old.get('scissors_box')!=d.game.opened.get('scissors_box'):changes.append(('box',old.get('scissors_box'),d.game.opened.get('scissors_box')))
        if old.get('key_box')!=d.game.opened.get('key_box'):changes.append(('cabinet',old.get('key_box'),d.game.opened.get('key_box')))
        oldbag=before.get('states',[{},{},{}])[2].get('setup_open',False);newbag=d.game.states[2].get('setup_open',False)
        if oldbag!=newbag:changes.append(('pouch',oldbag,newbag))
        for what,a,b in changes:
            for t in [.25,.50,.75]:
                q=float(bool(a))+(float(bool(b))-float(bool(a)))*t;self.sync(d.game)
                if what=='drawer':self.transform(self.drawer,[1.46,4.70-.43*q,.54])
                elif what=='box':self.transform(self.box_lid,rpy=[-105*q,0,0])
                elif what=='cabinet':self.transform(self.cabinet_door,rpy=[0,0,-103*q])
                else:self.transform(self.pouch_flap,rpy=[-105*q,0,0])
                d.frame(warm=4);d.append('Observe the furniture response',4)
        oldpatch=before.get('states',[{},{},{}])[2].get('selected',[0,0,0,0]);newpatch=d.game.states[2]['selected']
        for j,(a,b) in enumerate(zip(oldpatch,newpatch)):
            if int(a)!=int(b):
                for t in [.25,.50,.75]:self.sync(d.game);self.transform(self.patch_nodes[j],rpy=[0,0,180*(int(a)+(int(b)-int(a))*t)]);d.frame(warm=3);d.append('Cloth insert turns over',3)
        self.sync(d.game)


class Scene(R03WorkroomScene):
    def __init__(self,og,run):
        super().__init__(og,run,SPEC)

_aff_build_last(Scene)
