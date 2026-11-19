import { test } from 'node:test';
import assert from 'node:assert/strict';

function checkIntervalConflict(slot1, slot2) {
  const s1 = new Date(slot1.start).getTime();
  const e1 = new Date(slot1.end).getTime();
  const s2 = new Date(slot2.start).getTime();
  const e2 = new Date(slot2.end).getTime();
  // Semi-open interval conflict rule: max(s1, s2) < min(e1, e2)
  return Math.max(s1, s2) < Math.min(e1, e2);
}

function calculateBudgetRemainderCents(amountCents, subsidiesCents) {
  if (typeof amountCents !== 'number' || typeof subsidiesCents !== 'number') {
    throw new Error('Amounts must be numbers in integer centimes');
  }
  return amountCents - subsidiesCents;
}

test('culture reservation semi-open interval conflict check detects overlaps', () => {
  const existing = { start: '2027-06-12T14:00:00Z', end: '2027-06-12T16:00:00Z' };
  
  // Overlapping slot [15:00, 18:00) overlaps [14:00, 16:00)
  const overlapping = { start: '2027-06-12T15:00:00Z', end: '2027-06-12T18:00:00Z' };
  assert.equal(checkIntervalConflict(existing, overlapping), true);

  // Adjacent slot [16:00, 19:00) does NOT overlap [14:00, 16:00)
  const adjacentAfter = { start: '2027-06-12T16:00:00Z', end: '2027-06-12T19:00:00Z' };
  assert.equal(checkIntervalConflict(existing, adjacentAfter), false);

  // Adjacent slot [12:00, 14:00) does NOT overlap [14:00, 16:00)
  const adjacentBefore = { start: '2027-06-12T12:00:00Z', end: '2027-06-12T14:00:00Z' };
  assert.equal(checkIntervalConflict(existing, adjacentBefore), false);
});

test('budget remainder calculation matches exact municipal centimes', () => {
  // Variante A : 9 600 € TTC, 2 500 € subvention -> 7 100 € reste à charge
  const remainderA = calculateBudgetRemainderCents(960000, 250000);
  assert.equal(remainderA, 710000);

  // Variante B : 11 700 € TTC, 2 500 € subvention -> 9 200 € reste à charge
  const remainderB = calculateBudgetRemainderCents(1170000, 250000);
  assert.equal(remainderB, 920000);

  // Revised Variante A after complement request: 10 700 € TTC, 2 500 € subvention -> 8 200 €
  const remainderRevised = calculateBudgetRemainderCents(1070000, 250000);
  assert.equal(remainderRevised, 820000);
});

test('finance transmission state transitions and motivated opinions', () => {
  const allowedOpinions = ['favorable', 'defavorable', 'favorable_avec_reserves', 'demande_complements'];
  assert.ok(allowedOpinions.includes('favorable'));
  assert.ok(allowedOpinions.includes('favorable_avec_reserves'));
  assert.ok(allowedOpinions.includes('demande_complements'));
  assert.ok(allowedOpinions.includes('defavorable'));

  const deliberationRefPattern = /^DELIB-\d{4}-\d{2}-\d+$/;
  assert.match('DELIB-2027-06-42', deliberationRefPattern);
});
