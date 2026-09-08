#!/usr/bin/env node
/**
 * A minimal Python lexer used to sanity-check the backend sources on a machine
 * with no Python interpreter available.
 *
 * It verifies, per file:
 *   - every string literal is terminated (catches nested triple-quote bugs)
 *   - brackets balance
 *   - indentation uses spaces only
 *
 * It is NOT a substitute for `python -m compileall`; it catches the class of
 * error that content-heavy files with embedded source code actually hit.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const PREFIX = /[rRbBuUfF]{0,3}$/;

function lex(src, file) {
  const problems = [];
  const stack = [];
  let i = 0;
  let line = 1;
  let atLineStart = true;

  const openers = { '(': ')', '[': ']', '{': '}' };
  const closers = { ')': '(', ']': '[', '}': '{' };

  while (i < src.length) {
    const ch = src[i];

    if (ch === '\n') {
      line++;
      i++;
      atLineStart = true;
      continue;
    }

    if (atLineStart && ch === '\t') {
      problems.push({ line, message: 'tab used for indentation' });
    }
    if (ch !== ' ' && ch !== '\t') atLineStart = false;

    if (ch === '#') {
      while (i < src.length && src[i] !== '\n') i++;
      continue;
    }

    if (ch === '"' || ch === "'") {
      // Determine prefix (r-strings disable escapes).
      const before = src.slice(Math.max(0, i - 3), i);
      const prefixMatch = before.match(PREFIX);
      const prefix = prefixMatch ? prefixMatch[0].toLowerCase() : '';
      const raw = prefix.includes('r');

      const triple = src.slice(i, i + 3);
      const isTriple = triple === ch.repeat(3);
      const delim = isTriple ? ch.repeat(3) : ch;
      const startLine = line;
      i += delim.length;

      let closed = false;
      while (i < src.length) {
        if (src[i] === '\\' && !raw) {
          if (src[i + 1] === '\n') line++;
          i += 2;
          continue;
        }
        if (src[i] === '\n') {
          line++;
          if (!isTriple) {
            problems.push({ line: startLine, message: 'unterminated single-line string' });
            closed = true;
            break;
          }
          i++;
          continue;
        }
        if (src.startsWith(delim, i)) {
          i += delim.length;
          closed = true;
          break;
        }
        i++;
      }
      if (!closed) {
        problems.push({
          line: startLine,
          message: `unterminated ${isTriple ? 'triple-quoted' : ''} string opened with ${delim}`,
        });
      }
      continue;
    }

    if (openers[ch]) {
      stack.push({ ch, line });
      i++;
      continue;
    }
    if (closers[ch]) {
      const top = stack.pop();
      if (!top) {
        problems.push({ line, message: `unmatched closing '${ch}'` });
      } else if (openers[top.ch] !== ch) {
        problems.push({
          line,
          message: `'${ch}' closes '${top.ch}' opened on line ${top.line}`,
        });
      }
      i++;
      continue;
    }

    i++;
  }

  for (const open of stack) {
    problems.push({ line: open.line, message: `unclosed '${open.ch}'` });
  }
  return problems.map((p) => ({ ...p, file }));
}

function walk(dir, out = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (['__pycache__', '.venv', 'node_modules', '.git'].includes(entry.name)) continue;
      walk(full, out);
    } else if (entry.name.endsWith('.py')) {
      out.push(full);
    }
  }
  return out;
}

const roots = process.argv.slice(2);
if (!roots.length) {
  console.error('usage: node pylex-check.js <dir> [dir...]');
  process.exit(2);
}

let all = [];
let fileCount = 0;
for (const root of roots) {
  for (const file of walk(root)) {
    fileCount++;
    all = all.concat(lex(fs.readFileSync(file, 'utf8'), file));
  }
}

if (all.length === 0) {
  console.log(`OK: ${fileCount} Python files lexed cleanly`);
  process.exit(0);
}
for (const problem of all) {
  console.log(`${problem.file}:${problem.line}: ${problem.message}`);
}
console.log(`\n${all.length} problem(s) across ${fileCount} files`);
process.exit(1);
