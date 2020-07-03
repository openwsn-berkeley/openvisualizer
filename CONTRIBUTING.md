# Contributing to OpenVisualizer and OpenWSN
:+1: :tada: First off, thanks for taking the time to contribute! :tada: :+1:

We use JIRA to track issues and new features: [jira-issues](https://openwsn.atlassian.net/projects/OV/issues)

We use `flake8` to enforce the Python PEP-8 style guide. The Travis builder verifies new pull requests and it fails if the Python code does not follow the style guide.

You can check locally if your code changes comply with PEP-8. First, install the main `flake8` package and two `flake8` plugins:

```bash
$ pip install flake8
$ pip install pep8-naming
$ pip install flake8-commas
```

Move to the root of the OpenVisualizer project and run:

```bash
$ flake8 --config=tox.ini
```

If `flake8` does not generate any output, your code passes the test; alternatively, you can check the return code:

```bash
$ flake8 --config=tox.ini
$ echo $?
0
```
