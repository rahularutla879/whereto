"""Offline Q2 schema/evidence audit; no provider I/O, credentials or live runner.

Proposals are data only. Canonical bounds stay mandatory at local validation.
No historical validator code is executed; retained Git source is read as data.
"""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import subprocess
from scripts import task52_q1 as q1
from scripts import cloud_model52 as e
from scripts import cloud_model52_proposal as old_proposal
from scripts import cloud_model52_v4 as v4

VERSION='52b-q2-provider-compatibility-v1'


def expanded(schema):
    """Finite local-ref expansion; reject cycles, external refs and siblings."""
    def walk(node, stack=()):
        if isinstance(node,list):return [walk(v,stack) for v in node]
        if not isinstance(node,dict):return node
        if '$ref' in node:
            ref=node['$ref']
            if set(node)!={'$ref'} or not ref.startswith('#/$defs/') or ref in stack:
                raise ValueError('Unreviewed reference representation')
            return walk(schema['$defs'][ref[len('#/$defs/'):]],stack+(ref,))
        return {k:walk(v,stack) for k,v in node.items() if k!='$defs'}
    return walk(schema)


def restored(schema,marker):
    """Audit existing bounds-to-description projection, never runtime repair."""
    def walk(node):
        if isinstance(node,list):return [walk(v) for v in node]
        if not isinstance(node,dict):return node
        result={k:walk(v) for k,v in node.items()}
        description=result.get('description','')
        if marker in description:
            prefix,encoded=description.rsplit(marker,1)
            constraints=json.loads(encoded)
            if any(k in result for k in constraints):raise ValueError('Constraint collision')
            result.update(constraints)
            if prefix.strip():result['description']=prefix.rstrip()
            else:result.pop('description')
        return result
    return walk(deepcopy(schema))


def schema_shape(schema):
    """Count reference-expanded structure separately from syntax counts."""
    value=expanded(schema);properties=0;depth=0;container_depth=0
    def visit(node,level=0):
        nonlocal properties,depth
        if isinstance(node,dict):
            if node.get('type')=='object':
                if set(node.get('required',[]))!=set(node.get('properties',{})) or node.get('additionalProperties') is not False:
                    raise ValueError('Required/closed-object contract changed')
                properties+=len(node['properties']);level+=1;depth=max(depth,level)
            for v in node.values():visit(v,level)
        elif isinstance(node,list):
            for v in node:visit(v,level)
    visit(value)
    def containers(node,level=0):
        nonlocal container_depth
        if isinstance(node,dict):
            level+=int(node.get('type') in ('object','array'));container_depth=max(container_depth,level)
            for child in node.values():containers(child,level)
        elif isinstance(node,list):
            for child in node:containers(child,level)
    containers(value)
    return {'expandedObjectProperties':properties,'expandedObjectDepth':depth,
            'expandedContainerDepth':container_depth,
            'expandedUnionNodes':old_proposal.schema_stats(value)['unionNodes'],
            'expandedHash':e.digest(value),**old_proposal.schema_stats(schema)}


def proposals():
    canonical=e.wire_schema('openai');google=old_proposal.google_array_projection()
    anthropic=e.wire_schema('anthropic');factored=v4.anthropic_grammar_proposal()
    if expanded(restored(google,'Canonical array bounds: '))!=expanded(canonical):
        raise ValueError('Google composed-contract equivalence failed')
    if expanded(anthropic)!=expanded(factored):raise ValueError('Anthropic factoring changes structure')
    if expanded(restored(factored,'Validation constraints: '))!=expanded(canonical):
        raise ValueError('Anthropic canonical bounds/fields equivalence failed')
    return {
        'google':{'identity':'52b-q2-google-array-bounds-review-v1','provider':'google','model':'gemini-3.8-flash',
            'baseSchemaHash':e.digest(canonical),'proposedSchemaHash':e.digest(google),'schema':google,
            'transformation':'Existing unactivated google_array_projection; minItems/maxItems moved to descriptions only.',
            'wireAloneEquivalent':False,'composedCanonicalContractEquivalent':True,'activated':False,
            'canonicalSchemaChanged':False,'promptExamplesChanged':False,'remoteCompilationEstablished':False,
            'baseStats':schema_shape(canonical),'proposalStats':schema_shape(google)},
        'anthropic':{'identity':'52b-q2-anthropic-nullable-duration-review-v1','provider':'anthropic','model':'claude-haiku-5-5',
            'baseSchemaHash':e.digest(anthropic),'proposedSchemaHash':e.digest(factored),'schema':factored,
            'transformation':'Existing unactivated shared NullableDuration definition; exactly two repeated unions factored.',
            'wireAloneEquivalent':True,'composedCanonicalContractEquivalent':True,'activated':False,
            'canonicalSchemaChanged':False,'promptExamplesChanged':False,'remoteCompilationEstablished':False,
            'baseStats':schema_shape(anthropic),'proposalStats':schema_shape(factored)}}


def historical_evidence():
    """Allowlisted error categories and hashes only; never arbitrary error text."""
    q1.verify();before=q1.private_hashes();state=e.STATE
    with q1.offline():
        with sqlite3.connect(f'file:{state}/journal.sqlite?mode=ro',uri=True) as db:
            if db.execute('pragma integrity_check').fetchone()!=('ok',):raise ValueError('Journal integrity')
            rows=db.execute('select * from attempts order by rowid').fetchall()
            expected=json.loads(q1.MANIFEST.read_text())['paidEvidence']
            if [e.digest(r) for r in rows]!=expected['rowHashes'] or e.digest(before)!=expected['privateFileSetHash']:
                raise ValueError('Original evidence changed')
            metadata=json.loads(db.execute('select config from metadata').fetchone()[0])
        cases={c['id']:c for c in json.loads(e.CORPUS.read_text())['cases']};errors=[];v4_verified=0
        for row in rows:
            if row[0]=='openai':
                record=json.loads(row[5])
                if record.get('promptVersion')=='52b-v4-order-edge-quotes':
                    if e.digest(old_proposal.payload('openai',cases[row[1]]['text']))!=record['payloadHash']:
                        raise ValueError('Reviewed OpenAI v4 payload drift')
                    v4_verified+=1
                continue
            record=json.loads(row[5]);response=record['response'];error=response.get('error',{})
            if response.get('_http_status')!=400:raise ValueError('Unexpected original provider outcome')
            if row[0]=='google':
                if error.get('status')!='INVALID_ARGUMENT' or error.get('details'):raise ValueError('Unexpected Google evidence')
                cause='unresolved_generic_INVALID_ARGUMENT'
            else:
                if error.get('type')!='invalid_request_error' or not any(w in error.get('message','').lower() for w in ('grammar','compil','complex')):
                    raise ValueError('Expected grammar-size evidence absent')
                cause='structured_output_grammar_size_rejection'
            reproduced=None
            if row[1]=='journey-02' or row[0]=='anthropic':
                reproduced=e.digest(e.Adapter(row[0],None).payload(cases[row[1]]['text']))==record['payloadHash']
                if not reproduced:raise ValueError('Historical revised payload drift')
            errors.append({'slot':list(row[:3]),'rowHash':e.digest(row),'responseHash':e.digest(response),
                'payloadHash':record['payloadHash'],'configurationHash':record.get('configurationHash'),
                'HTTP':400,'cause':cause,'fieldDetailsAvailable':False,'completeModelOutput':False,
                'currentPureBuilderReproducesPayloadHash':reproduced,'reservationNanodollars':row[4]})
        ip=[]
        def denied(value):
            if isinstance(value,dict):return value.get('reason')=='API_KEY_IP_ADDRESS_BLOCKED' or any(denied(v) for v in value.values())
            if isinstance(value,list):return any(denied(v) for v in value)
            return value=='API_KEY_IP_ADDRESS_BLOCKED'
        for name,sha in before.items():
            if name.endswith('.json'):
                if denied(json.loads((state/name).read_text())):ip.append({'fileHash':sha,'category':'API_KEY_IP_ADDRESS_BLOCKED'})
        if not ip:raise ValueError('Retained IP restriction evidence missing')
        retained_source=subprocess.check_output(['git','show','8df31f2:scripts/cloud_model52.py'])
        # Static source evidence only; never import/compile/execute the old file.
        if b"'thinkingLevel': 'low'" not in retained_source or b"'responseSchema'" not in retained_source:
            raise ValueError('Original envelope source evidence mismatch')
    if before!=q1.private_hashes():raise ValueError('Audit changed private evidence')
    if v4_verified!=3:raise ValueError('Expected three recorded v4 responses')
    return {'errors':errors,'unchangedOpenAIV4PayloadHashesVerified':v4_verified,
        'IPRestrictionEvidence':ip,'originalGoogleEnvelope':{
        'retainedGitSnapshot':'8df31f2','sourceBlobSHA256':q1.sha(retained_source),
        'originalWireSchemaSHA256':metadata['wireSchemaHashes']['google'],
        'generationConfigKeys':['temperature','maxOutputTokens','thinkingConfig','responseMimeType','responseSchema'],
        'thinkingLevel':'low','firstPayloadReexecuted':False,
        'scope':'Source read as data + original payload/schema/count-diagnostic hashes; no exact historical environment claim.'},
        'journal':{'sha256':before['journal.sqlite'],'counts':{'openai':7,'google':2,'anthropic':1},'attempts':10,'remaining':584,
            'accountedNanodollars':47366625,'remainingNanodollars':11952633375,'privateFilesUnchanged':324,'persistentHalt':True}}


def static_payloads():
    """Pure construction only; no configuration() override or paid-source shim."""
    q1.verify();cases=json.loads(e.CORPUS.read_text())['cases'];counts={p:0 for p in e.CANDIDATES}
    for case in cases:
        for provider in counts:
            body=old_proposal.payload(provider,case['text'])
            if provider=='google':
                from scripts.cloud_model52_live import validate_google_request
                base=e.Adapter(provider,None).payload(case['text'])
                validate_google_request(base)
                base['systemInstruction']['parts'][0]['text']+=old_proposal.ADDITION
                if body!=base:raise ValueError('Reviewed v4 Google addition mismatch')
            if provider=='openai':
                if (body['model']!='gpt-6-luna' or body['reasoning']!={'effort':'none'} or body['store'] is not False
                    or body['max_output_tokens']!=2000 or body['text']['format']['strict'] is not True):raise ValueError('OpenAI envelope changed')
            elif provider=='anthropic':
                if body['max_tokens']!=2000 or body['thinking']!={'type':'disabled'}:raise ValueError('Anthropic settings changed')
            counts[provider]+=1
    return counts
