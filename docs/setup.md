# Setup for Development environment

This is a Python-based project, which needs specific modules. A
`requirements.txt` file is provided in the root of the project listing out all
needed modules.

A Python `venv` can be created and used, to ensure we have a clean development environment.

## Creating the Venv

NOTE: You only need to create the Venv ff the `.venv` directory does not exist!

```console
$ python -m venv redfish && mv redfish .venv && ls -a
.  ..  docs  .git  .gitignore  .hpe_redfish_auth  hpe-redfish-exporter.py  requirements.txt  .venv

$ source .venv/bin/activate

$ pip install -r requirements.txt
```
