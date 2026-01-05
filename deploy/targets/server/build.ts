import { existsSync, mkdirSync, writeFileSync } from 'fs';
import { join } from 'path';
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

interface ServerBuildOptions {
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
  const versionFile = join(import.meta.dir, '..', '..', 'server.json');
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
  
  const versionFile = join(import.meta.dir, '..', '..', 'server.json');
  writeFileSync(versionFile, JSON.stringify(newVersion, null, 2));
  
  return newVersion;
}

export async function buildServer(options: ServerBuildOptions): Promise<boolean> {
  const SERVER_DIR = join(options.rootDir, 'server');
  const DEPLOY_DIR = join(options.rootDir, 'deploy');

  // Update version
  const versionInfo = await updateVersion();
  const buildDate = versionInfo.build;
  
  log.info(`Server Version: ${versionInfo.version} (${buildDate})`);

  // Run pack_modules.py to create server.pyz (if needed)
  const packScript = join(import.meta.dir, 'pack_modules.py');
  if (existsSync(packScript)) {
    // Use Python from venv to get all dependencies
    const venvPython = join(DEPLOY_DIR, '.venv', 'Scripts', 'python.exe');
    const pythonExe = existsSync(venvPython) ? venvPython : 'C:/Python314/python.exe';
    
    const success = await execCommand(
      [pythonExe, packScript],
      SERVER_DIR,
      'Creating server.pyz archive',
      options.verbose
    );
    if (!success) {
      log.warn('Failed to create server.pyz - continuing anyway');
    }
  }

  // Run PyInstaller if release build
  if (options.release) {
    // Find PyInstaller
    const localPyInstaller = join(DEPLOY_DIR, '.venv', 'Scripts', 'pyinstaller.exe');
    const globalPyInstaller = join(options.rootDir, '.venv', 'Scripts', 'pyinstaller.exe');
    
    let pyinstallerPath = '';
    if (existsSync(localPyInstaller)) {
      pyinstallerPath = localPyInstaller;
    } else if (existsSync(globalPyInstaller)) {
      pyinstallerPath = globalPyInstaller;
    }
    
    if (pyinstallerPath) {
      // Build both server and tray versions
      const specs = [
        { spec: join(DEPLOY_DIR, 'Oracle-Server.spec'), name: 'Oracle-Server' },
        { spec: join(DEPLOY_DIR, 'Oracle-Server-Tray.spec'), name: 'Oracle-Server-Tray' }
      ];
      
      for (const { spec, name } of specs) {
        if (existsSync(spec)) {
          const buildSuccess = await execCommand(
            [pyinstallerPath, spec],
            DEPLOY_DIR,
            `Building ${name}.exe with PyInstaller`,
            options.verbose
          );
          
          if (!buildSuccess) {
            log.error(`${name} build failed`);
            return false;
          }
          
          log.success(`${name}.exe built successfully`);
        }
      }
    } else {
      log.error('PyInstaller not installed - cannot create release build');
      log.info('Run: bun run setup');
      return false;
    }
  }

  log.success('Server build completed');
  return true;
}
