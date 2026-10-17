"""Run Bandit on bounded Python text. No PR code is executed."""
import json, os, subprocess, sys, tempfile

def run_bandit(files: list[dict], timeout: int = 8) -> dict:
    sources=[f for f in files if f.get("filename", "").endswith(".py") and f.get("content") is not None]
    if not sources: return {"tool":"bandit","status":"skipped","reason":"No Python source content supplied.","findings":[]}
    with tempfile.TemporaryDirectory(prefix="prmentor-bandit-") as root:
        paths=[]
        for i,item in enumerate(sources[:20]):
            path=os.path.join(root,f"source_{i}.py")
            with open(path,"w",encoding="utf-8") as stream: stream.write(str(item["content"])[:100_000])
            paths.append((path,item["filename"]))
        try: proc=subprocess.run([sys.executable,"-m","bandit","-f","json","-q",*[p[0] for p in paths]],capture_output=True,text=True,timeout=timeout,shell=False)
        except (FileNotFoundError,subprocess.TimeoutExpired): return {"tool":"bandit","status":"unavailable","reason":"Bandit is not installed or exceeded its time limit.","findings":[]}
        if "No module named bandit" in proc.stderr: return {"tool":"bandit","status":"unavailable","reason":"Bandit is not installed.","findings":[]}
        try: raw=json.loads(proc.stdout or "{}")
        except ValueError: raw={}
        reverse={p:f for p,f in paths}
        findings=[{"tool":"bandit","file_path":reverse.get(x.get("filename"),"unknown"),"line":x.get("line_number"),"code":x.get("test_id"),"message":x.get("issue_text"),"severity":x.get("issue_severity")} for x in raw.get("results",[])]
        return {"tool":"bandit","status":"completed","exit_code":proc.returncode,"findings":findings}
