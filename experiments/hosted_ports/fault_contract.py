"""Pinned synthetic expectation; not an application price or financial grant."""
EXPECTED=(6845,1,0)
def assert_state(before,after):
 if before!=after:raise AssertionError('Committed reservation or history changed')
 if tuple(before)!=EXPECTED:raise AssertionError('Unexpected synthetic charge/INTENT/delivery tuple')
