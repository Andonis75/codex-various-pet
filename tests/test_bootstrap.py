"""Bootstrap state transitions, without networking or modifying a real venv."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


BOOTSTRAP = Path(__file__).resolve().parents[1] / "tools/bootstrap.py"


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="various-pet-bootstrap-test-")
        self.addCleanup(self.temporary.cleanup)
        # Windows runners may expose TEMP as RUNNER~1 while bootstrap resolves
        # it to runneradmin. Compare canonical paths, not two valid spellings.
        self.repo = (Path(self.temporary.name) / "checkout").resolve()
        (self.repo / "tools").mkdir(parents=True)
        spec = importlib.util.spec_from_file_location("bootstrap_under_test", BOOTSTRAP)
        self.bootstrap = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.bootstrap)
        self.bootstrap.__file__ = str(self.repo / "tools/bootstrap.py")
        self.environment = self.repo / ".venv"
        self.interpreter = self.environment / ("Scripts/python.exe" if self.bootstrap.sys.platform == "win32" else "bin/python")
        self.result = {"python": str(self.interpreter), "repo": str(self.repo), "version": "0.1.0"}

    def fake_environment(self):
        self.interpreter.parent.mkdir(parents=True)
        self.interpreter.write_bytes(b"test-only placeholder, never executed")

    def probe(self, *, repo=None):
        result = dict(self.result)
        if repo is not None:
            result["repo"] = str(repo)
        return subprocess.CompletedProcess([], 0, json.dumps(result), "")

    def test_reuses_ready_local_environment_and_emits_machine_readable_route(self):
        self.fake_environment()
        output = io.StringIO()
        with patch.object(self.bootstrap.subprocess, "run", return_value=self.probe()) as run, redirect_stdout(output):
            self.assertEqual(self.bootstrap.main(), 0)
        self.assertEqual(json.loads(output.getvalue()), self.result)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0][0], str(self.interpreter))
        self.assertNotIn("pip", run.call_args.args[0])

    def test_creates_and_installs_missing_environment_in_checkout_only(self):
        output = io.StringIO()
        calls = []

        def process(arguments, **kwargs):
            calls.append(arguments)
            if arguments[1:3] == ["-m", "venv"]:
                self.fake_environment()
                return subprocess.CompletedProcess(arguments, 0)
            if len(calls) == 2:
                return subprocess.CompletedProcess(arguments, 1, "", "missing dependency")
            return self.probe() if arguments[1] == "-c" else subprocess.CompletedProcess(arguments, 0)

        with patch.object(self.bootstrap.subprocess, "run", side_effect=process), redirect_stdout(output):
            self.assertEqual(self.bootstrap.main(), 0)
        self.assertEqual(len(calls), 4)
        self.assertEqual(calls[0][1:], ["-m", "venv", str(self.environment)])
        self.assertEqual(calls[2], [str(self.interpreter), "-m", "pip", "install", "-e", str(self.repo)])
        self.assertEqual(json.loads(output.getvalue()), self.result)

    def test_existing_incomplete_environment_is_not_replaced(self):
        self.environment.mkdir()
        marker = self.environment / "user-note.txt"
        marker.write_bytes(b"preserve")
        with patch.object(self.bootstrap.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "inspect it instead"):
                self.bootstrap.main()
        run.assert_not_called()
        self.assertEqual(marker.read_bytes(), b"preserve")

    def test_pip_failure_is_reported_and_does_not_emit_success_json(self):
        self.fake_environment()
        failure = subprocess.CalledProcessError(1, ["pip", "install"])
        output = io.StringIO()
        with patch.object(self.bootstrap.subprocess, "run", side_effect=[subprocess.CompletedProcess([], 1, "", "missing dependency"), failure]), redirect_stdout(output):
            with self.assertRaises(subprocess.CalledProcessError):
                self.bootstrap.main()
        self.assertEqual(output.getvalue(), "")

    def test_wrong_checkout_import_is_rejected_even_after_install(self):
        self.fake_environment()
        foreign = self.repo.parent / "different-checkout"
        output = io.StringIO()
        with patch.object(self.bootstrap.subprocess, "run", side_effect=[self.probe(repo=foreign), subprocess.CompletedProcess([], 0), self.probe(repo=foreign)]), redirect_stdout(output):
            with self.assertRaisesRegex(ValueError, "does not belong"):
                self.bootstrap.main()
        self.assertEqual(output.getvalue(), "")

    def test_unsupported_python_is_rejected_before_any_install(self):
        with patch.object(self.bootstrap.sys, "version_info", (3, 9)), patch.object(self.bootstrap.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "3.10"):
                self.bootstrap.main()
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
