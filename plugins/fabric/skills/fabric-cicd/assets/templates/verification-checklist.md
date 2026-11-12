# Fabric deployment verification checklist

Release artifact: record the immutable artifact path and source digest.

Target: record the approved TEST, UAT, rehearsal, or PROD target.

- [ ] Confirm the protected deployment job completed successfully.
- [ ] Confirm each selected managed definition is present in the target workspace.
- [ ] Record any definition import warning or mismatch.
- [ ] Obtain the required human approval for this target.
- [ ] If runtime execution is explicitly authorized, record the workload, operator, time window, and result separately.

Deployment success is not runtime verification. Do not mark runtime verification complete
unless an authorized operator has performed and recorded it.
