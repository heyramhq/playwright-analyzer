# Publishing to PyPI

This guide explains how to publish the `playwright-analyzer` package to PyPI.

## Prerequisites

1. **PyPI Account**: Create an account at [https://pypi.org](https://pypi.org)
2. **Test PyPI Account** (optional): Create an account at [https://test.pypi.org](https://test.pypi.org) for testing
3. **API Tokens**: Generate API tokens for both PyPI and Test PyPI:
   - Go to Account Settings → API tokens
   - Create a token with "Entire account" scope
   - Save tokens securely

## Setup

1. **Install Publishing Tools**:
   ```bash
   pip install build twine
   ```

2. **Configure PyPI Credentials**:
   - Copy `.pypirc.example` to `~/.pypirc`
   - Add your API tokens to `~/.pypirc`
   - Ensure file permissions: `chmod 600 ~/.pypirc`

## Manual Publishing Process

### 1. Prepare Release

```bash
# Run tests
pytest tests/

# Check code quality
black src/ tests/ --check
ruff check src/ tests/
mypy src/

# Update version in pyproject.toml
# Update CHANGELOG.md
```

### 2. Build Package

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build source distribution and wheel
python -m build

# Verify package
twine check dist/*
```

### 3. Test on Test PyPI (Optional)

```bash
# Upload to Test PyPI
twine upload -r testpypi dist/*

# Test installation
pip install -i https://test.pypi.org/simple/ playwright-analyzer
```

### 4. Publish to PyPI

```bash
# Upload to PyPI
twine upload dist/*

# Verify installation
pip install playwright-analyzer
```

## Automated Release Process

### Using Release Script

```bash
# For patch release (0.1.0 → 0.1.1)
./scripts/release.sh patch

# For minor release (0.1.0 → 0.2.0)
./scripts/release.sh minor

# For major release (0.1.0 → 1.0.0)
./scripts/release.sh major

# Push changes and tag
git push origin main
git push origin v<version>
```

### Using GitHub Actions

The project includes two GitHub Actions workflows:

1. **CI Workflow** (`ci.yml`): Runs on every push and PR
   - Linting (Black, Ruff, MyPy)
   - Testing (Python 3.9-3.12)
   - Building and checking packages

2. **Release Workflow** (`release.yml`): Publishes to PyPI
   - **Automatic**: Triggered when a GitHub release is created
   - **Manual**: Use workflow dispatch with version input

#### Setting up GitHub Actions for PyPI

1. Go to your GitHub repository settings
2. Navigate to Secrets and variables → Actions
3. Add the following secrets:
   - `PYPI_API_TOKEN`: Your PyPI API token
   - `TEST_PYPI_API_TOKEN`: Your Test PyPI API token (optional)

4. Enable trusted publishing (recommended):
   - Go to PyPI → Your project → Settings → Publishing
   - Add GitHub as a trusted publisher
   - Repository: `your-username/playwright-analyzer`
   - Workflow: `.github/workflows/release.yml`
   - Environment: `release`

#### Creating a Release

1. **Via GitHub UI**:
   - Go to Releases → Create a new release
   - Choose a tag (e.g., `v0.1.0`)
   - Set release title and notes
   - Publish release → GitHub Action will deploy to PyPI

2. **Via Command Line**:
   ```bash
   # Create and push a tag
   git tag -a v0.1.0 -m "Release v0.1.0"
   git push origin v0.1.0

   # Then create release on GitHub UI
   ```

## Version Management

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR** (1.0.0): Incompatible API changes
- **MINOR** (0.1.0): Backwards-compatible functionality
- **PATCH** (0.0.1): Backwards-compatible bug fixes

## Troubleshooting

### Common Issues

1. **Authentication Failed**:
   - Verify API token is correct
   - Ensure token has upload permissions
   - Check `.pypirc` configuration

2. **Package Name Conflict**:
   - Package name must be unique on PyPI
   - Check availability at https://pypi.org/project/<name>

3. **Build Errors**:
   - Ensure all dependencies are installed
   - Check `pyproject.toml` syntax
   - Verify package structure

4. **Upload Errors**:
   - Check internet connection
   - Verify package passes `twine check`
   - Ensure version number is unique

### Getting Help

- PyPI Documentation: https://packaging.python.org/
- Twine Documentation: https://twine.readthedocs.io/
- GitHub Actions: https://docs.github.com/en/actions

## Security Best Practices

1. **Never commit credentials** to the repository
2. **Use API tokens** instead of passwords
3. **Limit token scope** when possible
4. **Rotate tokens** regularly
5. **Use trusted publishing** with GitHub Actions
6. **Enable 2FA** on PyPI account

## Checklist Before Publishing

- [ ] All tests pass
- [ ] Code is properly formatted
- [ ] Version number is updated
- [ ] CHANGELOG is updated
- [ ] Documentation is current
- [ ] Package builds successfully
- [ ] Package passes `twine check`
- [ ] Tested on Test PyPI (optional)