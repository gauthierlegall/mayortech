import test from 'node:test';
import assert from 'node:assert/strict';

// Pure logic tests for Enfance & Social domain (Lot 4)
function getBracketForQF(qf) {
  if (qf <= 450) return 'T1';
  if (qf <= 750) return 'T2';
  if (qf <= 1100) return 'T3';
  if (qf <= 1600) return 'T4';
  return 'T5';
}

const CANTEEN_BRACKETS_INFO = {
  T1: {label: 'Tranche 1 (QF ≤ 450 €) - Tarif solidaire', rate: '1,00 €', subsidy: 'Commune : 3,95 €', css: 't1'},
  T2: {label: 'Tranche 2 (451 € à 750 €)', rate: '2,15 €', subsidy: 'Commune : 2,80 €', css: 't2'},
  T3: {label: 'Tranche 3 (751 € à 1 100 €)', rate: '3,20 €', subsidy: 'Commune : 1,75 €', css: 't3'},
  T4: {label: 'Tranche 4 (1 101 € à 1 600 €)', rate: '4,10 €', subsidy: 'Commune : 0,85 €', css: 't4'},
  T5: {label: 'Tranche 5 (> 1 600 €) - Tarif plein', rate: '4,95 €', subsidy: 'Sans subvention', css: 't5'},
};

function shiftYear(yearStr, delta = 1) {
  const parts = yearStr.split('-');
  if (parts.length === 2) {
    return `${parseInt(parts[0], 10) + delta}-${parseInt(parts[1], 10) + delta}`;
  }
  return `${parseInt(yearStr, 10) + delta}`;
}

test('getBracketForQF accurately computes municipal canteen tiers', () => {
  assert.equal(getBracketForQF(0), 'T1');
  assert.equal(getBracketForQF(350), 'T1');
  assert.equal(getBracketForQF(450), 'T1');

  assert.equal(getBracketForQF(451), 'T2');
  assert.equal(getBracketForQF(600), 'T2');
  assert.equal(getBracketForQF(750), 'T2');

  assert.equal(getBracketForQF(751), 'T3');
  assert.equal(getBracketForQF(900), 'T3');
  assert.equal(getBracketForQF(1100), 'T3');

  assert.equal(getBracketForQF(1101), 'T4');
  assert.equal(getBracketForQF(1400), 'T4');
  assert.equal(getBracketForQF(1600), 'T4');

  assert.equal(getBracketForQF(1601), 'T5');
  assert.equal(getBracketForQF(2500), 'T5');
});

test('CANTEEN_BRACKETS_INFO matches municipal rates of Plougastel', () => {
  assert.equal(CANTEEN_BRACKETS_INFO.T1.rate, '1,00 €');
  assert.equal(CANTEEN_BRACKETS_INFO.T2.rate, '2,15 €');
  assert.equal(CANTEEN_BRACKETS_INFO.T3.rate, '3,20 €');
  assert.equal(CANTEEN_BRACKETS_INFO.T4.rate, '4,10 €');
  assert.equal(CANTEEN_BRACKETS_INFO.T5.rate, '4,95 €');
});

test('shiftYear shifts school year string forward', () => {
  assert.equal(shiftYear('2026-2027'), '2027-2028');
  assert.equal(shiftYear('2026-2027', 2), '2028-2029');
  assert.equal(shiftYear('2027'), '2028');
});
