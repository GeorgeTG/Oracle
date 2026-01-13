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
  const buildJsonFile = join(import.meta.dir, 'build.json');
  if (existsSync(buildJsonFile)) {
    const buildConfig = JSON.parse(await Bun.file(buildJsonFile).text());
    return { 
      version: buildConfig.version || '0.1', 
      build: buildConfig.build || new Date().toISOString().split('T')[0] 
    };
  }
  return { version: '0.1', build: new Date().toISOString().split('T')[0] };
}

export async function buildLauncher(options: LauncherBuildOptions): Promise<boolean> {
  const LAUNCHER_DIR = join(options.rootDir, 'launcher');
  const DEPLOY_DIR = join(options.rootDir, 'deploy');

  // Read build.json configuration
  const buildConfigPath = join(import.meta.dir, 'build.json');
  const buildConfig = JSON.parse(await Bun.file(buildConfigPath).text());
  
  const venvPath = join(options.rootDir, buildConfig.dir, `${buildConfig.name}-venv`);
  const pipExe = join(venvPath, 'Scripts', 'pip.exe');
  const pyinstallerExe = join(venvPath, 'Scripts', 'pyinstaller.exe');

  // Read and update version from build.json
  const versionInfo = await getCurrentVersion();
  const buildDate = new Date().toISOString().replace(/[:.]/g, '-').replace('T', '_').split('.')[0];
  
  // Update build.json with new timestamp
  buildConfig.build = buildDate;
  writeFileSync(buildConfigPath, JSON.stringify(buildConfig, null, 2));
  
  log.info(`Launcher Version: ${versionInfo.version} (${buildDate})`);

  // Check venv exists
  if (!existsSync(venvPath)) {
    log.error(`Launcher venv not found at ${venvPath}. Run setup first.`);
    return false;
  }

  // Run PyInstaller if release build
  if (options.release) {
    const spec = join(LAUNCHER_DIR, 'Oracle-Launcher.spec');
    
    if (!existsSync(spec)) {
      log.error(`Spec file not found: ${spec}`);
      return false;
    }
    
    if (!existsSync(pyinstallerExe)) {
      log.error('PyInstaller not installed in launcher venv. Run setup first.');
      return false;
    }
    
    const distPath = join(DEPLOY_DIR, 'build', 'dist');
    const buildPath = join(DEPLOY_DIR, 'build', 'Oracle-Launcher');
    
    const buildSuccess = await execCommand(
      [pyinstallerExe, '--distpath', distPath, '--workpath', buildPath, spec],
      LAUNCHER_DIR,
      'Building Oracle-Launcher.exe with PyInstaller',
      options.verbose
    );
    
    if (!buildSuccess) {
      log.error('PyInstaller build failed');
      return false;
    }
    
    log.success('Oracle-Launcher.exe built successfully');
  }

  log.success('Launcher build completed');
  return true;
}
