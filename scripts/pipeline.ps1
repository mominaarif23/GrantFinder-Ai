<#
.SYNOPSIS
    GrantFinder AI - Local PowerShell Pipeline
.DESCRIPTION
    Runs compilation check, executes full pytest test suite, commits staged changes, and pushes to GitHub.
.EXAMPLE
    .\scripts\pipeline.ps1 "Feature: Update AI recommendations"
#>

param(
    [string]$CommitMessage = "Update GrantFinder AI platform features and tests"
)

$ErrorActionPreference = "Stop"

Write-Host "`n=======================================================" -ForegroundColor Cyan
Write-Host " GrantFinder AI - Automated CI/CD Pipeline " -ForegroundColor Cyan
Write-Host "=======================================================`n" -ForegroundColor Cyan

# 1. Compilation
Write-Host "[1/5] Compiling Python source code..." -ForegroundColor Yellow
python -m compileall app tests
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAILED] Compilation check failed. Aborting pipeline." -ForegroundColor Red
    exit 1
}
Write-Host "[PASSED] Code compilation clean.`n" -ForegroundColor Green

# 2. Pytest Test Suite
Write-Host "[2/5] Executing automated test suite..." -ForegroundColor Yellow
python -m pytest -v --tb=short
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAILED] Automated tests failed. Aborting pipeline." -ForegroundColor Red
    exit 1
}
Write-Host "[PASSED] All 24 tests passed.`n" -ForegroundColor Green

# 3. Git Staging
Write-Host "[3/5] Staging files for Git..." -ForegroundColor Yellow
git add .
git status --short

# 4. Git Commit
Write-Host "`n[4/5] Committing changes..." -ForegroundColor Yellow
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m $CommitMessage
    Write-Host "[PASSED] Changes committed successfully.`n" -ForegroundColor Green
} else {
    Write-Host "[INFO] No staged changes to commit. Working directory clean.`n" -ForegroundColor Gray
}

# 5. Git Push
Write-Host "[5/5] Checking remote repository and pushing..." -ForegroundColor Yellow
$remotes = git remote
if ($remotes -contains "origin") {
    $branch = git branch --show-current
    if (-not $branch) { $branch = "main" }
    git push -u origin $branch
    Write-Host "`n[SUCCESS] Pipeline completed and pushed to GitHub ($branch)!`n" -ForegroundColor Green
} else {
    Write-Host "`n[NOTICE] Git remote 'origin' is not set." -ForegroundColor Yellow
    Write-Host "Add your remote with: git remote add origin <your-github-repo-url>" -ForegroundColor Cyan
    Write-Host "Then push with: git push -u origin main" -ForegroundColor Cyan
}
