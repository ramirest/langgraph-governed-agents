# Meridian Transit Authority — Data governance

## Ownership

No named owner exists for the fare-collection dataset. Three teams write to it:
Revenue Operations, the mobile app team, and a nightly reconciliation job
maintained by a contractor whose engagement ended in March.

The passenger-counting dataset has a named owner in Planning, documented in the
team handbook, reviewed annually.

## Policy

A data classification policy was approved two years ago. It defines four tiers
and assigns retention periods to each. Interviews indicate the policy is
unknown outside the Information Security team; no team surveyed could name its
own datasets' tiers.

## Access control

Access to the warehouse is granted per person by ticket. There is no group or
role layer, so access is never revoked when someone changes team. An audit last
quarter found 41 accounts with warehouse write access, of which 12 belong to
people who have left the Authority.

## Quality

There are no automated quality checks. Errors are found by downstream
consumers, usually the monthly ridership report, and reported by email.
