from pathlib import Path
import math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from font_utils import load_font

class Art:
    def __init__(self,og,run):
        from pxr import UsdGeom,UsdShade,Gf,Sdf
        self.og=og;self.stage=og.sim.stage;self.G=UsdGeom;self.S=UsdShade;self.F=Gf;self.D=Sdf
        self.run=Path(run);self.tex=self.run/'textures';self.tex.mkdir(exist_ok=True)
        self.nodes={};self.groups={};self.mats={};self.count=0
        self.textures();self.palette()

    def textures(self):
        rng=np.random.default_rng(361);h=w=768;y,x=np.mgrid[:h,:w]
        grain=np.sin(x*.065+np.sin(y*.007)*5)+.5*np.sin(x*.20+np.sin(y*.012)*3)+.2*rng.normal(size=(h,w))
        bands=2.5*np.sin(y*.004)+grain*9
        wood=np.clip(np.array([132,87,48])[None,None,:]+bands[:,:,None]*np.array([1.0,.78,.52]),0,255).astype('uint8')
        Image.fromarray(wood).save(self.tex/'wood.png')
        wall=np.clip(np.array([151,156,147])[None,None,:]+rng.normal(0,2,(h,w,1))+3*np.sin(x*.009)[:,:,None],0,255).astype('uint8')
        Image.fromarray(wall).save(self.tex/'plaster.png')
        paint=np.clip(np.array([70,96,107])[None,None,:]+rng.normal(0,2.2,(h,w,1)),0,255).astype('uint8')
        im=Image.fromarray(paint);d=ImageDraw.Draw(im)
        for _ in range(220):
            a,b=rng.integers(0,768,2);d.line((int(a),int(b),int(a+rng.integers(2,14)),int(b+rng.integers(-3,4))),fill=(76,84,82),width=1)
        im.save(self.tex/'paint.png')
        from scipy.ndimage import gaussian_filter
        grime=gaussian_filter(rng.normal(0,1,(h,w)),24)
        grime=(grime-grime.mean())/(grime.std()+1e-6)
        fine=rng.normal(0,2,(h,w))
        dirt=np.clip(np.array([147,130,99])[None,None,:]+grime[:,:,None]*np.array([11,10,8])+fine[:,:,None],0,255).astype('uint8')
        im=Image.fromarray(dirt);d=ImageDraw.Draw(im)
        for _ in range(900):
            a,b=rng.integers(0,768,2);rad=int(rng.integers(1,5));d.ellipse((int(a),int(b),int(a+rad),int(b+rad)),fill=(111,99,78))
        im.save(self.tex/'dust.png')

    def mat(self,name,color=(.5,.5,.5),rough=.6,metal=0.,texture=None,emission=None,opacity=1.):
        if name in self.mats:return self.mats[name]
        with self.og.sim.editing_usd():
            p='/World/redesign364/materials/'+name;m=self.S.Material.Define(self.stage,p)
            s=self.S.Shader.Define(self.stage,p+'/surface');s.CreateIdAttr('UsdPreviewSurface')
            s.CreateInput('diffuseColor',self.D.ValueTypeNames.Color3f).Set(self.F.Vec3f(*color));s.CreateInput('roughness',self.D.ValueTypeNames.Float).Set(rough);s.CreateInput('metallic',self.D.ValueTypeNames.Float).Set(metal)
            if opacity<1:s.CreateInput('opacity',self.D.ValueTypeNames.Float).Set(opacity)
            if name=='dust':
                s.CreateInput('useSpecularWorkflow',self.D.ValueTypeNames.Int).Set(1)
                s.CreateInput('specularColor',self.D.ValueTypeNames.Color3f).Set(self.F.Vec3f(0,0,0))
            if emission:s.CreateInput('emissiveColor',self.D.ValueTypeNames.Color3f).Set(self.F.Vec3f(*emission))
            if texture:
                t=self.S.Shader.Define(self.stage,p+'/texture');t.CreateIdAttr('UsdUVTexture');t.CreateInput('file',self.D.ValueTypeNames.Asset).Set(str(texture));t.CreateOutput('rgb',self.D.ValueTypeNames.Float3)
                st=self.S.Shader.Define(self.stage,p+'/st');st.CreateIdAttr('UsdPrimvarReader_float2');st.CreateInput('varname',self.D.ValueTypeNames.Token).Set('st');t.CreateInput('st',self.D.ValueTypeNames.Float2).ConnectToSource(st.ConnectableAPI(),'result')
                s.CreateInput('diffuseColor',self.D.ValueTypeNames.Color3f).ConnectToSource(t.ConnectableAPI(),'rgb')
            m.CreateSurfaceOutput().ConnectToSource(s.ConnectableAPI(),'surface')
        self.mats[name]=m;return m

    def palette(self):
        self.mat('wood',texture=self.tex/'wood.png',rough=.65)
        self.mat('darkwood',(.17,.095,.045),rough=.7)
        self.mat('paint',texture=self.tex/'paint.png',rough=.52,metal=.22)
        self.mat('plaster',texture=self.tex/'plaster.png',rough=.94)
        self.mat('steel',(.46,.52,.55),rough=.38,metal=.55)
        self.mat('iron',(.055,.066,.07),rough=.5,metal=.7)
        self.mat('brass',(.70,.47,.16),rough=.38,metal=.65)
        self.mat('rubber',(.035,.043,.045),rough=.84)
        self.mat('paper',(.78,.74,.62),rough=.95)
        self.mat('cloth',(.16,.23,.22),rough=.98)
        self.mat('red',(.40,.12,.065),rough=.6)
        self.mat('bristle',(.61,.43,.23),rough=.94)
        self.mat('glass',(.15,.23,.24),rough=.12,metal=.1,opacity=.12)
        self.mat('lamp',(.92,.68,.34),rough=.3,emission=(3.,1.6,.55))
        self.mat('green',(.09,.25,.12),rough=.3,emission=(.08,.55,.13))
        self.mat('dust',texture=self.tex/'dust.png',rough=1.,opacity=1.)
        self.mat('drawer_felt',(.24,.38,.41),rough=1.)
        self.mat('key_gold',(.90,.57,.13),rough=.44,metal=.45)

    def group(self,key,pos=(0,0,0),parent=None):
        with self.og.sim.editing_usd():
            base=str(parent['prim'].GetPath()) if parent else '/World/redesign364'
            x=self.G.Xform.Define(self.stage,base+'/'+key)
            t=x.AddTranslateOp();t.Set(self.F.Vec3d(*pos));rot=x.AddRotateXYZOp();rot.Set(self.F.Vec3f(0,0,0))
        node={'prim':x.GetPrim(),'translate':t,'rotate':rot,'meshes':[]};self.groups[key]=node;return node

    def transform(self,group,pos=None,rpy=None):
        with self.og.sim.editing_usd():
            xform=self.G.Xformable(group['prim'])
            def operation(key,kind,create):
                if group.get(key) is not None:return group[key]
                ops=[op for op in xform.GetOrderedXformOps() if op.GetOpType()==kind and not op.IsInverseOp()]
                preferred=[op for op in ops if str(op.GetOpName())=='xformOp:'+key]
                if len(preferred)==1:op=preferred[0]
                elif len(ops)==1:op=ops[0]
                elif ops:raise ValueError('Ambiguous authored '+key+' xform ops')
                else:op=create()
                group[key]=op;return op
            def vector(op,values):
                vector_type=self.F.Vec3d if op.GetPrecision()==self.G.XformOp.PrecisionDouble else self.F.Vec3f
                op.Set(vector_type(*map(float,values)))
            if pos is not None:vector(operation('translate',self.G.XformOp.TypeTranslate,xform.AddTranslateOp),pos)
            if rpy is not None:vector(operation('rotate',self.G.XformOp.TypeRotateXYZ,xform.AddRotateXYZOp),rpy)

    def mesh(self,key,points,faces,material='wood',parent=None,uv=None):
        mat=self.mats[material] if isinstance(material,str) else material
        self.count+=1;base=str(parent['prim'].GetPath()) if parent else '/World/redesign364/geometry'
        path=base+'/'+key+'_'+str(self.count)
        points=np.asarray(points,float);indices=[int(i) for f in faces for i in f]
        if uv is None:
            lo=points.min(0);size=np.maximum(points.max(0)-lo,.001);uv=[]
            for face in faces:
                pp=points[list(face)];normal=np.abs(np.cross(pp[1]-pp[0],pp[2]-pp[0]));axes=[i for i in range(3) if i!=int(normal.argmax())]
                uv.extend([((points[i,axes[0]]-lo[axes[0]])/size[axes[0]],(points[i,axes[1]]-lo[axes[1]])/size[axes[1]]) for i in face])
        with self.og.sim.editing_usd():
            m=self.G.Mesh.Define(self.stage,path);m.CreatePointsAttr([self.F.Vec3f(*v) for v in points]);m.CreateFaceVertexCountsAttr([len(f) for f in faces]);m.CreateFaceVertexIndicesAttr(indices);m.CreateSubdivisionSchemeAttr('none');m.CreateDoubleSidedAttr(True)
            self.G.PrimvarsAPI(m).CreatePrimvar('st',self.D.ValueTypeNames.TexCoord2fArray,self.G.Tokens.faceVarying).Set(uv)
            self.S.MaterialBindingAPI.Apply(m.GetPrim()).Bind(mat)
        node={'prim':m.GetPrim(),'points':points,'faces':faces,'meshes':[]}
        if parent:parent['meshes'].append(node)
        self.nodes[key]=node;return node

    def box(self,key,c,size,mat='wood',parent=None,bevel=.008):
        from scipy.spatial import ConvexHull
        c=np.asarray(c,float);h=np.asarray(size,float)/2;b=min(bevel,float(min(h))*.35)
        pts=[]
        for axis in range(3):
            for sx in [-1,1]:
                for sy in [-1,1]:
                    for sz in [-1,1]:
                        v=(h-b)*np.array([sx,sy,sz]);v[axis]=h[axis]*[sx,sy,sz][axis];pts.append(c+v)
        pts=np.array(pts);hull=ConvexHull(pts);faces=[]
        for tri,eq in zip(hull.simplices,hull.equations):
            f=list(map(int,tri));p=pts[f]
            if np.dot(np.cross(p[1]-p[0],p[2]-p[0]),eq[:3])<0:f=f[::-1]
            faces.append(f)
        return self.mesh(key,pts,faces,mat,parent)

    def cylinder(self,key,c,radius,length,mat='steel',axis='z',parent=None,n=18):
        c=np.array(c,float);pts=[]
        for end in [-.5,.5]:
            for i in range(n):
                a=2*math.pi*i/n;v=np.array([radius*math.cos(a),radius*math.sin(a),length*end])
                if axis=='x':v=v[[2,0,1]]
                if axis=='y':v=v[[0,2,1]]
                pts.append(c+v)
        faces=[list(range(n-1,-1,-1)),list(range(n,n*2))]
        faces += [[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)]
        return self.mesh(key,pts,faces,mat,parent)

    def tube(self,key,a,b,radius=.025,mat='steel',parent=None):
        from scipy.spatial.transform import Rotation
        a=np.array(a,float);b=np.array(b,float);delta=b-a;ln=np.linalg.norm(delta);z=delta/ln
        right=np.cross(z,[0,0,1] if abs(z[2])<.95 else [0,1,0]);right/=np.linalg.norm(right);up=np.cross(z,right)
        pts=[];n=16
        for end in [a,b]:
            for i in range(n):
                t=2*math.pi*i/n;pts.append(end+radius*(right*math.cos(t)+up*math.sin(t)))
        faces=[list(range(n-1,-1,-1)),list(range(n,n*2))]+[[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)]
        return self.mesh(key,pts,faces,mat,parent)

    def plane(self,key,c,w,h,right,up,texture,parent=None,material=None):
        c=np.array(c,float);r=np.array(right,float)*w/2;u=np.array(up,float)*h/2
        if material is None:material=self.mat('image_'+key,texture=texture,rough=.9,emission=None)
        return self.mesh(key,[c-r-u,c+r-u,c+r+u,c-r+u],[[0,1,2,3]],material,parent,uv=[(0,0),(1,0),(1,1),(0,1)])

    def visibility(self,node,on):
        with self.og.sim.editing_usd():
            self.G.Imageable(node['prim']).GetVisibilityAttr().Set(self.G.Tokens.inherited if on else self.G.Tokens.invisible)

    def triangles(self,node):
        result=[];cache=self.G.XformCache()
        meshes=node['meshes'] if node.get('meshes') else [node]
        for mesh in meshes:
            if 'points' not in mesh:continue
            T=cache.GetLocalToWorldTransform(mesh['prim']);pts=np.array([list(T.Transform(self.F.Vec3d(*p))) for p in mesh['points']])
            for f in mesh['faces']:
                for i in range(1,len(f)-1):result.append(pts[[f[0],f[i],f[i+1]]])
        return np.array(result)

    def candidate(self,key,node):
        tri=self.triangles(node);p=tri.reshape(-1,3)
        return {'key':key,'room':'workshop','lo':p.min(0).tolist(),'hi':p.max(0).tolist(),'triangles':tri.tolist()}

    def label_image(self,key,text,width=800,height=200):
        im=Image.new('RGB',(width,height),(202,187,152));d=ImageDraw.Draw(im);f=load_font(int(height*.35));d.text((height*.12,height*.25),text,font=f,fill=(38,48,47))
        p=self.tex/(key+'.png');im.save(p);return p

    def framed(self,key,c,w,h,right,up,texture,parent=None):
        c=np.array(c,float);r=np.array(right,float);u=np.array(up,float);normal=np.cross(r,u)
        if abs(normal[1])>.9:
            for i in [-1,1]:self.box(key+'_side',c+r*i*(w/2+.025),[.045,.06,h+.10],'darkwood',parent)
            for i in [-1,1]:self.box(key+'_edge',c+u*i*(h/2+.025),[w+.1,.06,.045],'darkwood',parent)
        elif abs(normal[0])>.9:
            for i in [-1,1]:self.box(key+'_side',c+r*i*(w/2+.025),[.06,.045,h+.10],'darkwood',parent)
            for i in [-1,1]:self.box(key+'_edge',c+u*i*(h/2+.025),[.06,w+.1,.045],'darkwood',parent)
        return self.plane(key,c+normal*.007,w,h,right,up,texture,parent)

    def tool(self,key):
        g=self.group('tool_'+key,[0,0,-8])
        if key=='hammer':
            self.box('hammer_handle',[0,0,-.035],[.034,.040,.29],'wood',g,bevel=.012)
            self.box('hammer_collar',[0,0,.095],[.045,.05,.055],'iron',g)
            self.box('hammer_head',[0,0,.13],[.19,.065,.065],'steel',g)
            self.cylinder('hammer_face',[-.115,0,.13],.047,.045,'steel','x',g)
            for y in [-.022,.022]:
                self.tube('hammer_claw',[.07,y,.14],[.13,y,.15],.019,'steel',g)
                self.tube('hammer_claw_tip',[.13,y,.15],[.18,y,.095],.013,'steel',g)
        elif key=='screwdriver':
            self.cylinder('driver_handle',[0,0,-.075],.032,.145,'red','z',g)
            for x in [-.024,.024]:self.box('driver_grip',[x,-.012,-.075],[.008,.045,.105],'iron',g,bevel=.002)
            self.cylinder('driver_collar',[0,0,.005],.023,.025,'steel','z',g)
            self.cylinder('driver_shaft',[0,0,.08],.008,.15,'steel','z',g)
            self.box('driver_flat_tip',[0,0,.165],[.022,.008,.035],'steel',g,bevel=.002)
        elif key=='brush':
            self.box('brush_handle',[0,0,-.075],[.037,.035,.17],'wood',g,bevel=.012)
            self.box('brush_ferrule',[0,0,.027],[.105,.035,.07],'steel',g)
            self.box('brush_bristles',[0,0,.105],[.115,.035,.10],'bristle',g,bevel=.002)
            for x in np.linspace(-.049,.049,10):self.box('bristle_line',[float(x),-.019,.105],[.003,.003,.095],'darkwood',g,bevel=.0004)
        elif key=='wrench':
            self.box('wrench_handle',[0,0,-.035],[.042,.025,.26],'steel',g,bevel=.010)
            self.box('wrench_neck',[0,0,.10],[.06,.028,.07],'steel',g)
            for side in [-1,1]:
                self.box('wrench_jaw',[side*.046,0,.15],[.035,.032,.09],'steel',g,bevel=.008)
                self.box('wrench_tip',[side*.037,0,.195],[.04,.032,.024],'steel',g,bevel=.005)
            self.cylinder('wrench_eye',[0,0,-.17],.035,.026,'steel','y',g)
            self.cylinder('wrench_eye_hole',[0,-.015,-.17],.013,.004,'iron','y',g)
        elif key=='key':
            n=32;pts=[]
            for y in [-.009,.009]:
                for radius in [.035,.021]:
                    for i in range(n):
                        t=2*math.pi*i/n;pts.append([radius*math.cos(t),y,.055+radius*math.sin(t)])
            faces=[]
            for i in range(n):
                j=(i+1)%n
                faces += [[i,j,n+j,n+i],[2*n+i,3*n+i,3*n+j,2*n+j],[i,2*n+i,2*n+j,j],[n+i,n+j,3*n+j,3*n+i]]
            self.mesh('key_ring',pts,faces,'key_gold',g)
            self.box('key_shaft',[0,0,-.025],[.015,.016,.12],'key_gold',g,bevel=.003)
            self.box('key_bit',[.022,0,-.065],[.045,.016,.04],'key_gold',g,bevel=.003)
            with self.og.sim.editing_usd():self.G.Xformable(g['prim']).AddScaleOp().Set(self.F.Vec3f(1.35,1.35,1.35))
        return g

    def build(self,photo_paths=None):
        for i in range(24):self.box('floor_plank',[.125+i*.25,2.5,-.020],[.247,5.02,.05],'wood',bevel=.002)
        for c,size in [([0,2.5,1.4],[.14,5.2,2.8]),([6,2.5,1.4],[.14,5.2,2.8]),([3,5,1.4],[6.1,.14,2.8]),([1.2,0,1.4],[2.4,.14,2.8]),([4.8,0,1.4],[2.4,.14,2.8])]:self.box('wall',c,size,'plaster')
        self.box('door_header',[3,0,2.58],[1.25,.16,.44],'darkwood')
        for c,size in [([.09,2.5,.45],[.05,5.0,.9]),([5.91,2.5,.45],[.05,5.0,.9]),([3,4.91,.45],[5.85,.05,.9])]:self.box('wainscot',c,size,'paint')
        for x in [.12,5.88]:
            self.box('skirting',[x,2.5,.09],[.08,4.9,.16],'darkwood');self.box('dado',[x,2.5,.92],[.08,4.9,.055],'darkwood')
        self.box('north_skirting',[3,4.88,.09],[5.9,.09,.16],'darkwood');self.box('north_dado',[3,4.88,.92],[5.9,.09,.055],'darkwood')
        for y in [.35,2.5,4.65]:self.box('ceiling_beam',[3,y,2.72],[6,.12,.16],'darkwood')
        self.box('ceiling',[3,2.5,2.84],[6.2,5.2,.1],'plaster')
        self.box('bench_top',[2.85,4.55,.88],[1.65,.72,.10],'wood',bevel=.025)
        for x in [2.12,3.58]:
            for y in [4.28,4.82]:self.box('bench_leg',[x,y,.44],[.075,.075,.83],'iron')
        self.box('bench_stretcher',[2.85,4.62,.20],[1.48,.06,.07],'iron')
        self.box('bench_shelf',[2.85,4.55,.27],[1.48,.6,.06],'wood')
        for i in range(3):
            self.cylinder('parts_tin',[2.15+i*.19,4.73,.99],.065,.15,'paint')
            self.cylinder('tin_lid',[2.15+i*.19,4.73,1.07],.068,.02,'steel')
        self.box('folded_rag',[3.48,4.55,.95],[.28,.24,.035],'cloth')
        self.cylinder('lamp_base',[3.48,4.77,.98],.11,.05,'iron')
        self.tube('lamp_stem',[3.48,4.77,1.0],[3.48,4.77,1.42],.018,'steel')
        self.tube('lamp_arm',[3.48,4.77,1.42],[3.22,4.58,1.48],.022,'steel')
        self.cylinder('lamp_shade',[3.22,4.58,1.46],.13,.10,'paint')
        self.cylinder('lamp_diffuser',[3.22,4.58,1.40],.105,.008,'lamp')
        self.box('case_stand_top',[1.0,.95,.46],[.95,.62,.07],'wood')
        for x in [.60,1.40]:
            for y in [.71,1.19]:self.box('stand_leg',[x,y,.23],[.07,.07,.44],'iron')
        for c,size in [([1.0,.70,.64],[.72,.045,.28]),([1.,1.20,.64],[.72,.045,.28]),([.66,.95,.64],[.045,.50,.28]),([1.34,.95,.64],[.045,.50,.28]),([1.,.95,.515],[.72,.5,.035])]:self.box('case_body',c,size,'wood')
        case=self.group('case_lid',[1.,1.21,.79]);self.box('case_lid_leaf',[0,-.26,0],[.78,.56,.055],'darkwood',case)
        for x in [-.29,.29]:self.box('case_hinge',[x,-.015,.028],[.10,.06,.025],'brass',case)
        self.box('case_latch',[0,-.54,-.055],[.08,.04,.085],'brass',case)
        for c,size in [([.18,4.00,1.03],[.08,.85,2.05]),([.50,3.58,1.03],[.66,.07,2.05]),([.50,4.42,1.03],[.66,.07,2.05]),([.50,4.,2.02],[.66,.9,.06]),([.50,4.,.10],[.66,.9,.10])]:self.box('locker_body',c,size,'paint')
        for z in [.55,1.05,1.55]:self.box('locker_shelf',[.50,4.,z],[.6,.78,.035],'steel')
        locker=self.group('locker_door',[.84,4.43,0]);self.box('locker_leaf',[0,-.43,1.05],[.055,.86,1.93],'paint',locker)
        self.box('locker_handle',[.06,-.71,1.13],[.08,.04,.18],'brass',locker)
        for z in [1.10,1.25]:self.cylinder('brush_clip',[-.045,-.43,z],.022,.065,'brass','x',locker)
        for z in [1.7,1.78,1.86]:self.box('locker_vent',[.032,-.43,z],[.008,.38,.018],'iron',locker,bevel=.002)
        for z in [.20,.36,.52,.68]:
            self.box('crate_front',[.82,2.08,z],[.06,.73,.145],'wood')
            self.box('crate_back',[.16,2.08,z],[.06,.73,.145],'wood')
            for y in [1.71,2.45]:self.box('crate_side',[.49,y,z],[.66,.06,.145],'wood')
        self.box('crate_bottom',[.49,2.08,.12],[.66,.72,.06],'darkwood')
        self.box('crate_padded_insert',[.49,2.08,.49],[.59,.64,.045],'cloth')
        crate=self.group('crate_lid',[.49,2.47,.78]);self.box('crate_top',[0,-.39,0],[.78,.82,.065],'wood',crate)
        for x in [-.28,.28]:self.box('crate_batten',[x,-.39,.05],[.07,.76,.035],'darkwood',crate)
        nail=self.group('crate_fasteners',[.49,2.47,.78])
        for x in [-.28,.28]:
            self.cylinder('raised_nail',[x,-.70,.085],.020,.055,'iron','z',nail)
            self.cylinder('nail_head',[x,-.70,.115],.030,.012,'steel','z',nail)
        for c,size in [([5.70,2.30,.72],[.10,1.15,1.35]),([5.30,1.75,.72],[.86,.08,1.35]),([5.30,2.85,.72],[.86,.08,1.35]),([5.30,2.30,.10],[.90,1.20,.15]),([5.30,2.30,1.38],[.90,1.2,.10])]:self.box('pump_body',c,size,'paint')
        self.cylinder('pump_motor',[5.35,2.30,1.65],.24,.55,'iron','x')
        for x in [5.05,5.20,5.35,5.50,5.65]:self.cylinder('motor_rib',[x,2.30,1.65],.255,.035,'steel','x')
        self.tube('pipe_a',[5.60,2.3,1.7],[5.60,2.3,2.2],.065)
        self.tube('pipe_b',[5.60,2.3,2.2],[5.88,2.3,2.2],.065)
        self.cylinder('pipe_flange',[5.60,2.3,2.05],.12,.06,'brass','z')
        self.box('service_ledge',[5.28,2.30,.55],[.65,.90,.06],'steel')
        hatch=self.group('pump_hatch',[4.86,2.88,0]);self.box('hatch_leaf',[0,-.58,.78],[.055,1.13,1.12],'paint',hatch)
        self.box('hatch_handle',[-.06,-.85,.78],[.06,.06,.21],'steel',hatch)
        screw=self.group('hatch_screw',[4.82,2.30,1.13]);self.cylinder('screw_head',[0,0,0],.044,.025,'steel','x',screw)
        self.box('screw_slot',[-.014,0,0],[.004,.058,.010],'iron',screw,bevel=.0005)
        self.box('rack_board',[4.70,4.86,1.63],[1.25,.10,1.25],'wood',bevel=.025)
        for x in [4.07,5.33]:self.box('rack_rail',[x,4.79,1.63],[.055,.07,1.29],'darkwood')
        for z in [1.0,2.26]:self.box('rack_rail',[4.7,4.79,z],[1.30,.07,.055],'darkwood')
        self.box('rack_corner1',[4.13,4.73,2.20],[.18,.025,.035],'brass');self.box('rack_corner2',[4.06,4.73,2.13],[.035,.025,.18],'brass')
        slots=[(4.42,4.70,1.94),(4.98,4.70,1.94),(4.42,4.70,1.40),(4.98,4.70,1.40)]
        slotnodes=[]
        for i,c in enumerate(slots):
            p=np.array(c);pad=self.box('holder'+str(i),p+[0,.035,-.03],[.17,.025,.22],'paint')
            for dx in [-.055,.055]:self.cylinder('holder_pin',[p[0]+dx,p[1]-.005,p[2]-.05],.012,.10,'brass','y')
            slotnodes.append(pad)
        self.tube('rack_latch_link',[4.1,4.75,1.0],[4.1,4.75,.74],.015,'brass')
        for c,size in [([4.70,4.90,.58],[1.15,.08,.80]),([4.13,4.69,.58],[.07,.50,.80]),([5.27,4.69,.58],[.07,.50,.80]),([4.70,4.69,.97],[1.15,.50,.07]),([4.70,4.69,.20],[1.15,.50,.08])]:self.box('keycab_body',c,size,'paint')
        drawer=self.group('key_drawer',[4.70,4.69,.47]);self.box('drawer_tray',[0,0,0],[.99,.43,.05],'wood',drawer)
        self.box('drawer_lining',[0,0,.035],[.93,.37,.012],'drawer_felt',drawer)
        for x in [-.49,.49]:
            self.box('drawer_front_side',[x,-.24,.135],[.08,.05,.28],'paint',drawer)
            self.box('drawer_sidewall',[x,0,.075],[.03,.43,.12],'wood',drawer)
            self.box('drawer_slide',[x*.97,0,-.035],[.025,.44,.035],'steel',drawer)
        for z in [-.005,.275]:self.box('drawer_front_rail',[0,-.24,z],[1.06,.05,.05],'paint',drawer)
        glass=self.plane('drawer_glass',[0,-.268,.135],.89,.21,[1,0,0],[0,0,1],None,drawer,material=self.mats['glass'])
        self.box('drawer_handle',[0,-.30,.26],[.28,.055,.045],'brass',drawer)
        label=self.label_image('shift_label','SHIFT HANDOVER',900,160)
        self.plane('shift_label',[4.70,4.412,.92],.63,.11,[1,0,0],[0,0,1],label)
        self.box('keycab_light_strip',[4.70,4.65,.882],[.32,.08,.018],'lamp')
        lamp=self.cylinder('rack_status',[5.18,4.42,.91],.025,.02,'brass','y')
        for x in [2.40,3.60]:self.box('door_jamb',[x,.05,1.17],[.12,.20,2.35],'darkwood')
        door=self.group('exit_door',[2.46,.09,0]);self.box('door_leaf',[.54,0,1.13],[1.08,.10,2.22],'wood',door,bevel=.025)
        for z in [.27,1.95]:self.box('door_iron_band',[.54,.06,z],[1.02,.04,.10],'iron',door)
        self.box('door_lock_plate',[.93,.075,1.03],[.13,.04,.24],'brass',door)
        self.cylinder('door_knob',[.93,.13,1.10],.045,.08,'steel','y',door)
        self.cylinder('keyhole',[.93,.101,.99],.020,.006,'iron','y',door)
        self.box('porch',[3.,-.5,-.025],[1.5,1.,.05],'wood')
        book=self.group('album_stand',[2.71,4.46,1.12]);self.transform(book,rpy=[60,0,0])
        album=self.group('album_cover',[-.23,0,.035],parent=book);self.box('album_cover_leaf',[.23,0,.01],[.46,.42,.045],'darkwood',album)
        self.box('album_pages',[0,0,0],[.45,.42,.035],'paper',book)
        self.box('album_spine',[-.25,0,0],[.04,.45,.06],'red',book)
        self.box('reading_stand_back',[2.71,4.59,1.11],[.48,.06,.34],'darkwood')
        self.box('reading_stand_lip',[2.71,4.33,.957],[.5,.055,.04],'brass')
        placeholder=self.label_image('photo_placeholder','',600,600)
        photo1=self.plane('photo1',[0,0,.022],.41,.36,[1,0,0],[0,1,0],placeholder,book)
        photo2=self.framed('photo2',[.105,2.99,1.55],.42,.63,[0,1,0],[0,0,1],placeholder)
        dust=self.plane('photo_dust',[.119,2.99,1.55],.375,.565,[0,1,0],[0,0,1],None,material=self.mats['dust'])
        self.tube('wall_conduit',[.2,4.78,2.42],[5.8,4.78,2.42],.018,'steel')
        for x in [1.9,3.8]:self.tube('conduit_drop',[x,4.78,2.42],[x,4.78,1.2],.018,'steel')
        self.box('side_shelf',[5.75,3.75,1.68],[.40,.85,.045],'wood')
        for y in [3.5,3.75,4.0]:
            self.cylinder('shelf_can',[5.72,y,1.78],.08,.18,'paint');self.cylinder('shelf_can_lid',[5.72,y,1.88],.085,.015,'steel')
        self.box('rug',[3.0,2.2,.006],[2.0,1.2,.012],'cloth',bevel=.002)
        self.box('window_back',[.085,1.85,2.06],[.035,1.18,.85],'iron')
        self.mat('window_glow',(.13,.22,.28),rough=.5,emission=(.15,.27,.35))
        self.box('window_glass',[.11,1.85,2.06],[.02,1.08,.76],'window_glow')
        for y in [1.28,1.85,2.42]:self.box('window_frame',[.14,y,2.06],[.05,.05,.85],'darkwood')
        for z in [1.64,2.48]:self.box('window_frame',[.14,1.85,z],[.05,1.18,.05],'darkwood')
        for x,y in [(2.4,2.7),(4.7,4.0)]:
            self.tube('light_cord',[x,y,2.72],[x,y,2.52],.009,'iron')
            self.cylinder('ceiling_shade',[x,y,2.49],.23,.10,'paint')
            self.cylinder('ceiling_diffuser',[x,y,2.43],.20,.015,'lamp')
        self.box('entry_light_frame',[3.,.50,2.58],[1.29,.39,.055],'paint')
        self.box('entry_light_diffuser',[3.,.50,2.555],[1.20,.30,.012],'lamp')
        tools={key:self.tool(key) for key in ['hammer','screwdriver','brush','wrench','key']}
        return dict(case=case,locker=locker,crate=crate,nails=nail,hatch=hatch,screw=screw,drawer=drawer,exit=door,album=album,photo1=photo1,photo2=photo2,dust=dust,tools=tools,slots=slots,slotnodes=slotnodes,glass=glass,status=lamp)
