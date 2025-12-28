#!/usr/bin/env node
const fs = require('fs');
const p = require('path');
// Resolve and validate the path to prevent path traversal
// Locate repository root and read commit message from .git without using CLI input
function findRepoRoot(startDir) {
  let dir = fs.realpathSync(startDir);
  while (true) {
    const gitDir = p.join(dir, '.git');
    if (fs.existsSync(gitDir) && fs.statSync(gitDir).isDirectory()) {
      return dir;
    }
    const parent = p.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

const repoRoot = findRepoRoot(process.cwd());
if (!repoRoot) {
  console.error('commit-msg: failed to locate repository root (.git)');
  process.exit(1);
}

const allowedFiles = ['COMMIT_EDITMSG', 'MERGE_MSG', 'SQUASH_MSG'];
let commitPath = null;
for (const fname of allowedFiles) {
  const candidate = p.join(repoRoot, '.git', fname);
  if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
    commitPath = candidate;
    break;
  }
}

if (!commitPath) {
  console.error('commit-msg: no commit message file found in .git');
  process.exit(1);
}

let msg;
try {
  msg = fs.readFileSync(commitPath, 'utf8').trim();
} catch (e) {
  console.error('commit-msg: failed to read commit message file');
  process.exit(1);
}

const TYPES = [
  'feat','fix','docs','style','refactor','perf','test','build','ci','chore','revert'
];
const headerRegex = new RegExp(
  `^(${TYPES.join('|')})(!?)(\\([^\\)]+\\))?:\\s.+`
);

function validate(message) {
  const lines = message.split(/\r?\n/);
  const header = lines[0] || '';
  if (header.length > 100) {
    return 'Header too long (>100 chars).';
  }
  if (!headerRegex.test(header)) {
    return 'Header must match: type(scope?): subject';
  }
  if (/\.$/.test(header)) {
    return 'Header should not end with a period.';
  }
  return null;
}

const error = validate(msg);
if (error) {
  console.error(`\n✖ Commit message invalid: ${error}`);
  console.error('\nExample: feat(users): adicionar endpoint de perfil');
  process.exit(1);
}
console.log('✔ Commit message validated');
