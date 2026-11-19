import test from 'node:test';
import assert from 'node:assert/strict';
import {encodeState, decodeState, normalizeStateResponse} from '../src/state-codec.mjs';

test('binary state survives base64 encoding without interpreting HTML or text', () => {
  const original = Uint8Array.from([0, 255, 128, 60, 62, 65, 1]);
  assert.deepEqual(decodeState(encodeState(original)), original);
});

test('invalid base64 and oversized states are refused', () => {
  assert.throws(() => decodeState('not base64%%%'), /invalid_state/);
  assert.throws(() => encodeState(new Uint8Array(1025), 1024), /state_too_large/);
});

test('response requires an explicit revision and state envelope', () => {
  assert.throws(() => normalizeStateResponse({state_base64: ''}), /invalid_state_response/);
  const response = normalizeStateResponse({state_base64: '', revision_hash: null});
  assert.equal(response.revision_hash, null);
  assert.equal(response.state.length, 0);
});
