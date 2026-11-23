import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

def main():
    root=Path(__file__).resolve().parent
    p=argparse.ArgumentParser(description="Get upstream simulator assets for one selected level. No model call.")
    p.add_argument('--level',required=True)
    a=p.parse_args()
    rows={v['id']:v for v in json.loads((root/'level/index.json').read_text('utf8'))['levels']}
    if a.level not in rows:p.error('Unknown public level ID')
    data=root/'assets/datasets';data.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ);env['OMNIGIBSON_DATA_PATH']=str(data)
    env['PYTHONDONTWRITEBYTECODE']='1'
    for k in ('OPENAI_API_KEY','OPENROUTER_API_KEY','DASHSCOPE_API_KEY'):env.pop(k,None)
    opts=['--download_omnigibson_robot_assets']
    if rows[a.level]['format']=='declarative_json':opts.append('--download_behavior_1k_assets')
    print('Official asset installer → assets/datasets; API keys are not used. Review the upstream asset license when prompted.',flush=True)
    subprocess.run([sys.executable,'-m','omnigibson.utils.asset_utils',*opts],cwd=root,env=env,check=True)
if __name__=='__main__':main()
