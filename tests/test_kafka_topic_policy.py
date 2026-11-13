"""Finite fixture admission must precede creation/publication and verify retention."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCENARIO = """
import json
import runpy
import sys
from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, 'scripts')
import kafka_topic_policy as policy
case, route = sys.argv[1:]
admin = Mock()
values, keys = (b'{}',)*3, (b'key',)*3

if case in ('full', 'cap', 'unknown', 'workspace'):
    measured = policy.Storage(policy.MAX_STORAGE_BYTES if case == 'cap' else 0,
                              0 if case == 'full' else 10*policy.GiB)
    module = runpy.run_path('scripts/kafka-probe.py' if route == 'probe'
                           else 'scripts/check-kafka-producer.py')
    admin.list_topics.return_value.topics = {}
    mutations = []
    def mutate(*args, **kwargs):
        mutations.append(args)
        raise RuntimeError('mutation_before_admission')
    if route == 'probe':module['publish'].__globals__['Producer'] = mutate
    admin.create_topics.side_effect = mutate
    operation = (lambda: module['publish'](admin, 'fresh',
                 SimpleNamespace(values=values, keys=keys))) if route == 'probe' else (
                 lambda: module['attempt'](Path('job'), Path('run'), 'fresh',
                                          Path('absent-receipt'), route == 'retry',
                                          'cluster', 'topic'))
    if route != 'probe':
        module['attempt'].__globals__.update(
            fixture=lambda *args: values, AdminClient=lambda *args: admin,
            read_battery_event=lambda value: {'vehicle_id': 'key'}, publish=mutate)
    error = (policy.FixturePolicyError('fixture_storage_inspection_failed')
             if case == 'unknown' else None)
    with patch.object(policy, 'storage', side_effect=error, return_value=measured), \
            patch.object(policy.shutil, 'disk_usage', return_value=SimpleNamespace(
                free=0 if case == 'workspace' else 10*policy.GiB)):
        try:
            operation()
        except policy.FixturePolicyError as error:
            assert str(error) == {'full':'fixture_free_disk_budget_exceeded',
                'cap':'fixture_retained_data_budget_exceeded',
                'workspace':'fixture_workspace_free_disk_budget_exceeded',
                'unknown':'fixture_storage_inspection_failed'}[case]
        else:
            raise AssertionError('unsafe_admission')
    assert not mutations and not Path('absent-receipt').exists()

elif case in ('mismatch', 'unknown_topic', 'fatal_config', 'nonexpiring', 'deadline'):
    calls = []
    clock = [0.0]
    def describe(resources, request_timeout):
        calls.append(request_timeout)
        future = Future()
        if case in ('fatal_config','deadline') or (
                case == 'unknown_topic' and len(calls) == 1):
            code = (policy.KafkaError.TOPIC_AUTHORIZATION_FAILED
                    if case == 'fatal_config'
                    else policy.KafkaError.UNKNOWN_TOPIC_OR_PART)
            future.set_exception(policy.KafkaException(policy.KafkaError(code)))
        else:
            config = dict(policy.topic_config())
            if case == 'mismatch':config['retention.bytes'] = '67108864'
            assert config['retention.ms'] == '-1'
            future.set_result({k:SimpleNamespace(value=v) for k,v in config.items()})
        return {resources[0]:future}
    admin.describe_configs.side_effect = describe
    with patch.object(policy.time, 'monotonic', lambda: clock[0]), patch.object(
            policy.time, 'sleep',
            lambda seconds: clock.__setitem__(0, clock[0]+seconds)):
        try:
            policy.verify_topic_config(admin, 'fresh')
        except policy.FixturePolicyError as error:
            assert str(error) == {'mismatch':'fixture_topic_config_differs',
                                 'deadline':'fixture_topic_config_deadline'}[case]
            if case == 'deadline':assert clock[0] == 15 and len(calls) <= 152
        except policy.KafkaException:
            assert case == 'fatal_config' and len(calls) == 1
        else:
            assert case in ('unknown_topic', 'nonexpiring')
            assert len(calls) == (2 if case == 'unknown_topic' else 1)

else:
    commands = []
    project = 'fleet-kafka-440-probe' if case == 'quarantine' else 'fresh-fixture'
    cluster = 'wrong' if case == 'cluster' else 'cluster'
    info = {'Config':{'Labels':{'com.docker.compose.project':project,
            'com.docker.compose.service':'kafka'},'Env':['KAFKA_CLUSTER_ID='+cluster]},
            'State':{'Running':True}, 'Mounts':[{'Type':'volume',
            'Name':project+'_kafka-data','Destination':policy.DATA_PATH,'RW':True}],
            'NetworkSettings':{'Ports':{'19092/tcp':[
                {'HostIp':'127.0.0.1','HostPort':'19092'}]}}}
    admin.list_topics.return_value = SimpleNamespace(cluster_id='cluster',
        brokers={1:SimpleNamespace(host='127.0.0.1',port=19092)})
    def command(*args):
        commands.append(args)
        if args == ('context', 'show'):return 'desktop-linux'
        if args[:2] == ('context','inspect'):
            return 'npipe:////./pipe/dockerDesktopLinuxEngine'
        if 'ps' in args:return 'abcdef123456'
        if 'inspect' in args:return json.dumps(info)
        if 'du' in args:return '1024 /var/lib/kafka/data'
        if 'df' in args:
            return 'not a df response' if case == 'malformed' else (
                'Filesystem 1024-blocks Used Available Capacity Mounted on\\n'
                '/dev/test 20971520 1048576 19922944 5% /data')
        raise AssertionError(args)
    with patch.object(policy, 'command', command), patch.dict(policy.os.environ,
            {'DOCKER_HOST':''}):
        try:
            measured = policy.storage(admin)
        except policy.FixturePolicyError as error:
            assert str(error) == {'quarantine':'historical_broker_quarantined',
                'cluster':'fixture_storage_cluster_differs',
                'malformed':'fixture_storage_measurement_invalid'}[case]
            if case in ('quarantine','cluster'):
                assert not any('exec' in args for args in commands)
        else:
            assert case == 'storage' and measured.allocated == 1024**2
            assert measured.free == 19922944*1024
"""


@pytest.mark.skipif(
    importlib.util.find_spec("confluent_kafka") is None,
    reason="Requires the existing pinned Kafka client; no broker is started.",
)
@pytest.mark.parametrize(
    ("case", "route"),
    [
        *(
            (case, route)
            for case in ("full", "cap", "unknown")
            for route in ("probe", "producer", "retry")
        ),
        ("workspace", "probe"),
        ("deadline", "policy"),
        *(
            (case, "policy")
            for case in (
                "mismatch",
                "unknown_topic",
                "fatal_config",
                "nonexpiring",
                "storage",
                "cluster",
                "quarantine",
                "malformed",
            )
        ),
    ],
)
def test_fixture_policy_refusal_and_readback(case: str, route: str) -> None:
    result = subprocess.run(
        [sys.executable, "-B", "-c", SCENARIO, case, route],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
