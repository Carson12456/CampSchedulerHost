# No-Code Git Guide: Managing Branches Visually

This guide explains how to manage your code using the **GitHub Website** and the **VS Code / Windsurf / Antigravity Interface**, without typing any commands in the terminal.

---

## Method 1: Creating a Branch on GitHub (The Website Way)

This is easiest if you want to set up your workspace before opening your editor.

1.  **Go to your Repository**: Open [https://github.com/Carson12456/CampSchedulerHost](https://github.com/Carson12456/CampSchedulerHost).
2.  **Find the Branch Selector**: Look for the button that says **"main"** (usually top-left of the file list).
3.  **Create Branch**:
    *   Click the **"main"** button.
    *   Type your new branch name in the text box (e.g., `update-colors`).
    *   You will see an option appear: **"Create branch: update-colors from main"**. Click that.
    *   *Success!* The branch now exists on the website.

### How to get this branch into your Editor:
1.  Open **Windsurf / Antigravity**.
2.  Look at the **Bottom Left Corner** of the window (the blue status bar). You often see a synchronization icon (arrows forming a circle).
3.  **Synchronization**:
    *   Go to the **Source Control** tab (the icon looks like a graph node/tree on the left sidebar).
    *   Click the **"..." (More Actions)** menu at the top right of the sidebar.
    *   Select **Pull, Push** -> **Sync**. (This downloads the new branch info from GitHub).
4.  **Switch Branch**:
    *   Click the branch name (e.g., `main`) in the very **bottom-left corner** of the window.
    *   A list will pop up at the top.
    *   Select your new branch (`update-colors` or `origin/update-colors`).

---

## Method 2: Creating a Branch in the Editor (The VS Code Way)

This is faster if you are already coding.

1.  **Click the Branch Name**: Look at the **bottom-left corner** of the window status bar. It likely says `main` or `dev-playground`. Click it.
2.  **Select Create New Branch**:
    *   A menu appears at the top center.
    *   Select **+ Create new branch...**.
3.  **Name It**: Type your branch name (e.g., `fix-loading-bug`) and press Enter.
    *   *You are now working on this new branch.*
4.  **Publish to GitHub**:
    *   Go to the **Source Control** tab (left sidebar).
    *   You will see a **Publish Branch** button (cloud icon with an arrow). Click it.
    *   *Success!* Your branch is now on GitHub.

---

## How to Save Changes (Commit & Push)

When you have edited files and want to save them to GitHub:

1.  **Go to Source Control**: Click the icon on the left sidebar (looks like a graph node).
2.  **Stage Changes**: You will see a list of changed files. Hover over the "Changes" header and click the **+ (Plus)** icon to "Stage All Changes".
3.  **Commit**: Type a message in the "Message" box (e.g., "Changed the background color") and press **Commit** (or the Checkmark icon).
4.  **Push**: Click the **Sync Changes** button (blue button) that appears after committing. This uploads your changes to GitHub.

---

## How to Update Main (Pull Request)

When you are done with your branch and want to merge it into `main`:

1.  Go to [GitHub.com](https://github.com/Carson12456/CampSchedulerHost).
2.  You will often see a yellow banner: **"fix-loading-bug had recent pushes"**.
3.  Click **Compare & pull request**.
4.  Click **Create pull request**.
5.  Click **Merge pull request**.
6.  *Success!* Your changes are now in the main production code.
