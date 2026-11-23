from pathlib import Path
from PIL import ImageFont
def install(runtime_root):
    if getattr(ImageFont,'_puzzlemix_font',False): return
    old=ImageFont.truetype
    local=Path(runtime_root)/'fonts'
    def use(font,*a,**kw):
        name=str(font).replace(chr(92),'/').rsplit('/',1)[-1].lower()
        if name in ('consola.ttf','consolab.ttf'):
            exact=local/name
            font=str(exact if exact.is_file() else local/'DejaVuSansMono.ttf')
        return old(font,*a,**kw)
    ImageFont.truetype=use;ImageFont._puzzlemix_font=True
