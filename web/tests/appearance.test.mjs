import test from 'node:test';
import assert from 'node:assert/strict';
import {palettes,normalizeAppearance} from '../appearance.js';

function luminance(hex){const channels=hex.slice(1).match(/../g).map(x=>parseInt(x,16)/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);return .2126*channels[0]+.7152*channels[1]+.0722*channels[2];}
function contrast(a,b){const x=luminance(a),y=luminance(b);return(Math.max(x,y)+.05)/(Math.min(x,y)+.05);}
test('each palette keeps buttons and selected labels readable',()=>{
  for(const palette of palettes){assert.ok(contrast(palette.accent,'#ffffff')>=4.5,palette.name);assert.ok(contrast(palette.accent,palette.soft)>=4.5,palette.name);}
});
test('stored settings cannot inject arbitrary CSS or select an unknown density',()=>{
  assert.deepEqual(normalizeAppearance({color:'url(javascript:evil)',density:'tiny'}),{color:'blue',density:'compact'});
  assert.deepEqual(normalizeAppearance({color:'blue',density:'comfortable'}),{color:'blue',density:'comfortable'});
});
