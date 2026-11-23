import math
import numpy as np
from PIL import Image,ImageDraw
from easy88_core import make_level,reachable_approach
from easy88_scene import EasyScene
from easy88_clues import draw_symbol
from font_utils import load_font
SPEC={'id':'R20','title':'Shoe Repair Workshop','chinese_title':'修鞋工作间','theme':'shoes',
'size':[4.0,5.8],'door':{'side':'west','start':.73,'width':1.04},'start':[1.25,1.25,1.35],'start_yaw':90,'floor':'wood',
'stages':[
{'kind':'assign','name':'sole pair inspection rack','wall':'north','items':[{'id':'sole_a','name':'right sole A'},{'id':'sole_b','name':'right sole B'},{'id':'sole_c','name':'right sole C'},{'id':'sole_d','name':'right sole D'}],'slots':2,'target':[3,0],'clue_text':''},
{'kind':'measure','name':'leather measuring bench','wall':'east','answer':'0120','setup':{'kind':'measure','item':'ruler','item_name':'straight ruler','target_name':'marked leather strip','consume':False},'clue_text':''},
{'kind':'sequence','name':'leather embossing jig','wall':'south','options':['circle','triangle','square','star','leaf','cross'],'answer':[3,1,4],'length':3,'setup':{'kind':'pluck','item':'pliers','item_name':'needle nose pliers','target_name':'card ring in narrow slot','post_take':False,'consume':False},'clue_text':''}]}
Game,_S,_T,exit_test,cpu_check=make_level(SPEC)
TITLE=SPEC['title'];LEVEL_ID=SPEC['id'];START=SPEC['start'];START_YAW=SPEC['start_yaw']
CAP=150;OBSERVATION_SIZE=(640,360);VISUAL_ONLY=False;READ_ENABLED=True;READ_FEEDBACK_TEXT=True
Game.LABELS.update({'s1_clue':'two fixed left soles','s1_confirm':'whole pair check','s1_reset':'clear pairs','s2_cover':'ruler drawer','s2_tool':'straight ruler','s2_setup':'marked leather strip','s2_clue':'ruler contact marks','s2_lock':'millimetre tool lock','s3_cover':'pliers drawer','s3_tool':'needle nose pliers','s3_setup':'card ring in narrow slot','s3_card':'retrieved embossed card','s3_clue':'three embossed symbols','s3_confirm':'symbol check','s3_reset':'clear symbols','key_box':'shoe workshop key drawer','key':'brass door key'})
LABELS=Game.LABELS
LABELS.update({'s3_card':'embossed leather sample','s3_clue':'embossed leather sample','s3_confirm':'embossing press lever','s3_reset':'clear the leather strip'})
for j,symbol in enumerate(SPEC['stages'][2]['options']):LABELS['s3_choice_'+str(j)]=symbol+' embossing die'

_act=Game.act
def shoe_act(self,a):
 r=_act(self,a)
 if r.get('ok') and a.get('_validated364') and a.get('action')=='use' and a.get('_hit364')=='s3_setup':self.states[2]['card_exposed']=True
 if a.get('_validated364') and a.get('action')=='unlock' and a.get('_hit364')=='s2_lock':self.states[1]['entered_code']=str(a.get('code',''))
 return r
Game.act=shoe_act
_shoe_cpu=cpu_check
def cpu_check():
    from easy88_core import stage_actions
    result=_shoe_cpu();g=Game()
    act=lambda kind,key,**kw:g.act(dict(action=kind,_hit364=key,_validated364=True,**kw))
    assert not act('press','s3_choice_0')['ok']
    for i in [0,1]:
        for kind,key,extra in stage_actions(g,i):assert act(kind,key,**extra)['ok']
    for kind,key,extra in stage_actions(g,2):
        if key.startswith('s3_choice_'):break
        assert act(kind,key,**extra)['ok']
    assert g.states[2]['card_exposed'] and not g.states[2]['card_taken']
    for _ in range(3):assert act('press','s3_choice_0')['ok']
    assert not act('press','s3_confirm')['ok'];assert not g.solved[2] and not g.opened['key_box']
    assert g.states[2]['buffer']==[]
    for j in [3,1,4]:assert act('press','s3_choice_'+str(j))['ok']
    assert act('press','s3_confirm')['ok'];assert not g.opened['key_box']
    result['checks']+=['dies unavailable before extracting the sample','wrong die pattern rejected','wrong pattern cannot release key drawer','wrong pattern selection clears for retry','correct embossing pattern works with sample left on tray and does not auto-open drawer'];result['passed']=len(result['checks']);return result

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


class Scene(EasyScene):
    def __init__(self,og,run):
        super().__init__(og,run,SPEC)
        self.views={};self.focus={};self.labels={};self.drawers={};self.lock_shaders={};self.lock_values={};self.expanded=[];self.screen_signature=None
    def palette(self):
        super().palette()
        for n,c in [('sole_rubber',(.14,.17,.16)),('leather',(.43,.24,.13)),('tread_ink',(.63,.66,.56)),('felt',(.25,.33,.28))]:self.mat(n,c,rough=.96)
    def reg_at(self,key,node,label,view,focus=None):
        self.reg(key,node);self.views[key]=list(view);self.labels[key]=label
        if focus is not None:self.focus[key]=list(focus)
        return node
    def flat(self,name,parent,pos,w,h,im,horizontal=False):
        path=self.tex/(name+'.png');im.save(path)
        return self.plane(name,pos,w,h,(1,0,0),(0,1,0) if horizontal else (0,0,1),None,parent,material=self.image_mat('r20_'+name,path))
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
        mat=self.mats['r20_'+key+'_display']
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


    def press_key(self,key,parent,pos,glyph,view,size=.10):
        n=self.group(key,pos,parent);self.box('button_base',[0,0,0],[size,.035,size],'iron',n)
        im=Image.new('RGB',(240,240),(218,215,189));dr=ImageDraw.Draw(im)
        if glyph in ['↻','✓']:dr.text((120,120),glyph,font=load_font(160),fill=(39,67,53),anchor='mm')
        else:draw_symbol(dr,glyph,(35,35,205,205),fill=(39,67,53),outline=(39,67,53))
        self.flat(key+'_print',n,[0,-.019,0],size*.9,size*.9,im)
        return self.reg_at(key,n,LABELS.get(key,glyph+' button'),view)
    def sole(self,name,parent,pos,pattern,left=False):
        n=self.group(name,pos,parent);mirror=-1 if left else 1
        coords=[(-.065,-.22),(.048,-.22),(.067,-.14),(.040,-.055),(.080,.04),(.10,.15),(.065,.23),(-.030,.24),(-.085,.185),(-.095,.08),(-.070,-.04),(-.080,-.13)]
        scale=1.03 if pattern=='D' else .92 if pattern=='A' else 1.0
        vertices=[(x*mirror*scale,y,z*scale) for y in [-.018,.018] for x,z in coords]
        N=len(coords);faces=[list(range(N-1,-1,-1)),list(range(N,2*N))]
        faces += [[i,(i+1)%N,(i+1)%N+N,i+N] for i in range(N)]
        self.mesh('true_asymmetric_sole',vertices,faces,'sole_rubber',n)
        if pattern in ('A','D'):
            for k in range(3 if pattern=='A' else 4):
                z=.04+k*.045;self.tube('matching_tread',[-.065*mirror,-.020,z],[.062*mirror,-.020,z],.006,'tread_ink',n)
        elif pattern=='B':
            for k in range(4):
                z=.02+k*.043;self.tube('diagonal_tread',[-.06*mirror,-.020,z-.025],[.06*mirror,-.020,z+.025],.006,'tread_ink',n)
        else:
            for x in [-.045,0,.045]:self.tube('vertical_tread',[x,-.020,.025],[x,-.020,.19],.006,'tread_ink',n)
        self.box('heel_tread',[0,-.021,-.15],[.10,.006,.028],'tread_ink',n)
        return n
    def symbol_screen(self,buffer):
        im=Image.new('RGB',(1200,350),(29,45,39));dr=ImageDraw.Draw(im)
        for j in range(3):
            x=285+j*270;dr.rectangle((x-90,15,x+90,125),outline=(127,153,128),width=3)
            if j<len(buffer):draw_symbol(dr,SPEC['stages'][2]['options'][buffer[j]],(x-42,28,x+42,112),fill=(224,222,187),outline=(224,222,187))
        dr.text((75,70),'↻',font=load_font(85),fill=(224,222,187),anchor='mm');dr.text((1120,70),'✓',font=load_font(85),fill=(224,222,187),anchor='mm')
        for j,sym in enumerate(SPEC['stages'][2]['options']):
            x=100+j*200;dr.rectangle((x-85,158,x+85,336),outline=(100,130,107),width=3);draw_symbol(dr,sym,(x-57,192,x+57,306),fill=(224,222,187),outline=(224,222,187))
        p=self.tex/('symbols_'+(''.join(map(str,buffer)) or 'blank')+'.png');im.save(p);return p
    def screen_piece(self,key,rect,target=True):
        x0,y0,x1,y1=rect
        points=[((x/1200-.5)*.90,-.14+(.5-y/350)*.262,.783) for x,y in [(x0,y1),(x1,y1),(x1,y0),(x0,y0)]]
        uv=[(x0/1200,1-y1/350),(x1/1200,1-y1/350),(x1/1200,1-y0/350),(x0/1200,1-y0/350)]
        n=self.mesh(key+'_screen',points,[[0,1,2,3]],self.screen_mat,self.south,uv=uv)
        if target:self.reg_at(key,n,LABELS.get(key,key.replace('_',' ')),[2.5,1.5])
    def build(self,g):
        self.room_shell('cobbler',size=(4.0,5.8),openings={'west':[(.71,1.81)]})
        self.box('continuous_subfloor',[2.,2.9,-.06],[4.15,5.95,.10],'darkwood')
        self.table('pair_inspection_bench',(2.,5.32),(2.95,.70),height=.72)
        self.rack=self.group('pair_rack',[2.,5.48,.755])
        self.box('rack_real_back',[0,.06,.56],[2.85,.06,1.12],'paint',self.rack)
        for x in [-1.38,1.38]:self.box('rack_side_support',[x,0,.56],[.05,.24,1.16],'wood',self.rack)
        for z in [.03,.57]:self.box('rack_shelf',[0,-.04,z],[2.85,.32,.035],'wood',self.rack)
        for j,pat in enumerate(['D','A']):
            x=(j-.5)*1.20-.16
            self.sole('fixed_left_sole_'+str(j),self.rack,[x,-.012,.82],pat,True)
            self.text('pair_order_'+str(j),self.rack,[x,-.044,1.075],.12,.07,str(j+1))
            clip=self.group('sole_clamp_'+str(j),[x+.33,-.012,.82],self.rack)
            self.box('generic_clamp_back',[0,.020,0],[.25,.03,.50],'felt',clip)
            for z in [-.20,.23]:self.box('clamp_jaw',[0,-.025,z],[.22,.045,.03],'steel',clip)
            self.reg_at('s1_slot_'+str(j),clip,'sole clamp '+str(j+1),[2.,4.5])
        self.soles=[]
        for j,pat in enumerate('ABCD'):
            x=(j-1.5)*.53
            n=self.sole('candidate_right_sole_'+str(j),self.rack,[x,-.02,.275],pat)
            self.reg_at('s1_item_'+str(j),n,'right sole '+pat,[2.,4.5]);self.soles.append(n)
            self.text('candidate_letter_'+pat,self.rack,[x,-.045,.105],.12,.07,pat)
        self.press_key('s1_confirm',self.rack,[1.15,-.16,.37],'✓',[2.,4.5])
        self.press_key('s1_reset',self.rack,[-1.15,-.16,.37],'↻',[2.,4.5])
        self.reg_at('s1_clue',self.rack,'two fixed left soles and their empty pair clamps',[2.,4.5],[2.,5.43,1.26])
        self.ruledrawer,rfront=self.drawer('ruler_drawer',None,(2.,4.98),.54,1.20,.43)
        self.reg_at('s2_cover',rfront,'ruler drawer',[2.,4.0])
        self.ruler=self.group('ruler_tool',[0,.22,-.065],self.ruledrawer)
        self.box('straight_ruler_body',[0,0,0],[.24,.045,.015],'steel',self.ruler)
        self.reg_at('s2_tool',self.ruler,'straight ruler',[2.,4.0])
        self.add_obstacle(.46,4.91,3.54,5.77)

        self.table('leather_measure_bench',(3.57,3.15),(.70,1.58),height=.83)
        self.measure=self.group('leather_measure_fixture',[3.40,3.15,.865]);self.transform(self.measure,rpy=[0,0,-90])
        self.box('leather_pad',[0,0,.008],[.54,.36,.016],'felt',self.measure)
        self.box('marked_leather_strip',[-.040,0,.022],[.120,.035,.012],'leather',self.measure)
        for x in [-.10,.020]:self.box('endpoint_pin',[x,0,.035],[.003,.070,.012],'cream',self.measure)
        self.reg_at('s2_setup',self.measure,'marked leather strip',[3.0,3.25],[3.40,3.15,.90])
        _add_outline(self,'ruler_outline',self.measure,[0,-.055,.0168],'ruler',.205,.06,up=(0,1,0))
        self.measuring_ruler=self.group('ruler_in_contact',[-.10,-.055,.037],self.measure)
        self.box('ruler_body',[.10,0,0],[.205,.060,.012],'steel',self.measuring_ruler)
        im=Image.new('RGB',(1500,400),(209,208,181));dr=ImageDraw.Draw(im)
        for value in range(0,201,20):
            x=30+value/200*1440;dr.line((x,0,x,95 if value%40 else 125),fill=(28,48,39),width=5)
            if value%40==0:dr.text((x,235),str(value),font=load_font(125),fill=(28,48,39),anchor='mm')
        dr.text((1400,355),'mm',font=load_font(60),fill=(28,48,39),anchor='mm')
        self.flat('ruler_own_ticks',self.measuring_ruler,[.10,0,.007],.205,.060,im,True)
        self.reg_at('s2_clue',self.measuring_ruler,'straight ruler scale touching both endpoint marks',[3.0,3.25],[3.40,3.15,.90])
        self.east_support=self.group('east_drawer_support',[3.60,3.15,0]);self.transform(self.east_support,rpy=[0,0,-90])
        self.pliersdrawer,pfront=self.drawer('pliers_drawer',self.east_support,(0,-.34),.62,1.13,.43)
        for x in [-.59,.59]:self.box('underbench_bracket',[x,-.12,.78],[.035,.38,.08],'steel',self.east_support)
        self.add_obstacle(3.18,2.29,3.97,4.00)
        self.reg_at('s3_cover',pfront,'pliers drawer',[2.5,3.25])
        self.numeric_lock('s2_lock',pfront,[.10,-.044,.016],4,[2.5,3.25])
        self.text('mm_lock_unit',pfront,[.10,-.065,-.094],.20,.045,'mm / 0000')
        self.pliers=self.group('pliers_tool',[0,.22,-.025],self.pliersdrawer)
        for j in [-1,1]:
            self.tube('pliers_long_jaw',[j*.006,0,.025],[j*.012,0,.14],.008,'steel',self.pliers)
            self.tube('pliers_handle',[j*.008,0,.015],[j*.045,0,-.10],.014,'iron',self.pliers)
        self.cylinder('pliers_pivot',[0,0,.018],.018,.018,'steel','y',self.pliers,n=24)
        self.transform(self.pliers,rpy=[90,0,0]);self.reg_at('s3_tool',self.pliers,'needle nose pliers',[2.5,3.25])

        self.table('embossed_card_bench',(2.5,.41),(2.35,.90),height=.72)
        self.south=self.group('card_case',[2.5,.40,0]);self.transform(self.south,rpy=[0,0,180])
        self.box('embossing_jig_base',[0,-.13,.755],[1.02,.48,.045],'wood',self.south)
        self.box('leather_strip_bed',[0,-.03,.783],[.75,.14,.015],'leather',self.south)
        self.impressions=[];self.stamp_dies=[]
        for slot in range(3):
            variants=[]
            for j,symbol in enumerate(SPEC['stages'][2]['options']):
                im=Image.new('RGB',(240,220),(145,101,60));draw_symbol(ImageDraw.Draw(im),symbol,(44,30,196,190),fill=(64,40,24),outline=(64,40,24))
                variants.append(self.flat('leather_impression_'+str(slot)+'_'+str(j),self.south,[(slot-1)*.24,-.03,.792],.19,.11,im,True))
            self.impressions.append(variants)
        for j,symbol in enumerate(SPEC['stages'][2]['options']):
            die=self.group('physical_embossing_die_'+str(j),[(j-2.5)*.15,-.295,.800],self.south)
            self.cylinder('die_metal_body',[0,0,0],.050,.070,'steel','z',die,n=28)
            im=Image.new('RGB',(240,240),(192,196,178));draw_symbol(ImageDraw.Draw(im),symbol,(38,38,202,202),fill=(38,50,42),outline=(38,50,42))
            self.flat('die_face_'+str(j),die,[0,0,.036],.086,.086,im,True)
            self.reg_at('s3_choice_'+str(j),die,LABELS['s3_choice_'+str(j)],[2.5,1.5]);self.stamp_dies.append(die)
        self.press_key('s3_reset',self.south,[-.57,-.13,.83],'↻',[2.5,1.5],size=.08)
        lever=self.group('embossing_check_lever',[.57,-.13,.82],self.south)
        self.box('lever_mount',[0,0,0],[.10,.12,.10],'iron',lever)
        self.tube('lever_arm',[0,0,.03],[0,-.045,.17],.013,'steel',lever)
        self.cylinder('lever_grip',[0,-.045,.17],.022,.10,'wood','x',lever,n=24)
        self.reg_at('s3_confirm',lever,LABELS['s3_confirm'],[2.5,1.5]);self.emboss_lever=lever
        self.stamp_release=self.group('embossing_drawer_release',[.59,-.33,.60],self.south)
        self.box('embossing_release_seat',[0,0,0],[.07,.045,.07],'iron',self.stamp_release)
        self.stamp_pin=self.group('release_pin',[-.075,-.026,0],self.stamp_release)
        self.box('drawer_release_pin',[0,0,0],[.15,.022,.022],'brass',self.stamp_pin)
        self.tube('press_release_rod',[.59,-.30,.82],[.59,-.30,.63],.009,'steel',self.south)
        for z in [.765,.905]:self.box('slot_housing_plate',[-.73,.09,z],[.38,.27,.020],'paint',self.south)
        for x in [-.92,-.54]:self.box('slot_housing_side',[x,.09,.835],[.020,.27,.16],'paint',self.south)
        self.box('slot_housing_back',[-.73,.225,.835],[.38,.020,.16],'paint',self.south)
        for z in [.78875,.88125]:self.box('slot_front_above_below',[-.73,-.049,z],[.38,.020,.0675],'paint',self.south)
        self.ring=self.group('card_extraction_ring',[-.73,-.071,.835],self.south)
        for j in range(24):
            a=j*2*math.pi/24;b=(j+1)*2*math.pi/24
            self.tube('actual_eyelet',[.018*math.cos(a),0,.018*math.sin(a)],[.018*math.cos(b),0,.018*math.sin(b)],.003,'brass',self.ring)
        self.box('eyelet_attachment',[0,.014,0],[.022,.032,.009],'brass',self.ring)
        self.reg_at('s3_setup',self.ring,'card eyelet in narrow slot',[3.25,1.5],[3.23,.471,.835])
        self.box('card_external_tray',[-.73,-.30,.792],[.39,.28,.072],'felt',self.south)
        self.card=self.group('embossed_card',[-.73,.09,.835],self.south)
        self.box('embossed_card_body',[0,0,0],[.35,.25,.014],'leather',self.card)
        im=Image.new('RGB',(900,500),(201,178,135));dr=ImageDraw.Draw(im)
        for j,sym in enumerate(['star','triangle','leaf']):draw_symbol(dr,sym,(45+j*290,145,245+j*290,345),fill=(43,60,45),outline=(43,60,45))
        self.flat('card_permanent_symbols',self.card,[0,0,.008],.34,.24,im,True)
        self.reg_at('s3_card',self.card,'retrieved embossed card',[3.25,1.5],[3.23,.70,.835])
        self.reg_at('s3_clue',self.card,'three embossed symbols',[3.25,1.5],[3.23,.70,.835])
        self.keydrawer,kfront=self.drawer('shoe_key_drawer',self.south,(0,-.27),.54,1.10,.43)
        self.reg_at('key_box',kfront,'shoe workshop key drawer',[2.5,1.5])
        self.box('key_pad',[0,.21,-.025],[1.,.34,.15],'felt',self.keydrawer)
        self.key=self.tool('flat_brass_key',self.keydrawer,[0,.21,.065],'key');self.target_nodes.pop('flat_brass_key',None)
        self.transform(self.key,rpy=[90,0,0]);self.reg_at('key',self.key,'brass door key',[2.5,1.5])
        self.add_obstacle(1.26,.04,3.74,.93)
        self.box('cobbler_tool_pegboard',[.055,3.25,1.46],[.035,.66,.46],'wood')
        for j,y in enumerate([3.04,3.43]):
            self.tube('fixed_tool_hook',[.07,y,1.62],[.14,y,1.62],.008,'steel')
            self.cylinder('fixed_awl_handle',[.10,y,1.48],.017,.17,'wood','z',n=20)
            self.cylinder('fixed_awl_point',[.10,y,1.355],.004,.10,'steel','z',n=16)
        for j,x in enumerate([.90,3.12]):
            spool=self.group('fixed_shoe_thread_spool_'+str(j),[x,5.35,.36])
            self.cylinder('shoe_thread_winding',[0,0,0],.055,.105,'cream','z',spool,n=28)
            for z in [-.057,.057]:self.cylinder('spool_flange',[0,0,z],.068,.010,'wood','z',spool,n=28)
        self.exit_node=self.door('shoe_exit',[.06,1.79,0],1.04);self.door_angle=-90
        self.door_view=[1.,1.25];self.reg_at('exit',self.exit_node,'exit door',self.door_view,[.06,1.27,1.12])
        for y in [.73,1.81]:self.box('door_jamb',[.05,y,1.14],[.17,.065,2.3],'paint')
        self.box('door_top',[.05,1.27,2.29],[.17,1.15,.065],'paint')
        self.stage_views=[[2.,4.5],[2.75,3.25],[2.5,1.5]];self.stage_centres=[[2.,5.43,1.26],[3.60,3.15,.9],[2.5,.4,.8]]
        self.bases=[([2.,5.48],0),([3.6,3.15],-90),([2.5,.4],180)];self.sync(g)
    def visible(self,key,g):
        if key.startswith('s1_item_'):
            j=int(key.rsplit('_',1)[1]);return key not in g.holding and (key not in g.taken or j in g.states[0]['assignment'].values())
        if key=='s2_tool':return bool(g.opened['s2_cover']) and key not in g.taken
        if key=='s3_tool':return bool(g.opened['s3_cover']) and key not in g.taken
        if key in ('s3_card','s3_clue'):return g.states[2]['card_exposed'] and not g.states[2]['card_taken']
        if key=='s2_clue':return g.states[1]['setup_used']
        if key=='key':return g.opened['key_box'] and key not in g.taken
        return key in self.target_nodes
    def sync(self,g):
        assign=g.states[0]['assignment']
        for j,n in enumerate(self.soles):
            slot=next((int(k) for k,v in assign.items() if int(v)==j),None)
            self.transform(n,[(j-1.5)*.53,-.02,.275] if slot is None else [(slot-.5)*1.20+.17,-.040,.82])
            self.visibility(n,'s1_item_'+str(j) not in g.holding and ('s1_item_'+str(j) not in g.taken or slot is not None))
        for key,flag in [('ruler_drawer','s2_cover'),('pliers_drawer','s3_cover'),('shoe_key_drawer','key_box')]:
            n,p=self.drawers[key];self.transform(n,[p[0],p[1]-(.42 if g.opened[flag] else 0),p[2]])
        self.visibility(self.ruler,'s2_tool' not in g.taken);self.visibility(self.measuring_ruler,g.states[1]['setup_used'])
        self.visibility(self.pliers,'s3_tool' not in g.taken)
        self.transform(self.card,[-.73,-.30,.835] if g.states[2]['card_exposed'] else [-.73,.09,.835])
        self.visibility(self.card,not g.states[2]['card_taken'])
        self.transform(self.ring,[-.73,-.461 if g.states[2]['card_exposed'] else -.071,.835])
        self.visibility(self.ring,not g.states[2]['card_taken'])
        self.visibility(self.key,'key' not in g.taken)
        value=g.states[1].get('entered_code','0000')
        if self.lock_values['s2_lock']!=value:
            p=self.tex/('shoe_entered_'+value+'.png');self.text_image(value,.27,.088,(47,67,56),(224,228,191)).save(p)
            with self.og.sim.editing_usd():self.lock_shaders['s2_lock'].GetInput('file').Set(str(p))
            self.lock_values['s2_lock']=value
        buffer=g.states[2]['buffer']
        for slot,variants in enumerate(self.impressions):
            for j,node in enumerate(variants):self.visibility(node,slot<len(buffer) and buffer[slot]==j)
        self.transform(self.stamp_pin,[.085 if g.solved[2] else -.075,-.026,0])
        self.transform(self.emboss_lever,rpy=[-22 if g.solved[2] else 0,0,0])
        self.transform(self.exit_node,rpy=[0,0,-90-(103 if g.opened['exit'] else 0)])
        self.centres={}
        for k,n in self.target_nodes.items():
            p=self.triangles(n).reshape(-1,3)
            if p.size:self.centres[k]=((p.min(0)+p.max(0))/2).tolist()
    def candidates(self,g):return self.base_candidates([k for k in self.target_nodes if self.visible(k,g)])
    def view_for(self,key):return self.views.get(key,self.door_view)
    def focus_for(self,key):return self.focus.get(key,self.centres.get(key))
    def label_for(self,key):return self.labels.get(key,LABELS.get(key,key.replace('_',' ')))
    def animate(self,d,before):
        previous=before['states'][2]['buffer'];current=d.game.states[2]['buffer']
        if len(current)>len(previous):
            j=current[-1];node=self.stamp_dies[j]
            for dz in [-.012,0]:
                self.transform(node,[(j-2.5)*.15,-.295,.800+dz]);d.frame(warm=4);d.append('Select the next embossing die pattern',4)

        if not before['states'][2]['card_exposed'] and d.game.states[2]['card_exposed']:
            for q in [.0,.33,.67,1.]:
                self.transform(self.card,[-.73,.09-.39*q,.835])
                self.transform(self.ring,[-.73,-.071-.39*q,.835])
                d.frame(warm=4);d.append('Card slides out onto the adjacent tray',4)
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

    observe('s1_clue','Compare fixed left soles with the right sole candidates')
    for slot,j in enumerate([3,0]):
        approach('s1_item_'+str(j),'Take the matching right sole',stay=True);click('s1_item_'+str(j),'take')
        approach('s1_slot_'+str(slot),'Place the sole in its generic pair clamp',stay=True);click('s1_slot_'+str(slot),'use','s1_item_'+str(j))
    click('s1_confirm')
    approach('s2_cover','Open the ruler drawer');click('s2_cover','open');approach('s2_tool','Take the straight ruler',stay=True);click('s2_tool','take')
    approach('s2_setup','Place the ruler against the leather endpoints');click('s2_setup','use','s2_tool')
    observe('s2_clue','Read the endpoint on the ruler itself',stay=True)
    approach('s2_lock','Use the millimetre measurement');click('s2_lock','unlock',code='0120');click('s3_cover','open')
    approach('s3_tool','Take the needle nose pliers',stay=True);click('s3_tool','take')
    approach('s3_setup','Grip the visible extraction ring');click('s3_setup','use','s3_tool')
    observe('s3_card','Observe the three symbols on the retrieved card')
    approach('s3_choice_0','Select the dies matching the embossed leather sample')
    for j in [3,1,4]:click('s3_choice_'+str(j))
    click('s3_confirm');approach('key_box','Open the unlocked key drawer',stay=True);click('key_box','open')
    d.append('Observe the flat key',18);approach('key','Take the brass key',stay=True);click('key','take')
    approach('exit','Return to the exit');click('exit','use','key');click('exit','open')
    if not exit_test(d.pos,g):raise RuntimeError('Open-door success was not reached')

_aff_build_last(Scene)
