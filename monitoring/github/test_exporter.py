import unittest
from urllib.error import HTTPError

from exporter import Cache, snapshot, state


class ExporterTest(unittest.TestCase):
    def setUp(self):
        self.run = {"id": 42, "run_number": 9, "status": "completed", "conclusion": "success", "run_started_at": "2026-11-26T10:00:00Z", "updated_at": "2026-11-26T10:02:00Z"}
        self.deploy = {"name": "Deploy to staging / Deploy to staging", "status": "completed", "conclusion": "failure", "started_at": "2026-11-26T10:01:00Z", "completed_at": "2026-11-26T10:02:00Z"}

    def api(self, path):
        if path.startswith("runs/"):
            return {"jobs": [self.deploy], "total_count": 1}
        if "branch=develop" in path:
            return {"workflow_runs": [self.run]}
        return {"workflow_runs": [self.run, dict(self.run, id=41, run_number=8, conclusion="failure")]}

    def test_workflows_and_deploy_separate(self):
        body = snapshot(self.api)
        self.assertIn('github_actions_success_ratio{workflow="FishTrack CI"} 0.5\n', body)
        self.assertIn('github_actions_latest_run_duration_seconds{workflow="FishTrack CI"} 120.0\n', body)
        self.assertIn('github_actions_stage_state{state="failure",stage="deploy"} 1\n', body)
        self.assertIn('github_actions_stage_duration_seconds{stage="deploy"} 60.0\n', body)
        self.assertIn('github_actions_stage_state{state="missing",stage="publish"} 1\n', body)

    def test_empty(self):
        body = snapshot(lambda _: {"workflow_runs": []})
        self.assertIn('github_actions_sample_size{workflow="Monitoring CI"} 0\n', body)
        self.assertNotIn("github_actions_success_ratio", body)
        self.assertIn('github_actions_stage_state{state="missing",stage="deploy"} 1\n', body)

    def test_statuses(self):
        self.assertEqual(state({"status": "queued"}), "queued")
        self.assertEqual(state({"status": "completed", "conclusion": "skipped"}), "skipped")
        self.assertEqual(state({"status": "completed", "conclusion": "timed_out"}), "failure")

    def test_api_failure_invalidates_snapshot(self):
        cache = Cache()
        cache.refresh(self.api)
        self.assertIn(b"github_actions_api_up 1", cache.read())
        previous = cache.last_success

        def failure(_):
            raise HTTPError("https://api.github.com", 403, "secret-example", {}, None)

        cache.refresh(failure)
        self.assertIn(b"github_actions_api_up 0", cache.read())
        self.assertNotIn(b"github_actions_stage_state", cache.read())
        self.assertNotIn(b"secret-example", cache.read())
        self.assertEqual(previous, cache.last_success)

    def test_no_duplicate_job_claim(self):
        def api(path):
            if path.startswith("runs/"):
                return {"jobs": [self.deploy, self.deploy], "total_count": 2}
            return self.api(path)

        self.assertIn('github_actions_stage_state{state="missing",stage="deploy"} 1\n', snapshot(api))


if __name__ == "__main__":
    unittest.main()
