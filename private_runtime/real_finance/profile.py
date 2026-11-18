"""Finite source-pinned profile projection; never installs, enrolls or sends.

Original SQL files and synthetic databases stay untouched. Outputs belong only in
fresh provider_state/provider_rules/provider_witness schemas under new roles.
Reservation, evidence/fence and witness history algorithms remain the parents'.
"""
from pathlib import Path
from hashlib import sha256
import json

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
VERSION='52-real-provider-finance-v1'
PARENT=ROOT/'experiments/shared_state'
FILES=('schema.sql','routines.sql','financial_schema.sql','financial_routines.sql','bridge.sql','evidence.sql','grant_rules.sql','application_grants.sql','grant_witness.sql')

def digest(b):return sha256(b).hexdigest()
def verify():
    manifest=json.loads((HERE/'sources.json').read_bytes())
    for n,h in manifest['inputs'].items():
        p=ROOT/n
        if p.is_symlink() or digest(p.read_bytes())!=h:raise ValueError('Real financial profile source changed: '+n)
    return manifest

def replace(text,old,new,count=1):
    if text.count(old)!=count:raise ValueError('Parent SQL projection changed')
    return text.replace(old,new)

def namespace(text):
    for a,b in [('synthetic_state','provider_state'),('grant_rules','provider_rules'),('witness.','provider_witness.'),('SCHEMA witness','SCHEMA provider_witness'),('IN SCHEMA witness','IN SCHEMA provider_witness'),('whereto_synthetic_','whereto_real_'),('synthetic_token_counter','real_token_counter'),('synthetic_witness_','real_witness_'),('synthetic_grant_operator','real_grant_operator'),("'synthetic_maps'","'google'"),("'synthetic_ai'","'openai'"),("'synthetic'","'real'"),('synthetic-local-project-v1','real-provider-accounts-v1'),('52-financial-authority-local-pg-v3',VERSION)]:text=text.replace(a,b)
    return text

def projected(name):
    text=namespace((PARENT/name).read_text())
    if name=='grant_rules.sql':
        text=replace(text,'used_outing numeric,attempts bigint','used_outing numeric,used_session numeric,attempts bigint')
        text=replace(text,"OR used_outing+price>(g->>'outing')::numeric","OR used_outing+price>(g->>'outing')::numeric OR used_session+price>(g->>'session')::numeric")
        text=replace(text,' PERFORM provider_rules.validate(g,rates);now_at:=',' PERFORM provider_rules.current_rates();now_at:=')
        text=replace(text,"THEN 'google' ELSE l->>'provider' END","THEN 'google' WHEN l->>'kind'='count' THEN 'openai' ELSE l->>'provider' END")
        text=replace(text,"OR q->>'version' IS DISTINCT FROM g->>'version'", "OR q->>'version' IS DISTINCT FROM g->>'version' OR q->>'account' IS DISTINCT FROM (CASE WHEN q->>'provider'='google' THEN rates->>'google_account' ELSE rates#>>'{models,gpt-6-luna,account}' END) OR q->>'policy' IS DISTINCT FROM encode(sha256(convert_to(rates::text,'UTF8')),'hex')")
    if name=='financial_routines.sql':
        a=text.index("p.rate_version<>'development_cost.");b=text.index('\n   OR NOT EXISTS',a)
        text=text[:a]+"p.rate_version IS DISTINCT FROM (SELECT rates->>'version' FROM provider_rules.configuration WHERE id=1) OR p.rates IS DISTINCT FROM (SELECT rates->'maps' FROM provider_rules.configuration WHERE id=1)"+text[b:]
        text=replace(text,"IF p.accounting_identity<>","IF p.profile IS DISTINCT FROM 'bounded' OR p.timezone IS DISTINCT FROM (SELECT grant_doc->>'timezone' FROM provider_rules.configuration WHERE id=1) OR p.accounting_identity<>")
        text=replace(text,' PERFORM provider_state.protocol(\'snapshot\',\'{}\');'," PERFORM provider_state.protocol('snapshot','{}'); PERFORM provider_rules.current_rates();")
        text=replace(text,"   op:=item->>'operation';variant:=item->>'variant';", "   op:=item->>'operation';variant:=item->>'variant'; IF op NOT IN ('search','matrix') OR (op='search' AND variant IS DISTINCT FROM 'pro') THEN RAISE EXCEPTION 'real_closed_operation'; END IF;")
        text=replace(text,"policy.version,policy.accounting_identity,'USD'","policy.version,(SELECT rates->>'google_account' FROM provider_rules.configuration WHERE id=1),'USD'")
        for scope in ('outing','session'):
            target='b.outing' if scope=='outing' else 'b.root';column='outing' if scope=='outing' else 'root'
            old=f"used.req+sums.req>(policy.settings->>'requests_per_{scope}')"
            new=f"used.req+sums.req+(SELECT count(*) FROM provider_state.count_intents WHERE quote->>'{column}'={target}::text)>(policy.settings->>'requests_per_{scope}')"
            text=replace(text,old,new)
    if name=='grant_witness.sql':
        text=replace(text,'q,used.t,used.p,used.d,used.o,used.n,active',"q,used.t,used.p,used.d,used.o,(SELECT coalesce(sum(charge),0) FROM provider_witness.claims WHERE phase='reserve' AND quote->>'root'=q->>'root'),used.n,active")
    if name=='application_grants.sql':
        text=replace(text,'q,used.t,used.pr,used.d,used.o,used.n,active',"q,used.t,used.pr,used.d,used.o,(SELECT coalesce(sum((quote->>'charge')::numeric),0) FROM provider_state.app_operations WHERE quote->>'root'=q->>'root'),used.n,active")
        text=replace(text,"'provider',provider_name,'root'", "'provider',provider_name,'account',CASE WHEN provider_name='google' THEN r->>'google_account' ELSE r#>>'{models,gpt-6-luna,account}' END,'policy',encode(sha256(convert_to(r::text,'UTF8')),'hex'),'root'")
        text=replace(text," IF NOT EXISTS(SELECT 1 FROM provider_state.token_counts WHERE", " PERFORM provider_state.real_count_current(cap); IF http IS DISTINCT FROM (SELECT rs.http FROM provider_state.real_sources rs WHERE capability=cap) OR inference IS DISTINCT FROM (SELECT rs.inference FROM provider_state.real_sources rs WHERE capability=cap) THEN RAISE EXCEPTION 'real_approval_admission'; END IF;\n IF NOT EXISTS(SELECT 1 FROM provider_state.token_counts WHERE")
        text=replace(text,"'synthetic-application-grant-v1','real-provider-accounts-v1'", "'real-application-grant-v1',llm.spec->>'account'")
        text=replace(text,"used.req+1>(SELECT", "used.req+1+(SELECT count(*) FROM provider_state.count_intents WHERE quote->>'root'=q->>'root')>(SELECT")
        text=replace(text,"(SELECT count(*)+1 FROM provider_state.financial_lines WHERE outing=(q->>'outing')::uuid)","(SELECT count(*)+1 FROM provider_state.financial_lines WHERE outing=(q->>'outing')::uuid)+(SELECT count(*) FROM provider_state.count_intents WHERE quote->>'outing'=q->>'outing')")
        text=replace(text,"     -- Frozen evidence front door", "     PERFORM provider_state.real_count_fresh(p->>'capability');\n     -- Frozen evidence front door")
        text=replace(text,"(SELECT count(*) FROM jsonb_object_keys(p->'report'))=7", "(SELECT count(*) FROM jsonb_object_keys(p->'report'))=8")
        text=replace(text,"p->'report'->'input_tokens'=llm.spec->'input_tokens'", "provider_rules.integer(p->'report'->'input_tokens',(llm.spec->>'input_tokens')::numeric) AND (p->'report'->>'input_tokens')::bigint>=(SELECT cr.measured FROM provider_state.count_results cr JOIN provider_state.count_attempts ca ON ca.operation=cr.operation WHERE ca.capability=llm.capability)")
        text=replace(text,"p->'report'->'cached_tokens'='0'::jsonb AND p->'report'->'reasoning_tokens'='0'::jsonb", "provider_rules.integer(p->'report'->'cached_tokens',(p->'report'->>'input_tokens')::numeric) AND provider_rules.integer(p->'report'->'cache_write_tokens',(p->'report'->>'input_tokens')::numeric) AND provider_rules.integer(p->'report'->'reasoning_tokens',(p->'report'->>'output_tokens')::numeric)")
        text=replace(text,"provider_rules.price(jsonb_build_array(jsonb_set(llm.spec,'{max_output}',p->'report'->'output_tokens')),(SELECT rates FROM provider_rules.configuration WHERE id=1))","provider_rules.reported_bound(llm.spec,p->'report',(SELECT rates FROM provider_rules.configuration WHERE id=1))")
    return text

def scripts():
    verify()
    # Rules are installed before the dependent PL/pgSQL helpers execute.
    rules=projected('grant_rules.sql')+'\n'+(HERE/'rules.sql').read_text()
    op='\n'.join(projected(n) for n in ('schema.sql','routines.sql','financial_schema.sql'))+'\n'+rules+'\n'+'\n'.join(projected(n) for n in ('financial_routines.sql','bridge.sql','evidence.sql','application_grants.sql'))+'\n'+(HERE/'counter.sql').read_text()
    wit=rules+'\n'+projected('grant_witness.sql')+'\n'+(HERE/'counter_witness.sql').read_text()
    return {'operational':op,'witness':wit}

def contracts():
    """Inert projections for the EXISTING SQLPool identity/session port.

    No roles, grants, policy values or enrollment rows are inserted. An installer
    must review exact DDL/ACL fingerprints before injecting any runtime secret.
    """
    manifest=verify();build=digest(json.dumps(manifest,sort_keys=True).encode());out={}
    for role in ('operational','witness'):
        text=namespace((ROOT/f'deployment/sql/hosted-{role}-contract-v1.sql').read_text())
        text=text.replace("'witness'","'provider_witness'").replace('52-hosted-storage-contract-v1','52-real-hosted-storage-contract-v1')
        if role=='operational':text=replace(text,"'profile',(SELECT to_jsonb(p) FROM provider_state.service_profile p WHERE id=1)",f"'profile',jsonb_build_object('financialProfile','{VERSION}','sourceBuild','{build}')")
        out[role]=text
    return out
