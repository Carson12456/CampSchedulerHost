# How to Contribute to CampSchedulerHost

Since you are the owner of this repository, you don't need to "fork" it in the traditional sense. Instead, you should use **Branches**.

Think of the `main` branch as the "Production" or "Stable" version of your code. You should never work directly on `main`. Instead, create a copy (a "branch"), make your changes there, and then merge it back when you're done.

> **Prefer a No-Code Interface?**
> Check out [GITHUB_GUI_GUIDE.md](GITHUB_GUI_GUIDE.md) for a step-by-step guide using the visual interface instead of commands.

## The Workflow

1.  **Create a Branch**: Make a new branch for your specific task (e.g., `fix-login-bug` or `add-new-calendar`).
2.  **Make Changes**: Edit files, save, and test.
3.  **Commit**: Save your changes to the branch history.
4.  **Push**: Upload your branch to GitHub.
5.  **Pull Request (PR)**: Ask GitHub to merge your branch back into `main`.

---

## Step-by-Step Guide

### 1. Create a New Branch
Open your terminal and run:

```bash
# Make sure you are on the latest main version
git checkout main
git pull origin main

# Create a new branch named 'feature-name'
git checkout -b feature-my-new-change
```

### 2. Make Your Changes
Edit your files as usual. When you are ready to save:

```bash
# See what changed
git status

# Add files to the "staging area"
git add .
```

### 3. Commit Your Changes
```bash
# Save the changes with a message describing what you did
git commit -m "Added a new cool feature"
```

### 4. Push to GitHub
Since this branch doesn't exist on GitHub yet, you need to "set the upstream":

```bash
git push -u origin feature-my-new-change
```

### 5. Merge (Pull Request)
1.  Go to your repository on GitHub: https://github.com/Carson12456/CampSchedulerHost
2.  You will see a yellow banner saying **"feature-my-new-change had recent pushes"**.
3.  Click **Compare & pull request**.
4.  Review your changes and click **Create pull request**.
5.  If everything looks good, click **Merge pull request** and confirm.

### 6. Cleanup
Once merged, you can delete the branch locally and go back to main:

```bash
git checkout main
git pull origin main
git branch -d feature-my-new-change
```
