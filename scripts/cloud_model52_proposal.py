"""Unactivated common prompt proposal. Pure construction/static audit only.

Not imported by runtime, active adapters, readiness or paid journal recovery.
"""
import copy
from scripts import cloud_model52 as e

VERSION = '52b-v4-PROPOSED-order-edge-quotes'
ADDITION = ('For each order edge, source must be one contiguous verbatim span containing '
    'BOTH referenced stop.source phrases and the explicit ordering cue. Bind the '
    'correct occurrence indexes and direction; cue words alone are insufficient. '
    'Never infer edges from list order. If the relationship is ambiguous, preserve '
    'the original conflicting clause in clarification; do not guess.\n')


def messages(text):
    value = copy.deepcopy(e.messages(text))
    value[0]['content'] += ADDITION
    return value


def payload(provider, text):
    value = copy.deepcopy(e.Adapter(provider, None).payload(text))
    if provider == 'openai':
        value['input'] = messages(text)
    elif provider == 'anthropic':
        value['system'] += ADDITION
    else:
        value['systemInstruction']['parts'][0]['text'] += ADDITION
    return value


def schema_stats(node):
    """Static counts are not provider grammar compilation/readiness evidence."""
    stats = {'unionNodes': 0, 'optionalProperties': 0, 'maxArrayBounds': [], 'refs': []}
    def walk(value, path='$'):
        if isinstance(value, dict):
            stats['unionNodes'] += int('anyOf' in value or isinstance(value.get('type'), list))
            if value.get('type') == 'object':
                stats['optionalProperties'] += len(set(value['properties']) - set(value.get('required', [])))
            if 'maxItems' in value:
                stats['maxArrayBounds'].append({'path': path, 'value': value['maxItems']})
            if '$ref' in value:
                stats['refs'].append({'path': path, 'value': value['$ref']})
            for key, child in value.items():
                walk(child, path + '.' + key)
        elif isinstance(value, list):
            for i, child in enumerate(value):
                walk(child, path + f'[{i}]')
    walk(node)
    return stats


def google_array_projection():
    """Unactivated wire candidate: remove array-bound grammar multiplication.

    Every original bound remains described and enforced by canonical parsing.
    This is a support/review artifact, not proof of the generic 400's cause.
    """
    schema = copy.deepcopy(e.wire_schema('google'))
    def walk(node):
        if isinstance(node, dict):
            moved = {k: node.pop(k) for k in ('minItems', 'maxItems') if k in node}
            if moved:
                import json
                node['description'] = (node.get('description', '') +
                    ' Canonical array bounds: ' + json.dumps(moved, sort_keys=True)).strip()
            for child in node.values(): walk(child)
        elif isinstance(node, list):
            for child in node: walk(child)
    walk(schema)
    return schema
