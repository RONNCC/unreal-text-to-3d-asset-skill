#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""End-to-end validation suite for the text-to-3d-asset repo (no GPU required).

What it proves, in this sandbox:
  T1  scripts/fooocus_gen.py  -> downloads a PNG from a Fooocus-API-shaped server
  T2  scripts/hunyuan_gen.py --server api  -> saves <name>_textured.glb
  T3  scripts/hunyuan_gen.py --server auto -> auto-detects api_server.py-style hosts
  T4  scripts/hunyuan_gen.py --server gradio fails cleanly when gradio_client
      is not installed (actionable message, no traceback)
  T5  the REAL scripts/glb_to_fbx.py converts the fixture GLB to a valid FBX
      with the texture embedded (King-of-the-road check: 'Kaydara FBX Binary')
  T6  scripts/validate_outputs.py accepts all artifacts produced above

Run with the repo venv python:
    .venv/bin/python tests/run_tests.py            # all tests
    .venv/bin/python tests/run_tests.py -k bpy     # only the Blender test
Needs: requests (venv). bpy + LD_LIBRARY_PATH stubs enable T5 (auto-skip otherwise).
"""
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tests", "mock_servers"))
sys.path.insert(0, os.path.join(REPO, "tests", "fixtures"))

PY = sys.executable  # run child scripts with the same interpreter/venv
STUBS = os.environ.get("BLENDER_STUB_LIBS", "/tmp/stublibs")


def have_bpy():
    env = dict(os.environ, LD_LIBRARY_PATH=STUBS)
    r = subprocess.run([PY, "-c", "import bpy"], env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return r.returncode == 0


def run_script(script, *args, expect_fail=False, env_extra=None, timeout=300):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    r = subprocess.run([PY, os.path.join(REPO, "scripts", script)] + list(args),
                       capture_output=True, text=True, timeout=timeout, env=env)
    out = r.stdout + r.stderr
    if not expect_fail and r.returncode != 0:
        raise AssertionError(f"{script} exited {r.returncode}:\n{out}")
    return out, r.returncode


class ServerFixture(unittest.TestCase):
    """Boot both mock servers in-process threads for the whole class."""
    fooocus_url = None
    hunyuan_url = None
    tmp = None

    @classmethod
    def setUpClass(cls):
        import mock_fooocus
        import mock_hunyuan_api
        import make_fixtures
        make_fixtures.main()  # ensure fixtures are fresh
        cls._srvs = []
        for mod in (mock_fooocus, mock_hunyuan_api):
            srv = ThreadingHTTPServer(("127.0.0.1", 0), mod.Handler)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            cls._srvs.append(srv)
        cls.fooocus_url = f"http://127.0.0.1:{cls._srvs[0].server_address[1]}"
        cls.hunyuan_url = f"http://127.0.0.1:{cls._srvs[1].server_address[1]}"
        cls.tmp = tempfile.mkdtemp(prefix="t3d_test_")

    @classmethod
    def tearDownClass(cls):
        for s in cls._srvs:
            s.shutdown()
        shutil.rmtree(cls.tmp, ignore_errors=True)


class TestPipeline(ServerFixture):
    image_png = None
    glb = None
    fbx = None

    def test_t1_fooocus_text_to_image(self):
        """fooocus_gen.py against mock Fooocus-API -> PNG on disk."""
        out = os.path.join(self.tmp, "image.png")
        txt, _ = run_script("fooocus_gen.py", "--prompt", "a fixture cube, centered",
                            "--out", out, "--url", self.fooocus_url)
        self.assertIn("[fooocus] done", txt)
        self.assertTrue(os.path.isfile(out), "PNG was not written")
        v, rc = run_script("validate_outputs.py", out)
        self.assertEqual(rc, 0)
        type(self).image_png = out

    def test_t2_hunyuan_api_mode(self):
        """hunyuan_gen.py --server api against mock api_server.py -> GLB."""
        outdir = self.tmp
        txt, _ = run_script("hunyuan_gen.py", "--image", self.image_png,
                            "--out", outdir, "--name", "Fixture",
                            "--server", "api", "--url", self.hunyuan_url)
        glb = os.path.join(outdir, "Fixture_textured.glb")
        self.assertIn("api mode", txt)
        self.assertTrue(os.path.isfile(glb), "GLB was not written")
        v, rc = run_script("validate_outputs.py", glb)
        self.assertEqual(rc, 0)
        type(self).glb = glb

    def test_t3_hunyuan_auto_detect(self):
        """--server auto must pick 'api' from /openapi.json, with no gradio_client installed."""
        self.assertIsNone(subprocess.run(
            [PY, "-c", "import gradio_client"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0 or None,
            "gradio_client unexpectedly installed — auto-detect test would not be meaningful")
        txt, _ = run_script("hunyuan_gen.py", "--image", self.image_png,
                            "--out", self.tmp, "--name", "Auto",
                            "--server", "auto", "--url", self.hunyuan_url)
        self.assertIn("auto-detected server type: api", txt)
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "Auto_textured.glb")))

    def test_t4_gradio_without_client_is_clean_error(self):
        """--server gradio without gradio_client: actionable message, not a traceback."""
        txt, rc = run_script("hunyuan_gen.py", "--image", self.image_png,
                             "--out", self.tmp, "--name", "Nope",
                             "--server", "gradio", "--url", self.hunyuan_url,
                             expect_fail=True)
        self.assertNotEqual(rc, 0)
        self.assertIn("pip install gradio_client", txt)
        self.assertNotIn("Traceback", txt)

    def test_t5_glb_to_fbx_real_blender_code_path(self):
        """The repo's actual glb_to_fbx.py (run inside bpy) converts GLB -> FBX."""
        if not have_bpy():
            self.skipTest("bpy (Blender module) not importable in this environment")
        fbx = os.path.join(self.tmp, "Fixture_textured.fbx")
        env = {"LD_LIBRARY_PATH": STUBS if os.path.isdir(STUBS) else ""}
        r = subprocess.run([PY, os.path.join(REPO, "tests", "run_blender_convert.py"),
                            "--src", self.glb, "--dst", fbx],
                           capture_output=True, text=True, env={**os.environ, **env}, timeout=600)
        self.assertEqual(r.returncode, 0, f"Blender conversion failed:\n{r.stdout}{r.stderr}")
        self.assertIn("BLENDER_EXPORT_DONE", r.stdout)
        self.assertTrue(os.path.isfile(fbx))
        v, rc = run_script("validate_outputs.py", fbx)
        self.assertEqual(rc, 0)
        with open(fbx, "rb") as f:
            data = f.read()
        self.assertIn(b"Kaydara FBX Binary", data[:32])
        self.assertIn(b"\x89PNG", data, "embedded texture (PNG) not found inside the FBX")
        type(self).fbx = fbx

    def test_t6_all_artifacts_validate(self):
        """Final sweep: every artifact the pipeline produced passes validation."""
        artifacts = [self.image_png, self.glb]
        if self.fbx:
            artifacts.append(self.fbx)
        txt, rc = run_script("validate_outputs.py", *artifacts)
        self.assertEqual(rc, 0)
        self.assertIn("all artifacts valid", txt)


if __name__ == "__main__":
    if "-k" in sys.argv:
        i = sys.argv.index("-k")
        unittest.main(argv=[sys.argv[0], "-k", sys.argv[i + 1], "-v"])
    else:
        unittest.main(argv=[sys.argv[0], "-v"])
