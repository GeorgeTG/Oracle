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
  verbose: boolean;
  rootDir: string;
  outputDir: string;
}

async function execCommand(cmd: string[], cwd: string, description: string, verbose: boolean = false): Promise<boolean> {
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
        const text = new TextDecoder().decode(chunk);
        output.push(text);
        if (verbose) {
          spinner.stop();
          process.stdout.write(text);
          spinner.start();
        }
      }
    }

    if (proc.stderr) {
      for await (const chunk of proc.stderr) {
        const text = new TextDecoder().decode(chunk);
        errors.push(text);
        if (verbose) {
          spinner.stop();
          process.stderr.write(text);
          spinner.start();
        }
      }
    }

    await proc.exited;

    if (proc.exitCode === 0) {
      spinner.succeed(description);
      return true;
    } else {
      spinner.fail(description);
      if (errors.length > 0 && !verbose) {
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

  // Install dependencies
  if (!existsSync(join(UI_DIR, 'node_modules'))) {
    const success = await execCommand(['npm', 'install'], UI_DIR, 'Installing dependencies', options.verbose);
    if (!success) return false;
  }

  // Build Angular app
  const buildSuccess = await execCommand(
    ['npm', 'run', 'build'],
    UI_DIR,
    'Building Angular application',
    options.verbose
  );
  if (!buildSuccess) return false;

  // Build Tauri app if release
  if (options.release) {
    const tauriSuccess = await execCommand(
      ['npm', 'run', 'tauri', 'build'],
      UI_DIR,
      'Building Tauri desktop application',
      options.verbose
    );
    if (!tauriSuccess) return false;
  }

  log.success('Frontend build completed');
  return true;
}
