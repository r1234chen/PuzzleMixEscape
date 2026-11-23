import math
import numpy as np
from PIL import Image,ImageDraw
from easy88_core import make_level,reachable_approach
from easy88_scene import EasyScene
from font_utils import load_font

SPEC={'id':'R18','title':'Book Repair Room','chinese_title':'书籍修补间','theme':'books',
'size':[4.5,5.5],'door':{'side':'east','start':1.0,'width':1.04},
'start':[3.5,1.5,1.35],'start_yaw':180,'floor':'wood',
'stages':[
{'kind':'sequence','name':'shelf number order','options':['30','10','40','20'],'answer':[1,3,0,2],'length':4,'distinct':True,'clue_text':'','wall':'west'},
{'kind':'half_code','name':'torn accession slip','answer':'2675','clue_text':'','wall':'north'},
{'kind':'page_code','name':'missing leaf book','answer':'1516','clue_text':'','wall':'east'}]}
BOOKLET_NOTE='Booklet: 1–12.\nA folded leaf surrounds those inside it.\nOutside → Inside.'
FOLIO_PAIRS=[(10,3),(8,5),(12,1),(11,4)]
SPEC['stages'][0]={'kind':'assign','name':'continuous branch book spines','wall':'west',
 'items':[{'id':'rise','name':'rising branch book'},{'id':'root','name':'root branch book'},{'id':'tip','name':'leaf tip book'},{'id':'fork','name':'fork branch book'}],
 'slots':4,'target':[1,3,0,2],'auto':False,'clue':{'type':'continuous_book_spine_picture'},'clue_text':'JOIN THE BRANCH'}
SPEC['stages'][1].update(name='folded folio collation',items=[{'id':'leaf_'+str(j),'name':'folded leaf '+str(pair[0])+'/'+str(pair[1])} for j,pair in enumerate(FOLIO_PAIRS)],slots=1,
 clue={'type':'folio_nesting','booklet_pages':12,'pairs':FOLIO_PAIRS,'order':'outside_to_inside','three_valid_leaves':True},clue_text='')
Game,_OldScene,_OldStandard,exit_test,cpu_check=make_level(SPEC)
TITLE=SPEC['title'];LEVEL_ID=SPEC['id'];START=SPEC['start'];START_YAW=SPEC['start_yaw']
CAP=150;OBSERVATION_SIZE=(640,360);VISUAL_ONLY=False;READ_ENABLED=True;READ_FEEDBACK_TEXT=True
Game.LABELS.update({'s1_clue':'four shelf numbers','s1_confirm':'order check','s1_reset':'clear order',
's2_cover':'accession folder cover','s2_clue':'two torn slip halves','s2_lock':'book case lock',
's3_cover':'book case cover','s3_clue':'missing leaf book','s3_lock':'front back page lock',
'key_box':'book shaped key box','key':'brass door key'})
Game.LABELS.update({'s1_clue':'continuous branch across book spines','s1_confirm':'book rack latch check',
 's2_cover':'lower book-rack folio compartment','s2_note':'booklet collation note','s2_slot_0':'folded-leaf cradle','s2_stack':'top leaf of the collation stack','s2_clue':'joined accession mark on leaf edges'})
LABELS=Game.LABELS
_act=Game.act
def book_act(self,a):
    k=a.get('_hit364');kind=a.get('action')
    r=_act(self,a)
    if a.get('_validated364') and kind=='unlock' and k in ('s2_lock','s3_lock'):
        self.states[int(k[1])-1]['entered_code']=str(a.get('code',''))
    return r
Game.act=book_act
_book_init=Game.__init__
def _collation_init(self):
    _book_init(self);self.states[0]['assignment']={j:j for j in range(4)};self.states[1]['collation']=[];self.states[1]['collated']=False
Game.__init__=_collation_init
Game.stage_accessible=lambda self,index:0<=index<3
Game.stage_exposed=lambda self,index:0<=index<3 and bool(self.states[index]['setup_ready'])
_collation_base=Game.act

def collation_valid(order):
    return len(order)==3 and len(set(order))==3 and all(sum(FOLIO_PAIRS[j])==13 for j in order) and [min(FOLIO_PAIRS[j]) for j in order]==[1,3,5]

def _collation_act(self,a):
    key=str(a.get('_hit364',''));kind=a.get('action');state=self.states[1]
    if a.get('_validated364') and key=='s2_note':
        from action_feedback import failure_for
        return {'ok':True,'text':BOOKLET_NOTE} if kind=='read' and self.opened['s2_cover'] else {'ok':False,'text':failure_for(kind)}
    if a.get('_validated364') and key.startswith('s2_item_'):
        from action_feedback import failure_for
        j=int(key.rsplit('_',1)[1]);order=state['collation']
        if kind=='read' and (self.opened['s2_cover'] or j in order or key in self.holding):return {'ok':True,'text':str(FOLIO_PAIRS[j][0])+' | '+str(FOLIO_PAIRS[j][1])}
        if kind!='take' or key in self.holding:return {'ok':False,'text':failure_for(kind)}
        if j in order:
            if order[-1]!=j:return {'ok':False,'text':failure_for(kind)}
            order.pop()
        elif key in self.taken or not self.opened['s2_cover']:return {'ok':False,'text':failure_for(kind)}
        self.taken.add(key);self.holding.append(key);state['collated']=collation_valid(order);return {'ok':True,'text':''}
    if a.get('_validated364') and key=='s2_stack':
        from action_feedback import failure_for
        if kind!='take' or not state['collation']:return {'ok':False,'text':failure_for(kind)}
        j=state['collation'].pop();self.holding.append('s2_item_'+str(j));state['collated']=collation_valid(state['collation']);return {'ok':True,'text':''}
    if a.get('_validated364') and key=='s2_slot_0':
        from action_feedback import failure_for,NO_ITEM
        if kind!='use':return {'ok':False,'text':failure_for(kind)}
        item=self._resolve_item(a.get('item'))
        if item is None:return {'ok':False,'text':NO_ITEM}
        if item not in ['s2_item_'+str(j) for j in range(4)] or len(state['collation'])>=3:return {'ok':False,'text':failure_for(kind)}
        state['collation'].append(int(item[-1]));self.holding.remove(item);state['collated']=collation_valid(state['collation']);return {'ok':True,'text':''}
    if a.get('_validated364') and key=='s2_clue' and kind=='read':
        from action_feedback import failure_for
        return {'ok':True,'text':'2675'} if state['collated'] else {'ok':False,'text':failure_for(kind)}
    return _collation_base(self,a)
Game.act=_collation_act

class Scene(EasyScene):
    def __init__(self,og,run):
        super().__init__(og,run,SPEC)
        self.views={};self.focus={};self.labels={};self.drawers={};self.lock_shaders={};self.lock_values={};self.expanded=[];self.books=[];self.book_slots=[];self.folios=[];self.placed_folios=[]
    def palette(self):
        super().palette()
        self.mat('paper_cream',(.78,.74,.63),rough=.95)
        self.mat('book_red',(.36,.16,.12),rough=.9)
        self.mat('book_blue',(.18,.29,.34),rough=.9)
        self.mat('felt',(.23,.32,.27),rough=.96)
    def reg_at(self,key,node,label,view,focus=None):
        self.reg(key,node);self.views[key]=list(view);self.labels[key]=label
        if focus is not None:self.focus[key]=list(focus)
        return node
    def flat(self,name,parent,pos,w,h,im,horizontal=False):
        path=self.tex/(name+'.png');im.save(path)
        return self.plane(name,pos,w,h,(1,0,0),(0,1,0) if horizontal else (0,0,1),None,parent,material=self.image_mat('r18_'+name,path))
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
        mat=self.mats['r18_'+key+'_display']
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

    def mark_button(self,key,parent,pos,glyph,view,size=.105):
        n=self.group(key,pos,parent)
        self.box('pressed_cap',[0,0,0],[size,.035,size],'iron',n)
        self.text(key+'_glyph',n,[0,-.019,0],size*.86,size*.86,glyph)
        return self.reg_at(key,n,LABELS.get(key,glyph),view)
    def case(self,name,origin,w,depth,height,parent=None):
        n=self.group(name,origin,parent)
        for x in [-w/2,w/2]:self.box('case_side',[x,0,height/2],[.035,depth,height],'wood',n)
        self.box('case_bottom',[0,0,.015],[w,depth,.03],'wood',n)
        self.box('case_back',[0,depth/2-.015,height/2],[w,.03,height],'wood',n)
        lid=self.group(name+'_lid',[0,depth/2,height],n)
        self.box('lid_board',[0,-depth/2,0],[w+.05,depth+.03,.035],'book_blue',lid)
        self.box('lid_handle',[0,-depth+.06,.027],[.17,.035,.025],'brass',lid)
        return n,lid
    def spine_picture(self):
        im=Image.new('RGB',(1200,480),(219,211,180));d=ImageDraw.Draw(im)
        d.line([(0,425),(180,330),(370,290),(580,310),(820,165),(1030,190),(1199,58)],fill=(93,62,35),width=22)
        d.line([(0,40),(300,140),(600,55),(900,350),(1199,160)],fill=(43,83,90),width=16)
        for x,y in [(155,345),(455,300),(760,200),(1080,150)]:
            d.ellipse((x-37,y-75,x+5,y-18),fill=(57,92,50));d.line((x-14,y-18,x+3,y+10),fill=(93,62,35),width=8)
        return im
    def folio(self,name,parent,pos,j):
        node=self.group(name,pos,parent)
        self.box('folded_paper_signature',[0,0,0],[.235,.27,.030],'paper_cream',node)
        self.box('actual_folded_spine',[0,.132,0],[.235,.010,.034],'paper_cream',node)
        label=self.text_image(str(FOLIO_PAIRS[j][0])+' | '+str(FOLIO_PAIRS[j][1]),.215,.20)
        self.flat(name+'_page_numbers',node,[0,0,.016],.215,.20,label,True)
        im=self.text_image('2675' if j<3 else '8194',.235,.093,(226,220,191),(35,55,45))
        band={0:1,1:0,2:2,3:1}[j];h=im.height
        self.flat(name+'_edge_fragment',node,[0,-.136,0],.235,.031,im.crop((0,band*h//3,im.width,(band+1)*h//3)))
        return node
    def build(self,g):
        self.room_shell('book_repair',size=(4.5,5.5),openings={'east':[(.98,2.08)]})
        self.box('continuous_subfloor',[2.25,2.75,-.06],[4.65,5.65,.10],'darkwood')
        self.rack=self.group('low_binding_rack',[.28,2.8,0]);self.transform(self.rack,rpy=[0,0,90])
        for x in [-.77,.77]:
            self.box('rack_post',[x,0,.64],[.055,.42,1.28],'darkwood',self.rack)
        self.box('rack_back',[0,.18,.72],[1.52,.03,1.12],'paint',self.rack)
        for z in [.18,.72,1.29]:self.box('rack_shelf',[0,0,z],[1.65,.46,.035],'wood',self.rack)
        picture=self.spine_picture()
        for j in range(4):
            x=(j-1.5)*.31
            book=self.group('fixed_order_book_'+str(j),[x,0,.97],self.rack)
            self.box('book_pages',[0,.005,0],[.22,.24,.45],'paper_cream',book)
            for xx in [-.116,.116]:self.box('book_cover',[xx,0,0],[.012,.26,.48],'book_red' if j%2 else 'book_blue',book)
            self.box('book_spine',[0,-.13,0],[.24,.018,.48],'book_red' if j%2 else 'book_blue',book)
            target_position=SPEC['stages'][0]['target'].index(j)
            self.flat('book_spine_branch_'+str(j),book,[0,-.141,0],.215,.43,picture.crop((target_position*300,0,(target_position+1)*300,480)))
            self.reg_at('s1_item_'+str(j),book,LABELS['s1_item_'+str(j)],[1.25,2.75]);self.books.append(book)
            slot=self.group('empty_book_recess_'+str(j),[x,.153,.97],self.rack)
            self.box('book_recess_back',[0,0,0],[.25,.012,.46],'felt',slot);self.book_slots.append(slot)
            self.reg_at('s1_slot_'+str(j),slot,'empty book recess',[1.25,2.75])
        self.text('spine_join_hint',self.rack,[0,-.247,.48],.72,.09,'JOIN THE BRANCH')
        self.mark_button('s1_confirm',self.rack,[.63,-.245,.48],'✓',[1.25,2.75])
        self.reg_at('s1_clue',self.rack,'continuous book-spine branch',[1.25,2.75],[.48,2.8,.93])
        self.add_obstacle(.05,1.92,.66,3.68)

        self.table('repair_bench',(2.25,5.05),(2.9,.67),height=.72)
        self.folder,self.folder_lid=self.case('accession_folder',[0,0,.20],1.22,.37,.105,self.rack)
        self.reg_at('s2_cover',self.folder_lid,'lower book-rack folio compartment',[1.25,2.75],[.28,2.8,.31])
        note=self.group('booklet_note',[0,-.19,-.019],self.folder_lid);self.transform(note,rpy=[180,0,0])
        im=Image.new('RGB',(1100,300),(230,222,195));dr=ImageDraw.Draw(im)
        dr.text((45,15),'Booklet: 1–12.',font=load_font(64),fill=(35,55,45))
        dr.text((45,105),'A folded leaf surrounds those inside it.',font=load_font(44),fill=(35,55,45))
        dr.text((45,205),'Outside → Inside.',font=load_font(57),fill=(35,55,45))
        self.flat('booklet_note_print',note,[0,0,0],1.04,.28,im,True);self.reg_at('s2_note',note,'booklet collation note',[1.25,2.75],[.114,2.8,.495])
        for j in range(4):
            node=self.folio('loose_folded_leaf_'+str(j),self.folder,[(j-1.5)*.285,-.045,.037],j)
            self.folios.append(node);self.reg_at('s2_item_'+str(j),node,LABELS['s2_item_'+str(j)],[1.25,2.75])
        self.rack_bolt=self.group('local_folio_bolt',[.43,-.204,.285],self.rack);self.box('folder_bolt',[0,0,0],[.19,.025,.025],'steel',self.rack_bolt)
        self.rack_red=self.cylinder('folio_release_red',[.64,-.211,.36],.015,.010,'red_led','y',self.rack,n=24)
        self.rack_green=self.cylinder('folio_release_green',[.64,-.211,.36],.015,.010,'green','y',self.rack,n=24)

        self.bookcase,self.bookcase_lid=self.case('single_book_clamp',[3.02,5.03,.755],1.15,.50,.12)
        self.reg_at('s3_cover',self.bookcase_lid,'book case cover',[3.0,4.0],[3.02,5.0,.91])
        self.numeric_lock('s2_lock',self.bookcase,[0,-.273,.055],4,[3.0,4.0])
        self.cradle=self.group('folded_leaf_cradle',[0,-.25,.020],self.bookcase_lid)
        self.box('folio_cradle_board',[0,0,0],[.76,.31,.006],'wood',self.cradle)
        for x in [-.148,.148]:self.box('folio_stack_side',[x,0,.057],[.020,.29,.114],'wood',self.cradle)
        self.box('booklet_size_tag_back',[-.28,-.09,.038],[.19,.016,.065],'wood',self.cradle)
        self.text('folio_cradle_identity',self.cradle,[-.28,-.099,.038],.17,.045,'1–12')
        insert=self.group('folio_insertion_point',[.24,0,.056],self.cradle)
        self.box('cradle_grip',[0,0,0],[.11,.09,.09],'wood',insert)
        self.reg_at('s2_slot_0',insert,'folded-leaf cradle',[3.0,4.0],[3.02,5.03,.95])
        for j in range(4):self.placed_folios.append(self.folio('nested_folded_leaf_'+str(j),self.cradle,[0,0,.018],j))
        self.reg_at('s2_clue',self.cradle,'joined accession mark on leaf edges',[3.0,4.0],[3.02,4.89,.94])
        self.box('bookbinding_spine',[0,.01,.048],[.045,.39,.030],'book_red',self.bookcase)
        for j,num in enumerate([14,17]):
            x=(j-.5)*.47
            self.box('page_block',[x,.01,.042],[.43,.38,.050],'paper_cream',self.bookcase)
            im=Image.new('RGB',(600,540),(229,222,196));dr=ImageDraw.Draw(im)
            for y in range(80,350,48):dr.line((65,y,530,y),fill=(164,154,126),width=3)
            dr.text((300,443),str(num),font=load_font(98),fill=(38,52,44),anchor='mm')
            self.flat('open_page_'+str(num),self.bookcase,[x,.01,.070],.42,.37,im,True)
        for y in [-.13,-.06,.01,.08,.15]:
            self.box('torn_missing_leaf_stub',[0,y,.075],[.031,.023,.012],'paper_cream',self.bookcase)
        self.reg_at('s3_clue',self.bookcase,'one missing leaf between pages 14 and 17',[3.0,4.0],[3.02,5.03,.83])
        self.keydrawer,keyfront=self.drawer('book_key_drawer',None,(3.02,4.72),.54,1.05,.43)
        self.reg_at('key_box',keyfront,'book shaped key box',[3.0,4.0],[3.02,4.72,.54])
        self.numeric_lock('s3_lock',keyfront,[.06,-.044,.016],4,[3.0,4.0])
        self.text('page_format',keyfront,[.06,-.064,-.093],.38,.048,'FRONT / BACK  XXYY')
        self.box('key_felt_pad',[0,.21,-.025],[.94,.34,.15],'felt',self.keydrawer)
        self.key=self.tool('flat_brass_key',self.keydrawer,[0,.21,.065],'key')
        self.target_nodes.pop('flat_brass_key',None);self.transform(self.key,rpy=[90,0,0])
        self.reg_at('key',self.key,'brass door key',[3.0,4.0])
        self.add_obstacle(.72,4.65,3.77,5.45)

        stock=self.group('repair_stock',[4.23,3.58,0]);self.transform(stock,rpy=[0,0,-90])
        for x in [-.52,.52]:self.box('stock_leg',[x,0,.54],[.05,.42,1.08],'darkwood',stock)
        for z in [.17,.73,1.08]:self.box('stock_shelf',[0,0,z],[1.15,.45,.035],'wood',stock)
        for j in range(3):
            for k in range(2):self.box('stacked_repair_book',[(j-1)*.32,0,.22+k*.065],[.27,.28,.06],'book_red' if j%2 else 'book_blue',stock)
        for x in [-.30,0,.30]:
            self.cylinder('rolled_repair_paper',[x,0,.84],.065,.18,'paper_cream','z',stock)
        self.add_obstacle(3.91,2.97,4.47,4.19)
        self.exit_node=self.door('book_exit',[4.44,1.02,0],1.04);self.door_angle=90
        self.door_view=[3.5,1.5];self.reg_at('exit',self.exit_node,'exit door',self.door_view,[4.44,1.54,1.12])
        for y in [1.0,2.08]:self.box('door_jamb',[4.45,y,1.14],[.17,.065,2.30],'paint')
        self.box('door_top',[4.45,1.54,2.29],[.17,1.15,.065],'paint')
        self.stage_views=[[1.25,2.75],[1.5,4.0],[3.0,4.0]]
        self.stage_centres=[[.4,2.8,.95],[3.02,4.89,.94],[3.02,5.03,.83]]
        self.bases=[([.28,2.8],90),([1.48,5.03],0),([3.02,5.03],0)]
        self.sync(g)
    def visible(self,key,g):
        if key.startswith('s1_item_'):return key not in g.holding
        if key.startswith('s1_slot_'):return int(key[-1]) not in {int(k) for k in g.states[0]['assignment']}
        if key=='s2_note':return bool(g.opened['s2_cover'])
        if key.startswith('s2_item_'):
            j=int(key[-1]);order=g.states[1]['collation']
            return not g.opened['s3_cover'] and (bool(order) and order[-1]==j or j not in order and g.opened['s2_cover'] and key not in g.taken)
        if key=='s2_stack':return bool(g.states[1]['collation']) and not g.opened['s3_cover']
        if key=='s2_clue':return bool(g.states[1]['collated']) and not g.opened['s3_cover']
        if key=='s3_clue':return bool(g.opened['s3_cover'])
        if key=='key':return bool(g.opened['key_box']) and key not in g.taken
        return key in self.target_nodes
    def sync(self,g):
        self.transform(self.folder_lid,rpy=[-90 if g.opened['s2_cover'] else 0,0,0])
        self.transform(self.bookcase_lid,rpy=[-100 if g.opened['s3_cover'] else 0,0,0])
        assignment={int(k):int(v) for k,v in g.states[0]['assignment'].items()}
        for j,node in enumerate(self.books):
            slot=next((k for k,v in assignment.items() if v==j),j)
            self.transform(node,[(slot-1.5)*.31,0,.97]);self.visibility(node,'s1_item_'+str(j) not in g.holding)
        self.transform(self.rack_bolt,[.43+(.16 if g.solved[0] else 0),-.204,.285])
        self.visibility(self.rack_red,not g.solved[0]);self.visibility(self.rack_green,g.solved[0])
        order=g.states[1]['collation']
        for j,(loose,nested) in enumerate(zip(self.folios,self.placed_folios)):
            placed=j in order
            self.visibility(loose,not placed and 's2_item_'+str(j) not in g.holding)
            self.visibility(nested,placed)
            if placed:self.transform(nested,[0,0,.018+.031*order.index(j)])
            active=nested if placed else loose;self.target_nodes['s2_item_'+str(j)]=active
            self.views['s2_item_'+str(j)]=[3.0,4.0] if placed else [1.25,2.75]
        if order:self.target_nodes['s2_stack']=self.placed_folios[order[-1]];self.views['s2_stack']=[3.0,4.0]
        for key,shader in self.lock_shaders.items():
            value=g.states[int(key[1])-1].get('entered_code','0000')
            if self.lock_values[key]!=value:
                path=self.tex/(key+'_entered_'+str(value)+'.png')
                self.text_image(value,.27,.088,(47,67,56),(224,228,191)).save(path)
                with self.og.sim.editing_usd():shader.GetInput('file').Set(str(path))
                self.lock_values[key]=value
        node,p=self.drawers['book_key_drawer'];self.transform(node,[p[0],p[1]-(.42 if g.opened['key_box'] else 0),p[2]])
        self.visibility(self.key,'key' not in g.taken)
        self.transform(self.exit_node,rpy=[0,0,self.door_angle-(103 if g.opened['exit'] else 0)])
        self.centres={}
        for key,node in self.target_nodes.items():
            p=self.triangles(node).reshape(-1,3)
            if p.size:self.centres[key]=((p.min(0)+p.max(0))/2).tolist()
    def candidates(self,g):return self.base_candidates([k for k in self.target_nodes if self.visible(k,g)])
    def view_for(self,key):return self.views.get(key,self.door_view)
    def focus_for(self,key):return self.focus.get(key,self.centres.get(key))
    def label_for(self,key):return self.labels.get(key,LABELS.get(key,key.replace('_',' ')))
    def animate(self,d,before):
        for key,node in [('s2_cover',self.folder_lid),('s3_cover',self.bookcase_lid)]:
            old=bool(before['opened'].get(key));now=bool(d.game.opened[key])
            if old!=now:
                for q in [.33,.67]:
                    self.transform(node,rpy=[-(90 if key=='s2_cover' else 100)*(old+(now-old)*q),0,0]);d.frame(warm=4);d.append('Folder opens',4)
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

    observe('s1_clue','Join the branch printed across the actual book spines')
    for j in range(4):click('s1_item_'+str(j),'take')
    for slot,item in enumerate([1,3,0,2]):click('s1_slot_'+str(slot),'use','s1_item_'+str(item))
    click('s1_confirm')
    approach('s2_cover','The released folio compartment is directly below the repaired spines',stay=True);click('s2_cover','open')
    approach('s2_note','Read the small booklet collation note',stay=True);click('s2_note','read')
    for j in [2,0,1]:
        approach('s2_item_'+str(j),'Take one folded leaf belonging to the twelve-page booklet',stay=True);click('s2_item_'+str(j),'take')
    approach('s2_slot_0','Use the folded leaves on the twelve-page cradle beside the book-clamp lock')
    for j in [2,0,1]:click('s2_slot_0','use','s2_item_'+str(j))
    observe('s2_clue','The three real edge fragments now join into the accession mark',stay=True)
    approach('s2_lock','Use the accession mark on the same book clamp',stay=True);click('s2_lock','unlock',code='2675');click('s3_cover','open')
    observe('s3_clue','Observe the two page numbers and the missing whole leaf',stay=True)
    approach('s3_lock','Use front then back page order',stay=True);click('s3_lock','unlock',code='1516')
    approach('key_box','Open the unlocked book-shaped key drawer',stay=True);click('key_box','open')
    d.append('Observe the flat brass key',18);click('key','take')
    approach('exit','Return to the exit');click('exit','use','key');click('exit','open')
    if not exit_test(d.pos,g):raise RuntimeError('Open-door success was not reached')


def cpu_check():
    import itertools
    checks=[];g=Game()
    def a(kind,key,**kw):return g.act(dict(action=kind,_hit364=key,_validated364=True,**kw))
    def ck(name,x):assert x,name;checks.append(name)
    ck('no number-key solution remains',not a('press','s1_choice_1')['ok'])
    ck('local folio compartment initially locked',not a('open','s2_cover')['ok'])
    for j in range(4):ck('take physical spine book '+str(j),a('take','s1_item_'+str(j))['ok'])
    for slot,item in enumerate([1,3,0,2]):ck('place spine book '+str(item),a('use','s1_slot_'+str(slot),item='s1_item_'+str(item))['ok'])
    ck('whole spine picture releases local compartment',a('press','s1_confirm')['ok'] and g.solved[0] and not g.opened['s2_cover'])
    ck('separate folio cover open',a('open','s2_cover')['ok'])
    ck('literal self-contained folio instruction',a('read','s2_note')['text']==BOOKLET_NOTE)
    valid=[x for x in itertools.permutations(range(4),3) if collation_valid(x)]
    ck('one pagination/nesting solution among 24',valid==[(2,0,1)])
    for j in [3,0,1,2]:ck('candidate leaf can be taken '+str(j),a('take','s2_item_'+str(j))['ok'])
    for j in [3,0,1]:ck('wrong placement is allowed and editable',a('use','s2_slot_0',item='s2_item_'+str(j))['ok'])
    ck('wrong stack cannot read full code',not a('read','s2_clue')['ok'] and not g.states[1]['collated'])
    for _ in range(3):ck('top leaf returns to inventory',a('take','s2_stack')['ok'])
    for j in [2,0,1]:ck('nest correct folded leaf '+str(j),a('use','s2_slot_0',item='s2_item_'+str(j))['ok'])
    ck('joined edge code now literally readable',a('read','s2_clue')['text']=='2675')
    ck('assembly does not auto-open the book clamp',not g.solved[1] and not g.opened['s3_cover'])
    ck('wrong code rejected',not a('unlock','s2_lock',code='0000')['ok'])
    ck('same clamp accepts observed code',a('unlock','s2_lock',code='2675')['ok'] and a('open','s3_cover')['ok'])
    ck('missing whole leaf front/back inference',a('unlock','s3_lock',code='1516')['ok'])
    ck('open local key drawer',a('open','key_box')['ok']);ck('take actual key',a('take','key')['ok']);ck('use exit key',a('use','exit',item='key')['ok']);ck('exit open wins',a('open','exit')['ok'] and g.exited)
    return {'level':'R18','scope':'CPU actual Game class, native visual pending','passed':len(checks),'checks':checks}
