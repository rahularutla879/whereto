"""Honest private-hosted startup gate, not a bypass of backend.main admission.

P9 cannot launch safely until the actual public-token/native-authority bridge and
real dependencies exist. Configuration booleans or an environment flag are not
readiness attestations. This checkpoint deliberately has no activation branch.
"""
from pathlib import Path
import json,sys

def blockers():
    plan=json.loads(Path(__file__).with_name('private-startup-v1.json').read_text())
    if plan.get('active') is not False or plan.get('launchable') is not False or plan.get('providerDispatchEnabled') is not False:
        raise RuntimeError('Unreviewed private startup configuration')
    return tuple(plan['missingReviewedBindings'])

def main():
    blockers()
    print('Private hosted startup refused: public native-session integration and enrolled dependencies remain incomplete.',file=sys.stderr)
    return 78

if __name__=='__main__':raise SystemExit(main())
