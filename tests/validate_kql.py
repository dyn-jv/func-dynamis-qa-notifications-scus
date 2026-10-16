"""Read-only integration tests: run the actual detector against synthetic KQL rows."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
from replay_52g import CLUSTER, DATABASE, detector_query, execute, reports

# Unordered input, independent units, threshold/gap boundaries, nulls and duplicates.
FIXTURE = '''
datatable(timestamp:datetime, UNIT_NUM:string, Breaker:long, Speed:real) [
 datetime(2026-10-01T00:00:01Z), "threshold", 0, 0.0,
 datetime(2026-10-01T00:00:00Z), "threshold", 1, 7000.0,
 datetime(2026-10-01T00:00:00Z), "above", 1, 7100.0,
 datetime(2026-10-01T00:00:01Z), "above", 0, 0.0,
 datetime(2026-10-01T00:00:00Z), "below", 1, 6999.0,
 datetime(2026-10-01T00:00:01Z), "below", 0, 8000.0,
 datetime(2026-10-01T00:00:00Z), "gap5", 1, 7000.0,
 datetime(2026-10-01T00:00:05Z), "gap5", 0, 0.0,
 datetime(2026-10-01T00:00:00Z), "gap6", 1, 7000.0,
 datetime(2026-10-01T00:00:06Z), "gap6", 0, 0.0,
 datetime(2026-10-01T00:00:00Z), "nullspeed", 1, real(null),
 datetime(2026-10-01T00:00:01Z), "nullspeed", 0, 0.0,
 datetime(2026-10-01T00:00:00Z), "baseline", 0, 8000.0,
 datetime(2026-10-01T00:00:01Z), "baseline", 0, 8000.0,
 datetime(2026-10-01T00:00:02Z), "baseline", 1, 8000.0,
 datetime(2026-10-01T00:00:00Z), "duplicate", 1, 8000.0,
 datetime(2026-10-01T00:00:00Z), "duplicate", 1, 8000.0,
 datetime(2026-10-01T00:00:01Z), "duplicate", 0, 0.0,
 datetime(2026-10-01T00:00:00Z), "conflict", 1, 8000.0,
 datetime(2026-10-01T00:00:01Z), "conflict", 1, 8000.0,
 datetime(2026-10-01T00:00:01Z), "conflict", 0, 8000.0,
 datetime(2026-10-01T00:00:02Z), "conflict", 0, 0.0,
 datetime(2026-10-01T00:00:00Z), "invalid", 1, 8000.0,
 datetime(2026-10-01T00:00:01Z), "invalid", long(null), 8000.0,
 datetime(2026-10-01T00:00:02Z), "invalid", 0, 0.0,
 datetime(2026-10-01T00:00:03Z), "invalid", 1, 8000.0,
 datetime(2026-10-01T00:00:04Z), "invalid", 0, 0.0,
 datetime(2026-10-01T00:00:00Z), "unitA", 1, 8000.0,
 datetime(2026-10-01T00:00:01Z), "unitB", 0, 0.0
]
'''

if __name__ == '__main__':
    with KustoClient(KustoConnectionStringBuilder.with_az_cli_authentication(CLUSTER)) as client:
        result = reports(execute(client, DATABASE, detector_query() + FIXTURE + '| invoke Detect52G()'))
        actual = {row['unit']: row['classification'] for row in result['events']}
        expected = {'threshold':'qualified','above':'qualified','below':'not_running',
                    'gap5':'qualified','gap6':'uncertain','nullspeed':'uncertain',
                    'duplicate':'qualified','invalid':'qualified'}
        assert actual == expected, (actual, expected)
        assert len(result['events']) == len(expected)
        assert len(result['quality']) == 2, result['quality']
        assert next(v for v in result['summary'] if v['unit']=='duplicate')['duplicates_collapsed'] == 1
        empty = reports(execute(client, DATABASE, detector_query() + FIXTURE + '| where false | invoke Detect52G()'))
        assert empty == {'events':[], 'quality':[], 'summary':[]}, empty
        print('PASS: actual KQL synthetic fixtures and empty input')
