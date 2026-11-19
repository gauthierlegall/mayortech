import test from 'node:test';
import assert from 'node:assert/strict';

// Logic tests for Séances & Instances Spécialisées (Lot 5)

function formatDeliberationRef(sessionDate, commissionCode, seq) {
  const year = sessionDate.length >= 4 ? sessionDate.substring(0, 4) : '2027';
  let code = commissionCode.replace(/[^A-Za-z0-9]/g, '').toUpperCase();
  if (code.startsWith('COMMISSION')) {
    code = `COM${code.replace('COMMISSION', '')}`;
  }
  const seqStr = String(seq).padStart(2, '0');
  return `DELIB-${year}-${code}-${seqStr}`;
}

function isQuorumSatisfied(presentCount, requiredCount) {
  return presentCount >= requiredCount;
}

function computeVoteOutcome(votesFor, votesAgainst, votesAbstention) {
  const totalExpressed = votesFor + votesAgainst;
  if (totalExpressed === 0) return 'en_attente';
  if (votesFor > votesAgainst) return 'favorable';
  if (votesAgainst > votesFor) return 'defavorable';
  return 'reserve';
}

function reorderAgendaItems(items, fromIndex, toIndex) {
  if (fromIndex < 0 || fromIndex >= items.length || toIndex < 0 || toIndex >= items.length) {
    return items;
  }
  const copy = [...items];
  const [removed] = copy.splice(fromIndex, 1);
  copy.splice(toIndex, 0, removed);
  return copy.map((it, idx) => ({ ...it, item_order: idx + 1 }));
}

test('formatDeliberationRef formats municipal references according to CGCT rules', () => {
  assert.equal(formatDeliberationRef('2027-04-10', 'commission-3', 1), 'DELIB-2027-COM3-01');
  assert.equal(formatDeliberationRef('2027-04-10', 'commission-1', 12), 'DELIB-2027-COM1-12');
  assert.equal(formatDeliberationRef('2027-06-20', 'cao', 4), 'DELIB-2027-CAO-04');
  assert.equal(formatDeliberationRef('2027-09-15', 'ccspl', 2), 'DELIB-2027-CCSPL-02');
  assert.equal(formatDeliberationRef('2027-11-05', 'ccid', 3), 'DELIB-2027-CCID-03');
});

test('isQuorumSatisfied checks legal threshold compliance', () => {
  assert.equal(isQuorumSatisfied(3, 3), true);
  assert.equal(isQuorumSatisfied(4, 3), true);
  assert.equal(isQuorumSatisfied(2, 3), false);
  assert.equal(isQuorumSatisfied(0, 1), false);
});

test('computeVoteOutcome computes accurate vote majority', () => {
  assert.equal(computeVoteOutcome(5, 0, 1), 'favorable');
  assert.equal(computeVoteOutcome(1, 4, 2), 'defavorable');
  assert.equal(computeVoteOutcome(3, 3, 1), 'reserve');
  assert.equal(computeVoteOutcome(0, 0, 5), 'en_attente');
});

test('reorderAgendaItems maintains sequential 1-based order', () => {
  const initial = [
    { id: '1', title: 'Point A', item_order: 1 },
    { id: '2', title: 'Point B', item_order: 2 },
    { id: '3', title: 'Point C', item_order: 3 },
  ];
  const reordered = reorderAgendaItems(initial, 2, 0); // Move Point C to top
  assert.equal(reordered[0].title, 'Point C');
  assert.equal(reordered[0].item_order, 1);
  assert.equal(reordered[1].title, 'Point A');
  assert.equal(reordered[1].item_order, 2);
  assert.equal(reordered[2].title, 'Point B');
  assert.equal(reordered[2].item_order, 3);
});
