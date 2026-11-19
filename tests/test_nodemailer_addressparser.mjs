import test from 'node:test';
import assert from 'node:assert/strict';
import addressparser from '../web/vendor/nodemailer-addressparser.js';

test('quoted display name keeps its comma inside one mailbox', () => {
  assert.deepEqual(addressparser('"Dupont, Marie" <marie@example.invalid>, jean@example.invalid'), [
    {address:'marie@example.invalid', name:'Dupont, Marie'},
    {address:'jean@example.invalid', name:''},
  ]);
});

test('RFC group remains structured and flatten exposes its mailboxes', () => {
  const value='Equipe: pierre@example.invalid, "Anne Martin" <anne@example.invalid>;';
  assert.deepEqual(addressparser(value), [{name:'Equipe', group:[
    {address:'pierre@example.invalid', name:''},
    {address:'anne@example.invalid', name:'Anne Martin'},
  ]}]);
  assert.deepEqual(addressparser(value,{flatten:true}).map(mailbox=>mailbox.address), [
    'pierre@example.invalid','anne@example.invalid',
  ]);
});

test('comment display name and Unicode display name are preserved as text', () => {
  assert.deepEqual(addressparser('chef@example.invalid (Chef des travaux), Élodie <elodie@example.invalid>'), [
    {address:'chef@example.invalid', name:'Chef des travaux'},
    {address:'elodie@example.invalid', name:'Élodie'},
  ]);
});
