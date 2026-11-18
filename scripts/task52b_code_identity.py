"""Deterministic CPython code identity, independently compiled from pinned source.

No marshal/pickle, execution, object IDs, refcounts, intern flags or adaptive
interpreter caches. Public semantic code fields and typed constants are retained.
"""
import ast
from hashlib import sha256
import json
from pathlib import Path
import struct
from types import CodeType,FunctionType

VERSION='52b-source-compiled-code-v1'
FIELDS=('co_argcount','co_posonlyargcount','co_kwonlyargcount','co_nlocals','co_stacksize','co_flags',
        'co_code','co_consts','co_names','co_varnames','co_filename','co_name','co_qualname',
        'co_firstlineno','co_linetable','co_exceptiontable','co_freevars','co_cellvars')

class IdentityRefused(ValueError):pass

def canonical(value):
    kind=type(value)
    if value is None:return ['none']
    if value is Ellipsis:return ['ellipsis']
    if kind is bool:return ['bool',value]
    if kind is int:return ['int',str(value)]
    if kind is str:return ['str',value]
    if kind is bytes:return ['bytes',value.hex()]
    if kind is float:return ['float64',struct.pack('>d',value).hex()]
    if kind is complex:return ['complex128',struct.pack('>dd',value.real,value.imag).hex()]
    if kind is tuple:return ['tuple',[canonical(v) for v in value]]
    if kind is frozenset:return ['frozenset',sorted((canonical(v) for v in value),key=encode)]
    if kind is CodeType:return ['code',[[n,canonical(getattr(value,n))] for n in FIELDS]]
    raise IdentityRefused('unsupported_code_value')

def encode(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')

def fingerprint(code,defaults=None,kwdefaults=None):
    if type(code)is not CodeType:raise IdentityRefused('code_type')
    if defaults is not None and type(defaults)is not tuple:raise IdentityRefused('defaults_type')
    if kwdefaults is not None and (type(kwdefaults)is not dict or any(type(k)is not str for k in kwdefaults)):
        raise IdentityRefused('kwdefaults_type')
    kw=None if kwdefaults is None else tuple(sorted(kwdefaults.items()))
    return sha256(encode([VERSION,canonical(code),canonical(defaults),canonical(kw)])).hexdigest()

def compiled(path,expected_source,qualname):
    path=Path(path).resolve();raw=path.read_bytes()
    if sha256(raw).hexdigest()!=expected_source:raise IdentityRefused('source_identity')
    # Compilation is data inspection only; module/class/function bodies never run.
    module=compile(raw,str(path),'exec',dont_inherit=True,optimize=0)
    tree=ast.parse(raw,filename=str(path));code=module;body=tree.body;node=None
    for part in qualname.split('.'):
        nodes=[n for n in body if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==part]
        codes=[v for v in code.co_consts if type(v)is CodeType and v.co_name==part]
        if len(nodes)!=1 or len(codes)!=1:raise IdentityRefused('source_qualname')
        node=nodes[0];code=codes[0];body=node.body
    if not isinstance(node,ast.FunctionDef):raise IdentityRefused('source_function')
    try:
        defaults=tuple(ast.literal_eval(n) for n in node.args.defaults) or None
        kw={a.arg:ast.literal_eval(v) for a,v in zip(node.args.kwonlyargs,node.args.kw_defaults) if v is not None} or None
    except (ValueError,TypeError):raise IdentityRefused('dynamic_default') from None
    return fingerprint(code,defaults,kw)

def require(function,path,expected_source,qualname,namespace):
    if (type(function)is not FunctionType or function.__globals__ is not namespace or
            function.__module__!=namespace['__name__'] or function.__qualname__!=qualname or
            function.__closure__ is not None):raise IdentityRefused('loaded_function_binding')
    expected=compiled(path,expected_source,qualname)
    actual=fingerprint(function.__code__,function.__defaults__,function.__kwdefaults__)
    if actual!=expected:raise IdentityRefused('loaded_code_identity')
    return expected
