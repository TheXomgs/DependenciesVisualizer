from subprocess import DEVNULL, Popen
from requests import Session
import yaml, os

def get_file_status_symbol(status: str):
    if status == "added":
        return "+"
    elif status == "removed":
        return "-"
    elif status == "modified":
        return "~"
    elif status == "renamed":
        return "@"
    else:
        return status

def get_dependencies(repo_url: str, tag: str, depth: int=100, token: str=None):
    _, uri = repo_url.split("://")
    registry, owner, repo = uri.split("/", 3)

    s = Session()
    s.auth = (token,'')

    req = s.get(f"https://api.{registry}/repos/{owner}/{repo}/tags?per_page={depth}")
    if not req:
        print(req.content)
        return None
    
    target_commit = None
    tags: dict = req.json()
    for commit in tags:
        if commit["name"] == tag:
            target_commit = commit["commit"]["sha"]
            break
    else:
        return None
    
    req = s.get(f"https://api.{registry}/repos/{owner}/{repo}/commits?sha={target_commit}&per_page={depth}")
    if not req:
        print(req.content)
        return None
    
    commits = (commit for commit in req.json())
    
    dependencies = []
    prev_commit = next(commits)
    for commit in commits:
        req = s.get(f'https://api.{registry}/repos/{owner}/{repo}/compare/{commit["sha"]}...{prev_commit["sha"]}')
        if not req:
            continue
        
        diff = req.json()
        dependencies.append({
            "sha": commit["sha"],
            "message": commit["commit"]["message"],
            "parents": commit["parents"],
            "files": [f'{get_file_status_symbol(file["status"])} /{file["filename"]}'  for file in diff["files"]] or ["Merge commit"]
        })
        prev_commit = commit

    s.close()
    
    return dependencies

def genuml(tag: str, commits: list[dict]):
    uml = ["@startuml"]
    uml.append(f'node "{tag}" as repo')
    links = []
    for commit in commits:
        uml.extend([
            f'card {commit["sha"]} [',
            commit["message"] or commit["sha"],
            '--',
            '\n'.join(commit["files"]),
            ']',
        ])
        links.extend([f'{parent["sha"]} --> {commit["sha"]}' for parent in commit["parents"]])
    uml.append(f'{commits[0]["sha"]} --> repo')
    uml.extend(links)

    uml.append("@enduml")
    return "\n".join(uml)

def main():
    with open("config.yml", "r") as file:
        config = yaml.safe_load(file)

    token = config["token"]
    repo = config["repo"]
    tag = config["tag"]
    depth = config.get("depth", 1000)
    executable = config.get("puml_executable")

    deps = get_dependencies(repo, tag, depth, token)
    if not deps:
        print("No such tag!")
        return
    uml = genuml(tag, deps)

    _, uri = repo.split("://")
    _, _, repo_name = uri.split("/", 3)
    out_name = f'{repo_name}@{tag}'

    if not os.path.exists("out"):
        os.mkdir("out")

    with open(f"out/{out_name}.puml", "w") as file:
        file.write(uml)

    if executable:
        proc = Popen(f"java -DPLANTUML_LIMIT_SIZE=102400 -jar {executable} ./out", stdout=DEVNULL)
        proc.wait()


if __name__ == "__main__":
    main()