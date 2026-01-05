import { existsSync, mkdirSync, writeFileSync } from 'fs';
import { join, resolve } from 'path';
import { spawn } from 'bun';
import ora from 'ora';
import chalk from 'chalk';

const log = {
  success: (text: string) => console.log(chalk.green(`  ✓ ${text}`)),
  error: (text: string) => console.log(chalk.red(`  ✗ ${text}`)),
  info: (text: string) => console.log(chalk.blue(`  ℹ ${text}`)),
  warn: (text: string) => console.log(chalk.yellow(`  ⚠ ${text}`)),
};

interface VersionInfo {
  version: string;
  build: string;
}

interface FrontendBuildOptions {
  release: boolean;
  clean: boolean;
  rootDir: string;
  outputDir: string;
}

async function execCommand(cmd: string[], cwd: string, description: string): Promise<boolean> {
  const spinner = ora(description).start();
  
  try {
    const proc = spawn(cmd, {
      cwd,
      stdout: 'pipe',
      stderr: 'pipe',
    });

    const output: string[] = [];
    const errors: string[] = [];

    if (proc.stdout) {
      for await (const chunk of proc.stdout) {
        output.push(new TextDecoder().decode(chunk));
      }
    }

    if (proc.stderr) {
      for await (const chunk of proc.stderr) {
        errors.push(new TextDecoder().decode(chunk));
      }
    }

    await proc.exited;

    if (proc.exitCode === 0) {
      spinner.succeed(description);
      return true;
    } else {
      spinner.fail(description);
      if (errors.length > 0) {
        console.log(chalk.red('\n' + errors.join('')));
      }
      return false;
    }
  } catch (error) {
    spinner.fail(description);
    console.error(error);
    return false;
  }
}

async function getCurrentVersion(): Promise<VersionInfo> {
  const versionFile = join(import.meta.dir, '..', 'frontend.json');
  if (existsSync(versionFile)) {
    return JSON.parse(await Bun.file(versionFile).text());
  }
  return { version: '0.1', build: new Date().toISOString().split('T')[0] };
}

async function updateVersion(version?: string): Promise<VersionInfo> {
  const current = await getCurrentVersion();
  const newVersion: VersionInfo = {
    version: version || current.version,
    build: new Date().toISOString().replace(/[:.]/g, '-').replace('T', '_').split('.')[0],
  };
  
  const versionFile = join(import.meta.dir, '..', 'frontend.json');
  writeFileSync(versionFile, JSON.stringify(newVersion, null, 2));
  
  return newVersion;
}

export async function buildFrontend(options: FrontendBuildOptions): Promise<boolean> {
  const UI_DIR = join(options.rootDir, 'ui', 'Oracle');

  // Update version
  const versionInfo = await updateVersion();
  const buildDate = versionInfo.build;
  
  log.info(`Frontend Version: ${versionInfo.version} (${buildDate})`);

  // Update environment file
  const envFile = join(UI_DIR, 'src', 'environments', 'environment.prod.ts');
  const envContent = `export const environment = {
  production: true,
  version: '${versionInfo.version}',
  buildDate: '${buildDate}',
  apiUrl: 'http://localhost:8899'
};
`;
  writeFileSync(envFile, envContent);
  log.success('Updated environment.prod.ts');

  // Clean Angular dist directory if clean flag is set
  if (options.clean) {
    const distDir = join(UI_DIR, 'dist');
    if (existsSync(distDir)) {
      const cleanSuccess = await execCommand(
        ['powershell', '-Command', `Remove-Item -Path "${distDir}" -Recurse -Force`],
        UI_DIR,
        'Cleaning Angular dist directory'
      );
      if (!cleanSuccess) log.warn('Failed to clean dist directory, continuing...');
    }
  }

  // Install dependencies
  if (!existsSync(join(UI_DIR, 'node_modules'))) {
    const success = await execCommand(['npm', 'install'], UI_DIR, 'Installing dependencies');
    if (!success) return false;
  }

  // Build Angular app to local dist for Tauri
  const buildSuccess = await execCommand(
    ['npm', 'run', 'build', '--', '--output-path=dist/oracle'],
    UI_DIR,
    'Building Angular application'
  );
  if (!buildSuccess) return false;

  // Build Tauri app if release
  if (options.release) {
    const tauriSuccess = await execCommand(
      ['npm', 'run', 'tauri', 'build'],
      UI_DIR,
      'Building Tauri desktop application'
    );
    if (!tauriSuccess) return false;
  }

  // Copy Angular build output to deploy output directory
  const angularDistDir = join(UI_DIR, 'dist', 'oracle');
  const outputFrontendDir = join(options.outputDir, 'frontend');
  if (existsSync(angularDistDir)) {
    const copySuccess = await execCommand(
      ['powershell', '-Command', `Copy-Item -Path "${angularDistDir}\\*" -Destination "${outputFrontendDir}" -Recurse -Force`],
      options.rootDir,
      'Copying Angular build to output directory'
    );
    if (!copySuccess) log.warn('Failed to copy Angular build to output');
  }

  log.success('Frontend build completed');
  return true;
}
