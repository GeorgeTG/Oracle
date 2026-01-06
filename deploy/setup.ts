#!/usr/bin/env bun
import { spawn } from 'bun';
import { existsSync, mkdirSync, readdirSync, rmSync } from 'fs';
import { join } from 'path';
import chalk from 'chalk';
import ora from 'ora';

const DEPLOY_DIR = import.meta.dir;
const ROOT_DIR = join(DEPLOY_DIR, '..');
const TARGETS_DIR = join(DEPLOY_DIR, 'targets');

// Check for --clean flag
const isClean = process.argv.includes('--clean');

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

async function setupTargetVenvs() {
  log.title('🔧 Target Virtual Environments Setup');
  
  if (isClean) {
    log.info('Clean mode enabled - removing existing virtual environments');
  }
  
  // Read all target build.json files
  const targetDirs = readdirSync(TARGETS_DIR, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory())
    .map(dirent => dirent.name);
  
  for (const targetName of targetDirs) {
    const buildJsonPath = join(TARGETS_DIR, targetName, 'build.json');
    
    if (!existsSync(buildJsonPath)) {
      continue;
    }
    
    const buildConfig = JSON.parse(await Bun.file(buildJsonPath).text());
    
    // Skip if venv is not required
    if (!buildConfig.venv) {
      continue;
    }
    
    const { name, root, dir } = buildConfig;
    
    if (!name || !root || !dir) {
      log.error(`Missing required fields in ${targetName}/build.json`);
      continue;
    }
    
    // Paths
    const requirementsPath = join(ROOT_DIR, root, 'requirements.txt');
    const venvPath = join(ROOT_DIR, dir, `${name}-venv`);
    const venvPython = join(venvPath, 'Scripts', 'python.exe');
    const venvPip = join(venvPath, 'Scripts', 'pip.exe');
    
    if (!existsSync(requirementsPath)) {
      log.error(`Requirements file not found: ${requirementsPath}`);
      continue;
    }
    
    // Remove venv if clean mode
    if (isClean && existsSync(venvPath)) {
      log.info(`Removing ${name} virtual environment...`);
      rmSync(venvPath, { recursive: true, force: true });
    }
    
    // Check if venv already exists
    if (existsSync(venvPython)) {
      log.info(`Virtual environment for ${name} already exists`);
      
      // Update dependencies - only build tomli from source to avoid mypyc issues
      await execCommand(
        [venvPip, 'install', '-r', requirementsPath, '--upgrade', '--no-binary', 'tomli'],
        `Updating ${name} dependencies`
      );
      
      continue;
    }
    
    // Create venv directory if needed
    mkdirSync(join(ROOT_DIR, dir), { recursive: true });
    
    // Create new venv
    log.info(`Creating virtual environment for ${name}...`);
    
    const createVenv = await execCommand(
      ['py', '-3', '-m', 'venv', venvPath],
      `Creating ${name} virtual environment`
    );
    
    if (!createVenv) {
      log.error(`Failed to create virtual environment for ${name}`);
      continue;
    }
    
    // Install dependencies - only build tomli from source to avoid mypyc issues
    const installDeps = await execCommand(
      [venvPip, 'install', '-r', requirementsPath, '--no-binary', 'tomli'],
      `Installing ${name} dependencies`
    );
    
    if (!installDeps) {
      log.error(`Failed to install dependencies for ${name}`);
      continue;
    }
    
    log.success(`${name} environment created successfully!`);
  }
  
  console.log(chalk.cyan('\nSetup complete! You can now run:'));
  console.log(chalk.yellow('  bun run build'));
  console.log(chalk.yellow('  bun run release'));
  console.log(chalk.cyan('\nTo clean and rebuild all venvs:'));
  console.log(chalk.yellow('  bun run setup --clean'));
}

setupTargetVenvs();
