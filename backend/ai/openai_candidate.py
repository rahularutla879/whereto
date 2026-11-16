"""Inactive GPT-6 Luna AIProvider seam; frozen V5.1 request, no network/key loading.

An exchange must be owned by the protected issuer/dispatcher, not the browser.
Normal create_provider deliberately does not import or select this class.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json

from backend.ai import AIError, parse_interpretation
from backend.provider_responses import HTTPResult, ProviderResponseError, strict_object
from backend.source_text import valid_input

PROMPT_FILE = Path(__file__).resolve().parents[2] / 'docs/task52-cloud-prompt-v51-REVIEWED-v1.json'
PROMPT_SHA = '02b20af7fbabeb93d9d305a10c1327b8e97043b2b995f830fc88ab44f218f5da'
MODEL = 'gpt-6-luna'


def request_bytes(text):
    valid_input(text)
    raw = PROMPT_FILE.read_bytes()
    if sha256(raw).hexdigest() != PROMPT_SHA:
        raise AIError('Candidate prompt identity refused')
    template = strict_object(raw)['frozenRequestTemplate']
    body = deepcopy(template)
    if body['model'] != MODEL or body['input'][-1] != {'role': 'user', 'content': ''}:
        raise AIError('Candidate configuration refused')
    body['input'][-1]['content'] = text
    return json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _require_wire_fields(value, node, root):
    """Required-key audit only; existing Pydantic validators own value semantics."""
    if '$ref' in node:
        node = root['$defs'][node['$ref'].split('/')[-1]]
    if 'anyOf' in node:
        if value is None and any(n.get('type') == 'null' for n in node['anyOf']):
            return
        branches = [n for n in node['anyOf'] if n.get('type') != 'null']
        if len(branches) != 1:
            raise ValueError('Unsupported wire shape')
        return _require_wire_fields(value, branches[0], root)
    expected = node.get('type')
    matches = {'object':type(value) is dict, 'array':type(value) is list,
               'string':type(value) is str, 'integer':type(value) is int,
               'number':type(value) in (int,float), 'boolean':type(value) is bool,
               'null':value is None}
    if expected in matches and not matches[expected]:
        raise ValueError('Wrong wire shape')
    if isinstance(value, dict) and node.get('type') == 'object':
        if set(node.get('required', ())) - set(value) or set(value) - set(node.get('properties', {})):
            raise ValueError('Incomplete wire object')
        for key, item in value.items():
            _require_wire_fields(item, node['properties'][key], root)
    elif isinstance(value, list) and 'items' in node:
        for item in value:
            _require_wire_fields(item, node['items'], root)


class OpenAICandidateProvider:
    def __init__(self, exchange=None):
        self._exchange = exchange
        self.raw_request = None
        self.raw_response = None
        self.usage = None

    def interpret(self, text):
        self.raw_request = self.raw_response = self.usage = None
        if self._exchange is None:
            raise AIError('Qualified model, counting, credentials, financial grant and reviewed transport are not enrolled')
        self.raw_request = request_bytes(text)
        response = self._exchange(self.raw_request)  # Exact bytes, once, no retry.
        if type(response) is not HTTPResult:
            raise AIError('Invalid provider response')
        self.raw_response = response  # Immutable raw evidence, separate from parsing.
        try:
            value = response.decode()
            if (type(value) is not dict or value.get('model') != MODEL or
                    value.get('error') is not None or value.get('status') != 'completed'):
                raise ValueError()
            output = value.get('output')
            if (type(output) is not list or len(output) != 1 or
                    output[0].get('type') != 'message' or output[0].get('role') != 'assistant' or
                    output[0].get('status') != 'completed'):
                raise ValueError()
            content = output[0].get('content')
            if (type(content) is not list or len(content) != 1 or
                    content[0].get('type') != 'output_text' or type(content[0].get('text')) is not str):
                raise ValueError()
            usage = value.get('usage')
            if (type(usage) is not dict or any(type(usage.get(k)) is not int or usage[k] < 0
                    for k in ('input_tokens', 'output_tokens', 'total_tokens')) or
                    usage['input_tokens'] + usage['output_tokens'] != usage['total_tokens'] or
                    usage['output_tokens'] > 2000 or usage['input_tokens'] > 12000 or
                    set(usage) - {'input_tokens','output_tokens','total_tokens','input_tokens_details','output_tokens_details'}):
                raise ValueError()
            for key, field in [('input_tokens_details','cached_tokens'), ('output_tokens_details','reasoning_tokens')]:
                details = usage.get(key, {})
                if type(details) is not dict or set(details) - {field} or type(details.get(field, 0)) is not int or details.get(field, 0) != 0:
                    raise ValueError()
            self.usage = deepcopy(usage)  # Reported usage is NOT pre-send cost authority.
            schema = json.loads(self.raw_request)['text']['format']['schema']
            _require_wire_fields(strict_object(content[0]['text']), schema, schema)
            return parse_interpretation(content[0]['text'])
        except (ProviderResponseError, ValueError, TypeError, KeyError, AttributeError):
            raise AIError('Cloud interpretation refused; raw response retained, no retry') from None
