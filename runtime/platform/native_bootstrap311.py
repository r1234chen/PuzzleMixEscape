from pathlib import Path
import os,sys,sysconfig,hashlib,json,ctypes
_HANDLES=[]
def prepare_hdf5(root=None):
    if os.name!='nt' or _HANDLES:return
    folder=Path(__file__).resolve().parents[2]/'.local'/'isaac_hdf5'
    folder.mkdir(parents=True,exist_ok=True)
    sources=Path(sysconfig.get_paths()['purelib'])/'isaacsim/kit/dev/libs/sensors/generic_model_output/bin'
    spec=json.loads(Path(__file__).with_name('hdf5.json').read_text('utf8'))
    for row in spec:
        f=sources/row['name'];raw=f.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=row['source_sha256']:raise ValueError('Incompatible Isaac Sim Windows library: '+f.name)
        for edit in row['import_changes']:
            old=edit['old'].encode();new=edit['new'].encode();at=edit['offset']
            if raw[at:at+len(old)]!=old or len(old)!=len(new):raise ValueError('Incompatible loader ABI')
            raw=raw[:at]+new+raw[at+len(old):]
        if hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('Unexpected private library identity')
        dest=folder/row['target']
        if not dest.exists() or dest.read_bytes()!=raw:dest.write_bytes(raw)
    _HANDLES.append(os.add_dll_directory(str(folder)))
    for row in spec:_HANDLES.append(ctypes.WinDLL(str(folder/row['target'])))
