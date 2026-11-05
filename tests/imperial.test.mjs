import {test} from 'node:test';
import assert from 'node:assert/strict';
import {formatLength,parseLength,inchesToWorld,squareFeet,imperialMessage} from '../apps/web/src/imperial.ts';
for(const [text,inches] of [[`3' 6 1/2"`,42.5],[`3'-6"`,42],[`42.5"`,42.5],['3.5 ft',42],['1/2',.5],[`-1' 6"`,-18],[`6'`,72],['0',0]])test(`parse imperial ${text}`,()=>assert.equal(parseLength(text),inchesToWorld(inches)));
test('fraction formatting and inch carry',()=>{assert.equal(formatLength(914.4),`3' 0"`);assert.equal(formatLength(1079.5),`3' 6 1/2"`);assert.equal(formatLength(-25.4),`-0' 1"`);});
test('reject invalid length',()=>{for(const input of ['', 'abc','1/0','--2',`3' garbage`])assert.equal(parseLength(input),null);});
test('area and engineering message conversion',()=>{assert.equal(squareFeet(304.8**2),1);assert.equal(imperialMessage('Required 914.4 mm; available 762 mm.'),`Required 3' 0"; available 2' 6".`);});
