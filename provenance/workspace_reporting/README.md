# Reporting-audit provenance

These scripts and the audit JSON came from the separate manuscript workspace.
They refer to that workspace's paper/ and project/ layout and are not executable
entry points in this standalone repository. Use scripts/verify_cached_results.py
for portable artifact/cached-metric checks. The earlier manuscript audit checked
specified tables and protected input hashes; it did not check every derived
field and missed the newly documented success-count inconsistencies.
