#!/usr/bin/env bun
import { spawn } from 'bun';
import { existsSync, mkdirSync } from 'fs';
import { join, resolve } from 'path';
import chalk from 'chalk';
import ora from 'ora';

const DEPLOY_DIR = import.meta.dir;
const VENV_DIR = join(DEPLOY_DIR, '.venv');
const PYTHON_EXE = join(VENV_DIR, 'Scripts', 'python.exe');
const PIP_EXE = join(VENV_DIR, 'Scripts', 'pip.exe');

const log = {
  title: (text: string) => console.log('\n' + chalk.magenta.bold('═'.repeat(60)) + '\n' + chalk.magenta.bold(`  ${text}`) + '\n' + chalk.magenta.bold('═'.repeat(60)) + '\n'),
  success: (text: string) => console.log(chalk.green(`  ✓ ${text}`)),
  error: (text: string) => console.log(chalk.red(`  ✗ ${text}`)),
  info: (text: string) => console.log(chalk.blue(`  ℹ ${text}`)),
};

async function execCommand(cmd: string[], description: string): Promise<boolean> {
  const spinner = ora(description).start();
  
  try {
    const proc = spawn(cmd, {
      cwd: DEPLOY_DIR,
      stdout: 'inherit',
      stderr: 'inherit',
    });

    const exitCode = await proc.exited;

    if (exitCode !== 0) {
      spinner.fail(`${description} failed`);
      return false;
    }

    spinner.succeed(description);
    return true;
  } catch (error) {
    spinner.fail(`${description} failed`);
    console.error(error);
    return false;
  }
}

async function setupBuildEnvironment() {
  log.title('🔧 Build Environment Setup');

  // Check if venv already exists
  if (existsSync(PYTHON_EXE)) {
    log.info('Virtual environment already exists');
    
    // Update dependencies
    const success = await execCommand(
      [PIP_EXE, 'install', '-r', 'requirements.txt', '--upgrade'],
      'Updating build dependencies'
    );

    // Install server dependencies for PyInstaller
    const serverReqs = join(DEPLOY_DIR, '..', 'server', 'requirements.txt');
    if (existsSync(serverReqs)) {
      await execCommand(
        [PIP_EXE, 'install', '-r', serverReqs],
        'Updating server dependencies'
      );
    }
    
    if (success) {
      log.success('Build environment is ready!');
      console.log(chalk.cyan('\nYou can now run:'));
      console.log(chalk.yellow('  bun run build'));
      console.log(chalk.yellow('  bun run release'));
    }
    return;
  }

  // Create new venv
  log.info('Creating new virtual environment...');
  
  const createVenv = await execCommand(
    ['python', '-m', 'venv', '.venv'],
    'Creating Python virtual environment'
  );

  if (!createVenv) {
    log.error('Failed to create virtual environment');
    process.exit(1);
  }

  // Install build dependencies
  const installDeps = await execCommand(
    [PIP_EXE, 'install', '-r', 'requirements.txt'],
    'Installing build dependencies'
  );

  if (!installDeps) {
    log.error('Failed to install build dependencies');
    process.exit(1);
  }

  // Install server dependencies for PyInstaller
  const serverReqs = join(DEPLOY_DIR, '..', 'server', 'requirements.txt');
  if (existsSync(serverReqs)) {
    const installServerDeps = await execCommand(
      [PIP_EXE, 'install', '-r', serverReqs],
      'Installing server dependencies'
    );

    if (!installServerDeps) {
      log.error('Failed to install server dependencies');
      process.exit(1);
    }
  }

  log.success('Build environment created successfully!');
  console.log(chalk.cyan('\nInstalled tools:'));
  console.log(chalk.yellow('  • PyInstaller - for creating executables'));
  console.log(chalk.yellow('  • Server dependencies - for building executables'));
  
  console.log(chalk.cyan('\nYou can now run:'));
  console.log(chalk.yellow('  bun run build'));
  console.log(chalk.yellow('  bun run release'));
}

setupBuildEnvironment();
