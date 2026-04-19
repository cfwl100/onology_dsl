import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRAPPER_DIRS = [
    'object-query',
    'aggregate-query',
    'association-query',
    'link-query',
    'create-object',
    'update-object',
    'delete-object',
    'upsert-batch',
]
SHARED_DIR = ROOT / 'shared'


def write_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def run_script(script: Path, *args: str):
    return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, check=False)


def pipeline_sample(name: str):
    samples = {
        'object-query': {
            'version':'1.0','schemaRef':'crm','strict':True,'operation':'QUERY',
            'objects':[{'objectType':'Customer','alias':'c'}],
            'conditions':{'all':[['c.status','EQ','active'],[{'$fn':'LENGTH','args':['c.name']},'GT',3]]},
            'returns':[['FIELDS','c',['id','name']],['EXPR',{'$fn':'UPPER','args':['c.name']},'nameUpper']],
            'orders':[['ORDER_BY','c','name','ASC']],
            'maxResults':10,
        },
        'aggregate-query': {
            'version':'1.0','schemaRef':'crm','strict':True,'operation':'AGGREGATE',
            'objects':[{'objectType':'Order','alias':'o'}],
            'returns':[['GROUP_BY','o.status','status'],['METRIC','COUNT','o.id','orderCount']],
        },
        'association-query': {
            'version':'1.0','schemaRef':'crm','strict':True,'operation':'ASSOCIATION_QUERY',
            'objects':[{'objectType':'Customer','alias':'c'},{'objectType':'Order','alias':'o'}],
            'relationships':[{'relationshipType':'PLACED','alias':'r1','from':'c','to':'o'}],
            'conditions':['c.id','EQ','cust-001'],
            'returns':[['FIELDS','o',['id','status']]],
        },
        'link-query': {
            'version':'1.0','schemaRef':'crm','strict':True,'operation':'LINK_QUERY',
            'objects':[{'objectType':'Customer','alias':'c'},{'objectType':'Order','alias':'o'}],
            'conditions':['c.id','EQ','cust-001'],
            'linkQuery':{'mode':'LIST','relationshipType':'PLACED','sourceRef':'c','targetRef':'o','direction':'OUTBOUND'},
            'returns':[['FIELDS','o',['id','status']]],
        },
        'create-object': {
            'version':'1.0','schemaRef':'crm','strict':True,'operation':'CREATE',
            'objects':[{'objectType':'Customer','alias':'c'}],
            'mutation':{'data':{'name':'Alice','email':'alice@example.com'}},
        },
        'update-object': {
            'version':'1.0','schemaRef':'crm','strict':True,'operation':'UPDATE',
            'objects':[{'objectType':'Customer','alias':'c'}],
            'conditions':['c.id','EQ','cust-001'],
            'mutation':{'scope':'ONE','set':{'status':'inactive'}},
        },
        'delete-object': {
            'version':'1.0','schemaRef':'crm','strict':True,'operation':'DELETE',
            'objects':[{'objectType':'Customer','alias':'c'}],
            'conditions':['c.id','EQ','cust-001'],
            'mutation':{'scope':'ONE'},
        },
        'upsert-batch': {
            'version':'1.0','schemaRef':'crm','strict':True,'operation':'UPSERT',
            'objects':[{'objectType':'Customer','alias':'c'}],
            'mutation':{'matchBy':['email'],'data':{'email':'alice@example.com','name':'Alice'}},
        },
    }
    return samples[name]


def test_python_script_inventory_matches_expected():
    """
    测试 Python 脚本清单是否与预期一致。
    兼容 Windows, Linux, macOS。
    """
    # 1. 定义需要排除的目录名称 (使用集合提高查找效率)
    EXCLUDE_DIRS = {'tests', '__pycache__', '.git', 'venv', '.venv'}

    # 2. 构建实际文件集合
    actual = set()
    for path in ROOT.rglob('*.py'):
        # 获取相对于 ROOT 的路径对象
        rel_path = path.relative_to(ROOT)

        # 【关键优化】检查路径的任何部分是否在排除列表中
        # 这比字符串包含判断更准确，避免误杀如 'my_tests_utils.py' 这样的文件
        if any(part in EXCLUDE_DIRS for part in rel_path.parts):
            continue

        # 【关键兼容】统一转换为 POSIX 风格字符串 ('/' 分隔)
        # 这样无论 Windows 还是 Linux，结果都是 'dir/subdir/file.py'
        actual.add(rel_path.as_posix())

    # 3. 构建预期文件集合 (保持原有的 '/' 风格)
    expected = {
        f'shared/{name}'
        for name in ('soql_to_oql.py', 'oql_builder.py', 'oql_validator.py')
    }

    for dirname in WRAPPER_DIRS:
        for script_name in ('soql_to_oql.py', 'oql_builder.py', 'oql_validator.py'):
            expected.add(f'{dirname}/scripts/{script_name}')

    # 4. 断言
    # 如果失败，pytest 会显示清晰的差异对比
    assert actual == expected, (
        f"Script inventory mismatch.\n"
        f"Missing scripts: {expected - actual}\n"
        f"Unexpected scripts: {actual - expected}"
    )


def test_shared_soql_to_oql_supports_functions_and_orders(tmp_path):
    payload = pipeline_sample('object-query')
    src = tmp_path / 'in.json'
    out = tmp_path / 'converted.json'
    write_json(src, payload)
    result = run_script(SHARED_DIR / 'soql_to_oql.py', '--input', str(src), '--output', str(out))
    assert result.returncode == 0, result.stderr + result.stdout
    data = json.loads(out.read_text(encoding='utf-8'))
    assert data['conditions']['kind'] == 'GROUP'
    assert data['returns'][1]['kind'] == 'EXPR'
    assert data['orders'][0]['direction'] == 'ASC'


def test_shared_oql_builder_applies_defaults(tmp_path):
    payload = {
        'schemaRef': 'crm',
        'operation': 'QUERY',
        'objects': [{'objectType': 'Customer', 'alias': 'c'}],
        'returns': [{'kind': 'FIELDS', 'ref': 'c', 'fields': ['id']}],
    }
    src = tmp_path / 'in.json'
    out = tmp_path / 'built.json'
    write_json(src, payload)
    result = run_script(SHARED_DIR / 'oql_builder.py', '--input', str(src), '--output', str(out))
    assert result.returncode == 0, result.stderr + result.stdout
    data = json.loads(out.read_text(encoding='utf-8'))
    assert data['version'] == '1.0'
    assert data['strict'] is True
    assert data['maxResults'] == 1000


def test_shared_oql_validator_rejects_nested_batch(tmp_path):
    payload = {
        'version': '1.0',
        'schemaRef': 'crm',
        'strict': True,
        'operation': 'BATCH',
        'mutation': {
            'atomic': True,
            'items': [
                {
                    'operation': 'BATCH',
                    'mutation': {'atomic': True, 'items': []},
                }
            ],
        },
    }
    src = tmp_path / 'invalid.json'
    write_json(src, payload)
    result = run_script(SHARED_DIR / 'oql_validator.py', '--input', str(src))
    assert result.returncode != 0
    assert 'BATCH items only allow CREATE/UPDATE/DELETE/UPSERT' in result.stdout


def test_wrapper_pipeline_for_each_operation(tmp_path):
    for dirname in WRAPPER_DIRS:
        base = ROOT / dirname / 'scripts'
        src = tmp_path / f'{dirname}-in.json'
        converted = tmp_path / f'{dirname}-converted.json'
        built = tmp_path / f'{dirname}-built.json'
        write_json(src, pipeline_sample(dirname))

        result_convert = run_script(base / 'soql_to_oql.py', '--input', str(src), '--output', str(converted))
        assert result_convert.returncode == 0, f'{dirname} convert failed: {result_convert.stderr} {result_convert.stdout}'

        result_build = run_script(base / 'oql_builder.py', '--input', str(converted), '--output', str(built))
        assert result_build.returncode == 0, f'{dirname} build failed: {result_build.stderr} {result_build.stdout}'

        result_validate = run_script(base / 'oql_validator.py', '--input', str(built))
        assert result_validate.returncode == 0, f'{dirname} validate failed: {result_validate.stderr} {result_validate.stdout}'
        assert '"success": true' in result_validate.stdout.lower()
