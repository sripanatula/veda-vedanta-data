# Project TODO List

This file tracks planned improvements and future work for the `veda-vedanta-data` repository.

## Duplicate Content Check

**Problem:**
The `veda-vedanta-raw` repository has a deduplication check (`--dedupe-last`) that only compares new content against the single most recent verse. This doesn't prevent re-adding older content or content that is substantially similar but not identical.

**Proposed Solution:**
Implement a more robust duplication check within `update_from_raw.py`. Before processing a new file, its content could be compared against all existing raw `.txt` files already present in the `vv/data/...` directory. This would provide a stronger guarantee against accidentally re-introducing content that has already been published.