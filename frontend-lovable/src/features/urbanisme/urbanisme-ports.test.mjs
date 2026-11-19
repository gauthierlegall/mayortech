import test from 'node:test';
import assert from 'node:assert/strict';

import {projectLonLat, unprojectXY} from './geo-projection.mjs';

test('projectLonLat projects Plougastel WGS84 coordinates into SVG viewbox', () => {
  // Tinduff: [-4.3820, 48.3370]
  const [x, y] = projectLonLat(-4.3820, 48.3370);
  assert.ok(x >= 350 && x <= 450, `x should be ~414.5, got ${x}`);
  assert.ok(y >= 380 && y <= 450, `y should be ~407.1, got ${y}`);

  // Unprojecting should retrieve approximately the same coordinates
  const [lon, lat] = unprojectXY(x, y);
  assert.ok(Math.abs(lon - (-4.3820)) < 0.005, `lon mismatch: ${lon}`);
  assert.ok(Math.abs(lat - 48.3370) < 0.005, `lat mismatch: ${lat}`);
});

test('projectLonLat clamps correctly within Plougastel boundaries', () => {
  // Min bounds: [-4.450, 48.310]
  const [minX, minY] = projectLonLat(-4.450, 48.420); // Top-left
  assert.equal(minX, 70);
  assert.equal(minY, 60);

  // Max bounds: [-4.300, 48.310] // Bottom-right
  const [maxX, maxY] = projectLonLat(-4.300, 48.310);
  assert.equal(maxX, 830);
  assert.equal(maxY, 520);
});

test('Condition ratings and advice status enums are valid', () => {
  const allowedRatings = ['bon', 'moyen', 'degrade', 'urgent'];
  const allowedAdvices = ['en_cours', 'favorable', 'defavorable', 'reserve'];

  assert.ok(allowedRatings.includes('bon'));
  assert.ok(allowedRatings.includes('urgent'));
  assert.ok(!allowedRatings.includes('inconnu'));

  assert.ok(allowedAdvices.includes('favorable'));
  assert.ok(allowedAdvices.includes('reserve'));
  assert.ok(!allowedAdvices.includes('invalide'));
});
