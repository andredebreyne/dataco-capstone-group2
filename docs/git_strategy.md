# Git Strategy

Task: `[W2][P0][#13] Quality Framework and Git Strategy Documentation`

Issue: `#80`

## Purpose

This document defines the Git workflow used by the DataCo Capstone team. The goal is to keep work traceable, reviewable, and easy to integrate without blocking dependent tasks.

## Standard Workflow

The repository uses `main` as the protected integration branch. Team members must not commit directly to `main`.

Standard task flow:

1. Start from the correct base branch.
2. Create a feature branch.
3. Commit focused changes.
4. Push the branch to GitHub.
5. Open a pull request.
6. Request peer review.
7. Address review comments.
8. Use squash and merge after approval.
9. Delete the merged branch.

## Branch Naming

Feature branches should use the internal task sequence when available:

```text
feature/<internal-task-number>-short-name
```

Examples:

```text
feature/11-silver-cleaning
feature/12-order-time-date-features
feature/13-quality-framework-git-strategy
```

## Pull Request Expectations

Every pull request should include:

- a short summary of the change
- validation performed
- linked issue or internal task reference
- known assumptions or limitations
- reviewer assignment

Pull requests should be small enough for a teammate to review confidently. Large work should be split by layer, objective, or output type when possible.

## Squash and Merge Rule

Approved pull requests should be merged with squash and merge. This keeps `main` readable and makes each task appear as one logical commit in the project history.

After a pull request is merged:

- delete the remote branch in GitHub
- prune local remote references
- delete the local branch if no longer needed

Useful commands:

```bash
git fetch -p
git branch -d feature/<branch-name>
```

Use `git branch -D` only for local branches that are already safely merged or intentionally abandoned.

## Cascading Branch Workflow

Sometimes a task depends on another task that is complete but not yet merged. To avoid blocking the team, a dependent branch may be created from the parent feature branch.

Example:

```bash
git switch feature/11-silver-cleaning
git pull
git switch -c feature/12-order-time-date-features
```

This is acceptable when the dependent task genuinely needs outputs, contracts, or code from the parent branch.

## Cascading PR Communication

When opening a pull request from a cascading branch, add a note such as:

```text
Note: This PR depends on #11 and was branched from the Silver cleaning work. After #11 is merged, this branch will be rebased onto main before final review/merge.
```

This tells reviewers that the diff may temporarily include parent-branch changes and that final cleanup is planned.

## Rebase After Parent Merge

After the parent pull request is merged into `main`, update the dependent branch:

```bash
git fetch origin
git switch feature/<dependent-branch>
git rebase origin/main
```

If conflicts appear, resolve them carefully, run the relevant validation, and push the cleaned branch:

```bash
git push --force-with-lease
```

Use `--force-with-lease` instead of plain `--force` to reduce the risk of overwriting another teammate's work.

## Review Discipline

Reviewers should focus on:

- correctness of the transformation or documentation
- alignment with the task objective
- reproducibility
- leakage-control rules
- validation evidence
- clarity for future team members

Approving a pull request means the reviewer believes the task can move toward Done after merge and branch cleanup.
