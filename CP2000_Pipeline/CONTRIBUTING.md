# Contributing Guidelines

## Overview

This is a proprietary internal project for Tax Relief Advocates. Contributions are limited to authorized team members only.

## Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/TaxReliefAdvocates/CP2000_Pipeline.git
cd CP2000_Pipeline
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure credentials**
   - Add `credentials.json` (Google Drive API)
   - Create `.env` file with API keys

## Coding Standards

### Python Style Guide
- Follow PEP 8 conventions
- Use meaningful variable names
- Add docstrings to all functions
- Keep functions focused and single-purpose

### Documentation
- Update README.md for new features
- Document API changes
- Add comments for complex logic
- Update workflow guides as needed

### Testing
- Test with `--test` flag before production
- Test with 5 files minimum
- Verify reports generation
- Check Google Drive organization

## Commit Guidelines

### Commit Message Format
```
<type>: <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

### Examples
```bash
git commit -m "feat: add fuzzy matching for taxpayer names"
git commit -m "fix: correct date parsing for future dates"
git commit -m "docs: update workflow guide with new folder structure"
```

## Branch Strategy

### Main Branches
- `main` - Production code
- `develop` - Development branch
- `feature/*` - Feature branches
- `hotfix/*` - Emergency fixes

### Workflow
1. Create feature branch from `develop`
```bash
git checkout -b feature/your-feature-name
```

2. Make changes and commit
```bash
git add .
git commit -m "feat: your feature description"
```

3. Push to remote
```bash
git push origin feature/your-feature-name
```

4. Create Pull Request to `develop`

## Pull Request Process

1. **Before PR**
   - Test thoroughly with `--test` flag
   - Update documentation
   - Run linters if applicable
   - Check .gitignore compliance

2. **PR Description**
   - Describe what changed
   - Why the change was needed
   - Testing performed
   - Any breaking changes

3. **Review Process**
   - Code review by team lead
   - Testing by QA
   - Approval required before merge

## Security Guidelines

### Never Commit
- API keys or credentials
- `credentials.json`
- `token.pickle`
- `.env` files
- Actual case data or PII

### Always Use
- Environment variables for secrets
- `.gitignore` for sensitive files
- Encrypted storage for credentials

## Testing Checklist

Before committing changes:

- [ ] Code runs without errors
- [ ] Tested with `--test` flag
- [ ] Documentation updated
- [ ] No sensitive data in code
- [ ] .gitignore updated if needed
- [ ] Error handling tested
- [ ] Reports generate correctly

## Release Process

1. **Version Update**
   - Update version in docstrings
   - Update CHANGELOG.md
   - Tag release in git

2. **Testing**
   - Full end-to-end test
   - Verify all reports
   - Check folder organization

3. **Deployment**
   - Merge to `main`
   - Deploy to production
   - Monitor first run

## Getting Help

**Project Lead:** Hemalatha Yalamanchi  
**Repository:** https://github.com/TaxReliefAdvocates  
**Documentation:** See README.md and workflow guides

## Code of Conduct

- Be professional and respectful
- Follow company policies
- Protect sensitive information
- Collaborate effectively
- Report security issues immediately

---

**Last Updated:** October 2025  
**Maintained by:** Hemalatha Yalamanchi

