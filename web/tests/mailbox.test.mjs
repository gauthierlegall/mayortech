import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseRecipients,mailFolderLinks} from '../mailbox.js';
test('RFC names and groups resolve to recipients without treating commas as separators',()=>{
  assert.deepEqual(parseRecipients('"Martin, Léa" <lea@example.fr>, Équipe: paul@example.fr, anne@example.fr;'),['lea@example.fr','paul@example.fr','anne@example.fr']);
});
test('composer rejects header injection, oversized input and incomplete recipients',()=>{
  for(const input of ['a@example.fr\r\nBcc: autre@example.fr','incomplet','a@b', 'x'.repeat(4001)])assert.throws(()=>parseRecipients(input));
  assert.deepEqual(parseRecipients(''),[]);
});
test('folder navigation is global and encodes the current folder once',()=>{
  const html=mailFolderLinks('drafts',[{id:'inbox',unread:3}]);
  assert.equal((html.match(/aria-current/g)||[]).length,1);
  assert.match(html,/Boîte de réception/);assert.match(html,/folder-count">3/);assert.match(html,/#\/mail\?folder=sent/);
});
