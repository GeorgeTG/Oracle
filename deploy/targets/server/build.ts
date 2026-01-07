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

  // Read build.json configuration
  const buildConfigPath = join(import.meta.dir, 'build.json');
  const buildConfig = JSON.parse(await Bun.file(buildConfigPath).text());
  
  const venvPath = join(options.rootDir, buildConfig.dir, `${buildConfig.name}-venv`);
  const venvPython = join(venvPath, 'Scripts', 'python.exe');
  const pipExe = join(venvPath, 'Scripts', 'pip.exe');
  const pyinstallerExe = join(venvPath, 'Scripts', 'pyinstaller.exe');

  // Update version
  const versionInfo = await updateVersion();
  const buildDate = versionInfo.build;
  
  log.info(`Server Version: ${versionInfo.version} (${buildDate})`);

  // Check venv exists
  if (!existsSync(venvPath)) {
    log.error(`Server venv not found at ${venvPath}. Run setup first.`);
    return false;
  }

  // Run pack_modules.py to create server.pyz (if needed)
  const packScript = join(import.meta.dir, 'pack_modules.py');
  if (existsSync(packScript)) {
    const success = await execCommand(
      [venvPython, packScript],
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
    if (!existsSync(pyinstallerExe)) {
      log.error('PyInstaller not installed in server venv. Run setup first.');
      return false;
    }
    
    // Build both server and tray versions
    const specs = [
      { spec: join(SERVER_DIR, 'Oracle-Server.spec'), name: 'Oracle-Server' },
      { spec: join(SERVER_DIR, 'Oracle-Server-Tray.spec'), name: 'Oracle-Server-Tray' }
    ];
    
    const distPath = join(DEPLOY_DIR, 'build', 'dist');
    
    for (const { spec, name } of specs) {
      if (existsSync(spec)) {
        const buildPath = join(DEPLOY_DIR, 'build', name);
        
        const buildSuccess = await execCommand(
          [pyinstallerExe, '--distpath', distPath, '--workpath', buildPath, spec],
          SERVER_DIR,
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
  }

  log.success('Server build completed');
  return true;
}
