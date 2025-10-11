# PATH: utils/git_utils.py
from os import path as os_path
import git
from git import Repo


def open_repo(repo_path: str) -> Repo:
    """
    Open a Git repository at the given path.
    """
    if not os_path.exists(repo_path):
        raise FileNotFoundError(f"Path does not exist: {repo_path}")
    return git.Repo(repo_path)


def create_branch_if_missing(repo: Repo, name: str) -> str:
    """
    Create a branch if it doesn't exist, otherwise return existing branch name.
    """
    try:
        repo.git.rev_parse("--verify", name)
        return name
    except git.GitCommandError:
        repo.git.branch(name)
        return name


def commit_all(repo: Repo, message: str) -> bool:
    """
    Add all changes and commit with the provided message.
    Returns True if commit succeeds, False otherwise.
    """
    try:
        repo.git.add(A=True)
        repo.index.commit(message)
        return True
    except git.GitCommandError:
        return False


def push_branch(repo: Repo, branch: str, remote: str = 'origin') -> bool:
    """
    Push the specified branch to remote.
    Returns True if push succeeds, False otherwise.
    """
    try:
        repo.git.push('--set-upstream', remote, branch)
        return True
    except git.GitCommandError:
        return False


def repo_open():
    return None