"""Carrying the data directory between machines over a git remote.

The engine and the packs are shareable; a ledger is not. So the data directory
is its own git repository, with its own remote, and the tool repo never sees it.
That keeps `studykit` publishable while your history lives somewhere private.

Both directions matter, and for different reasons. `push` is backup: the ledger
is the only thing here that cannot be recomputed. `pull` is correctness: the due
queue is a function of the ledger, so a machine working from a stale one is
given the wrong questions and then collides on the next push.

Only the source of truth is tracked. `state.json`, `metrics.json` and the
dashboard are pure functions of the ledger and are rebuilt on every write, so
committing them would produce a diff on every command and merge conflicts on
every second machine.

git is invoked as a subprocess, not imported. Nothing here adds a dependency,
and every command no-ops cleanly when sync is not configured.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .config import Profile, StudykitError, data_dir

#: Derived artefacts. Rebuilt from the ledger, so never committed.
IGNORED = ("state.json", "metrics.json", "dashboard.html", "*.tmp", ".DS_Store")

GITIGNORE = "# Derived from ledger.jsonl on every write. Not history.\n" + "\n".join(IGNORED) + "\n"

#: Two machines studying between syncs both append to the end of the ledger,
#: which is a conflict on every single line-based merge. `union` takes both
#: sides, which is the correct resolution for an append-only log: no row is
#: ever edited, so there is nothing to choose between. `ledger.read` sorts by
#: timestamp, so the interleaving the union produces does not matter either.
GITATTRIBUTES = "# Append-only. Concurrent appends are both kept, not reconciled.\nledger.jsonl merge=union\n"


def _git(*args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    if shutil.which("git") is None:
        raise StudykitError("git is not on PATH, so `study sync` cannot run.")
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd or data_dir()),
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise StudykitError(f"git {args[0]} failed: {detail[-1] if detail else 'no output'}")
    return result


def is_repo(path: Path | None = None) -> bool:
    """True only when the data directory is a repository *in its own right*.

    The default data directory lives inside the studykit checkout, so a plain
    `rev-parse --git-dir` walks up and finds the tool's repo. Treating that as a
    hit would commit a private ledger into a public repository. The top level
    has to be the data directory itself.
    """
    path = path or data_dir()
    if not path.exists():
        return False
    result = _git("rev-parse", "--show-toplevel", cwd=path, check=False)
    if result.returncode != 0:
        return False
    return Path(result.stdout.strip()).resolve() == path.resolve()


def _has_commits() -> bool:
    return _git("rev-parse", "--verify", "HEAD", check=False).returncode == 0


def _current_branch() -> str:
    return _git("rev-parse", "--abbrev-ref", "HEAD", check=False).stdout.strip()


def _remote_url() -> str:
    return _git("remote", "get-url", "origin", check=False).stdout.strip()


def _dirty() -> list[str]:
    lines = _git("status", "--porcelain").stdout.splitlines()
    return [line[3:] for line in lines if line.strip()]


def _ahead(branch: str) -> int | None:
    """Commits not yet on the remote, or None when the remote is unknown here."""
    return _count(f"origin/{branch}..HEAD", branch)


def _behind(branch: str) -> int | None:
    """Commits on the remote not yet here, or None when the remote is unknown here.

    Counted against the last fetch, not the live remote, so it is only as fresh
    as the last `fetch`. `pull` fetches first; `status` deliberately does not,
    because reporting state should not need the network.
    """
    return _count(f"HEAD..origin/{branch}", branch)


def _count(rev_range: str, branch: str) -> int | None:
    if _git("rev-parse", "--verify", f"origin/{branch}", check=False).returncode != 0:
        return None
    out = _git("rev-list", "--count", rev_range, check=False).stdout.strip()
    return int(out) if out.isdigit() else None


def _ensure_repo_files(path: Path | None = None) -> None:
    """Write the two control files, without clobbering a user's edits.

    Called from `pull` as well as `init`, because a data repo created before
    the merge driver existed would otherwise conflict on its first pull and
    never get the file that would have prevented it.
    """
    path = path or data_dir()
    for name, body in ((".gitignore", GITIGNORE), (".gitattributes", GITATTRIBUTES)):
        target = path / name
        if not target.exists():
            target.write_text(body, encoding="utf-8")


def configured(profile: Profile) -> bool:
    return bool(profile.sync_remote)


def require_configured(profile: Profile) -> None:
    if not configured(profile):
        raise StudykitError(
            "Sync is not set up. Create a private repository, then run "
            "`./study sync init git@github.com:you/studykit-data.git`."
        )


def init(profile: Profile, remote: str, branch: str = "", *, auto: bool = False) -> dict:
    """Make the data directory a git repo pointed at `remote`, and push it.

    Refuses when the remote already carries history, because the right move
    there is to clone it into the data directory rather than to graft onto it.
    """
    branch = branch or profile.sync_branch or "main"
    path = data_dir()
    path.mkdir(parents=True, exist_ok=True)

    fresh = not is_repo(path)
    if fresh:
        _git("init", "-b", branch)

    if _remote_url():
        _git("remote", "set-url", "origin", remote)
    else:
        _git("remote", "add", "origin", remote)

    _ensure_repo_files(path)

    _git("fetch", "origin", check=False)
    remote_exists = _git("rev-parse", "--verify", f"origin/{branch}", check=False).returncode == 0
    if remote_exists and not _has_commits():
        raise StudykitError(
            f"{remote} already has a {branch} branch with history. Clone it into "
            f"{path} instead of initialising over it:\n"
            f"  rm -rf {path} && git clone {remote} {path}"
        )

    # Every profile change has to land before the push, or the first commit
    # leaves profile.json dirty and `sync status` reports work outstanding
    # that nobody did.
    profile.sync_remote = remote
    profile.sync_branch = branch
    if auto:
        profile.sync_auto = True
    profile.save()

    result = push(profile, message="studykit: initial sync", set_upstream=True)
    result["initialised"] = fresh
    result["remote"] = remote
    result["branch"] = branch
    return result


def push(profile: Profile, *, message: str = "", set_upstream: bool = False) -> dict:
    """Commit whatever has changed and push it. Idempotent when nothing has."""
    require_configured(profile)
    branch = profile.sync_branch or "main"
    if not is_repo():
        raise StudykitError(
            f"{data_dir()} is not a git repository. Run `./study sync init {profile.sync_remote}`."
        )

    files = _commit(message)
    committed = files > 0

    ahead = _ahead(branch)
    if not committed and ahead == 0:
        return {"ok": True, "committed": False, "pushed": False, "files": 0, "note": "already in sync"}

    args = ["push", "-u", "origin", branch] if set_upstream else ["push", "origin", branch]
    result = _git(*args, check=False)
    if result.returncode != 0:
        # The usual cause is another machine having pushed since. One rebase,
        # then one retry; anything worse is the user's to untangle.
        if _git("pull", "--rebase", "origin", branch, check=False).returncode != 0:
            raise StudykitError(
                f"Push rejected and the rebase onto origin/{branch} failed. "
                f"Resolve it by hand in {data_dir()}."
            )
        retry = _git(*args, check=False)
        if retry.returncode != 0:
            detail = (retry.stderr or retry.stdout).strip().splitlines()
            raise StudykitError(f"git push failed: {detail[-1] if detail else 'no output'}")

    return {"ok": True, "committed": committed, "pushed": True, "files": files}


def _commit(message: str = "") -> int:
    """Commit whatever has changed, and say how many paths that was."""
    changed = _dirty()
    if not changed:
        return 0
    _git("add", "-A")
    # `add` may stage nothing if everything that changed is ignored.
    if _git("diff", "--cached", "--quiet", check=False).returncode == 0:
        return 0
    _git("commit", "-m", message or _message())
    return len(changed)


def _message() -> str:
    from .ledger import read

    rows = read()
    last = rows[-1].date if rows else "no rows"
    return f"study: {len(rows)} rows, latest {last}"


def pull(profile: Profile) -> dict:
    """Fetch the remote and rebase onto it. Idempotent when nothing is waiting.

    Rebase rather than merge, because the ledger is append-only and a merge
    commit in it carries no information.

    Local work is committed first rather than stashed. A rebase that goes wrong
    can be aborted back to a commit; a stash that fails to pop leaves the
    session's measurements somewhere the user has to know about `git stash` to
    find. Committing also puts the local rows under the union merge driver,
    which is what stops two machines' appends from colliding at all.
    """
    require_configured(profile)
    branch = profile.sync_branch or "main"
    if not is_repo():
        raise StudykitError(
            f"{data_dir()} is not a git repository. Run `./study sync init {profile.sync_remote}`."
        )

    _ensure_repo_files()
    _commit()

    if _git("fetch", "origin", branch, check=False).returncode != 0:
        raise StudykitError(f"Could not reach {profile.sync_remote}.")

    behind = _behind(branch)
    if behind is None:
        return {"ok": True, "pulled": False, "commits": 0, "note": f"no {branch} on the remote yet"}
    if behind == 0:
        return {"ok": True, "pulled": False, "commits": 0, "note": "already current"}

    result = _git("pull", "--rebase", "origin", branch, check=False)
    if result.returncode != 0:
        # Leave nothing half-rebased. The abort restores the pre-pull commit,
        # so the worst case is that the pull did not happen.
        _git("rebase", "--abort", check=False)
        raise StudykitError(
            f"Rebase onto origin/{branch} hit a conflict and was aborted. "
            f"Resolve it by hand in {data_dir()}."
        )
    return {"ok": True, "pulled": True, "commits": behind}


def auto_pull(profile: Profile) -> dict | None:
    """Pull at the start of a session, when the profile asks for it.

    Same contract as `auto`: a machine that cannot reach the remote still gets
    to study. The cost of working from a stale ledger is a suboptimal queue and
    a rebase on the next push, not lost data.
    """
    if not (profile.sync_auto and configured(profile)):
        return None
    try:
        return pull(profile)
    except StudykitError as exc:
        return {"ok": False, "error": str(exc)}


def status(profile: Profile) -> dict:
    """Everything `sync` and `doctor` need to describe the current state."""
    payload = {
        "configured": configured(profile),
        "remote": profile.sync_remote,
        "branch": profile.sync_branch or "main",
        "auto": profile.sync_auto,
        "data_dir": str(data_dir()),
        "repo": is_repo(),
    }
    if not payload["repo"]:
        return payload
    payload["remote_actual"] = _remote_url()
    payload["branch_actual"] = _current_branch()
    payload["uncommitted"] = _dirty()
    payload["unpushed"] = _ahead(payload["branch"])
    payload["unpulled"] = _behind(payload["branch"])
    return payload


def auto(profile: Profile) -> dict | None:
    """Push after a write, when the profile asks for it.

    A failed sync must never fail the session that produced the measurement:
    the ledger is already on disk, and the next `study sync` will carry it.
    """
    if not (profile.sync_auto and configured(profile)):
        return None
    try:
        return push(profile)
    except StudykitError as exc:
        return {"ok": False, "error": str(exc)}
