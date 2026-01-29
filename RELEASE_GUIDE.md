# 🚀 AutoLogin Release Guide

> **MUST READ** for all developers before creating releases!

## ⚠️ Critical: Version Synchronization

When creating a new release, you **MUST** update the version in **TWO places**:

### 1. Update `pyproject.toml`

```toml
[tool.briefcase]
version = "X.Y.Z"  # ← Update this!
```

### 2. Update `src/autologin/utils/updater.py`

```python
# Hardcoded version as fallback (updated during build)
APP_VERSION = "X.Y.Z"  # ← Update this!
```

> **Why both?** The `pyproject.toml` version is used by Briefcase during packaging. The `APP_VERSION` in `updater.py` is a fallback when `importlib.metadata` cannot retrieve the version (common in packaged apps).

---

## 📋 Release Checklist

Before pushing a release tag:

- [ ] Update version in `pyproject.toml`
- [ ] Update `APP_VERSION` in `src/autologin/utils/updater.py`
- [ ] Commit all changes
- [ ] Push to main branch
- [ ] Create and push version tag

---

## 🔖 Creating a Release

### Step 1: Update Versions

Edit both files mentioned above with the new version number (e.g., `1.0.3`).

### Step 2: Commit Changes

```bash
git add pyproject.toml src/autologin/utils/updater.py
git commit -m "Bump version to 1.0.3"
git push origin main
```

### Step 3: Create and Push Tag

```bash
git tag -a v1.0.3 -m "Release v1.0.3: Brief description of changes"
git push origin v1.0.3
```

### Step 4: Verify GitHub Actions

1. Go to [GitHub Actions](https://github.com/TradinxLite/autologin/actions)
2. Verify the `Release` workflow runs successfully
3. Check that all platform builds complete:
   - ✅ Windows (.msi)
   - ✅ macOS (.dmg)
   - ✅ Linux (.AppImage)

### Step 5: Verify Release Assets

Go to [Releases](https://github.com/TradinxLite/autologin/releases) and verify:
- Release is created with correct version tag
- All platform installers are attached
- Asset filenames include correct version number

---

## 🔄 How Auto-Update Works

```
┌─────────────────────────────────────────────────────────────┐
│                    APP STARTUP                               │
├─────────────────────────────────────────────────────────────┤
│  1. App shows "Checking for updates..." in status bar       │
│  2. Fetches latest release from GitHub API                  │
│  3. Compares versions:                                       │
│     • Current: from importlib.metadata OR APP_VERSION        │
│     • Latest: from GitHub release tag (strips 'v' prefix)   │
│  4. If update available:                                     │
│     • Finds correct asset for platform (.msi/.dmg/.AppImage)│
│     • Shows update dialog with release notes                │
│     • Downloads and launches installer                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🐛 Troubleshooting

### Update Not Detected

1. **Check versions match**: Ensure `pyproject.toml` and `APP_VERSION` are updated
2. **Check GitHub release**: Verify release was created and has correct tag
3. **Check asset names**: Assets must contain platform identifiers:
   - Windows: `.msi` extension
   - macOS: `.dmg` extension  
   - Linux: `.AppImage` extension

### Build Fails on GitHub Actions

1. Check workflow logs for specific errors
2. Common issues:
   - Missing dependencies in workflow
   - Playwright browser installation failures
   - Code signing issues (macOS)

### Windows Playwright Issue

The installer for Windows now:
1. Pre-installs Playwright Chromium during CI build
2. Uses custom browser path (`AutoLogin/playwright-browsers` in user data)
3. Falls back to multiple installation methods at runtime

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Briefcase config, **version source** |
| `src/autologin/utils/updater.py` | Update check logic, **fallback version** |
| `src/autologin/dialogs/update_dialog.py` | Update UI dialogs |
| `src/autologin/utils/install_browser.py` | Playwright browser installation |
| `.github/workflows/release.yml` | Release build workflow |
| `.github/workflows/build.yml` | CI build workflow |

---

## 🎯 Version Numbering

We use [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., `1.2.3`)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes

---

*Last updated: January 2026*
