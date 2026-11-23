import math
FAILURES={
 'take':'You cannot take this object.',
 'open':'This object cannot be opened.',
 'close':'This object cannot be closed.',
 'use':'You cannot use this item on this object.',
 'unlock':'This object cannot be unlocked with a code.',
 'press':'This object cannot be pressed.',
 'read':'This object cannot be read.',
 'recall':'No relevant records found.'}
NO_OBJECT='No interactable object at this point.'
TOO_FAR='Too far away to reach.'
NO_ITEM='You do not have this item.'
NO_RECALLS='No recalls remaining.'
COMMON={NO_OBJECT,TOO_FAR,NO_ITEM,NO_RECALLS}
def failure_for(action):return FAILURES.get(action,'Invalid action parameters.')
def movement_feedback(moved):
    amount=f"{max(0.,float(moved)):.2f}".rstrip('0').rstrip('.') or '0'
    return 'An obstacle blocks your movement.' if float(moved)<=1e-8 else f'You moved {amount} m before an obstacle blocked further movement.'
def input_failure(action,reason):
    if reason.startswith('Current target beyond'):return TOO_FAR
    if reason.startswith('Public standard walk blocked'):return movement_feedback(0)
    return NO_OBJECT
def public_feedback(action,result):
    if action=='read' or not result.get('ok',False):return result.get('text','') or failure_for(action)
    return ''
def swept_endpoint(start,delta,blocked,spacing=.025):
    start=[float(x) for x in start];delta=[float(x) for x in delta]
    distance=math.sqrt(sum(x*x for x in delta));n=max(1,math.ceil(distance/spacing));end=list(start);was_blocked=False
    for i in range(1,n+1):
        p=[start[j]+delta[j]*i/n for j in range(len(start))]
        if blocked(p[0],p[1]):was_blocked=True;break
        end=p
    moved=math.sqrt(sum((end[j]-start[j])**2 for j in range(len(start))))
    return end,moved,was_blocked


WRONG_CODE='Wrong code.'
WRONG_SEQUENCE='Wrong sequence.'
WRONG_ITEM='Wrong item.'
NOT_READY='This item cannot be used here yet.'
LOCKED='This object is locked.'
NO_CODE_LOCK='This object cannot be unlocked with a code.'
INCORRECT_ARRANGEMENT='Incorrect arrangement.'
COMMON.update({WRONG_CODE,WRONG_SEQUENCE,WRONG_ITEM,NOT_READY,LOCKED,NO_CODE_LOCK,INCORRECT_ARRANGEMENT})

def _feedback_context22(game,a):
    import re
    key=a.get('_hit364');kind=a.get('action');snap=game.snapshot()
    if key=='case_lid':key='camera_case'
    if key in ('vent_screw_1','vent_screw_2','vent_screw_3','vent_screw_4'):key='vent'
    context={'key':key,'snapshot':snap,'stage':None,'expected_item':None,'code_supported':False,'unlocked':False,'locked':False}
    if 'drawer_unlocked' in snap:
        mapping={'drawer2':'drawer_unlocked','toolbox':'toolbox_unlocked','exit':'exit_unlocked','vent':'vent_freed'}
        context.update(code_supported=key in ('drawer2','toolbox'),unlocked=bool(snap.get(mapping.get(key,''))),locked=key in mapping and not snap.get(mapping[key],False))
        if key=='vent' and a.get('_hit364')!='vent':context['expected_item']=None
        else:context['expected_item']={'vent':'screwdriver','exit':'key'}.get(key)
    elif 'case_unlocked' in snap:
        context.update(code_supported=key=='camera_case',unlocked=bool(snap.get('case_unlocked')) if key=='camera_case' else bool(snap.get('exit_unlocked')) if key=='exit' else False,
                       locked=(key=='camera_case' and not snap['case_unlocked']) or (key=='exit' and not snap['exit_unlocked']) or (key=='album_drawer' and not snap['puzzle_solved']))
        context['expected_item']={'exit':'key','battery_slot':'battery'}.get(key)
    elif hasattr(game,'SPEC') and 'states' in snap:
        from easy88_core import CODE
        match=re.fullmatch(r's([123])_(.+)',str(key))
        context['locked']=(key=='exit' and not snap['exit_unlocked']) or (key=='key_box' and not snap['solved'][2])
        if key=='exit':context['expected_item']='key'
        if match:
            i=int(match[1])-1;suffix=match[2];stage=game.SPEC['stages'][i];st=snap['states'][i];setup=stage.get('setup') or {};p='s%d'%(i+1)
            context.update(stage=i,suffix=suffix,stage_kind=stage['kind'],choice_failure_feedback=stage.get('choice_failure_feedback'))
            context['code_supported']=suffix=='lock' and (stage['kind'] in CODE or stage['kind']=='slide_align' and stage.get('code_after_alignment',False))
            context['code_accessible']=game.stage_accessible(i) and st.get('setup_ready',True)
            context['unlocked']=bool(snap['solved'][i]) if suffix=='lock' else False
            if suffix=='cover':context['locked']=not game.cover_unlocked(i)
            if suffix=='setup' and (setup.get('kind')=='key' or setup.get('open_after_use')):context['locked']=not st['setup_unlocked']
            if stage['kind']=='float_key' and suffix in ('tap','setup'):context['expected_item']=p+'_tool'
            elif suffix=='setup' and setup.get('item') is not None:context['expected_item']=p+'_tool'
            elif suffix.startswith('overlay_') and setup.get('kind')=='overlay':context['expected_item']=p+'_tool_'+suffix[8:]
            elif suffix=='cover' and i>0 and game.SPEC['stages'][i-1]['kind']=='float_key':context['expected_item']='s%d_float_key'%i
    return context

def install_game_feedback(game,scene=None):
    if getattr(game,'_reason_feedback22_installed',False):
        if scene is not None:_install_failure_flash22(game,scene)
        return game
    original=game.act
    def act(a):
        kind=a.get('action')
        game._failed_input_stage22=None
        if not a.get('_validated364'):
            return {'ok':False,'text':NO_OBJECT}
        c=_feedback_context22(game,a);key=c['key'];before=c['snapshot']
        opened=before.get('opened',{})
        if kind in ('open','close') and key in opened and opened[key]==(kind=='open'):
            return {'ok':False,'text':'This object is already '+('open.' if kind=='open' else 'closed.')}
        if kind=='unlock' and c['code_supported'] and c['unlocked']:
            return {'ok':False,'text':'This object is already unlocked.'}
        result=dict(original(a))
        if result.get('ok'):
            result['text']=result.get('text','') if kind=='read' else ''
            return result
        text=result.get('text','')
        if text in (NO_OBJECT,TOO_FAR,NO_ITEM,NO_RECALLS):return result
        if kind=='unlock':
            if c['code_supported'] and c.get('code_accessible',True):
                text=WRONG_CODE;game._failed_input_stage22=c['stage']
            else:text=NO_CODE_LOCK
        elif kind=='open' and c['locked']:text=LOCKED
        elif kind=='press' and (c.get('suffix')=='confirm' or (str(c.get('suffix','')).startswith('choice_') and c.get('choice_failure_feedback')=='arrangement') or (str(c.get('suffix','')).startswith('choice_') and c.get('stage_kind') in __import__('easy88_core').SEQUENCE and len(before['states'][c['stage']]['buffer'])+1>=int(game.SPEC['stages'][c['stage']].get('length',len(__import__('easy88_core')._seq(game.SPEC['stages'][c['stage']])))))):
            from easy88_core import SEQUENCE
            text=WRONG_SEQUENCE if c['stage_kind'] in SEQUENCE else INCORRECT_ARRANGEMENT
            if c['stage_kind'] in SEQUENCE:
                state=game.states[c['stage']];state['buffer']=[];state['overflow']=False
            game._failed_input_stage22=c['stage']
        elif kind=='use':
            resolver=getattr(game,'_resolve_item',None)
            if resolver is not None:item=resolver(a.get('item'))
            else:
                import sys
                labels=getattr(sys.modules.get(type(game).__module__),'LABELS',{})
                name=str(a.get('item','')).strip().lower()
                item=next((k for k in game.holding if name in (str(k).lower(),str(labels.get(k,k)).lower())),None)
            from use_feedback import rejection
            import sys
            labels=getattr(game,'LABELS',None) or getattr(sys.modules.get(type(game).__module__),'LABELS',{})
            text=rejection(labels.get(item),labels.get(c['key']))
        else:text=failure_for(kind)
        result['text']=text
        return result
    game.act=act;game._reason_feedback22_installed=True
    if scene is not None:_install_failure_flash22(game,scene)
    return game

def _install_failure_flash22(game,scene):
    if getattr(scene,'_reason_feedback22_installed',False) or not hasattr(scene,'animate'):return
    original=scene.animate
    def animate(driver,before):
        original(driver,before)
        index=getattr(game,'_failed_input_stage22',None)
        lamps=getattr(scene,'status_nodes',[])
        if index is None or index>=len(lamps):return
        red,green=lamps[index]
        scene.sync(game);scene.visibility(red,False);scene.visibility(green,False)
        driver.frame(warm=4);driver.append('',3)
        scene.visibility(red,True);scene.visibility(green,False)
        driver.frame(warm=4);driver.append('',6)
        game._failed_input_stage22=None
    scene.animate=animate;scene._reason_feedback22_installed=True
