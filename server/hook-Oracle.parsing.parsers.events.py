"""
PyInstaller hook for Oracle.parsing.parsers.events
Dynamically discovers and includes all event modules
"""
from PyInstaller.utils.hooks import collect_submodules

# Collect all submodules in the events package
hiddenimports = collect_submodules('Oracle.parsing.parsers.events')
