# PATH: utils/git_utils.py (updated flush_to_flood)

from git import Repo, GitCommandError

def flush_to_flood(repo: Repo, branch_name: str):
    """
    Merge branch_name into FLOOD_BRANCH intelligently.
    Keeps only the last 250 commits in FLOOD_BRANCH.
    """
    FLOOD_BRANCH = "<flood>"

    try:
        # Create flood branch if missing
        if FLOOD_BRANCH not in repo.branches:
            repo.git.branch(FLOOD_BRANCH)
        repo.git.checkout(FLOOD_BRANCH)

        # Merge safely with no-fast-forward
        try:
            repo.git.merge(branch_name, "--no-ff", "--strategy-option=theirs")
            log(f"🌊 Merged {branch_name} into {FLOOD_BRANCH}")
        except GitCommandError as merge_err:
            log(f"⚠️ Merge conflict during flush_to_flood: {merge_err}")
            # Abort merge to keep flood branch safe
            repo.git.merge("--abort")
            return

        # Trim to last 250 commits
        commits = list(repo.iter_commits(FLOOD_BRANCH))
        if len(commits) > 250:
            oldest_hash = commits[249].hexsha
            repo.git.reset("--hard", oldest_hash)
            log(f"♻️ FLOOD branch trimmed to 250 commits")

        # Push safely
        repo.git.push("--set-upstream", "origin", FLOOD_BRANCH)
        log(f"🚀 FLOOD branch updated with {branch_name}")

    except Exception as e:
        log(f"💥 flush_to_flood failed: {repr(e)}")
