# Contributing to Tailwind CSS Forge

🤝 Thank you for considering a contribution.

This project aims to be practical, safe, and distribution-ready. Please keep that bar in mind before opening issues or pull requests.

## ✨ Principles

Contributions should preserve these qualities:

- 🧠 technical clarity
- 🔐 safe local execution
- 🧱 predictable filesystem behavior
- 🧪 verifiable changes
- 🖥️ installer-ready compatibility

## 🐛 Before Opening an Issue

Please try to include:

- a clear description of the problem
- exact reproduction steps
- expected behavior
- actual behavior
- environment details:
  - operating system
  - Python version
  - Node.js version
  - whether you used source layout or installer-ready bundle
- logs or screenshots when relevant

## 🌿 Branch and Pull Request Guidance

- Keep pull requests focused.
- Avoid mixing refactors, features, and unrelated cleanup in one PR.
- Do not introduce destructive behavior for imported projects.
- Do not weaken path validation, workspace isolation, or publish safety rules.
- Update documentation when behavior or commands change.

## 🧪 Local Development

### Backend

```bash
cd backend
python -m pip install -e .[dev]
python -m ruff check app tests
python -m pytest
```

### Frontend

```bash
cd frontend
npm install
npm run build
npm run test
npm run test:e2e
```

### Desktop

```bash
cd desktop
npm install
cd src-tauri
cargo check
```

### Launcher and installer-ready validation

```bash
python scripts/render_installer_assets.py
python scripts/prepare_installer_bundle.py --force
python scripts/validate_installer_bundle.py
```

## 🧭 Contribution Areas

Good contribution targets include:

- Tailwind detection improvements
- build strategy safety and compatibility
- frontend UX improvements tied to real backend capabilities
- report quality and diagnostics
- installer-ready robustness
- tests for real regressions
- documentation accuracy

## 🔒 Security-Sensitive Areas

Be especially careful when changing:

- workspace creation and file copying
- path resolution and traversal protection
- process execution allowlists
- dependency installation flows
- publish profile handling
- encryption and secrets storage
- launcher behavior in installed layouts

Security-impacting changes should include explicit rationale in the PR description.

## 📝 Code Style Expectations

- Prefer small, readable, maintainable changes.
- Follow the existing project structure.
- Preserve ASCII unless the file already uses broader Unicode intentionally.
- Keep comments concise and useful.
- Add or update tests when behavior changes.

## ✅ Pull Request Checklist

Before submitting:

- [ ] the change is scoped and documented
- [ ] backend tests pass
- [ ] lint passes where applicable
- [ ] frontend build and tests pass if frontend code changed
- [ ] desktop shell still checks if desktop files changed
- [ ] installer-ready flow still works if launcher/distribution files changed
- [ ] documentation was updated if commands, behavior, or architecture changed

## 💬 Discussion

If a change is large, architectural, or security-sensitive, open an issue first so the approach can be aligned before implementation.

Thanks for helping keep Tailwind CSS Forge solid and reliable.
