"""Inactive artifact-selection proposal: no deployment or authority migration."""
import json,unittest
from hashlib import sha256
from deployment.prepare_private_services import ROOT
D=ROOT/'deployment/candidates/trixie-zlib-v2'
class PromotionTests(unittest.TestCase):
    def test_exact_guarded_replacements_and_no_activation(self):
        p=json.loads((D/'promotion-PROPOSED.json').read_bytes())
        for k in ('approved','securityAcceptance','applyAuthorized','cloudActivationAuthorized','financialAuthorization','realProviderDispatchAuthorized'):
            self.assertIs(p[k],False)
        self.assertEqual({x['target'] for x in p['replacements']},{'deployment/private-services-v1.json','deployment/private-frontend-v1.json'})
        for x in p['replacements']:
            self.assertFalse(x['applyAuthorized'])
            self.assertEqual(sha256((ROOT/x['target']).read_bytes()).hexdigest(),x['beforeSHA256'])
            self.assertEqual(sha256((ROOT/x['proposedReplacement']).read_bytes()).hexdigest(),x['afterSHA256'])
            self.assertIs(json.loads((ROOT/x['proposedReplacement']).read_bytes())['launchable'],False)
        self.assertFalse(p['rollbackReferences']['rollbackOfFinancialOrSessionHistoryAllowed'])
        self.assertFalse(p['registry']['published']);self.assertFalse(p['registry']['registryManifestVerified'])
    def test_cohort_unchanged_application_and_exact_image_inventory(self):
        p=json.loads((D/'promotion-PROPOSED.json').read_bytes());raw=(D/'cohort.json').read_bytes();c=json.loads(raw)
        self.assertEqual(sha256(raw).hexdigest(),p['cohort'])
        self.assertEqual(c['outputs'],json.loads((ROOT/'deployment/private-role-cohort-v1.json').read_bytes())['outputs'])
        self.assertEqual(set(p['candidateImages']),{'frontend','backend','factory','counter','dispatcher','recovery'})
        self.assertEqual(p['candidateImages'],json.loads((D/'images.json').read_bytes())['candidateForReview'])
        self.assertEqual(c['candidate']['securityPackage']['confirmedFix'],'CVE-2026-85091')
    def test_shadow_changes_are_artifact_selection_only(self):
        services=json.loads((ROOT/'deployment/private-services-v1.json').read_bytes())
        proposed=json.loads((D/'proposed/private-services-v1.json').read_bytes())
        for x in (services,proposed):
            for k in ('activation','artifactSelections','buildRecipe','cohortManifest','cohortSHA256'):x.pop(k,None)
            x['roles']['frontend'].pop('image')
        self.assertEqual(services,proposed)
        frontend=json.loads((ROOT/'deployment/private-frontend-v1.json').read_bytes())
        proposed=json.loads((D/'proposed/private-frontend-v1.json').read_bytes())
        self.assertNotIn('fixture',proposed['artifacts']);self.assertFalse(proposed['productionManifest']['fixture'])
        for x in (frontend,proposed):
            for k in ('artifacts','productionManifest','roleCohort'):x.pop(k)
        self.assertEqual(frontend,proposed)
