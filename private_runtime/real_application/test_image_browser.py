"""Disposable controller: external fixture enrollment of actual immutable images."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import base64,json,os,time,uuid
from . import test_services as base
from .test_native import g
from . import test_hosted
test_hosted.CA='/testing/real-store-ca.pem'
base.BUILD=os.environ['TASK52_IMAGE_COHORT']
_original=base.configurations
def configurations(*a):
    configs,users=_original(*a)
    for c in configs.values():c['identityEnvironment']='private-staging'
    return configs,users
base.configurations=configurations
Q=Path('/tmp/image-role-requests')
class Remote:
    def __init__(self,c,provider,cert,key):
        Q.mkdir(exist_ok=True);self.id=uuid.uuid4().hex;self.s=Q/(self.id+'.state');self.stop=Q/(self.id+'.stop');self.exitcode=None
        v=dict(id=self.id,config=c,provider=provider,certificate=cert,tlsKey=key,files={p:base64.b64encode(Path(p).read_bytes()).decode() for p in (cert,key,'/tmp/real-store-ca.pem')})
        p=Q/(self.id+'.json');p.write_text(json.dumps(v));p.chmod(0o600)
    def poll(self,seconds):
        end=time.monotonic()+max(seconds,60)
        while time.monotonic()<end:
            if self.s.exists():return True
            time.sleep(.1)
        return False
    def recv(self):
        v=json.loads(self.s.read_bytes());return 'ready' if v['ready'] else {'error':'Image role refused'}
    def is_alive(self):return not self.stop.with_suffix('.stopped').exists()
    def terminate(self):self.stop.write_text('stop')
    def join(self,seconds):
        end=time.monotonic()+seconds
        while self.is_alive() and time.monotonic()<end:time.sleep(.1)
        if not self.is_alive():self.exitcode=0
    def kill(self):self.stop.write_text('kill')
    def close(self):pass
class Tests(base.Tests):
    def start(self,target,*args):
        if target is base.serve:
            c,_,provider,cert,key=args;r=Remote(c,provider,cert,key);self.workers.append((r,r,c['principal']));return r,r
        return super().start(target,*args)
    def setUp(self):
        if self._testMethodName=='test_image_uncertain':self.behavior='/v1/places:searchText'
        super().setUp()
    def ready_source(self):
        source=dict(text=base.TEXT,calendarTimezone='America/New_York')
        first=self.call('/api/interpret',source)
        answer=(datetime.now(timezone.utc)+timedelta(days=2)).date().isoformat()
        return source,first,answer
    def plan_value(self,ready):
        return dict(**ready['request'],privateOuting=ready['privateOuting'],startingLocation=dict(point=dict(id='device-origin',coordinates=dict(latitude=39.29,longitude=-76.61)),source='device',explicitly_authorized=True))
    def test_image_replacement_and_replay(self):
        source,first,date=self.ready_source();handle=first['privateOuting'];path,raw,headers=self.last_request
        with self.assertRaises(Exception):self.http.request(self.endpoint,'POST',path,raw,headers)
        with self.assertRaises(Exception):self.call('/api/interpret',dict(**source,privateOuting=handle,answers={'date':date}),who='bob')
        self.handoff()
        ready=self.call('/api/interpret',dict(**source,privateOuting=handle,answers={'date':date}))
        self.assertEqual(ready['privateOuting']['expiresMs'],handle['expiresMs'])
        cards=self.call('/api/plans/generate',self.plan_value(ready));self.assertEqual(len(cards['provisionalPlans']),3)
        paths=self.paths();self.assertEqual(paths.count('/v1/responses'),1);self.assertEqual(paths.count('/v1/responses/input_tokens'),1)
        with self.assertRaises(Exception):self.call('/api/plans/generate',self.plan_value(ready))
        self.assertFalse(self.paths())
        with g.admin() as c:self.assertEqual(c.execute('SELECT sum(charge) FROM provider_state.operations').fetchone()[0],190148)
    def test_image_uncertain(self):
        from private_runtime.https import Refused
        source,first,date=self.ready_source()
        ready=self.call('/api/interpret',dict(**source,privateOuting=first['privateOuting'],answers={'date':date}))
        value=self.plan_value(ready)
        try:self.assertFalse(self.call('/api/plans/generate',value)['provisionalPlans'])
        except Refused:pass
        self.assertEqual(self.paths(),['/v1/responses/input_tokens','/v1/responses','/v1/places:searchText'])
        with g.admin() as c:self.assertEqual(c.execute('SELECT sum(charge) FROM provider_state.operations').fetchone()[0],38148)
        with g.connect('witness') as c:status=c.execute("SELECT provider_witness.protocol('status','{}')").fetchone()[0]
        self.assertTrue(status['quarantined']);self.assertEqual(status['gross'],38148)
        with self.assertRaises(Refused):self.call('/api/plans/generate',value)
        self.assertFalse(self.paths())
    def test_image_redis_loss(self):
        source,first,date=self.ready_source();self.assertEqual(self.paths(),['/v1/responses/input_tokens','/v1/responses'])
        g.cache().client.flushdb()
        with self.assertRaises(Exception):self.call('/api/interpret',dict(**source,privateOuting=first['privateOuting'],answers={'date':date}))
        self.assertFalse(self.paths())
        with g.admin() as c:self.assertEqual(c.execute('SELECT sum(charge) FROM provider_state.operations').fetchone()[0],6148)
    def test_browser_entry(self):
        value=dict(frontend=self.configs['frontend'],users=self.users,backendPort=self.ports['backend'],serviceCA=self.cert,text=base.TEXT,answerDate=(datetime.now(timezone.utc)+timedelta(days=2)).date().isoformat())
        p=Path('/tmp/real-browser-control.json');p.write_text(json.dumps(value));p.chmod(0o600)
        print(json.dumps(dict(event='real_container_browser_services_ready',build=base.BUILD)),flush=True)
        done=Path('/tmp/real-browser-done.json')
        for _ in range(1800):
            if done.exists():break
            time.sleep(.5)
        else:self.fail('Image browser window ended')
        result=json.loads(done.read_bytes());self.assertTrue(result['passed']);paths=self.paths()
        self.assertEqual(paths.count('/v1/responses/input_tokens'),2);self.assertEqual(paths.count('/v1/responses'),2);self.assertEqual(paths.count('/v1/places:searchText'),4)
        with g.admin() as c:
            self.assertEqual(c.execute('SELECT sum(charge) FROM provider_state.operations').fetchone()[0],380296)
            self.assertEqual(c.execute('SELECT count(*) FROM provider_state.count_transport_uses').fetchone()[0],2)
            self.assertEqual(c.execute('SELECT count(*) FROM provider_state.sessions s JOIN provider_state.native_checkpoints n ON n.session=s.id WHERE NOT s.revoked').fetchone()[0],0)
            self.assertNotIn('Fixture_',json.dumps(c.execute('SELECT payload FROM provider_state.evidence').fetchall()))
        print(json.dumps(dict(event='container_browser_verified',result=result)),flush=True)
