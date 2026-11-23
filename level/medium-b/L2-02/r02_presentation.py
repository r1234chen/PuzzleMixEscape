from types import MethodType
from pathlib import Path
import json,sys
NOTE='Press a panel to rotate it 90°.'
BENCH_TOP=.58
DROP=.20
SCREEN_GAIN=.65
REVISION='R02_low_case_image_lit_note_sealed_shell_v2'

def install(scene):
    original_table=scene.table;original_mat=scene.mat;original_build=scene.build;original_sync=scene.sync;original_candidates=scene.candidates
    def table(self,key,center=(3,3),size=(1.6,.7),height=.9):
        if key=='north_bench':height=BENCH_TOP-.04
        return original_table(key,center,size,height)
    def material(self,name,*args,**kwargs):
        image_panel=name.startswith('tile_') and name.endswith('_translucent')
        if not image_panel:return original_mat(name,*args,**kwargs)
        kwargs=dict(kwargs,rough=1.,emission=None)
        result=original_mat(name,*args,**kwargs)
        with self.og.sim.editing_usd():
            surface=self.S.Shader(self.stage.GetPrimAtPath(str(result.GetPath())+'/surface'))
            texture=self.S.Shader(self.stage.GetPrimAtPath(str(result.GetPath())+'/texture'))
            surface.GetInput('diffuseColor').DisconnectSource()
            surface.GetInput('diffuseColor').Set(self.F.Vec3f(0,0,0))
            surface.CreateInput('useSpecularWorkflow',self.D.ValueTypeNames.Int).Set(1)
            surface.CreateInput('specularColor',self.D.ValueTypeNames.Color3f).Set(self.F.Vec3f(0,0,0))
            texture.CreateInput('sourceColorSpace',self.D.ValueTypeNames.Token).Set('sRGB')
            texture.CreateInput('scale',self.D.ValueTypeNames.Float4).Set(self.F.Vec4f(SCREEN_GAIN,SCREEN_GAIN,SCREEN_GAIN,1))
            surface.CreateInput('emissiveColor',self.D.ValueTypeNames.Color3f).ConnectToSource(texture.ConnectableAPI(),'rgb')
        return result
    def sync(self,g,blend=None):
        original_sync(g,blend)
        if hasattr(self,'case'):
            self.transform(self.case,[0,0,-DROP])
            self.transform(self.lock,[1.90,4.49,.945])
            self.transform(self.lid,[1.65,5.015,1.055-DROP])
            self.transform(self.key,[1.65,4.85,.865-DROP],[90,0,0])
    def build(self,g):
        original_build(g)
        self.box('studio_solid_subfloor',[2.60,2.60,-.075],[5.34,5.34,.10],'darkwood',bevel=.001)
        self.sealed_door_frame=self.group('sealed_door_frame')
        for yy in [.65,1.75]:
            self.box('door_jamb_core',[.03,yy,1.1675],[.24,.06,2.335],'paint',self.sealed_door_frame)
            self.box('door_jamb_stop',[.1575,yy,1.135],[.025,.10,2.27],'darkwood',self.sealed_door_frame,bevel=.002)
        self.box('door_header_core',[.03,1.20,2.29],[.24,1.22,.09],'paint',self.sealed_door_frame)
        self.box('door_header_stop',[.1575,1.20,2.245],[.025,1.20,.06],'darkwood',self.sealed_door_frame,bevel=.002)
        self.rotation_note=self.group('rotation_note',[2.50,2.40,.816]);self.add_target('rotation_note',self.rotation_note)
        self.box('rotation_note_paper',[0,0,0],[.86,.13,.002],'paper',self.rotation_note,bevel=.0003)
        self.label('rotation_note_print',NOTE,[0,0,.0016],.854,.125,right=(1,0,0),up=(0,1,0),parent=self.rotation_note)
        original_act=g.act
        def act(game,action):
            if action.get('_validated364') and action.get('_hit364')=='rotation_note' and action.get('action')=='read':return {'ok':True,'text':NOTE}
            return original_act(action)
        g.act=MethodType(act,g)
        level=sys.modules.get(type(g).__module__)
        if level is not None and hasattr(level,'LABELS'):level.LABELS['rotation_note']='paper on the light box table'
        self.sync(g)
        p=Path(self.run)/'R02_GEOMETRY.json';meta=json.loads(p.read_text(encoding='utf-8'));meta.update(panel_instruction_note=True,initial_rule_note=True,camera_case_bench_top=BENCH_TOP,case_key_vertical_drop=DROP,key_rearward_offset=.09,rotation_note=NOTE,presentation_revision=REVISION,screen_material='image-textured emission; no uniform white emission or glossy diffuse',continuous_subfloor=True,door_rebate_frame=True);p.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    def candidates(self,g):
        items=original_candidates(g)
        if hasattr(self,'rotation_note'):items+=self.base_candidates(['rotation_note'])
        return items
    scene.table=MethodType(table,scene);scene.mat=MethodType(material,scene);scene.sync=MethodType(sync,scene);scene.build=MethodType(build,scene);scene.candidates=MethodType(candidates,scene)
