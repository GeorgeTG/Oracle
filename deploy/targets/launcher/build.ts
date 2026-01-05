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

interface LauncherBuildOptions {
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

export async function buildLauncher(options: LauncherBuildOptions): Promise<boolean> {
  const LAUNCHER_DIR = join(options.rootDir, 'launcher');
  const DEPLOY_DIR = join(options.rootDir, 'deploy');

  // Read version from server.json (launcher follows server version)
  const versionInfo = await getCurrentVersion();
  const buildDate = new Date().toISOString().replace(/[:.]/g, '-').replace('T', '_').split('.')[0];
  
  log.info(`Launcher Version: ${versionInfo.version} (${buildDate})`);

  // Create temporary build venv for PyInstaller
  const buildVenv = join(DEPLOY_DIR, 'build', 'launcher-venv');
  const pythonExe = 'C:/Python314/python.exe';
  
  if (!existsSync(buildVenv)) {
    mkdirSync(join(DEPLOY_DIR, 'build'), { recursive: true });
    const venvSuccess = await execCommand(
      [pythonExe, '-m', 'venv', 'launcher-venv'],
      join(DEPLOY_DIR, 'build'),
      'Creating launcher build environment',
      options.verbose
    );
    if (!venvSuccess) {
      log.error('Failed to create build venv');
      return false;
    }
  }
  
  // Install launcher dependencies in build venv
  const pipExe = join(buildVenv, 'Scripts', 'pip.exe');
  if (existsSync(pipExe)) {
    const requirementsFile = join(LAUNCHER_DIR, 'requirements.txt');
    const installSuccess = await execCommand(
      [pipExe, 'install', '--no-binary', ':all:', '-r', requirementsFile],
      DEPLOY_DIR,
      'Installing launcher dependencies (no binary)',
      options.verbose
    );
    if (!installSuccess) {
      log.warn('Failed to install dependencies - continuing anyway');
    }
  }

  // Run PyInstaller if release build
  if (options.release) {
    const spec = join(DEPLOY_DIR, 'Oracle-Launcher.spec');
    
    if (existsSync(spec)) {
      // Install PyInstaller in build venv if needed
      const pyinstallerExe = join(buildVenv, 'Scripts', 'pyinstaller.exe');
      
      if (!existsSync(pyinstallerExe) && existsSync(pipExe)) {
        await execCommand(
          [pipExe, 'install', 'pyinstaller'],
          DEPLOY_DIR,
          'Installing PyInstaller',
          options.verbose
        );
      }
      
      if (existsSync(pyinstallerExe)) {
        const buildSuccess = await execCommand(
          [pyinstallerExe, spec],
          DEPLOY_DIR,
          'Building Oracle-Launcher.exe with PyInstaller',
          options.verbose
        );
        
        if (!buildSuccess) {
          log.error('PyInstaller build failed');
          return false;
        }
        
        log.success('Oracle-Launcher.exe built successfully');
      } else {
        log.error('PyInstaller not installed');
        return false;
      }
    }
  }

  log.success('Launcher build completed');
  return true;
}
