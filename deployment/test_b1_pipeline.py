"""Nonsecret pipe fixtures only; no encryption key, SQL, backup or restore."""
from tempfile import TemporaryDirectory
from pathlib import Path
import os,sys,time,unittest
from unittest.mock import patch
from .b1_pipeline import stream,Refused

class Tests(unittest.TestCase):
    def test_complete_pipe_and_no_overwrite(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'fictional.cms';env={'PATH':os.defpath}
            result=stream([sys.executable,'-c',"print('FICTIONAL')"],[sys.executable,'-c','import sys;sys.stdout.write(sys.stdin.read().upper())'],p,producer_env=env)
            self.assertEqual(p.read_bytes(),b'FICTIONAL\n');self.assertEqual(result['bytes'],10);self.assertEqual(p.stat().st_mode&0o777,0o600)
            with patch('subprocess.Popen',side_effect=AssertionError('Existing generation must refuse before subprocess')):
                with self.assertRaises(Refused):stream([sys.executable,'-c','pass'],[sys.executable,'-c','pass'],p,producer_env=env)
            self.assertEqual(p.read_bytes(),b'FICTIONAL\n')
    def test_producer_failure_never_becomes_backup(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'failed.cms'
            with self.assertRaises(Refused):stream([sys.executable,'-c','raise SystemExit(1)'],[sys.executable,'-c','import sys;sys.stdout.write(sys.stdin.read())'],p,producer_env={})
            self.assertFalse(p.exists());self.assertTrue(Path(str(p)+'.partial').exists())
    def test_timeout_kills_both_stages(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'timeout.cms';start=time.monotonic()
            with self.assertRaises(Refused):stream([sys.executable,'-c','import time;time.sleep(10)'],[sys.executable,'-c','import sys;sys.stdout.write(sys.stdin.read())'],p,producer_env={},seconds=.05)
            self.assertLess(time.monotonic()-start,3);self.assertFalse(p.exists())
    def test_deadline_cannot_be_increased(self):
        with self.assertRaises(Refused):stream([],[],'/not-used',producer_env={},seconds=61)
    def test_encryptor_failure_preserves_only_failed_partial(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'encrypt-failed.cms'
            with self.assertRaises(Refused):stream([sys.executable,'-c',"print('FICTIONAL')"],[sys.executable,'-c','raise SystemExit(1)'],p,producer_env={})
            self.assertFalse(p.exists());self.assertTrue(Path(str(p)+'.partial').exists())
    def test_public_output_directory_refused_before_process(self):
        with TemporaryDirectory() as tmp:
            Path(tmp).chmod(0o755)
            with patch('subprocess.Popen',side_effect=AssertionError('No subprocess')):
                with self.assertRaises(Refused):stream([],[],Path(tmp)/'bad.cms',producer_env={})
    def test_warning_with_zero_exit_is_not_certified(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'warning.cms'
            with self.assertRaises(Refused):stream([sys.executable,'-c',"import sys;print('FICTIONAL');print('FICTIONAL WARNING',file=sys.stderr)"],[sys.executable,'-c','import sys;sys.stdout.write(sys.stdin.read())'],p,producer_env={})
            self.assertFalse(p.exists())
