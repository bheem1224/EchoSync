import { parse } from 'svelte/compiler';
import fs from 'fs';
const code = fs.readFileSync('./src/routes/library/manager/+page.svelte', 'utf8');
try {
  parse(code);
  console.log('parsed ok');
} catch (err) {
  console.error('error:', err.message);
  if (err.start) console.error('start', err.start, 'end', err.end);
  if (err.frame) console.error(err.frame);
  process.exit(1);
}
