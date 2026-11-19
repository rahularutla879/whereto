"""Fixed credential-owning dispatcher count relay. Counter has no provider key."""
from hashlib import sha256
from psycopg.types.json import Jsonb
from experiments.shared_state.contracts import Denied
from experiments.service_isolation.auth import b64,unb64
from private_runtime.provider_callbacks import CounterCallback,CountRecord,count_payload,generation_source
from backend.provider_responses import HTTPResult

class RemoteCount:
    def __init__(self,client,project):self.client,self.project=client,project
    def count(self,operation,wire):
        result=self.client.request('dispatcher','/count-provider',dict(operation=operation,wire=b64(wire)))
        if type(result)is not dict or set(result)!={'raw','sha256'}:raise Denied('count_transport_response')
        raw=unb64(result['raw'])
        if len(raw)>700000 or sha256(raw).hexdigest()!=result['sha256']:raise Denied('count_transport_response')
        response=HTTPResult(200,raw);v=response.decode()
        if type(v)is not dict or set(v)!={'object','input_tokens'} or v['object']!='response.input_tokens' or type(v['input_tokens'])is not int or not 1<=v['input_tokens']<=100000:raise Denied('count_transport_response')
        return v['input_tokens'],response

class RelayCounter(CounterCallback):
    def count(self,capability,wire):
        generation_source(wire);projected=count_payload(wire)
        operation=self.authority.begin(capability,wire,sha256(projected).hexdigest(),self.exchange.project)
        try:
            tokens,raw=self.exchange.count(operation,wire)
            record=CountRecord(sha256(wire).hexdigest(),sha256(projected).hexdigest(),raw.digest,tokens)
            self.authority.commit(operation,record,raw);return record
        except BaseException:
            self.authority.uncertain(operation);raise

class CountDelivery:
    def __init__(self,connection,witness,exchange):self.connection,self.witness,self.exchange=connection,witness,exchange
    def __call__(self,value):
        from experiments.shared_state.postgres import uuid
        if type(value)is not dict or set(value)!={'operation','wire'}:raise Denied('count_transport_shape')
        uuid(value['operation']);wire=unb64(value['wire']);generation_source(wire)
        def quote(consume):
            with self.connection() as c:return c.execute('SELECT provider_state.count_transport(%s,%s,%s)',(value['operation'],wire,consume)).fetchone()[0]
        with self.witness.serial():
            q=quote(False)
            if q['account']!=self.exchange.project:raise Denied('count_transport_project')
            with self.connection() as c:observed=c.execute('SELECT provider_state.real_counter_observed()').fetchone()[0]
            self.witness.call('confirm',observed=observed)
            self.witness._active.get().execute('SELECT provider_witness.count_transport(%s)',(Jsonb(q),))
        # Both independent durable one-use facts commit BEFORE credential/HTTP.
        if quote(True)!=q:raise Denied('count_transport_changed')
        _,raw=self.exchange.count(wire)
        return dict(raw=b64(raw.body),sha256=raw.digest)
