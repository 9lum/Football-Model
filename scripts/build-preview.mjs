import {readFile,writeFile} from 'node:fs/promises';
await writeFile('site-preview.html',await readFile('web/redirect.template.html','utf8'));
console.log('Built compatibility redirect to the professional dashboard');
