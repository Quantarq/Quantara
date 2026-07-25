import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const srcRoot = path.resolve(__dirname, '../src');
const allowedFiles = new Set([path.join(srcRoot, 'utils/logger.js')]);
const sourceExtensions = new Set(['.js', '.jsx', '.ts', '.tsx']);

function listSourceFiles(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) return listSourceFiles(fullPath);
    if (!sourceExtensions.has(path.extname(entry.name))) return [];
    return [fullPath];
  });
}

describe('frontend production logging', () => {
  it('routes production source logging through the dev-only logger', () => {
    const offenders = listSourceFiles(srcRoot)
      .filter((file) => !allowedFiles.has(file))
      .filter((file) => fs.readFileSync(file, 'utf8').includes('console.'));

    expect(offenders).toEqual([]);
  });

  it('keeps logger output gated to development builds', () => {
    const loggerSource = fs.readFileSync(path.join(srcRoot, 'utils/logger.js'), 'utf8');

    expect(loggerSource).toContain('import.meta.env.DEV');
    expect(loggerSource).not.toContain('console.log');
  });
});