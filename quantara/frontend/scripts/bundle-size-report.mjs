import { readFile, readdir, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';

const distDir = path.resolve('dist');
const reportPath = path.resolve('bundle-size-report.json');
const baselinePath = path.resolve('bundle-size-baseline.json');
const thresholdPercent = Number(process.env.BUNDLE_SIZE_THRESHOLD_PERCENT ?? 10);

async function collectFiles(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...await collectFiles(fullPath));
      continue;
    }

    const fileStat = await stat(fullPath);
    files.push({
      path: path.relative(distDir, fullPath).replaceAll(path.sep, '/'),
      bytes: fileStat.size,
    });
  }

  return files;
}

const files = await collectFiles(distDir);
files.sort((a, b) => b.bytes - a.bytes || a.path.localeCompare(b.path));

const totalBytes = files.reduce((sum, file) => sum + file.bytes, 0);
const report = {
  totalBytes,
  files,
};

await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`);

console.log(`Bundle size: ${totalBytes} bytes`);
for (const file of files.slice(0, 10)) {
  console.log(`${file.bytes.toString().padStart(10)}  ${file.path}`);
}

try {
  const baseline = JSON.parse(await readFile(baselinePath, 'utf8'));
  const baselineBytes = Number(baseline.totalBytes);
  if (Number.isFinite(baselineBytes) && baselineBytes > 0) {
    const deltaPercent = ((totalBytes - baselineBytes) / baselineBytes) * 100;
    console.log(`Bundle size change: ${deltaPercent.toFixed(2)}%`);

    if (deltaPercent > thresholdPercent) {
      const message = `Bundle size increased by ${deltaPercent.toFixed(2)}%, above ${thresholdPercent}% threshold`;
      if (process.env.BUNDLE_SIZE_FAIL_ON_THRESHOLD === 'true') {
        throw new Error(message);
      }
      console.warn(message);
    }
  }
} catch (error) {
  if (error.code !== 'ENOENT') {
    throw error;
  }
  console.log('No bundle size baseline found; report generated for baseline setup.');
}
