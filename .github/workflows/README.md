# GitHub Actions Development Guide

This guide explains how to develop and test CI workflows without polluting your git history.

## Workflow

### `ci.yml` - Single CI Workflow

**Automatic triggers:**
- Runs on pushes to `master`/`main`
- Runs on pull requests to `master`/`main`

**Manual trigger with options:**
- Can be run on **any branch** manually
- Filter by OS (all, ubuntu-latest, macos-latest)
- Filter by Python version (all, 3.8-3.13)
- Optional SSH debugging with tmate

## Local Workflow Validation with act

**CRITICAL:** Always validate workflows locally before pushing to avoid syntax errors and wasted CI time.

### Installation

You need to install `act` on your system:

```bash
# Linux/macOS
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Or via package managers:
# Homebrew (macOS/Linux)
brew install act

# Chocolatey (Windows)
choco install act-cli

# See more options: https://nektosact.com/installation/index.html
```

**Verify installation:**
```bash
act --version
```

### Usage via tox (Recommended)

The easiest way to validate workflows:

```bash
# Validate all workflows
tox -e workflow
```

This will:
- ✅ Check workflow syntax and schema
- ✅ List all jobs that would run
- ✅ Catch errors before you push
- ✅ Run in seconds (no actual job execution)

### Direct act Usage

**Basic Commands:**

```bash
# List all workflows and jobs
act -l

# List jobs for a specific event (push, pull_request, workflow_dispatch)
act -l push
act -l pull_request

# Show what would run without actually executing (dry-run)
act -n
act -n push
```

**Validation Only (No Execution):**

```bash
# Validate workflow syntax and list jobs (fast, no Docker needed)
# This is what `tox -e workflow` does under the hood
act -l --detect-event
```

**Local Execution (Requires Docker):**

```bash
# Run a specific job by name
act push -j test
act push -j lint
act push -j type-check

# Run all jobs for a specific event
act push                    # All jobs triggered by push
act pull_request           # All jobs triggered by PR
act workflow_dispatch      # All jobs triggered by manual dispatch

# Run on a specific platform
act -P ubuntu-latest=catthehacker/ubuntu:act-latest push

# Run with environment variables or secrets
act push -s GITHUB_TOKEN=your_token
act push --env MY_VAR=value

# Verbose output for debugging
act push -v
act push -vv  # Even more verbose
```

**Useful Options:**

```bash
# Don't pull Docker images (use cached)
act push --pull=false

# Reuse previous container (faster iteration)
act push --reuse

# Run specific workflow file
act -W .github/workflows/ci.yml

# List available secrets that would be needed
act -l --secret-file .secrets
```

**Common Workflows:**

```bash
# Quick syntax check (recommended before committing)
act -l

# Test a single job locally
act push -j lint

# Full local CI run (slow, tests everything)
act push
```

**Note:** Full job execution with `act push` requires Docker and can be slow. For most development, `tox -e workflow` (validation only) is sufficient.

### Integration into Development Workflow

**Before committing workflow changes:**

```bash
# 1. Edit workflow
vim .github/workflows/ci.yml

# 2. Validate syntax
tox -e workflow

# 3. If validation passes, commit
git add .github/workflows/ci.yml
git commit -m "Update CI workflow"

# 4. Push with confidence
git push
```

### Running CI on Feature Branches

1. **Create and push your feature branch:**
   ```bash
   git checkout -b my-feature
   # Make your changes
   git add .
   git commit -m "Work in progress"
   git push origin my-feature
   ```

2. **Manually trigger CI on your branch:**
   - Go to GitHub → Actions → "CI" workflow
   - Click "Run workflow" button
   - **Select your branch** from dropdown (e.g., `my-feature`)
   - **Choose filters** (optional):
     - OS: `all` or specific OS
     - Python: `all` or specific version
     - Debug: enable for SSH access
   - Click "Run workflow"

3. **Iterate without new commits:**
   - Make changes locally
   - Amend your commit:
     ```bash
     git add .
     git commit --amend --no-edit
     git push --force origin my-feature
     ```
   - Re-run workflow from GitHub UI (same branch)

4. **Clean up when done:**
   ```bash
   git checkout master
   git branch -D my-feature
   git push origin --delete my-feature
   ```

### Interactive Debugging with tmate

When you need to debug interactively:

1. **Enable debug mode** when manually triggering:
   - GitHub → Actions → "CI" workflow → "Run workflow"
   - Select your branch
   - Check "Run with tmate debugging session"
   - Click "Run workflow"

2. **Wait for the job** to reach the tmate step

3. **SSH into the runner:**
   - The job log will show an SSH command like:
     ```
     ssh YOUR_SESSION@nyc1.tmate.io
     ```
   - Copy and run it in your terminal

4. **Debug interactively:**
   - You're now inside the GitHub Actions runner
   - Run commands manually to test
   - The session is private (only you can access it)

5. **Exit** when done:
   - Type `exit` or close the SSH session
   - The workflow will continue

## Best Practices

### For Quick Iterations on Branches
- Push to a feature branch
- Manually trigger `ci.yml` on that branch
- Use filters to test one OS/Python combo at a time (faster, cheaper)
- Use `git commit --amend` to avoid polluting history
- Only merge to `master` when everything works

### For Debugging Failures
- Enable tmate debugging when manually triggering
- SSH into the runner
- Run commands interactively to understand the issue
- Session is private (only you can access)

### For Clean Git History
- Use feature branches for development
- Use `git commit --amend` + `git push --force` to iterate
- Squash commits before merging to `master`
- Delete feature branches after merging

## Quick Reference

| Goal | Method |
|------|---------|
| **Validate workflow before push** | **`tox -e workflow`** |
| Test on branch without auto-trigger | Push to branch → manually trigger `ci.yml` on that branch |
| Debug a specific failure | Enable tmate, SSH into runner |
| Avoid commit spam | Use feature branch + `git commit --amend` |
| Automatic testing | Push to master (auto-runs full matrix) |
| Run workflow locally (full execution) | `act push` - [Requires Docker](https://nektosact.com/) |
| List all jobs | `act -l` |

## Example: Testing impact in macOS, when working in Linux 

```bash
# 1. Create feature branch
git checkout -b my-new-feature

# 2. Make changes
vim src/shm_rpc_bridge/server.py

# 3. Commit and push
git add src/
git commit -m "WIP: Add new feature"
git push origin my-new-feature

# 4. Manually trigger CI on your branch
# Go to GitHub → Actions → "CI" → Run workflow
# Select branch: my-new-feature
# Click "Run workflow"

# 5. If it fails, iterate:
vim src/shm_rpc_bridge/server.py
git add src/
git commit --amend --no-edit
git push --force origin my-new-feature

# 6. Run workflow again from GitHub UI (same settings)

# 7. All tests pass? Merge to master
git checkout master
git merge --squash my-new-feature
git commit -m "Add new feature"
git push origin master  # Auto-runs full CI

# 8. Clean up
git branch -D my-new-feature
git push origin --delete my-new-feature
```

## Example: Developing CI Workflow Changes

**CRITICAL: This example shows the proper way to modify workflows without breaking CI.**

```bash
# 1. Create branch for workflow changes
git checkout -b update-ci-workflow

# 2. Edit workflow
vim .github/workflows/ci.yml

# 3. VALIDATE LOCALLY FIRST (catches 90% of errors)
tox -e workflow

# 4. If validation fails, fix and repeat
#    Example error: "Unknown Property runs-on"
#    Fix the YAML syntax and run again
vim .github/workflows/ci.yml
tox -e workflow

# 5. Once validation passes, commit
git add .github/workflows/ci.yml
git commit -m "Update CI: add new test job"

# 6. Push
git push origin update-ci-workflow

# 7. Manually trigger to test on GitHub
# Go to GitHub → Actions → "CI" → Run workflow
# Select branch: update-ci-workflow
# Click "Run workflow"

# 8. Monitor the run - if it works, merge
git checkout master
git merge --squash update-ci-workflow
git commit -m "Update CI workflow"
git push origin master

# 9. Clean up
git branch -D update-ci-workflow
git push origin --delete update-ci-workflow
```

**Key Point:** Always run `tox -e workflow` before committing workflow changes. This prevents:
- ❌ Syntax errors that break CI
- ❌ Wasted GitHub Actions minutes
- ❌ Embarrassing "fix CI" commits
- ❌ Broken master branch

## Example: Debugging a macOS-Specific Issue

```bash
# 1. Create debug branch
git checkout -b debug-macos-issue

# 2. Push branch
git push origin debug-macos-issue

# 3. Manually trigger with debugging enabled
# GitHub → Actions → "CI" → Run workflow
# Select branch: debug-macos-issue
# Select OS: macos-latest
# Select Python: 3.11
# Check "Run with tmate debugging session"
# Click "Run workflow"

# 4. Wait for workflow to start, then SSH in
# Job log will show: ssh XYZ@nyc1.tmate.io
ssh XYZ@nyc1.tmate.io

# 5. Debug interactively on the macOS runner
cd /home/runner/work/shm-rpc-bridge/shm-rpc-bridge
python -m pytest tests/ -v
# ... investigate issue ...

# 6. Exit SSH when done
exit

# 7. Fix locally and repeat
vim src/shm_rpc_bridge/server.py
git add src/
git commit --amend --no-edit
git push --force origin debug-macos-issue
# Re-trigger workflow
```

## Notes

- **Workflow dispatch** = manual trigger from GitHub UI
- **tmate** = SSH session into the runner for debugging
- **Matrix** = test multiple configurations in parallel
- **Filters** = narrow down which jobs run (saves time and CI minutes)
- GitHub Actions is free for public repos, has limits for private repos
