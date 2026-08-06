# Version control

**Area:** tooling · **Levels:** graduate → staff+

**One line:** A queryable history of every change, whose value shows up on the day you need to know why something is the way it is.

## commits-history

A commit is a **snapshot** of the whole tree plus a pointer to its parent, identified by a hash of its content. Not a diff - diffs are computed between snapshots when you ask for one. Because the id is a content hash, history is tamper-evident: changing anything old changes every id after it.

What makes history useful later:

- **One logical change per commit.** A commit mixing a rename, a bug fix and a new feature cannot be reverted, cherry-picked or understood.
- **The message explains why, not what.** The diff already shows what. "Fix null check" is worthless; "Guard against a missing profile, which happens for users created before the migration" answers the question someone will actually have.
- The **first line is a summary** under ~50 characters, then a blank line, then detail. Tools everywhere assume this shape.
- Link the issue or ticket. Six months later that link is the only path to the context.

Three tools that make history pay off: `git log -p <file>` (how this file got this way), `git blame` (who last touched this line and in which commit), and `git log -S "string"` (which commit introduced or removed this text).

## branching

A branch is a movable pointer to a commit. It is not a copy of anything, which is why creating one is instant.

- **Trunk-based** — short-lived branches merged into main within a day or two, features hidden behind flags. Fewer conflicts, continuous integration in the literal sense, and requires the discipline to keep main releasable.
- **Long-lived feature branches** — isolated work, and divergence grows with time. A branch alive for three weeks is three weeks of conflicts arriving at once.
- **Release branches** — a stabilisation line for a version, with fixes cherry-picked. Necessary when you support released versions, overhead when you deploy continuously.

The general rule: **merge frequency beats merge strategy**. Most painful merges are a scheduling problem wearing a tooling costume.

## merge-vs-rebase

- **Merge** creates a commit with two parents. History is truthful about what happened and contains merge commits that clutter a linear read.
- **Rebase** replays your commits on top of the new base, producing a linear history and **new commit hashes**, because the parent changed.

The rule that follows from the hashes: **never rebase commits that others have pulled.** Their history still refers to the old hashes, and reconciling is painful. Rebase your own unpushed work; merge shared branches.

The middle ground most teams settle on: rebase your feature branch onto main to keep it current and to clean up your own commits, then merge it into main with a merge commit or a squash. Squashing turns a messy branch into one clean commit and discards the intermediate steps, which is a real loss if those steps were meaningful and a real gain if they were "wip" and "fix typo".

## conflicts

A conflict is Git declining to guess when the same region changed on both sides. It is not an error, and there is no way to configure it away.

- Resolve by understanding **both intentions**, not by picking a side. The commonest bad resolution is keeping your version and silently discarding someone else's fix.
- After resolving, **run the tests**. A syntactically clean merge can be semantically broken - your rename plus their new call site compile independently and not together.
- `git rerere` remembers how you resolved a conflict and reapplies it, which pays off during a long rebase.
- The real prevention is smaller, more frequent merges and not reformatting files you are also changing.

If a merge or rebase is going badly, `git merge --abort` or `git rebase --abort` returns you to where you started. Knowing that removes most of the fear.

## finding-bugs

- **`git bisect`** — binary search over history. Mark a known-good and a known-bad commit and Git checks out the midpoint; you say good or bad and it converges in log₂(n) steps. A thousand commits takes ten tests. With a script that exits non-zero on the bug, `git bisect run` does it unattended. This is the highest-leverage Git command most people never use, and it only works if commits are individually buildable.
- **`git revert`** — creates a new commit undoing an old one. Safe on shared history, unlike `reset`, which rewrites it.
- **`git reflog`** — every position HEAD has held, including ones no branch points at any more. This is how you recover from a bad reset or a deleted branch, and it is why almost nothing in Git is truly lost for the first 90 days.
- **`git stash`** — park uncommitted work. Useful, and easy to forget about; a stash is not a branch and nobody reviews it.

## Related

- [testing](testing.md) — bisect is only as good as the test that defines "bad"
- [errors-and-logging](errors-and-logging.md) — a commit message is a log entry for humans
