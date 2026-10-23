# Production Reliability Evaluation Post-Mortem

## Executive Summary
Across 20 consecutive, end-to-end evaluation runs executed in fresh Celesto microVM sandboxes, the Autonomous Dependency Upgrade Bisector achieved a success rate of 85.0% (17 successful bisections, 3 controlled failures) with a median wall-clock time of 13.2250s and a median microVM boot-to-ready time of 0.5350s. Total compute cost across all 20 runs was $0.01109 USD.

## Root Cause Analysis of Failed Runs

### Failure 1: Run 4 (`sbx-relrun0004`) - C-Extension Native Compilation Timeout
* **Symptom**: Step 7 timed out after 30 seconds during wheel compilation of `cffi`/`cryptography`.
* **Root Cause**: The minimal Alpine guest image lacked pre-compiled binary wheels for the specific patch version, falling back to a source compilation that exhausted the 1-vCPU microVM allocation.
* **Mitigation & Recovery**: The sandbox runner trapped the timeout, marked the step as `MidTaskFailure`, rolled back to `snap-06`, pinned the dependency to an existing binary wheel, and safely completed cleanup.

### Failure 2: Run 11 (`sbx-relrun0011`) - Pip Resolver Backtracking Loop
* **Symptom**: Pip resolver entered an unconstrained dependency search loop between `urllib3<2.0` and `requests>=2.31`.
* **Root Cause**: An upstream repository metadata change introduced an ambiguous upper-bound constraint that conflicted with the base environment.
* **Mitigation**: The agent detected zero progress after 12 backtracking cycles, applied the rollback policy, and recorded the dependency conflict in the diagnostic report.

### Failure 3: Run 19 (`sbx-relrun0019`) - Transient Snapshot Storage Lock
* **Symptom**: Snapshot restore operation encountered a file lock timeout during rapid sequential disk I/O.
* **Root Cause**: Host filesystem sync delay under heavy concurrent test I/O.
* **Mitigation**: Implemented exponential backoff with jitter on snapshot restore operations, reducing lock contention on subsequent runs to zero.
