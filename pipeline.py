#!/usr/bin/env python3
"""
GrantFinder AI - Automated Quality & Deployment Pipeline
Usage:
    python pipeline.py
    python pipeline.py "Your commit message here"
"""

import sys
import os
import subprocess
import time

def run_step(step_number: int, title: str, command: list, check: bool = True) -> bool:
    print(f"\n=======================================================")
    print(f"STEP {step_number}: {title}")
    print(f"Command: {' '.join(command)}")
    print(f"=======================================================")
    
    start_time = time.time()
    result = subprocess.run(command)
    elapsed = time.time() - start_time
    
    if result.returncode != 0:
        print(f"\n[PIPELINE FAILED] Step {step_number} failed with exit code {result.returncode} ({elapsed:.2f}s)")
        if check:
            print("Aborting pipeline to protect repository integrity.")
            sys.exit(result.returncode)
        return False
        
    print(f"[PIPELINE PASSED] Step {step_number} completed in {elapsed:.2f}s")
    return True

def main():
    commit_message = sys.argv[1] if len(sys.argv) > 1 else "Update GrantFinder AI platform features and tests"
    print("-------------------------------------------------------")
    print(" GrantFinder AI - Automated CI/CD & Verification Pipeline ")
    print("-------------------------------------------------------")

    # Step 1: Syntax & Code Compilation Check
    run_step(1, "Syntax & Bytecode Compilation Check", [sys.executable, "-m", "compileall", "app", "tests"])

    # Step 2: Automated Pytest Suite
    run_step(2, "Automated Pytest Test Suite", [sys.executable, "-m", "pytest", "-v", "--tb=short"])

    # Step 3: Git Status
    run_step(3, "Checking Git Status", ["git", "status", "--short"])

    # Step 4: Git Stage
    run_step(4, "Staging Modified & New Files", ["git", "add", "."])

    # Step 5: Git Commit
    # Check if there are changes to commit
    diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if diff_check.returncode != 0:
        run_step(5, f"Creating Git Commit: '{commit_message}'", ["git", "commit", "-m", commit_message])
    else:
        print("\n[INFO] No staged changes to commit. Working directory clean.")

    # Step 6: Git Push
    # Check if remote 'origin' exists
    remotes_check = subprocess.run(["git", "remote"], capture_output=True, text=True)
    if "origin" in remotes_check.stdout:
        # Determine current branch
        branch_check = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
        branch = branch_check.stdout.strip() or "main"
        run_step(6, f"Pushing Changes to GitHub (origin/{branch})", ["git", "push", "-u", "origin", branch])
        print("\n=======================================================")
        print(" PIPELINE SUCCESS: Code tested, committed, and pushed! ")
        print("=======================================================")
    else:
        print("\n=======================================================")
        print(" [LOCAL PIPELINE PASSED] All tests & commits succeeded! ")
        print(" Note: Git remote 'origin' is not yet configured.")
        print(" To push to GitHub, run:")
        print("   git remote add origin <your-github-repo-url>")
        print("   git push -u origin main")
        print("=======================================================")

if __name__ == "__main__":
    main()
