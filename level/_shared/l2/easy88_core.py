from __future__ import annotations
import copy,re,json,math,collections
from action_feedback import failure_for,NO_OBJECT,NO_ITEM

ROTATE={'rotate_picture','rotate_pipes','rotate_rails'}
ADJUST={'adjust','support_align','window_align','colour_windows','block_faces','cup_orient','slide_align'}
BINARY={'binary_pattern','difference'}
SEQUENCE={'sequence','repeat_symbols','missing_objects','flash_sequence','select_pair','ordered_select'}
CODE={'read_code','weigh','net_weigh','measure','liquid_read','clock','mirror','transfer','half_code','page_code','count','index_code','label_index','height_read','arithmetic'}
KINDS=ROTATE|ADJUST|BINARY|SEQUENCE|CODE|{'assign','sliding_puzzle','float_key'}
PUBLIC_ACTION_FIELDS=('action','point','target','item','code','distance','direction','degrees','thought','photo')

def _seq(stage):
    values=list(stage.get('answer',stage.get('sequence',[])));options=stage.get('options',[])
    return [options.index(v) if isinstance(v,str) and v in options else int(v) for v in values]

def _moduli(stage):
    initial=stage.get('initial',stage.get('target',[]))
    return list(stage.get('moduli',[4]*len(initial)))

def _assignment(state):
    state['assignment']={int(k):int(v) for k,v in state.get('assignment',{}).items()}
    return state['assignment']

def pipe_connected(stage,angles):
    cells=[tuple(map(int,c)) for c in stage.get('cells',[])]
    if not cells:raise ValueError('Pipe/rail cells required')
    ports=stage.get('ports',[])
    if len(ports)!=len(cells) or len(angles)!=len(cells):raise ValueError('Pipe cell/port/angle count mismatch')
    active={cell:{(int(p)+int(q))%4 for p in ps} for cell,ps,q in zip(cells,ports,angles)}
    entry=stage.get('inlet');exit_=stage.get('outlet')
    if entry is None or exit_ is None:raise ValueError('Pipe/rail inlet and outlet required')
    start=tuple(entry[:2]);end=tuple(exit_[:2]);side_in=int(entry[2]);side_out=int(exit_[2])
    if side_in not in active.get(start,set()) or side_out not in active.get(end,set()):return False
    offsets=((-1,0),(0,1),(1,0),(0,-1));todo=[start];seen={start}
    while todo:
        cell=todo.pop()
        if cell==end:return True
        for direction in active[cell]:
            dr,dc=offsets[direction];next_=(cell[0]+dr,cell[1]+dc)
            if next_ in active and (direction+2)%4 in active[next_] and next_ not in seen:seen.add(next_);todo.append(next_)
    return False

def sliding_path(initial,target,grid):
    rows,cols=map(int,grid);initial=tuple(initial);target=tuple(target)
    if len(initial)!=rows*cols or sorted(map(str,initial))!=sorted(map(str,target)):raise ValueError('Invalid sliding puzzle permutation')
    todo=collections.deque([initial]);parent={initial:None}
    while todo:
        state=todo.popleft()
        if state==target:
            moves=[]
            while parent[state] is not None:
                old,index=parent[state];moves.append(index);state=old
            return moves[::-1]
        empty=next(i for i,v in enumerate(state) if v in ('',None,'_'))
        r,c=divmod(empty,cols)
        for nr,nc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
            if 0<=nr<rows and 0<=nc<cols:
                index=nr*cols+nc;s=list(state);s[empty],s[index]=s[index],s[empty];s=tuple(s)
                if s not in parent:parent[s]=(state,index);todo.append(s)
    raise ValueError('Unsolvable sliding puzzle')


def reachable_approach(actor_xy,yaw,candidate,blocked,size,reach=1.2):
    from oracle560 import plan_route
    lo,hi=candidate['lo'],candidate['hi'];reach=float(reach)
    def distance(xy):return math.hypot(max(lo[0]-xy[0],xy[0]-hi[0],0.),max(lo[1]-xy[1],xy[1]-hi[1],0.))
    goals=[]
    for x in range(1,int(math.floor((float(size[0])-.18)/.25))+1):
        for y in range(1,int(math.floor((float(size[1])-.18)/.25))+1):
            xy=(x*.25,y*.25)
            if distance(xy)<=reach-.05 and not blocked(*xy):goals.append(xy)
    goals.sort(key=lambda xy:(math.dist(actor_xy,xy),xy))
    choices=[]
    for xy in goals[:32]:
        try:actions=plan_route(actor_xy,xy,blocked,yaw=yaw)
        except (ValueError,RuntimeError):continue
        count=sum(math.ceil(float(a['distance'])/.5-1e-8) if a['action'] in ('side_step','step_back') else 1 for a in actions)
        choices.append((count,math.dist(actor_xy,xy),xy))
    if not choices:raise RuntimeError('No reachable public stand point within unchanged interaction reach')
    return min(choices)[2]


def build_labels(spec):
    labels={'exit':'exit door','key':'brass door key','key_box':'small key compartment','room_shell':'wall','floor':'floor'}
    for i,stage in enumerate(spec['stages'],1):
        p='s'+str(i);name=stage.get('name','storage device')
        labels.update({p+'_cover':name+' protective cover',p+'_clue':name+' reference',p+'_lock':name+' lock',p+'_confirm':name+' check button',p+'_reset':name+' reset button',p+'_play':name+' replay button',p+'_setup':stage.get('setup',{}).get('target_name',name+' service opening'),p+'_tap':'water tap',p+'_float_key':'small seed-cabinet key',p+'_card':'embossed card'})
        count=max(len(stage.get('initial',[])),len(stage.get('target',[]))) if stage.get('kind')!='assign' else 0
        if stage['kind'] in BINARY:count=len(stage.get('target',[]))
        for j in range(count):labels[p+'_control_'+str(j)]=(stage.get('control_names') or [])[j] if j<len(stage.get('control_names',[])) else name+' control '+str(j+1)
        for j,v in enumerate(stage.get('options',[])):labels[p+'_choice_'+str(j)]=(stage.get('option_names',[])[j] if j<len(stage.get('option_names',[])) else str(v).replace('_',' '))+' button'
        if stage['kind']=='sliding_puzzle':
            for j in range(len(stage.get('initial',[]))):labels[p+'_tile_'+str(j)]=name+' tile '+str(j+1)
        for j,item in enumerate(stage.get('items',[])):labels[p+'_item_'+str(j)]=item.get('name',item.get('id','component '+str(j+1))) if isinstance(item,dict) else str(item)
        for j in range(int(stage.get('slots',len(stage.get('target',[])) if stage['kind']=='assign' else 0))):labels[p+'_slot_'+str(j)]=name+' socket '+str(j+1)
        setup=stage.get('setup') or {}
        labels[p+'_tool']=setup.get('item_name',setup.get('item','small jug' if stage['kind']=='float_key' else 'small tool')) or 'small tool'
        if stage['kind']=='float_key':labels[p+'_tool']='small water jug'
        for j,item in enumerate(setup.get('items',[])):labels[p+'_tool_'+str(j)]=item.get('name',item.get('id','tracing sheet '+str(j+1))) if isinstance(item,dict) else str(item)
        for j in range(int(setup.get('item_count',len(setup.get('items',[]))))):labels[p+'_overlay_'+str(j)]=name+' tracing-sheet slot '+str(j+1)
    return labels

class EasyGame:
    SPEC=None
    LABELS={}
    def __init__(self):
        self.opened={f's{i}_cover':i==1 for i in range(1,4)};self.opened.update(key_box=False,exit=False)
        self.solved=[False]*3;self.states=[];self.holding=[];self.taken=set();self.exit_unlocked=False;self.exited=False
        for stage in self.SPEC['stages']:
            setup=stage.get('setup') or {};kind=stage['kind'];initial=stage.get('initial',[])
            self.states.append({'angles':list(initial) if kind in ROTATE|ADJUST else [],'buffer':[],'overflow':False,'selected':list(initial or [0]*len(stage.get('target',[]))) if kind in BINARY else [],'assignment':{},'grid':list(initial) if kind=='sliding_puzzle' else [],'setup_ready':not bool(setup) or setup.get('gate') is False,'setup_used':False,'setup_unlocked':False,'setup_open':False,'filled':False,'floated':False,'launched':False,'flash':False,'playback':0,'overlay':[False]*int(setup.get('item_count',len(setup.get('items',[])))),'card_exposed':False,'card_taken':False})
    def snapshot(self):
        return {'opened':dict(self.opened),'solved':list(self.solved),'states':copy.deepcopy(self.states),'holding':list(self.holding),'taken':sorted(self.taken),'exit_unlocked':self.exit_unlocked,'exited':self.exited}
    def stage_accessible(self,index):
        return 0<=index<3 and (index==0 or self.solved[index-1]) and bool(self.opened.get(f's{index+1}_cover'))
    def stage_exposed(self,index):return self.stage_accessible(index) and bool(self.states[index]['setup_ready'])
    def _solve(self,index):
        self.solved[index]=True
    def cover_unlocked(self,index):return index==0 or self.solved[index-1]
    def _check(self,index):
        stage=self.SPEC['stages'][index];state=self.states[index];kind=stage['kind']
        if kind=='rotate_picture' or kind in ADJUST:return list(state['angles'])==list(stage.get('target',[]))
        if kind in ('rotate_pipes','rotate_rails'):return pipe_connected(stage,state['angles'])
        if kind in BINARY:return list(state['selected'])==list(stage['target'])
        if kind in SEQUENCE:
            answer=_seq(stage);buffer=state['buffer']
            return not state['overflow'] and len(buffer)==len(answer) and buffer==answer and (not stage.get('distinct') or len(set(buffer))==len(buffer))
        if kind=='assign':
            expected={j:int(v) for j,v in enumerate(stage['target']) if v is not None}
            return _assignment(state)==expected
        if kind=='sliding_puzzle':return state['grid']==list(stage['target'])
        return False
    def _resolve_item(self,name):
        name=str(name or '').strip().lower()
        if name in self.holding:return name
        matches=[k for k in self.holding if name==str(self.LABELS.get(k,k)).lower()]
        if len(matches)==1:return matches[0]
        matches=[k for k in self.holding if name and name in str(self.LABELS.get(k,k)).lower()]
        return matches[0] if len(matches)==1 else None
    def act(self,a):
        kind=a.get('action');key=a.get('_hit364')
        def out(ok,text=''):return {'ok':bool(ok),'text':str(text) if kind=='read' and ok else '' if ok else str(text or failure_for(kind))}
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
        if key=='key_box':
            if kind in ('open','close'):
                if kind=='open' and not self.solved[2]:return out(False)
                self.opened[key]=kind=='open';return out(True)
            return out(False)
        if key=='key':
            if kind=='take' and self.solved[2] and self.opened['key_box'] and 'key' not in self.taken:
                self.taken.add('key');self.holding.append('key');return out(True)
            return out(False)
        match=re.fullmatch(r's([123])_(.+)',key)
        if match is None:return out(False)
        index=int(match[1])-1;suffix=match[2];stage=self.SPEC['stages'][index];state=self.states[index];setup=stage.get('setup') or {};stagekind=stage['kind'];prefix=f's{index+1}'
        if suffix=='cover':
            if kind=='use' and index>0 and self.SPEC['stages'][index-1]['kind']=='float_key':
                item=self._resolve_item(a.get('item'))
                if item is None:return out(False,NO_ITEM)
                if item!=f's{index}_float_key':return out(False)
                self._solve(index-1);return out(True)
            if kind in ('open','close'):
                if kind=='open' and not self.cover_unlocked(index):return out(False)
                self.opened[key]=kind=='open';return out(True)
            return out(False)
        if not self.stage_accessible(index):return out(False)
        if suffix.startswith('item_') and stagekind=='assign':
            try:itemindex=int(suffix[5:])
            except ValueError:return out(False)
            if not 0<=itemindex<len(stage.get('items',[])):return out(False)
            if kind=='take':
                if not state['setup_ready'] or key in self.holding:return out(False)
                assignments=_assignment(state);placed=next((j for j,v in assignments.items() if v==itemindex),None)
                if placed is None and key in self.taken:return out(False)
                if placed is not None:assignments.pop(placed)
                self.taken.add(key);self.holding.append(key);return out(True)
            if kind=='read':return out(False)
        if suffix=='tool' or re.fullmatch(r'tool_\d+',suffix):
            valid=stagekind=='float_key' and suffix=='tool' or bool(setup) and (suffix=='tool' and setup.get('item') is not None or suffix.startswith('tool_') and int(suffix[5:])<len(state['overlay']))
            if kind=='take' and valid and key not in self.taken:self.taken.add(key);self.holding.append(key);return out(True)
            return out(False)
        if suffix=='card':
            if kind=='take' and state['card_exposed'] and not state['card_taken']:
                state['card_taken']=True;state['setup_ready']=True;self.taken.add(key);self.holding.append(key);return out(True)
            if kind=='read' and state['card_exposed'] and stage.get('clue_text'):return out(True,stage['clue_text'])
            return out(False)
        if suffix=='float_key':
            if stagekind=='float_key' and kind=='take' and state['floated'] and key not in self.taken:self.taken.add(key);self.holding.append(key);return out(True)
            return out(False)
        if stagekind=='float_key' and suffix in ('tap','setup'):
            if kind!='use':return out(False)
            item=self._resolve_item(a.get('item'))
            if item is None:return out(False,NO_ITEM)
            if item!=prefix+'_tool':return out(False)
            if suffix=='tap':state['filled']=True;return out(True)
            if not state['filled']:return out(False)
            state['floated']=True;state['filled']=False;return out(True)
        if suffix.startswith('overlay_') and setup.get('kind')=='overlay':
            if kind!='use':return out(False)
            item=self._resolve_item(a.get('item'))
            if item is None:return out(False,NO_ITEM)
            try:j=int(suffix[8:])
            except ValueError:return out(False)
            if not 0<=j<len(state['overlay']) or item!=prefix+'_tool_'+str(j):return out(False)
            state['overlay'][j]=True;self.holding.remove(item);state['setup_ready']=all(state['overlay']);state['setup_used']=state['setup_ready'];state['setup_open']=state['setup_ready'];return out(True)
        if suffix=='setup' and setup:
            wants_open=setup.get('kind')=='key' or setup.get('open_after_use',False)
            if kind in ('open','close') and wants_open:
                if kind=='open' and not state['setup_unlocked']:return out(False)
                state['setup_open']=kind=='open';state['setup_ready']=kind=='open';return out(True)
            if kind not in ('press','use'):return out(False)
            if setup.get('item') is None:
                if kind!='press':return out(False)
            else:
                if kind!='use':return out(False)
                item=self._resolve_item(a.get('item'))
                if item is None:return out(False,NO_ITEM)
                if item!=prefix+'_tool':return out(False)
                if setup.get('consume'):self.holding.remove(item)
            state['setup_used']=True
            if setup.get('kind')=='uv':state['flash']=True;return out(True)
            if wants_open:state['setup_unlocked']=True;return out(True)
            if setup.get('post_take'):state['card_exposed']=True;return out(True)
            state['setup_ready']=True;state['setup_open']=True;return out(True)
        if not state['setup_ready']:return out(False)
        if suffix=='clue':
            if kind=='read' and stage.get('clue_text'):return out(True,stage['clue_text'])
            return out(False)
        if suffix=='lock' and kind=='unlock':
            code_kind=stagekind in CODE or stagekind=='slide_align' and stage.get('code_after_alignment')
            if not code_kind or str(a.get('code','')).strip()!=str(stage.get('answer','')):return out(False)
            self._solve(index);return out(True)
        if kind=='use' and suffix.startswith('slot_') and stagekind=='assign':
            item=self._resolve_item(a.get('item'))
            if item is None:return out(False,NO_ITEM)
            im=re.fullmatch(prefix+r'_item_(\d+)',item)
            if im is None:return out(False)
            slot=int(suffix[5:]);assignments=_assignment(state)
            if not 0<=slot<int(stage.get('slots',len(stage.get('target',[])))) or slot in assignments:return out(False)
            assignments[slot]=int(im[1]);self.holding.remove(item);return out(True)
        if kind!='press':return out(False)
        if suffix=='play':state['playback']+=1;return out(True)
        if suffix=='reset':
            state['buffer']=[];state['overflow']=False
            if stagekind in ROTATE|ADJUST:state['angles']=list(stage.get('initial',[0]*len(stage['target'])))
            elif stagekind in BINARY:state['selected']=list(stage.get('initial',[0]*len(stage['target'])))
            elif stagekind=='sliding_puzzle':state['grid']=list(stage['initial'])
            return out(True)
        if suffix=='confirm':
            correct=self._check(index)
            if correct:
                if stagekind=='rotate_rails':state['launched']=True
                self._solve(index);return out(True)
            if stagekind in SEQUENCE:state['buffer']=[];state['overflow']=False
            return out(False)
        control=re.fullmatch(r'control_(\d+)',suffix)
        if control and stagekind in ROTATE|ADJUST|BINARY:
            j=int(control[1]);values=state['selected'] if stagekind in BINARY else state['angles']
            if not 0<=j<len(values):return out(False)
            modulus=2 if stagekind in BINARY else (_moduli(stage)[j] if stagekind in ADJUST else 4)
            values[j]=(int(values[j])+1)%modulus
            if stage.get('auto',stagekind in ('rotate_picture','rotate_pipes')) and not (stagekind=='slide_align' and stage.get('code_after_alignment')) and self._check(index):self._solve(index)
            return out(True)
        choice=re.fullmatch(r'choice_(\d+)',suffix)
        if choice and stagekind in SEQUENCE:
            j=int(choice[1]);length=int(stage.get('length',len(_seq(stage))))
            if not 0<=j<len(stage.get('options',[])):return out(False)
            if len(state['buffer'])<length:state['buffer'].append(j)
            else:state['overflow']=True
            return out(True)
        tile=re.fullmatch(r'tile_(\d+)',suffix)
        if tile and stagekind=='sliding_puzzle':
            j=int(tile[1]);grid=state['grid'];rows,cols=stage.get('grid',[2,3]);empty=next(i for i,v in enumerate(grid) if v in ('',None,'_'))
            if not 0<=j<len(grid) or j==empty or abs(j//cols-empty//cols)+abs(j%cols-empty%cols)!=1:return out(False)
            grid[j],grid[empty]=grid[empty],grid[j]
            if stage.get('auto',True) and self._check(index):self._solve(index)
            return out(True)
        return out(False)


def _setup_actions(game,index):
    stage=game.SPEC['stages'][index];setup=stage.get('setup') or {};state=game.states[index];p=f's{index+1}'
    if not setup:return
    if setup.get('kind')=='overlay':
        for j,placed in enumerate(state['overlay']):
            if not placed:
                tool=p+'_tool_'+str(j)
                if tool not in game.holding:yield ('take',tool,{})
                yield ('use',p+'_overlay_'+str(j),{'item':tool})
        return
    if setup.get('kind')=='uv':
        if p+'_tool' not in game.holding:yield ('take',p+'_tool',{})
        yield ('use',p+'_setup',{'item':p+'_tool'});return
    if not state['setup_ready']:
        if not state['setup_used']:
            if setup.get('item') is None:yield ('press',p+'_setup',{})
            else:
                if p+'_tool' not in game.holding:yield ('take',p+'_tool',{})
                yield ('use',p+'_setup',{'item':p+'_tool'})
        if setup.get('kind')=='key' or setup.get('open_after_use'):yield ('open',p+'_setup',{})
        if setup.get('post_take') and not state['card_taken']:yield ('take',p+'_card',{})


def stage_actions(game,index):
    stage=game.SPEC['stages'][index];state=game.states[index];kind=stage['kind'];p=f's{index+1}'
    if not game.opened[p+'_cover']:yield ('open',p+'_cover',{})
    yield from _setup_actions(game,index)
    if kind=='float_key':
        if p+'_tool' not in game.holding:yield ('take',p+'_tool',{})
        if not state['floated']:
            yield ('use',p+'_tap',{'item':p+'_tool'});yield ('use',p+'_setup',{'item':p+'_tool'})
        if p+'_float_key' not in game.holding:yield ('take',p+'_float_key',{})
        yield ('use',f's{index+2}_cover',{'item':p+'_float_key'});return
    if stage.get('standard_read',False) and stage.get('clue_text'):yield ('read',p+'_clue',{})
    if kind in ROTATE|ADJUST:
        target=stage.get('target',[]);moduli=_moduli(stage) if kind in ADJUST else [4]*len(target)
        for j,want in enumerate(target):
            if game.solved[index]:break
            for _ in range((int(want)-int(state['angles'][j]))%int(moduli[j])):
                if game.solved[index]:break
                yield ('press',p+'_control_'+str(j),{})
        if kind=='slide_align' and stage.get('code_after_alignment'):yield ('unlock',p+'_lock',{'code':str(stage['answer'])})
        elif not game.solved[index]:yield ('press',p+'_confirm',{})
    elif kind in SEQUENCE:
        if state['buffer'] or state['overflow']:yield ('press',p+'_reset',{})
        if stage.get('playback') or stage.get('visual',{}).get('type')=='flash':yield ('press',p+'_play',{})
        for j in _seq(stage):yield ('press',p+'_choice_'+str(j),{})
        yield ('press',p+'_confirm',{})
    elif kind in BINARY:
        for j,want in enumerate(stage['target']):
            if int(state['selected'][j])!=int(want):yield ('press',p+'_control_'+str(j),{})
        if not game.solved[index]:yield ('press',p+'_confirm',{})
    elif kind=='assign':
        expected={j:int(v) for j,v in enumerate(stage['target']) if v is not None}
        for slot,item in list(_assignment(state).items()):
            if expected.get(slot)!=item:yield ('take',p+'_item_'+str(item),{})
        for slot,item in expected.items():
            if _assignment(state).get(slot)==item:continue
            key=p+'_item_'+str(item)
            if key not in game.holding:yield ('take',key,{})
            yield ('use',p+'_slot_'+str(slot),{'item':key})
        yield ('press',p+'_confirm',{})
    elif kind=='sliding_puzzle':
        for j in sliding_path(state['grid'],stage['target'],stage.get('grid',[2,3])):yield ('press',p+'_tile_'+str(j),{})
        if not game.solved[index]:yield ('press',p+'_confirm',{})
    elif kind in CODE:yield ('unlock',p+'_lock',{'code':str(stage['answer'])})
    else:raise NotImplementedError(kind)


def make_level(spec):
    spec=copy.deepcopy(spec)
    if len(spec.get('stages',[]))!=3:raise ValueError('Exactly3 sequential puzzles required')
    for s in spec['stages']:
        if s.get('kind') not in KINDS:raise ValueError('Unsupported mechanism: '+str(s.get('kind')))
        if s['kind'] in SEQUENCE:
            answer=_seq(s)
            if len(answer)!=int(s.get('length',len(answer))):raise ValueError('Sequence slot count mismatch')
            if s.get('distinct') and len(set(answer))!=len(answer):raise ValueError('Distinct sequence has duplicate answer')
        if s['kind']=='sliding_puzzle':sliding_path(s['initial'],s['target'],s.get('grid',[2,3]))
    class Game(EasyGame):pass
    Game.SPEC=spec;Game.LABELS=build_labels(spec)
    class Scene:
        def __new__(cls,og,run):
            from easy88_scene import EasyScene
            return EasyScene(og,run,spec)
    def exit_test(pos,g):return bool(g.exit_unlocked and g.opened['exit'])
    def standard(d):
        from observation1280 import FX,FY,CX,CY
        from pixel355 import find_point
        import numpy as np
        game=d.game;scene=d.scene
        def centre(key):
            if key in getattr(scene,'centres',{}):return scene.centres[key]
            candidates=scene.candidates(game);c=next((x for x in candidates if x['key']==key),None)
            if c is None:raise RuntimeError('Standard target not exposed: '+key)
            return (np.array(c['lo'])+np.array(c['hi']))/2
        def click(key,kind='press',fields=None):
            reference=re.match(r's([123])_',key)
            if kind=='press' and reference and hasattr(d,'prepare_reference'):d.prepare_reference(int(reference[1])-1)
            match=re.fullmatch(r's([123])_lock',key)
            if kind=='unlock' and match and hasattr(d,'observe_readout'):d.observe_readout(int(match[1])-1)
            fields=dict(fields or {});candidates=scene.candidates(game)
            candidate=next((c for c in candidates if c['key']==key),None)
            if candidate is not None:
                lo=np.asarray(candidate['lo'],float);hi=np.asarray(candidate['hi'],float);xy=np.asarray(d.pos[:2],float)
                footprint=np.maximum(lo[:2]-xy,np.maximum(xy-hi[:2],0.));distance=float(np.linalg.norm(footprint))
                if distance>(1.5 if key=='exit' else 1.2):
                    view=reachable_approach(d.pos[:2],d.yaw,candidate,lambda x,y:scene.blocked(x,y,game),scene.spec['size'],1.5 if key=='exit' else 1.2)
                    d.route(view,'Approach the visible target without reach bypass')
                    d.aim(centre(key),'Look at the visible target');candidates=scene.candidates(game)
            hit=find_point(key,d.pos,d.quat,d.depth,candidates,fx=FX,fy=FY,cx=CX,cy=CY,actor_xy=d.pos[:2],tolerance=.05,mesh_tolerance=.04,grid=41,return_hit=True)
            if hit is None:
                d.aim(centre(key),'Look at the visible mechanism')
                hit=find_point(key,d.pos,d.quat,d.depth,scene.candidates(game),fx=FX,fy=FY,cx=CX,cy=CY,actor_xy=d.pos[:2],tolerance=.05,mesh_tolerance=.04,grid=61,return_hit=True)
            if hit is None:raise RuntimeError('No current visible native pixel for '+key)
            reach=1.5 if key=='exit' else 1.2
            if float(hit['distance'])>reach:
                view=reachable_approach(d.pos[:2],d.yaw,hit,lambda x,y:scene.blocked(x,y,game),scene.spec['size'],reach)
                d.route(view,'Approach the actual visible surface without reach bypass');d.aim(centre(key),'Look at the visible target')
                hit=find_point(key,d.pos,d.quat,d.depth,scene.candidates(game),fx=FX,fy=FY,cx=CX,cy=CY,actor_xy=d.pos[:2],tolerance=.05,mesh_tolerance=.04,grid=61,return_hit=True)
                if hit is None or float(hit['distance'])>reach:raise RuntimeError('No current visible native pixel within unchanged reach for '+key)
            point=hit['point']
            if 'item' in fields:fields['item']=Game.LABELS.get(fields['item'],fields['item'])
            action={'thought':'Follow the visible clue.','action':kind,'point':point,'target':scene.label_for(key) if hasattr(scene,'label_for') else Game.LABELS.get(key,key.replace('_',' '))};action.update(fields)
            return d.execute(action,'Observe the mechanism response')
        for i in range(3):
            view=scene.stage_views[i];d.route(view,'Approach the next device')
            target=scene.stage_centres[i] if hasattr(scene,'stage_centres') else centre(f's{i+1}_cover')
            d.aim(target,'Keep the device and its response in view')
            if hasattr(d,'append'):d.append('Observe the visible reference',12)
            for action,key,fields in stage_actions(game,i):click(key,action,fields)
            if not game.solved[i]:raise RuntimeError('Public standard did not solve stage '+str(i+1))
        if hasattr(scene,'view_for'):
            view=scene.view_for('key_box')
            if view is not None and math.dist(d.pos[:2],view)>.01:d.route(view,'Approach the unlocked key compartment')
        d.aim(centre('key_box'),'Look into the unlocked compartment');click('key_box','open');click('key','take')
        d.route(scene.door_view,'Return to the exit');d.aim(centre('exit'),'Look at the exit door');click('exit','use',{'item':'key'});click('exit','open')
        if not exit_test(d.pos,game):raise RuntimeError('Open-door terminal state not reached')
    def cpu_check():
        g=Game();checks=[];trace=[]
        def ck(n,c):assert c,n;checks.append(n)
        def a(kind,key,**fields):
            before=g.snapshot();result=g.act(dict(action=kind,_hit364=key,_validated364=True,**fields));trace.append({'action':kind,'target':key,'fields':fields,'result':result,'before':before,'after':g.snapshot()});return result
        ck('no privileged unvalidated interaction',not g.act({'action':'open','_hit364':'s2_cover'})['ok'])
        ck('stage2 physical cover locked',not a('open','s2_cover')['ok'])
        ck('stage3 physical cover locked',not a('open','s3_cover')['ok'])
        ck('key cannot be taken through final compartment',not a('take','key')['ok'])
        ck('locked exit rejects open',not a('open','exit')['ok'])
        for i in range(3):
            for kind,key,fields in stage_actions(g,i):ck(f'stage{i+1} public {kind} {key}',a(kind,key,**fields)['ok'])
            ck('stage'+str(i+1)+' solved by actions',g.solved[i])
            ck('later stage not auto solved',all(not v for v in g.solved[i+1:]))
        ck('solution does not auto open key compartment',not g.opened['key_box']);a('open','key_box');a('take','key');ck('key enters inventory','key' in g.holding)
        a('use','exit',item='key');ck('use key alone not terminal',not exit_test(spec['start'],g));a('open','exit');ck('open door wins without walking out',exit_test(spec['start'],g))
        return {'level':spec['id'],'scope':'CPU public state-machine fixture only; no SDK, native pixels, or model calls','passed':len(checks),'checks':checks,'trace':trace,'final':g.snapshot()}
    return Game,Scene,standard,exit_test,cpu_check
