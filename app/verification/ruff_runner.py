"""Run Ruff on supplied Python text without executing submitted code."""
import json, os, subprocess, sys, tempfile

def run_ruff(files: list[dict], timeout: int = 8) -> dict:
    sources = [f for f in files if f.get("filename", "").endswith(".py") and f.get("content") is not None]
    if not sources: return {"tool":"ruff","status":"skipped","reason":"No Python source content supplied.","findings":[]}
    with tempfile.TemporaryDirectory(prefix="prmentor-ruff-") as root:
        paths=[]
        for i, item in enumerate(sources[:20]):
            path=os.path.join(root, f"source_{i}.py")
            with open(path,"w",encoding="utf-8") as stream: stream.write(str(item["content"])[:100_000])
            paths.append((path,item["filename"]))
        try:
            proc=subprocess.run([sys.executable,"-m","ruff","check","--output-format","json",*[p[0] for p in paths]],capture_output=True,text=True,timeout=timeout,shell=False)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return {"tool":"ruff","status":"unavailable","reason":"Ruff is not installed or exceeded its time limit.","findings":[]}
        if "No module named ruff" in proc.stderr:
            return {"tool":"ruff","status":"unavailable","reason":"Ruff is not installed.","findings":[]}
        try: raw=json.loads(proc.stdout or "[]")
        except ValueError: raw=[]
        reverse={p:f for p,f in paths}
        findings=[{"tool":"ruff","file_path":reverse.get(x.get("filename"),"unknown"),"line":x.get("location",{}).get("row"),"code":x.get("code"),"message":x.get("message")} for x in raw]
        return {"tool":"ruff","status":"completed","exit_code":proc.returncode,"findings":findings}
