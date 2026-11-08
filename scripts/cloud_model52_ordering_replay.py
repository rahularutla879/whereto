"""Read-only recorded-output replay; no credential access or model transport.

Writes only the explicitly chosen report. Never writes the paid journal, its
sidecars or historical classifications. Network is prohibited during scoring.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
from unittest.mock import patch

from backend.ai import Interpretation, parse_interpretation
from backend.journey import validate_journey
from scripts import cloud_model52 as e
from scripts import cloud_model52_audit as audit
from scripts import cloud_model52_offline as scorer
from scripts import cloud_model52_ordering as ordering


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cloud_rows(db, correction_directory):
    results = []
    cases = {c['id']: c for c in e.corpus()['cases']}
    for row in db.execute('select * from attempts order by rowid'):
        record = json.loads(row[5])
        output = {'slot': list(row[:3]), 'originalRowHash': e.digest(row),
            'originalDatabaseState': row[3], 'originalClassification': record['status'],
            'originalConfigurationHash': record.get('configurationHash'),
            'originalReservationNanodollars': row[4], 'responseHash': e.digest(record.get('response')),
            'historicalClassificationChanged': False}
        if row[:3] == ('openai', 'journey-01', 1):
            audit.effective_record(row, correction_directory)
            output['historicalDecoderCorrectionVerified'] = True
        if row[0] != 'openai':
            output['replay'] = 'no_model_output_provider_error'
        else:
            content, _, status = e.Adapter('openai', None).decode(record['response'])
            output['decodedStatus'] = status
            if status == 'complete':
                ai = parse_interpretation(content)
                result = scorer.score(cases[row[1]], content)
                output.update(structuredValid=result['structuredValid'],
                    unchangedTrustedAccepted=result['validatedAccepted'],
                    unchangedScorerFailures=result.get('automatedFailures'),
                    proposedOrdering=ordering.inspect_order(cases[row[1]]['text'], ai),
                    fullyCorrect=None, independentHumanSignoff=False)
                output['proposedCombinedAcceptedExtraction'] = bool(result['structuredValid']
                    and result['validatedAccepted'] and output['proposedOrdering']['outcome'] != 'clarification_required')
        results.append(output)
    return results


def qwen_rows(path):
    data = json.loads(path.read_text())
    text_by_case = {r['case']: r['text'] for r in data['baseline']['rows']}
    results = []
    for cohort in ('baseline', 'finalRuntimeSmoke'):
        for index, row in enumerate(data[cohort]['rows']):
            raw = row.get('raw')
            item = {'cohort': cohort, 'case': row['case'], 'row': index,
                'rawHash': e.digest(raw), 'originalExecutionStatus': row.get('executionStatus')}
            if not isinstance(raw, dict):
                item['replay'] = 'no_recorded_extraction'
            else:
                ai = Interpretation.model_validate(raw)
                text = row.get('text') or text_by_case[row['case']]
                item['sourceHash'] = e.digest(text)
                original = ai.model_dump(mode='json')
                explanation, clarification = validate_journey(text, ai.model_copy(deep=True))
                item.update(unchangedCanonicalJourney={'explanation': explanation, 'clarification': clarification},
                    proposedOrdering=ordering.inspect_order(text, ai))
                assert ai.model_dump(mode='json') == original
            results.append(item)
    return results


def replay(state=None):
    state = Path(state or e.STATE)
    path = state / 'journal.sqlite'
    before = file_hash(path)
    evidence = {str(p.relative_to(state)): file_hash(p) for p in state.rglob('*') if p.is_file()}
    db = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    try:
        if db.execute('pragma integrity_check').fetchone() != ('ok',): raise ValueError('Journal integrity')
        rows = db.execute('select * from attempts order by rowid').fetchall()
        if len(rows) != 10 or sum(r[4] for r in rows) != 47366625 or rows[-1][3] != 'recorded_halted':
            raise ValueError('Expected existing ten-row halted journal; never reset it')
        # A hard no-network boundary for all replayed providers, not just mocks
        # in individual validators. No provider/token-counting transport used.
        with patch('socket.create_connection', side_effect=AssertionError('Offline replay only')), patch('requests.sessions.Session.send', side_effect=AssertionError('Offline replay only')):
            cloud = cloud_rows(db, state / 'corrections')
            fixture = e.ROOT / 'backend/evaluation/results-task50e-model-investigation.json'
            qwen = qwen_rows(fixture)
        root_hash = e.digest(db.execute('select config from metadata').fetchone()[0])
    finally:
        db.close()
    if file_hash(path) != before or evidence != {str(p.relative_to(state)): file_hash(p) for p in state.rglob('*') if p.is_file()}:
        raise ValueError('Offline replay changed paid evidence')
    return {'version': ordering.VERSION, 'orderingModuleSHA256': file_hash(Path(ordering.__file__)),
        'scope': 'Offline ordering only; not complete semantic correctness or production activation.',
        'cloud': cloud, 'qwen': qwen,
        'qwenSummary': {cohort: dict(Counter(r['proposedOrdering']['outcome'] for r in qwen
            if r['cohort'] == cohort and 'proposedOrdering' in r)) for cohort in ('baseline', 'finalRuntimeSmoke')},
        'qwenFixtureSHA256': file_hash(fixture),
        'journal': {'sha256Before': before, 'sha256After': file_hash(path),
            'rootHash': root_hash, 'allTenRowHashes': [e.digest(r) for r in rows],
            'allIgnoredFilesUnchanged': True, 'ignoredFilesVerified': len(evidence),
            'providerCounts': dict(Counter(r[0] for r in rows)), 'totalAttempts': 10,
            'remainingAttempts': 584, 'accountedNanodollars': 47366625,
            'remainingNanodollars': 11952633375, 'persistentHalt': True},
        'requestsSent': {'inference': 0, 'counting': 0, 'otherProvider': 0},
        'historicalClassificationsUnchanged': True, 'independentHumanSignoff': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Never allow the output report to target private evidence or runtime files.
    destination = args.output.resolve()
    if destination.parent != (e.ROOT / 'docs').resolve() or destination.name != 'task52-ordering-safety-replay.json':
        raise SystemExit('Output must be docs/task52-ordering-safety-replay.json')
    result = replay()
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'version': result['version'], 'cloudRows': len(result['cloud']),
        'qwenSummary': result['qwenSummary'], 'journalUnchanged': True}))
