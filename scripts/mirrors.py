"""Push data/ to Hugging Face, Kaggle and Zenodo.

    python scripts/mirrors.py hf       # needs HF_TOKEN (optional HF_REPO, default <user>/instagram-top-accounts)
    python scripts/mirrors.py kaggle   # needs KAGGLE_USERNAME + KAGGLE_KEY
    python scripts/mirrors.py zenodo   # needs ZENODO_TOKEN; new version, state kept in zenodo.json

Each command exits 0 and prints "skip" when its credentials are missing.
"""
import datetime as dt
import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")
SLUG = "instagram-top-accounts"
TITLE = "Most followed Instagram accounts: daily follower counts"
SOURCE = "https://fastsocial.co/most-followed-instagram-accounts"
STATS = "https://fastsocial.co/instagram-stats"
GITHUB = "https://github.com/FastSocialCo/instagram-top-accounts"


def manifest():
    with open(os.path.join(DATA, "manifest.json"), encoding="utf-8") as f:
        return json.load(f)


def description(m):
    return (
        "Daily public follower counts for the most-followed Instagram accounts, from FastSocial Top Charts. "
        "%d readings of %d accounts, %s to %s. The top 500 accounts are read every day, the rest every five days. "
        "Private accounts are left out. Licence: CC BY 4.0, credit FastSocial and link to %s. "
        "Columns and method: %s#data. Updated daily: %s"
        % (m["rows"], m["accounts"], m["start"], m["end"], SOURCE, STATS, GITHUB)
    )


# ---------------------------------------------------------------- Hugging Face
def hf():
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("hf: skip (no HF_TOKEN)")
        return
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    repo = os.environ.get("HF_REPO") or "%s/%s" % (api.whoami()["name"], SLUG)
    api.create_repo(repo, repo_type="dataset", exist_ok=True, private=False)
    m = manifest()
    n = m["rows"]
    size = "n<1K" if n < 1000 else "1K<n<10K" if n < 10000 else "10K<n<100K" if n < 100000 else "100K<n<1M"
    card = (
        "---\n"
        "license: cc-by-4.0\n"
        "pretty_name: %s\n"
        "task_categories:\n- time-series-forecasting\n- tabular-regression\n"
        "tags:\n- instagram\n- social-media\n- followers\n- time-series\n"
        "size_categories:\n- %s\n"
        "configs:\n- config_name: daily\n  data_files: daily.csv\n  default: true\n"
        "- config_name: latest\n  data_files: latest.csv\n"
        "---\n\n" % (TITLE, size)
    )
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
        body = f.read()
    tmp = tempfile.mkdtemp()
    try:
        for name in ("daily.csv", "latest.csv", "manifest.json"):
            shutil.copy(os.path.join(DATA, name), tmp)
        shutil.copytree(os.path.join(DATA, "monthly"), os.path.join(tmp, "monthly"))
        with open(os.path.join(tmp, "README.md"), "w", encoding="utf-8") as f:
            f.write(card + body.replace("data/", ""))
        api.upload_folder(folder_path=tmp, repo_id=repo, repo_type="dataset",
                          commit_message="Daily update %s" % m["end"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("hf: https://huggingface.co/datasets/%s" % repo)


# ---------------------------------------------------------------- Kaggle
def kaggle():
    user = os.environ.get("KAGGLE_USERNAME")
    if not user or not os.environ.get("KAGGLE_KEY"):
        print("kaggle: skip (no KAGGLE_USERNAME/KAGGLE_KEY)")
        return
    m = manifest()
    ref = "%s/%s" % (user, SLUG)
    tmp = tempfile.mkdtemp()
    try:
        for name in ("daily.csv", "latest.csv"):
            shutil.copy(os.path.join(DATA, name), tmp)
        meta = {
            "title": "Most Followed Instagram Accounts Daily",
            "id": ref,
            "subtitle": "Daily public follower counts of the biggest Instagram accounts",
            "description": description(m),
            "keywords": ["social networks", "internet", "time series"],
            "licenses": [{"name": "CC-BY-4.0"}],
            "resources": [
                {"path": "daily.csv", "description": "Every reading since %s" % m["start"]},
                {"path": "latest.csv", "description": "Newest reading per account, ordered by rank"},
            ],
        }
        with open(os.path.join(tmp, "dataset-metadata.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=1)
        exists = subprocess.run(["kaggle", "datasets", "status", ref], capture_output=True, text=True)
        if exists.returncode == 0 and "ready" in (exists.stdout + exists.stderr).lower():
            cmd = ["kaggle", "datasets", "version", "-p", tmp, "-m", "Daily update %s" % m["end"]]
        else:
            cmd = ["kaggle", "datasets", "create", "-p", tmp, "--public"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip()
        print("kaggle:", out[-400:])
        if r.returncode != 0 or "error" in out.lower():
            sys.exit(1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("kaggle: https://www.kaggle.com/datasets/%s" % ref)


# ---------------------------------------------------------------- Zenodo
ZAPI = "https://zenodo.org/api"
ZSTATE = os.path.join(ROOT, "zenodo.json")


def zreq(method, url, token, body=None, raw=None, ctype="application/json"):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    if data is not None:
        req.add_header("Content-Type", ctype)
    with urllib.request.urlopen(req, timeout=120) as r:
        txt = r.read()
    return json.loads(txt) if txt else {}


def zenodo():
    token = os.environ.get("ZENODO_TOKEN")
    if not token:
        print("zenodo: skip (no ZENODO_TOKEN)")
        return
    m = manifest()
    state = {}
    if os.path.exists(ZSTATE):
        with open(ZSTATE, encoding="utf-8") as f:
            state = json.load(f)
    if state.get("last_end") == m["end"]:
        print("zenodo: skip (already published %s)" % m["end"])
        return
    if state.get("latest_id"):
        nv = zreq("POST", "%s/deposit/depositions/%s/actions/newversion" % (ZAPI, state["latest_id"]), token)
        draft = zreq("GET", nv["links"]["latest_draft"], token)
        for f in draft.get("files", []):
            zreq("DELETE", f["links"]["self"], token)
    else:
        draft = zreq("POST", ZAPI + "/deposit/depositions", token, body={})
    bucket = draft["links"]["bucket"]
    gz = gzip.compress(open(os.path.join(DATA, "daily.csv"), "rb").read())
    zreq("PUT", bucket + "/instagram-top-accounts-daily.csv.gz", token, raw=gz, ctype="application/octet-stream")
    zreq("PUT", bucket + "/latest.csv", token, raw=open(os.path.join(DATA, "latest.csv"), "rb").read(),
         ctype="application/octet-stream")
    meta = {"metadata": {
        "upload_type": "dataset",
        "title": TITLE,
        "creators": [{"name": "FastSocial"}],
        "description": description(m),
        "license": "cc-by-4.0",
        "access_right": "open",
        "version": m["end"],
        "publication_date": dt.date.today().isoformat(),
        "keywords": ["Instagram", "social media", "followers", "time series", "open data"],
        "related_identifiers": [
            {"identifier": SOURCE, "relation": "isDerivedFrom", "resource_type": "dataset", "scheme": "url"},
            {"identifier": STATS, "relation": "isDocumentedBy", "scheme": "url"},
            {"identifier": GITHUB, "relation": "isSupplementTo", "scheme": "url"},
        ],
    }}
    zreq("PUT", draft["links"]["self"], token, body=meta)
    pub = zreq("POST", draft["links"]["publish"], token)
    state.update({"latest_id": pub["id"], "concept_doi": pub.get("conceptdoi"),
                  "latest_doi": pub.get("doi"), "last_end": m["end"]})
    with open(ZSTATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1)
        f.write("\n")
    print("zenodo: published %s (concept %s)" % (pub.get("doi"), pub.get("conceptdoi")))


if __name__ == "__main__":
    {"hf": hf, "kaggle": kaggle, "zenodo": zenodo}[sys.argv[1]]()
