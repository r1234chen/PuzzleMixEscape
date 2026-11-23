from easy88_core import make_level

SPEC = {'id': 'R15',
 'title': 'Camping Equipment Room',
 'chinese_title': '露营装备室',
 'theme': 'camping',
 'size': [4.5, 5.75],
 'door': {'side': 'south', 'start': 1.0, 'width': 1.04},
 'start': [1.5, 1.0, 1.35],
 'start_yaw': 90,
 'floor': 'wood',
 'stages': [{'kind': 'sequence',
             'name': 'camp map and field case',
             'wall': 'north',
             'centre': [2.25, 5.33],
             'view': [2.25, 4.25],
             'board_height': 0.96,
             'options': ['circle', 'triangle', 'square', 'star', 'leaf', 'cross'],
             'answer': [4, 3, 4],
             'length': 3,
             'distinct': False,
             'setup': {'kind': 'uv',
                       'item': 'uv_lamp',
                       'item_name': 'UV torch',
                       'target_name': 'camp map',
                       'gate': False,
                       'transient': True,
                       'consume': False},
             'clue': {'route_symbols': ['leaf', 'star', 'leaf'],
                      'route_start': 'tent',
                      'route_finish': 'hut',
                      'branched': False,
                      'hidden_until_uv': True},
             'clue_text': '',
             'visual': {'type': 'uv_route',
                        'symbols': ['leaf', 'star', 'leaf'],
                        'start': 'tent',
                        'finish': 'hut',
                        'branch_count': 0,
                        'blank_in_ordinary_view': True},
             'author_notes': 'UV use must return illuminated and ordinary native views in this order. Do not '
                             'enforce that read was used, or reveal the route in ordinary read feedback.'},
            {'kind': 'assign',
             'name': 'rope route board',
             'wall': 'west',
             'centre': [0.42, 3.0],
             'view': [1.25, 3.0],
             'board_height': 0.96,
             'slots': 4,
             'items': [{'id': 'round_rope_clip', 'name': 'round-marked rope clip', 'symbol': 'circle'},
                       {'id': 'star_rope_clip', 'name': 'star-marked rope clip', 'symbol': 'star'}],
             'target': [None, 0, None, 1],
             'setup': {'kind': 'hook',
                       'item': 'hook_rod',
                       'item_name': 'short hook rod',
                       'target_name': 'protective curtain',
                       'gate': True,
                       'consume': False},
             'clue': {'source_symbols': ['circle', 'star'],
                      'trace_ends': [2, 4],
                      'terminal_count': 4,
                      'one_clip_per_peg': True},
             'clue_text': '',
             'visual': {'type': 'wire_trace',
                        'sources': ['circle', 'star'],
                        'ends': [2, 4],
                        'terminal_count': 4,
                        'material': 'rope',
                        'cover': 'cloth_curtain'},
             'author_notes': 'Both rope clips are takeable and every empty peg accepts either. Whole-board '
                             'check only; taking a placed clip restores it to inventory.'},
            {'kind': 'sequence',
             'name': 'numbered camp photograph',
             'wall': 'east',
             'centre': [4.08, 3.0],
             'view': [3.25, 3.0],
             'board_height': 0.96,
             'options': ['circle', 'triangle', 'square', 'star', 'leaf', 'cross'],
             'answer': [1, 0, 4],
             'length': 3,
             'clue': {'numbered_marks': [[1, 'triangle'], [2, 'circle'], [3, 'leaf']]},
             'clue_text': '',
             'visual': {'type': 'symbol_strip',
                        'symbols': ['triangle', 'circle', 'leaf'],
                        'numbered': True,
                        'photograph_style': 'camp_equipment'},
             'author_notes': 'Make all three numbered marks large and legible; do not replace the photograph '
                             'with the answer as text.'}],
 'decor': [{'kind': 'camp_bag', 'name': 'rolled tent bag', 'fixed': True},
           {'kind': 'rope_coil', 'name': 'spare rope coil', 'fixed': True},
           {'kind': 'metal_cup', 'name': 'enamel cup', 'fixed': True},
           {'kind': 'lantern', 'name': 'old camping lantern', 'fixed': True}],
 'design_notes': 'Exactly three serial puzzles: UV trace, rope trace matching, numbered photograph. Hook '
                 'curtain opening is a setup action, not another puzzle.'}


CASE_LABELS=('The key is not in the red case.','The key is in the red case.','The key is not in the blue case.')
CASE_RULE='Exactly one label is true.'
def case_label_truths(candidate):return (candidate!=0,candidate==0,candidate!=1)
SPEC['stages'][2].update(kind='binary_pattern',semantic_kind='one_true_case_deduction',choice_failure_feedback='arrangement',name='three labelled camp cases',
 initial=[0,0,0],target=[0,1,0],auto=False,clue={'type':'self_contained_case_logic','rule':CASE_RULE,'labels':list(CASE_LABELS),'colours':['red','blue','green']},
 visual={'type':'three_physical_cases'},clue_text=CASE_RULE+'\nRed: '+CASE_LABELS[0]+'\nBlue: '+CASE_LABELS[1]+'\nGreen: '+CASE_LABELS[2])
for field in ['options','answer','length','distinct']:SPEC['stages'][2].pop(field,None)
Game,_OriginalScene,_OriginalStandard,exit_test,cpu_check=make_level(SPEC)
TITLE=SPEC['title'];LEVEL_ID=SPEC['id'];START=SPEC['start'];START_YAW=SPEC['start_yaw']
CAP=150;OBSERVATION_SIZE=(640,360);VISUAL_ONLY=False;READ_ENABLED=True;READ_FEEDBACK_TEXT=True
Game.LABELS.update({'s1_tool':'UV torch','s1_setup':'camp map','s1_clue':'camp map','s1_confirm':'map case check icon','s1_reset':'map case clear icon',
 's2_cover':'hook rod drawer','s2_tool':'short hook rod','s2_setup':'protective curtain','s2_clue':'two rope source marks and four pegs',
 's2_confirm':'whole rope board check button','s3_cover':'rope-latched case cover','s3_clue':'three camp case labels and one-true rule',
 's3_confirm':'photograph case check icon','s3_reset':'photograph case clear icon','key_box':'blue camp case lid','key':'brass door key'})
LABELS=Game.LABELS
LABELS.update({'s3_choice_0':'red case latch','s3_choice_1':'blue case latch','s3_choice_2':'green case latch'})
_original_act=Game.act
Game.stage_accessible=lambda self,index:0<=index<3
Game.stage_exposed=lambda self,index:0<=index<3 and bool(self.states[index]['setup_ready'])
def _camp_act(self,a):
    key=a.get('_hit364');kind=a.get('action')
    if not a.get('_validated364'):return _original_act(self,a)
    from action_feedback import failure_for
    if key=='s2_tool' and kind=='take' and not self.opened['s2_cover']:return {'ok':False,'text':failure_for(kind)}
    if key in ('s3_clue','key_box','key') and not self.opened['s3_cover']:return {'ok':False,'text':failure_for(kind)}
    if str(key).startswith('s3_choice_'):
        try:j=int(str(key).rsplit('_',1)[1])
        except ValueError:return {'ok':False,'text':failure_for(kind)}
        if kind!='press' or not self.opened['s3_cover'] or not 0<=j<3:return {'ok':False,'text':failure_for(kind)}
        self.states[2]['selected']=[int(k==j) for k in range(3)]
        correct=sum(case_label_truths(j))==1
        if correct:self.solved[2]=True
        return {'ok':correct,'text':'' if correct else failure_for(kind)}
    if key in ('s3_confirm','s3_reset'):return {'ok':False,'text':failure_for(kind)}
    return _original_act(self,a)
Game.act=_camp_act
import math
import numpy as np
from PIL import Image,ImageDraw
from easy88_scene import EasyScene
from easy88_clues import draw_symbol
from font_utils import load_font

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
        self.views={};self.focus={};self.labels={};self.drawers={};self.expanded=[];self.screens={};self.screen_signatures={};self.clips=[]
    def palette(self):
        super().palette()
        for name,c in [('camp_green',(.23,.33,.22)),('camp_blue',(.16,.28,.34)),('camp_curtain',(.30,.37,.22)),('camp_felt',(.25,.32,.25)),('rope_tan',(.56,.43,.24)),('camp_paper',(.73,.70,.57)),('sleeping_red',(.43,.21,.15)),('case_red',(.48,.16,.10)),('case_blue',(.12,.29,.39)),('case_green',(.20,.35,.18))]:self.mat(name,c,rough=.94)
        self.mat('fluorescent_ink',(.08,.35,.13),rough=1.,opacity=0.,emission=(0,0,0))
    def reg_at(self,key,node,label,view,focus=None):
        self.reg(key,node);self.views[key]=list(view);self.labels[key]=label
        if focus is not None:self.focus[key]=list(focus)
        return node
    def flat(self,name,parent,pos,w,h,im,horizontal=False):
        path=self.tex/(name+'.png');im.save(path)
        return self.plane(name,pos,w,h,(1,0,0),(0,1,0) if horizontal else (0,0,1),None,parent,material=self.image_mat('r15_'+name,path))
    def text(self,name,parent,pos,w,h,value):
        ih=360;iw=max(180,int(ih*w/h));im=Image.new('RGB',(iw,ih),(220,212,185));d=ImageDraw.Draw(im);size=int(ih*.7)
        while size>12:
            b=d.textbbox((0,0),str(value),font=load_font(size))
            if b[2]-b[0]<iw*.84 and b[3]-b[1]<ih*.80:break
            size-=8
        d.text((iw/2,ih/2),str(value),font=load_font(size),fill=(36,60,44),anchor='mm');return self.flat(name,parent,pos,w,h,im)
    def multiline(self,name,parent,pos,w,h,lines):
        im=Image.new('RGB',(660,230),(225,218,190));dr=ImageDraw.Draw(im)
        for j,line in enumerate(lines):dr.text((330,55+j*100),line,font=load_font(60),fill=(35,53,42),anchor='mm')
        return self.flat(name,parent,pos,w,h,im)
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

    def screen_file(self,index,buffer,solved=False):
        im=Image.new('RGB',(1200,510),(29,45,40));d=ImageDraw.Draw(im)
        d.arc((37,41,112,116),35,306,fill=(218,224,190),width=9);d.polygon([(110,36),(116,75),(81,56)],fill=(218,224,190))
        for j in range(3):
            x=275+j*240;d.rounded_rectangle((x-85,18,x+85,132),radius=12,fill=(42,61,49),outline=(110,139,108),width=3)
            if j<len(buffer):draw_symbol(d,SPEC['stages'][index]['options'][buffer[j]],(x-42,33,x+42,117),fill=(225,219,186),outline=(225,219,186))
            else:d.line((x-26,82,x+26,82),fill=(121,146,119),width=6)
        d.line([(1060,73),(1092,107),(1161,33)],fill=(222,228,188),width=11)
        for j,symbol in enumerate(SPEC['stages'][index]['options']):
            x=200+(j%3)*400;y=240+(j//3)*180;d.rounded_rectangle((x-178,y-76,x+178,y+76),radius=12,fill=(42,61,49),outline=(98,124,97),width=3);draw_symbol(d,symbol,(x-49,y-49,x+49,y+49),fill=(226,218,183),outline=(226,218,183))
        d.rounded_rectangle((3,3,1197,507),radius=14,outline=(99,155,99) if solved else (92,122,96),width=5)
        path=self.tex/('camp_lcd_'+str(index)+'_'+(''.join(map(str,buffer)) or 'empty')+('_ok' if solved else '')+'.png');im.save(path);return path
    def lcd(self,index,parent,view,focus):
        self.box('camp_lcd_bezel_'+str(index),[0,-.18,.775],[.85,.39,.020],'iron',parent)
        mat=self.image_mat('camp_touchscreen_'+str(index),self.screen_file(index,[]));self.screens[index]=self.S.Shader(self.stage.GetPrimAtPath(str(mat.GetPath())+'/texture'))
        rects=[('s'+str(index+1)+'_reset',(0,0,160,150)),('s'+str(index+1)+'_confirm',(1010,0,1200,150)),('slots_'+str(index),(160,0,1010,150))]
        for j in range(6):
            c=j%3;r=j//3;rects.append(('s'+str(index+1)+'_choice_'+str(j),(c*400,150+r*180,(c+1)*400,330+r*180)))
        for key,(x0,y0,x1,y1) in rects:
            points=[((x/1200-.5)*.80,-.18+(.5-y/510)*.34,.7875) for x,y in [(x0,y1),(x1,y1),(x1,y0),(x0,y0)]];uv=[(x0/1200,1-y1/510),(x1/1200,1-y1/510),(x1/1200,1-y0/510),(x0/1200,1-y0/510)]
            node=self.mesh(key+'_display',points,[[0,1,2,3]],mat,parent,uv=uv)
            if not key.startswith('slots_'):self.reg_at(key,node,LABELS.get(key,key.replace('_',' ')),view,focus)
    def ordinary_map(self):
        im=Image.new('RGB',(1500,850),(215,211,179));d=ImageDraw.Draw(im)
        for j in range(7):
            pts=[(40+x*75,180+j*67+32*math.sin(x*.45+j*.67)) for x in range(20)];d.line(pts,fill=(170,177,135),width=4)
        d.line([(1110,0),(1070,130),(1190,260),(1120,400),(1240,550),(1200,850)],fill=(114,158,161),width=35)
        for x,y in [(200,190),(400,180),(740,650),(910,300),(320,620),(600,350)]:
            for k in [-1,0,1]:d.polygon([(x+k*20,y-29),(x-17+k*20,y+10),(x+17+k*20,y+10)],fill=(141,161,119))
        draw_symbol(d,'tent',(75,580,230,760),fill=(119,105,69),outline=(84,91,63));d.rectangle((1270,155,1390,250),fill=(150,120,76),outline=(87,88,61),width=5);d.polygon([(1250,157),(1330,75),(1410,157)],fill=(111,88,57),outline=(87,88,61),width=5)
        d.rectangle((9,9,1490,840),outline=(121,133,99),width=7);return im
    def uv_line(self,a,b):
        a=np.array(a,float);b=np.array(b,float);delta=b-a;n=np.array([-delta[1],delta[0]]);n=n/np.linalg.norm(n)*.003
        points=[[float(p[0]),-.0225,float(p[1])] for p in [a-n,b-n,b+n,a+n]];self.mesh('invisible_route_ink',points,[[0,1,2,3]],'fluorescent_ink',self.uv_layer)
    def uv_glyph(self,name,x,z):
        if name=='star':
            ring=[]
            for j in range(10):
                a=math.pi/2-j*math.pi/5;r=.060 if j%2==0 else .027;ring.append([x+r*math.cos(a),-.0226,z+r*math.sin(a)])
            points=[[x,-.0226,z]]+ring;faces=[[0,j+1,(j+1)%10+1] for j in range(10)]
        else:
            points=[[x+(u-.5)*.13,-.0226,z+(.5-v)*.13] for u,v in [(0.12,.88),(.13,.50),(.37,.18),(.88,.09),(.85,.56),(.59,.82)]];faces=[list(range(len(points)))]
        self.mesh('invisible_fluorescent_'+name,points,faces,'fluorescent_ink',self.uv_layer)
    def hook_rod(self,parent):
        n=self.group('short_hook_rod',[0,.22,.074],parent);self.cylinder('hook_wood_grip',[-.11,0,0],.016,.14,'darkwood','x',n,n=24);self.tube('steel_hook_shaft',[-.04,0,0],[.17,0,0],.007,'steel',n)
        self.tube('hook_tip_a',[.17,0,0],[.20,.035,0],.007,'steel',n);self.tube('hook_tip_b',[.20,.035,0],[.175,.060,0],.007,'steel',n);return n
    def rope_clip(self,j):
        n=self.group('marked_rope_clip_'+str(j));points=[[.040*math.cos(a),0,.055*math.sin(a)] for a in np.linspace(0,2*math.pi,25)]
        for a,b in zip(points,points[1:]):self.tube('carabiner_frame',a,b,.006,'steel',n)
        self.box('clip_tag',[0,-.004,-.085],[.075,.012,.048],'camp_paper',n,bevel=.002)
        im=Image.new('RGB',(300,180),(222,213,184));draw_symbol(ImageDraw.Draw(im),'circle' if j==0 else 'star',(91,25,209,155),fill=(40,66,46),outline=(40,66,46));self.flat('clip_mark_'+str(j),n,[0,-.011,-.085],.070,.043,im)
        return n
    def camp_scene_image(self):
        im=Image.new('RGB',(1600,1000));a=np.zeros((1000,1600,3),dtype=np.uint8)
        for y in range(1000):
            t=y/1000;a[y,:]=np.array([158,192,199])*(1-t)+np.array([179,163,113])*t
        im=Image.fromarray(a);d=ImageDraw.Draw(im)
        d.polygon([(0,360),(260,155),(510,337),(760,140),(1030,345),(1330,160),(1600,350),(1600,590),(0,590)],fill=(95,126,119));d.polygon([(0,450),(360,295),(660,445),(1060,270),(1600,430),(1600,660),(0,660)],fill=(91,126,97))
        for j in range(19):
            x=18+j*88;y=320+(j%4)*32;h=170+(j%5)*27;d.rectangle((x-8,y,x+8,y+h),fill=(83,91,57));d.polygon([(x,y-90),(x-75,y+145),(x+75,y+145)],fill=(55+(j%3)*9,100+(j%4)*6,74))
        d.polygon([(0,620),(420,530),(890,580),(1600,520),(1600,1000),(0,1000)],fill=(165,151,105));d.polygon([(900,590),(1170,600),(1490,1000),(1020,1000)],fill=(192,177,125))
        for j in range(85):
            x=(j*173)%1600;y=610+(j*57)%385;d.line((x,y,x+8,y-12),fill=(126,137,80),width=3)
        d.ellipse((100,675,745,845),fill=(131,129,87));d.polygon([(115,735),(310,360),(692,711)],fill=(181,128,66),outline=(85,93,63),width=7);d.polygon([(310,360),(535,400),(785,725),(692,711)],fill=(138,105,59),outline=(85,93,63),width=6)
        d.polygon([(310,405),(165,712),(572,703)],fill=(62,90,81));d.line((310,405,355,708),fill=(210,187,132),width=7)
        draw_symbol(d,'triangle',(252,507,362,617),fill=(230,215,168),outline=(230,215,168));d.line((125,731,71,824),fill=(103,104,69),width=4);d.line((782,724,848,809),fill=(103,104,69),width=4)
        d.polygon([(990,563),(1395,554),(1454,622),(972,639)],fill=(139,100,58),outline=(84,73,44),width=5)
        for x,y in [(1005,625),(1385,611)]:d.polygon([(x,y),(x+20,y),(x+31,y+161),(x+8,y+166)],fill=(88,78,49))
        d.rectangle((1168,397,1304,567),fill=(79,126,143));d.ellipse((1168,375,1304,418),fill=(117,157,166),outline=(54,88,99),width=4);d.ellipse((1168,545,1304,580),fill=(65,105,119));d.ellipse((1196,443,1277,524),fill=(224,215,172),outline=(224,215,172),width=3)
        d.ellipse((595,849,1040,965),fill=(128,128,87));d.rounded_rectangle((680,670,918,919),radius=35,fill=(66,97,72),outline=(44,67,48),width=6);d.rounded_rectangle((709,633,891,730),radius=32,fill=(86,117,82),outline=(44,67,48),width=6)
        d.line((726,667,733,892),fill=(133,142,96),width=16);d.line((874,668,867,891),fill=(133,142,96),width=16);d.rectangle((743,771,858,871),fill=(184,172,120),outline=(51,76,52),width=4);draw_symbol(d,'leaf',(760,784,841,857),fill=(52,85,56),outline=(52,85,56))
        for text,x,y in [('1',182,512),('2',1350,454),('3',954,777)]:
            d.rounded_rectangle((x-33,y-43,x+33,y+43),radius=8,fill=(231,222,184),outline=(77,88,61),width=4);d.text((x,y),text,font=load_font(65),fill=(43,69,49),anchor='mm')
        d.rectangle((8,8,1592,992),outline=(78,91,67),width=10);return im
    def build(self,g):
        self.room_shell('camp_equipment_room',size=(4.5,5.75),openings={'south':[(.97,2.07)]});self.box('solid_subfloor',[2.25,2.875,-.075],[4.64,5.89,.10],'darkwood',bevel=.001)
        self.table('camp_map_bench',(2.25,5.33),(2.0,.65),height=.72)
        self.map_base=self.group('camp_map_control_console',[2.25,5.33,0]);self.lcd(0,self.map_base,[2.25,4.25],[2.25,5.15,.98])
        self.map=self.group('framed_camp_map',[2.25,5.37,1.10]);self.box('map_wood_frame',[0,0,0],[1.20,.035,.68],'wood',self.map)
        self.flat('ordinary_camp_map',self.map,[0,-.020,0],1.16,.64,self.ordinary_map())
        self.uv_layer=self.group('permanent_invisible_ink_geometry',parent=self.map)
        route=[(-.43,-.19),(-.27,-.10),(-.18,.09),(-.02,.09),(.11,-.13),(.25,-.13),(.43,.18)]
        for a,b in zip(route,route[1:]):self.uv_line(a,b)
        self.mesh('UV_route_direction',[[-.343,-.023,-.135],[-.373,-.023,-.137],[-.359,-.023,-.161]],[[0,1,2]],'fluorescent_ink',self.uv_layer)
        for name,x,z in [('leaf',-.27,-.10),('star',-.02,.09),('leaf',.25,-.13)]:self.uv_glyph(name,x,z)
        self.uv_shader=self.S.Shader(self.stage.GetPrimAtPath(str(self.mats['fluorescent_ink'].GetPath())+'/surface'))
        self.reg_at('s1_setup',self.map,'camp map',[2.25,4.25],[2.25,5.35,1.10])
        self.uv=torch=self.group('UV_torch',[1.40,5.35,.855]);self.cylinder('UV_torch_body',[0,0,0],.027,.19,'iron','z',torch,n=28);self.cylinder('UV_torch_head',[0,0,.110],.041,.04,'steel','z',torch,n=28);self.cylinder('UV_purple_lens',[0,0,.132],.034,.006,'purple','z',torch,n=28)
        self.text('UV_torch_label',torch,[0,-.029,0],.040,.060,'UV');self.reg_at('s1_tool',torch,'UV torch',[1.5,4.25],[1.40,5.35,.88])
        self.hookdrawer,hookfront=self.drawer('hook_rod_drawer',None,(2.25,5.005),.54,width=1.16,depth=.44)
        self.reg_at('s2_cover',hookfront,'hook rod drawer',[2.25,4.25],[2.25,5.0,.54]);self.box('hook_support_pad',[0,.22,-.021],[1.03,.34,.158],'camp_felt',self.hookdrawer);self.hook=self.hook_rod(self.hookdrawer);self.reg_at('s2_tool',self.hook,'short hook rod',[2.25,4.25],[2.25,4.80,.614])
        self.rack=self.group('shared_camp_equipment_rack',[.38,3.75,0]);self.transform(self.rack,rpy=[0,0,90])
        self.box('long_rack_counter',[0,0,.72],[3.25,.66,.08],'wood',self.rack)
        for x in [-1.50,0,1.50]:
            for y in [-.23,.23]:self.box('rack_leg',[x,y,.35],[.075,.075,.70],'iron',self.rack)
        self.box('rack_lower_shelf',[0,0,.23],[3.12,.55,.045],'wood',self.rack);self.add_obstacle(.03,2.06,.75,5.44)
        self.ropeboard=self.group('rope_route_board',[-.75,0,0],self.rack)
        for x in [-.755,.755]:self.box('rope_frame_side',[x,0,1.105],[.035,.58,.81],'wood',self.ropeboard)
        self.box('rope_frame_top',[0,0,1.52],[1.55,.60,.03],'wood',self.ropeboard);self.box('rope_frame_floor',[0,0,.78],[1.55,.58,.025],'wood',self.ropeboard)
        self.box('rope_board_back',[0,.20,1.145],[1.51,.03,.73],'camp_green',self.ropeboard)
        for j,symbol in enumerate(['circle','star']):
            image=Image.new('RGB',(240,240),(220,213,184));draw_symbol(ImageDraw.Draw(image),symbol,(44,44,196,196),fill=(44,69,48),outline=(44,69,48));self.flat('rope_source_'+str(j),self.ropeboard,[-.32+j*.64,.182,1.38],.12,.12,image)
        paths=[[(-.32,1.32),(-.32,1.18),(.02,1.18),(.02,1.08),(-.15,1.08),(-.15,1.02)],[(.32,1.32),(.32,1.26),(.49,1.26),(.49,1.08),(.45,1.08),(.45,1.02)]]
        for path in paths:
            for a,b in zip(path,path[1:]):self.tube('fixed_rope_trace',[a[0],.164,a[1]],[b[0],.164,b[1]],.008,'rope_tan',self.ropeboard)
        self.reg_at('s2_clue',self.ropeboard,'two rope routes and four pegs',[1.25,3.0],[.68,3.0,1.14])
        self.slot_points=[]
        for j in range(4):
            x=(j-1.5)*.30;peg=self.group('rope_terminal_'+str(j),[x,.13,1.02],self.ropeboard);self.cylinder('general_peg',[0,0,0],.014,.11,'brass','y',peg,n=24);self.reg_at('s2_slot_'+str(j),peg,'rope peg '+str(j+1),[1.25,3.0],[.31,3.0,1.02]);self.slot_points.append([x,.072,.985]);self.text('peg_number_'+str(j),self.ropeboard,[x,.178,.945],.075,.045,str(j+1))
        for j,x in enumerate([-.32,0]):
            self.cylinder('clip_parking_peg',[x,.13,.950],.014,.11,'brass','y',self.ropeboard,n=24);n=self.rope_clip(j);self.clips.append(n);self.reg_at('s2_item_'+str(j),n,LABELS['s2_item_'+str(j)],[1.25,3.0],[.31,2.8,.915])
        check=self.group('rope_pair_check',[.35,-.29,.825],self.ropeboard);self.box('rope_check_bezel',[0,0,0],[.15,.027,.08],'iron',check);self.text('rope_check_mark',check,[0,-.015,0],.13,.066,'✓');self.reg_at('s2_confirm',check,'whole rope board check button',[1.25,3.0],[.69,3.35,.825])
        self.curtain=self.group('pleated_protective_curtain',[0,-.31,1.10],self.ropeboard);pts=[];count=40
        for z in [-.40,.40]:
            for j in range(count+1):
                x=-.675+j*1.35/count;pts.append([x,.014*math.cos(j*math.pi/2),z])
        self.mesh('real_cloth_curtain',pts,[[j,j+1,count+2+j,count+1+j] for j in range(count)],'camp_curtain',self.curtain)
        self.cylinder('curtain_rail',[0,-.31,1.525],.013,1.54,'steel','x',self.ropeboard,n=28)
        for j in range(8):self.cylinder('curtain_ring',[-.61+j*.174,0,.405],.020,.012,'brass','y',self.curtain,n=20)
        self.reg_at('s2_setup',self.curtain,'protective curtain',[1.25,3.0],[.71,3.0,1.10])
        _add_box(self,'hook_outline_plate',[-.725,-.30,1.25],[.095,.02,.30],'darkwood',self.ropeboard)
        _add_outline(self,'hook_outline',self.ropeboard,[-.725,-.3105,1.25],'hook',.08,.28)
        with self.og.sim.editing_usd():self.curtain_scale=self.G.Xformable(self.curtain['prim']).AddScaleOp()
        self.photo=self.group('camp_photograph_case',[.90,0,0],self.rack)
        for x in [-.64,.64]:self.box('photo_case_side',[x,-.04,1.15],[.035,.56,.80],'wood',self.photo)
        self.box('photo_case_back',[0,.225,1.15],[1.30,.03,.80],'wood',self.photo);self.box('photo_case_top',[0,-.04,1.56],[1.33,.59,.035],'wood',self.photo);self.box('photo_case_floor',[0,-.04,.77],[1.30,.56,.03],'wood',self.photo)
        self.logic_reference=self.group('three_case_logic_reference',parent=self.photo)
        self.box('one_true_rule_backing',[0,.19,1.39],[1.18,.09,.13],'camp_paper',self.logic_reference)
        self.text('one_true_rule',self.logic_reference,[0,.144,1.39],1.14,.105,'ONE LABEL IS TRUE')
        self.reg_at('s3_clue',self.logic_reference,'three camp case labels and one-true rule',[1.5,4.5],[.47,4.65,1.08])
        self.case_lids=[];self.case_latches=[]
        labels=[['The key is not','in the red case.'],['The key is in','the red case.'],['The key is not','in the blue case.']]
        for j,colour in enumerate(['case_red','case_blue','case_green']):
            case=self.group('weatherproof_camp_case_'+str(j),[(j-1)*.40,-.035,.80],self.photo)
            self.box('case_floor',[0,0,.014],[.35,.30,.028],colour,case)
            for x in [-.166,.166]:self.box('case_side',[x,0,.10],[.018,.30,.17],colour,case)
            self.box('case_rear',[0,.141,.10],[.35,.018,.17],colour,case)
            self.box('low_case_front_lip',[0,-.141,.045],[.35,.018,.070],colour,case)
            self.box('case_label_mount',[(j-1)*.40,.19,1.20],[.355,.09,.155],colour,self.logic_reference)
            self.multiline('case_statement_'+str(j),self.logic_reference,[(j-1)*.40,.144,1.20],.315,.135,labels[j])
            latch=self.group('actual_case_latch_'+str(j),[0,-.166,.038],case)
            self.box('case_latch_lever',[0,0,0],[.115,.035,.042],'brass',latch)
            self.reg_at('s3_choice_'+str(j),latch,LABELS['s3_choice_'+str(j)],[1.5,4.5],[.58,4.65,.96]);self.case_latches.append(latch)
            lid=self.group('camp_case_lid_'+str(j),[0,.15,.19],case)
            self.box('camp_case_lid_shell',[0,-.15,0],[.365,.315,.025],colour,lid)
            self.box('case_lid_front_skirt',[0,-.300,-.065],[.365,.020,.13],colour,lid)
            self.box('camp_case_lid_pull',[0,-.32,0],[.10,.025,.025],'brass',lid);self.case_lids.append(lid)
            if j==1:
                self.key_lid=lid;self.reg_at('key_box',lid,'blue camp case lid',[1.5,4.5],[.49,4.65,1.00])
                self.box('flat_case_lining',[0,0,.028],[.30,.25,.012],'camp_felt',case)
                self.key=self.tool('flat_brass_key',case,[0,0,.046],'key');self.target_nodes.pop('flat_brass_key',None);self.transform(self.key,rpy=[90,0,0]);self.reg_at('key',self.key,'brass door key',[1.5,4.5],[.43,4.65,.86])
        self.photo_cover=self.group('photograph_cover_hinge',[0,-.39,1.56],self.photo)
        photo_door=self.group('photograph_cover_face',parent=self.photo_cover);self.box('photo_protection_cover',[0,0,-.41],[1.33,.04,.82],'paint',photo_door);self.box('photo_cover_pull',[0,-.043,-.69],[.19,.045,.03],'brass',photo_door);self.reg_at('s3_cover',photo_door,'rope-latched case cover',[1.5,4.5],[.80,4.65,1.16])
        self.box('latch_mounting_stile',[.13,-.30,1.10],[.22,.08,.78],'wood',self.rack)
        self.box('latch_stand_off_bracket',[.10,-.37,.90],[.20,.15,.09],'iron',self.rack)
        self.box('rope_latch_receiver',[.04,-.445,.90],[.39,.080,.10],'iron',self.rack)
        self.rope_gate=self.group('rope_operated_case_bolt',[.26,-.456,.90],self.rack)
        self.box('visible_case_retaining_bolt',[0,0,0],[.32,.035,.050],'brass',self.rope_gate)
        self.tube('pulley_support_axle',[.18,-.34,1.38],[.18,-.445,1.38],.009,'steel',self.rack)
        self.cylinder('rope_link_pulley',[.18,-.445,1.38],.045,.025,'steel','y',self.rack,n=28)
        self.tube('rope_check_tie',[-.40,-.285,.84],[-.045,-.285,.84],.008,'rope_tan',self.rack)
        _defer(self,lambda:self.tube('rope_check_jog',[-.045,-.285,.84],[-.045,-.345,.84],.008,'rope_tan',self.rack))
        self.tube('rope_check_vertical_link',[-.045,-.345,.84],[-.045,-.345,1.38],.008,'rope_tan',self.rack)
        self.tube('visible_rope_link',[-.045,-.345,1.38],[.18,-.445,1.38],.008,'rope_tan',self.rack)
        self.tube('rope_into_latch',[.18,-.445,1.38],[.18,-.445,.90],.008,'rope_tan',self.rack)
        store=self.group('camping_gear_shelf',[4.20,3.0,0]);self.transform(store,rpy=[0,0,-90])
        for x in [-.72,.72]:self.box('gear_shelf_post',[x,0,.76],[.055,.40,1.52],'darkwood',store)
        for z in [.15,.75,1.43]:self.box('gear_shelf',[0,0,z],[1.52,.43,.04],'wood',store)
        self.box('gear_shelf_back',[0,.18,.76],[1.46,.035,1.48],'paint',store)
        for j,col in enumerate(['camp_green','sleeping_red']):
            n=self.group('fixed_camping_pack_'+str(j),[-.33+j*.66,0,.755],store);self.box('pack_body',[0,0,.18],[.38,.28,.33],col,n,bevel=.042);self.box('pack_top_flap',[0,-.025,.36],[.36,.30,.075],col,n,bevel=.023)
            for x in [-.105,.105]:self.box('pack_strap',[x,-.15,.18],[.028,.018,.31],'camp_paper',n)
        for j in range(2):self.cylinder('rolled_sleeping_mat',[-.34+j*.68,0,.265],.095,.45,'camp_blue','y',store,n=32)
        for j in range(3):self.cylinder('stored_tent_pole',[0,-.12+j*.12,1.462],.012,.85,'steel','x',store,n=20)
        self.add_obstacle(3.94,2.21,4.45,3.79)
        lantern=self.group('fixed_camp_lantern',[3.02,5.35,0]);self.cylinder('lantern_base',[0,0,.78],.073,.04,'iron','z',lantern,n=28);self.cylinder('lantern_globe',[0,0,.86],.054,.12,'camp_paper','z',lantern,n=28);self.cylinder('lantern_cap',[0,0,.943],.073,.035,'camp_green','z',lantern,n=28)
        for x in [-.057,.057]:self.tube('lantern_frame',[x,0,.80],[x,0,.935],.006,'iron',lantern)
        self.exit_node=self.door('camp_room_exit',[1.0,.06,0],1.04);self.reg_at('exit',self.exit_node,'exit door',[1.5,1.0],[1.52,.06,1.12]);self.door_view=[1.5,1.0]
        for x in [.98,2.06]:self.box('door_jamb',[x,.05,1.14],[.065,.17,2.30],'paint')
        self.box('door_lintel',[1.52,.05,2.29],[1.15,.17,.065],'paint')
        for x in [.99,2.05]:self.box('door_stop_jamb',[x,.01,1.14],[.035,.026,2.28],'darkwood')
        self.box('door_stop_top',[1.52,.01,2.28],[1.13,.026,.035],'darkwood')
        self.stage_views=[[2.25,4.25],[1.25,3.0],[1.5,4.5]];self.stage_centres=[[2.25,5.35,1.10],[.69,3.0,1.14],[.244,4.65,1.16]];self.bases=[([2.25,5.33],0),([.38,3.0],90),([.38,4.65],90)];self.sync(g)
    def visible(self,key,g):
        if key=='key_box':return bool(g.opened['s3_cover'])
        if key=='s1_tool':return key not in g.taken
        if key=='s2_tool':return bool(g.opened['s2_cover']) and key not in g.taken
        if key=='s2_clue' or key.startswith('s2_slot_') or key=='s2_confirm':return bool(g.states[1]['setup_open'])
        if key.startswith('s2_item_'):
            j=int(key.rsplit('_',1)[1]);placed=j in {int(v) for v in g.states[1]['assignment'].values()};return key not in g.holding and (placed or g.states[1]['setup_open'] and key not in g.taken)
        if key=='s3_clue' or key.startswith('s3_choice_') or key in ('s3_confirm','s3_reset'):return bool(g.opened['s3_cover'])
        if key=='key':return bool(g.opened['key_box']) and key not in g.taken
        return key in self.target_nodes
    def sync(self,g):
        lit=bool(g.states[0]['flash'])
        self.visibility(self.uv_layer,lit)
        with self.og.sim.editing_usd():self.uv_shader.GetInput('opacity').Set(1. if lit else 0.);self.uv_shader.GetInput('emissiveColor').Set(self.F.Vec3f(.18,.60,.15) if lit else self.F.Vec3f(0,0,0))
        self.visibility(self.uv,'s1_tool' not in g.taken);self.visibility(self.hook,'s2_tool' not in g.taken)
        n,p=self.drawers['hook_rod_drawer'];self.transform(n,[p[0],p[1]-(.42 if g.opened['s2_cover'] else 0),p[2]])
        opened=bool(g.states[1]['setup_open']);self.transform(self.curtain,[.66 if opened else 0,-.31,1.10])
        with self.og.sim.editing_usd():self.curtain_scale.Set(self.F.Vec3f(.15 if opened else 1,1,1))
        assignments={int(k):int(v) for k,v in g.states[1]['assignment'].items()}
        for j,node in enumerate(self.clips):
            slot=next((k for k,v in assignments.items() if v==j),None);point=self.slot_points[slot] if slot is not None else [[-.32,.072,.915],[0,.072,.915]][j]
            self.transform(node,[.38-point[1],3.0+point[0],point[2]],[0,0,90]);self.visibility(node,'s2_item_'+str(j) not in g.holding)
        self.transform(self.photo_cover,rpy=[-160 if g.opened['s3_cover'] else 0,0,0])
        for index,shader in self.screens.items():
            signature=(tuple(g.states[index]['buffer']),bool(g.solved[index]))
            if self.screen_signatures.get(index)!=signature:
                with self.og.sim.editing_usd():shader.GetInput('file').Set(str(self.screen_file(index,*signature)))
                self.screen_signatures[index]=signature
        self.transform(self.rope_gate,[.03 if g.solved[1] else .26,-.456,.90])
        self.transform(self.key_lid,rpy=[-110 if g.opened['key_box'] else 0,0,0])
        self.transform(self.case_latches[1],[0,-.166,.038],rpy=[0,0,28 if g.solved[2] else 0])
        self.visibility(self.key,'key' not in g.taken);self.transform(self.exit_node,rpy=[0,0,-103 if g.opened['exit'] else 0])
        self.expanded=[]
        for flag,node in [(g.opened['s2_cover'],self.hookdrawer),(g.opened['s3_cover'],self.photo_cover),(g.opened['key_box'],self.key_lid)]:
            if flag:
                points=self.triangles(node).reshape(-1,3);self.expanded.append((points.min(0)[:2]-.12,points.max(0)[:2]+.12))
        self.centres={}
        for key,node in self.target_nodes.items():
            points=self.triangles(node).reshape(-1,3)
            if points.size:self.centres[key]=((points.min(0)+points.max(0))/2).tolist()
    def candidates(self,g):return self.base_candidates([k for k in self.target_nodes if self.visible(k,g)])
    def blocked(self,x,y,g):return super().blocked(x,y,g) or any(lo[0]<x<hi[0] and lo[1]<y<hi[1] for lo,hi in self.expanded)
    def view_for(self,key):return self.views.get(key,[1.5,1.0])
    def focus_for(self,key):return self.focus.get(key,self.centres.get(key))
    def label_for(self,key):return self.labels.get(key,LABELS.get(key,key.replace('_',' ')))
    def animate(self,d,before):
        if d.game.states[0]['flash']:
            self.sync(d.game);d.frame(warm=12);d.append('Ultraviolet light reveals the route marks',24);d.capture_feedback_frame()
            d.game.states[0]['flash']=False;self.sync(d.game);d.frame(warm=12);d.append('Ordinary view after the UV torch switches off',12)
        old=before.get('opened',{})
        for key,name in [('s2_cover','hook_rod_drawer')]:
            if bool(old.get(key))!=bool(d.game.opened[key]):
                n,p=self.drawers[name]
                for q in [.33,.67]:
                    t=float(bool(old.get(key)))+(float(bool(d.game.opened[key]))-float(bool(old.get(key))))*q;self.sync(d.game);self.transform(n,[p[0],p[1]-.42*t,p[2]]);d.frame(warm=4);d.append('Equipment drawer opens',4)
        was=before['states'][1]['setup_open'];now=d.game.states[1]['setup_open']
        if bool(was)!=bool(now):
            for q in [.33,.67]:
                t=float(bool(was))+(float(bool(now))-float(bool(was)))*q;self.sync(d.game);self.transform(self.curtain,[.66*t,-.31,1.10])
                with self.og.sim.editing_usd():self.curtain_scale.Set(self.F.Vec3f(1-.85*t,1,1))
                d.frame(warm=4);d.append('The hook draws the pleated curtain aside',4)
        if not before['solved'][1] and d.game.solved[1]:
            for q in [.33,.67,1.0]:
                self.sync(d.game);self.transform(self.rope_gate,[.26-.23*q,-.456,.90]);d.frame(warm=4);d.append('The rope linkage retracts the bolt on the adjacent case bay',5)
        if bool(old.get('key_box'))!=bool(d.game.opened['key_box']):
            for q in [.33,.67]:
                t=float(bool(old.get('key_box')))+(float(bool(d.game.opened['key_box']))-float(bool(old.get('key_box'))))*q;self.sync(d.game);self.transform(self.key_lid,rpy=[-110*t,0,0]);d.frame(warm=4);d.append('The selected blue camp case opens',4)
        if bool(old.get('s3_cover'))!=bool(d.game.opened['s3_cover']):
            for q in [.33,.67]:
                t=float(bool(old.get('s3_cover')))+(float(bool(d.game.opened['s3_cover']))-float(bool(old.get('s3_cover'))))*q;self.sync(d.game);self.transform(self.photo_cover,rpy=[-160*t,0,0]);d.frame(warm=4);d.append('Camp photograph cover opens',4)
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

    approach('s1_tool','Approach the UV torch');click('s1_tool','take')
    observe('s1_setup','Observe the ordinary camp map before illuminating it');click('s1_setup','use','s1_tool')
    approach('s1_choice_4','Look at the map case input',stay=True)
    for j in [4,3,4]:click('s1_choice_'+str(j))
    click('s1_confirm');approach('s2_cover','Look into the unlocked hook drawer');click('s2_cover','open');d.append('Observe the short hook resting on its pad',18);click('s2_tool','take')
    approach('s2_setup','Approach the protective curtain');click('s2_setup','use','s2_tool')
    observe('s2_clue','Trace the two real ropes to the numbered pegs',stay=True)
    for j in range(2):click('s2_item_'+str(j),'take')
    click('s2_slot_1','use','s2_item_0');click('s2_slot_3','use','s2_item_1');click('s2_confirm')
    approach('s3_cover','Follow the visible rope linkage to the released adjacent case bay');click('s3_cover','open')
    observe('s3_clue','Compare the three case labels and the one-true-label rule',stay=True);click('s3_clue','read')
    approach('s3_choice_1','Release the case that makes exactly one label true',stay=True);click('s3_choice_1')
    approach('key_box','Open the blue case after its latch releases',stay=True);click('key_box','open');d.append('Observe the flat brass key in the actual blue case',18);click('key','take')
    approach('exit','Return to the exit');click('exit','use','key');click('exit','open')
    if not exit_test(d.pos,g):raise RuntimeError('Open-door success was not reached')

def cpu_check():
    from easy88_core import stage_actions
    g=Game();checks=[]
    def act(kind,key,**kw):return g.act(dict(action=kind,_validated364=True,_hit364=key,**kw))
    assert not act('open','key_box')['ok'];checks.append('real key case locked before logic solution')
    assert not act('press','s3_choice_1')['ok'];checks.append('cannot select hidden case latch through the closed cover')
    for i in [0,1]:
        for kind,key,extra in stage_actions(g,i):assert act(kind,key,**extra)['ok'],(kind,key)
    assert g.solved[1] and not g.opened['s3_cover'];checks.append('rope arrangement retracts a local bolt, without auto-opening the cover')
    assert act('open','s3_cover')['ok'];r=act('read','s3_clue');assert r['ok'] and r['text']==SPEC['stages'][2]['clue_text'];checks.append('one-true rule and every label are self-contained read feedback')
    solutions=[j for j in range(3) if sum(case_label_truths(j))==1];assert solutions==[1];checks.append('exhaustive3-case truth table has one legal case')
    assert not act('press','s3_choice_0')['ok'];assert not act('press','s3_choice_2')['ok'];assert not g.solved[2];checks.append('wrong assumptions do not release key case and remain recoverable')
    assert not act('press','s3_confirm')['ok'];assert not act('press','s3_choice_4')['ok'];checks.append('obsolete six-symbol sequence unavailable')
    assert act('press','s3_choice_1')['ok'];assert g.solved[2] and not g.opened['key_box'];checks.append('correct logical case releases its latch, lid remains manual')
    for kind,key,extra in [('open','key_box',{}),('take','key',{}),('use','exit',{'item':'key'}),('open','exit',{})]:assert act(kind,key,**extra)['ok']
    assert g.exited;checks.append('manual case open key take door use open completes')
    return dict(level='R15',scope='CPU state-machine and exhaustive truth table; no SDK/native pixels/API',passed=len(checks),checks=checks)

_aff_build_last(Scene)
