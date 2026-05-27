"""Single source of truth for the application version.

Bump this, commit, then publish a GitHub release tagged with the matching
version (e.g. v1.0.1) that has a QAudioPlayer.exe asset. Installed copies
check the repo's latest release on startup and offer to update when this
number is older than the release tag. See updater.py.
"""

__version__ = "1.0.1"
