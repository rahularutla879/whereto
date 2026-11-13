"""Aggregate only structural test spans; retain no request or credential data."""
import json,subprocess
from pathlib import Path
from statistics import median

def collect(D,containers,node_file,destination='/tmp/network-latency.json'):
 rows=[]
 for c in containers:
  r=subprocess.run(D+['exec',c,'cat','/tmp/network-spans.jsonl'],capture_output=True,text=True)
  if r.returncode==0:
   for line in r.stdout.splitlines():
    x=json.loads(line)
    if set(x)=={'stage','nanoseconds','ok'}:rows.append(x)
 if Path(node_file).exists():rows += [json.loads(x) for x in Path(node_file).read_text().splitlines()]
 stages={}
 for stage in sorted({x['stage'] for x in rows}):
  group=[x for x in rows if x['stage']==stage];values=sorted(x['nanoseconds']/1e6 for x in group)
  stages[stage]=dict(samples=len(values),failed=sum(not x['ok'] for x in group),p50Milliseconds=round(median(values),3),p95Milliseconds=round(values[min(len(values)-1,int(len(values)*.95))],3),maxMilliseconds=round(max(values),3))
 Path(destination).write_text(json.dumps(dict(scope='Synthetic local inclusive spans; overlapping stages must not be summed. Not cloud/provider/model latency.',stages=stages),indent=2)+'\n')
