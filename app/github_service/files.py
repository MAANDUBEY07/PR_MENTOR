from app.github_service.pull_requests import fetch_pull_request

async def get_pull_request_files(url: str):
    _, files = await fetch_pull_request(url)
    return files

def parse_patch(file: dict) -> dict:
    patch = file.get("patch")
    if patch is None:
        return {"path":file.get("filename", ""),"status":file.get("status", "unknown"),"added":0,"removed":0,"hunks":[],"truncated":True}
    import re
    hunks=[]; current=None; old_line=new_line=0
    for raw in patch.splitlines():
        match=re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@",raw)
        if match:
            old_line,new_line=map(int,match.groups()); current={"header":raw,"lines":[]}; hunks.append(current); continue
        if current is None: continue
        if raw.startswith("+") and not raw.startswith("+++"):
            current["lines"].append({"kind":"added","line":new_line,"text":raw[1:]}); new_line+=1
        elif raw.startswith("-") and not raw.startswith("---"):
            current["lines"].append({"kind":"removed","line":old_line,"text":raw[1:]}); old_line+=1
        else:
            if raw.startswith(" "): current["lines"].append({"kind":"context","line":new_line,"text":raw[1:]})
            old_line+=1; new_line+=1
    return {"path":file.get("filename", ""),"previous_path":file.get("previous_filename"),"status":file.get("status", "unknown"),"added":file.get("additions",0),"removed":file.get("deletions",0),"hunks":hunks,"truncated":False}
