import os,subprocess,tempfile,unittest
from pathlib import Path

class PublishRaceTests(unittest.TestCase):
 def test_publication_retries_without_losing_other_jobs_commit(self):
  helper=Path(__file__).with_name('push_refresh.sh').resolve()
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);remote=root/'remote.git';ours=root/'ours';other=root/'other'
   def git(*args,cwd=None):return subprocess.run(['git',*args],cwd=cwd,check=True,capture_output=True)
   git('init','--bare',str(remote));git('clone',str(remote),str(ours));git('checkout','-b','main',cwd=ours)
   git('config','user.name','test',cwd=ours);git('config','user.email','test@example.com',cwd=ours)
   (ours/'initial').write_text('initial');git('add','.',cwd=ours);git('commit','-m','initial',cwd=ours);git('push','origin','main',cwd=ours)
   git('clone','-b','main',str(remote),str(other));git('config','user.name','test',cwd=other);git('config','user.email','test@example.com',cwd=other)
   (other/'other-job').write_text('other');git('add','.',cwd=other);git('commit','-m','other',cwd=other)
   (ours/'our-job').write_text('ours');git('add','.',cwd=ours);git('commit','-m','ours',cwd=ours)
   real_git=git('rev-parse','--git-dir',cwd=ours) # Verify the temporary checkout before wrapping git.
   import shutil
   executable=shutil.which('git');bin_dir=root/'bin';bin_dir.mkdir();marker=root/'race'
   wrapper=bin_dir/'git'
   wrapper.write_text('#!/usr/bin/env bash\nif [[ "$1" == push && ! -f "$RACE_MARKER" ]]; then\n touch "$RACE_MARKER"\n "$REAL_GIT" -C "$OTHER_REPO" push origin HEAD:main >/dev/null 2>&1\nfi\nexec "$REAL_GIT" "$@"\n')
   wrapper.chmod(0o755)
   env={**os.environ,'PATH':str(bin_dir)+':'+os.environ['PATH'],'REAL_GIT':executable,'OTHER_REPO':str(other),'RACE_MARKER':str(marker)}
   subprocess.run(['bash',str(helper)],cwd=ours,env=env,check=True,capture_output=True)
   for name in ['our-job','other-job']:self.assertTrue(git('--git-dir='+str(remote),'show','main:'+name).stdout)
