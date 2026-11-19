import test from 'node:test';
import assert from 'node:assert/strict';
import * as mailbox from '../web/mailbox.js';
const {mailboxDestination,readMailboxLocation}=mailbox;

test('folder and project survive route roundtrip without becoming a text search',()=>{
 const route=mailboxDestination({folder:'archive',projectId:'project-uuid',mailId:'source/id'});
 assert.deepEqual(readMailboxLocation(route),{folder:'archive',projectId:'project-uuid',mailId:'source/id'});
 assert.equal(new URLSearchParams(route.split('?')[1]).get('q'),null);
});

test('malformed links cannot pass an invalid folder or oversized project to the API',()=>{
 assert.deepEqual(readMailboxLocation('#/messagerie?folder=unknown&project='+'x'.repeat(101)),{folder:'inbox',projectId:null,mailId:null});
 assert.equal(readMailboxLocation('#/mail/%ZZ?folder=all').mailId,null);
 assert.equal(readMailboxLocation('#/mail','?project=uuid&folder=trash').projectId,'uuid');
});

test('drafts remain actor-private and project folders only filter imported sources',()=>{
 const route=mailboxDestination({folder:'drafts',projectId:'project-uuid'});
 assert.deepEqual(readMailboxLocation(route),{folder:'drafts',projectId:null,mailId:null});
});
