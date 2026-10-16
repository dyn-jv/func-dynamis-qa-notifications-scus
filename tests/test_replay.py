import unittest
from unittest.mock import Mock
from replay_52g import utc_time, reports, execute


class ReplayTests(unittest.TestCase):
    def test_requires_timezone(self):
        with self.assertRaises(ValueError):
            utc_time('2026-10-01T12:00:00')
        self.assertEqual(utc_time('2026-10-01T12:00:00-05:00').hour, 17)

    def test_partial_results_fail(self):
        client = Mock()
        client.execute_query.return_value.get_exceptions.return_value = ['truncated']
        with self.assertRaises(RuntimeError):
            execute(client, 'db', 'query')

    def test_results_normalized_and_ordered(self):
        client = Mock()
        client.execute_query.return_value.get_exceptions.return_value = []
        client.execute_query.return_value.primary_results = [[
            {'Kind':'event', 'Data':'{"unit":"2","timestamp":"2026-10-01"}'},
            {'Kind':'event', 'Data':{'unit':'1','timestamp':'2026-10-01'}}]]
        result = reports(execute(client, 'db', 'query'))
        self.assertEqual([v['unit'] for v in result['events']], ['1','2'])

    def test_empty_result_is_valid(self):
        self.assertEqual(reports([]), {'events':[], 'quality':[], 'summary':[]})

    def test_unknown_shape_fails(self):
        with self.assertRaises(ValueError):
            reports([('unexpected', {})])


if __name__ == '__main__':
    unittest.main()
