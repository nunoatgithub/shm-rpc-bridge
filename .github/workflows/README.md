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

## Development Workflow (Manual Trigger on Branches)

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
|------|--------|
| Test on branch without auto-trigger | Push to branch → manually trigger `ci.yml` on that branch |
| Test single OS/Python combo | Manually trigger with filters (select specific OS/Python) |
| Test all configurations | Manually trigger with filters set to "all" |
| Debug a specific failure | Enable tmate, SSH into runner |
| Avoid commit spam | Use feature branch + `git commit --amend` |
| Automatic testing | Push to master (auto-runs full matrix) |

## Example: Testing Changes on a Feature Branch

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
# Select OS: macos-latest (test just macOS first)
# Select Python: 3.11 (test one version first)
# Click "Run workflow"

# 5. If it fails, iterate:
vim src/shm_rpc_bridge/server.py
git add src/
git commit --amend --no-edit
git push --force origin my-new-feature

# 6. Run workflow again from GitHub UI (same settings)

# 7. Once macOS works, test all combinations:
# GitHub → Actions → "CI" → Run workflow
# Select OS: all
# Select Python: all
# Click "Run workflow"

# 8. All tests pass? Merge to master
git checkout master
git merge --squash my-new-feature
git commit -m "Add new feature"
git push origin master  # Auto-runs full CI

# 9. Clean up
git branch -D my-new-feature
git push origin --delete my-new-feature
```

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
