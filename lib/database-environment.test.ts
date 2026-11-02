import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import path from 'node:path';

test('Next refuses public database credentials without printing their values',()=>{
  for(const key of ['NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY','NEXT_PUBLIC_WHERETO_DB_PASSWORD','NEXT_PUBLIC_DATABASE_URL']) {
    const result=spawnSync(process.execPath,['--experimental-strip-types',path.resolve('next.config.ts')],{
      env:{...process.env,[key]:'INVENTED_PRIVATE_SENTINEL'},encoding:'utf8',timeout:10000,
    });
    assert.notEqual(result.status,0);
    assert.match(result.stderr,/Database configuration must stay in the backend/);
    assert.ok(!result.stderr.includes('INVENTED_PRIVATE_SENTINEL'));
  }
});
