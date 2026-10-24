import contextlib
import io
from pathlib import Path
import tempfile
import unittest
import tracebench as tb

ROOT = Path(__file__).resolve().parents[1]


class ReplayTests(unittest.TestCase):
    def fixtures(self, name):
        return tb.evaluate(tb.load(ROOT / 'examples' / (name + '.jsonl')))

    def test_known_failures(self):
        self.assertEqual(tb.summarize(self.fixtures('baseline'))['rules'],
                         {'unsafe-retry': 1, 'late-handoff': 1, 'missing-handoff': 1})

    def test_candidate_passes(self):
        self.assertEqual(tb.summarize(self.fixtures('candidate'))['findings'], 0)

    def test_missing_scenario_rejected(self):
        with self.assertRaises(tb.TraceError):
            tb.compare(self.fixtures('baseline'), self.fixtures('candidate')[:1])

    def test_regression_not_hidden_by_improvement(self):
        before = [dict(id='x', findings=[dict(rule='unsafe-retry')])]
        after = [dict(id='x', findings=[dict(rule='missing-handoff')])]
        self.assertEqual(tb.compare(before, after)['changes'][0]['introduced'], {'missing-handoff': 1})

    def test_idempotent_retry_allowed(self):
        trace = tb.load(ROOT / 'examples/baseline.jsonl')[0]
        for event in trace['events'][:2]:
            event['idempotent'] = True
        self.assertNotIn('unsafe-retry', tb.summarize(tb.evaluate([trace]))['rules'])

    def test_handoff_boundary(self):
        trace = tb.load(ROOT / 'examples/candidate.jsonl')[0]
        trace['events'][-1]['at_ms'] = 5000
        self.assertEqual(tb.summarize(tb.evaluate([trace]))['findings'], 0)
        trace['events'][-1]['at_ms'] = 5001
        self.assertEqual(tb.summarize(tb.evaluate([trace]))['findings'], 1)

    def test_invalid_inputs(self):
        for content in ['', '{bad', '{"id":"x","events":[]}',
                        '{"id":"x","events":[{"type":"answer","at_ms":-1}]}',
                        '{"id":"x","events":[{"type":"unknown","at_ms":0}]}']:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as folder:
                path = Path(folder)/'input.jsonl'
                path.write_text(content)
                with self.assertRaises(tb.TraceError):
                    tb.load(path)

    def test_html_escapes_trace_content(self):
        runs = self.fixtures('candidate')
        runs[0]['id'] = '<script>alert(1)</script>'
        report = tb.html_report(runs, runs)
        self.assertNotIn('<script>', report)
        self.assertIn('&lt;script&gt;', report)

    def test_report_deterministic(self):
        self.assertEqual(tb.html_report(self.fixtures('baseline'), self.fixtures('candidate')),
                         tb.html_report(self.fixtures('baseline'), self.fixtures('candidate')))

    def test_ci_exit_status(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(tb.main(['check', str(ROOT/'examples/baseline.jsonl'), '--fail-on-findings']), 1)
            self.assertEqual(tb.main(['check', str(ROOT/'examples/candidate.jsonl'), '--fail-on-findings']), 0)


if __name__ == '__main__':
    unittest.main()
