"""Reviewed invented replies for missing-area/relative-date HTTP tests only."""
from unittest.mock import patch
from experiments.hosted_identity import server
from experiments.service_isolation import synthetic
original=synthetic.outputs
def outputs():
 return {**original(),
  'Coffee and museum on November 7, 2026':dict(activities=['coffee','museum'],location=None,date='2026-11-07',budget_per_person=None,preferences=[]),
  'Coffee and museum in Baltimore tomorrow':dict(activities=['coffee','museum'],location='Baltimore',date=None,date_expressions=['tomorrow'],budget_per_person=None,preferences=[])}
def main():
 with patch.object(synthetic,'outputs',outputs):server.main()
if __name__=='__main__':main()
