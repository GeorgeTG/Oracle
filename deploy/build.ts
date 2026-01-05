#!/usr/bin/env bun
import { existsSync, rmSync, mkdirSync, writeFileSync } from 'fs';
import { join, resolve, basename, dirname } from 'path';
import { program } from 'commander';
import { glob } from 'glob';
import chalk from 'chalk';
import ora from 'ora';

// Types
interface BuildOptions {
  target: string;
  release: boolean;
  clean: boolean;
  verbose: boolean;
}

interface BuildTarget {
  glob_source: string;
  output: string;
  release_only?: boolean;
}

interface TargetConfig {
  name: string;
  version: string;
  build: string;
  script: string;
  requires: string[];
  output_to_root?: boolean;
  targets: BuildTarget[];
}

// Constants
const ROOT_DIR = resolve(import.meta.dir, '..');
const DEPLOY_DIR = import.meta.dir;
const OUTPUT_DIR = join(DEPLOY_DIR, 'output');
const TARGETS_DIR = join(DEPLOY_DIR, 'targets');

// Utilities
const log = {
  title: (text: string) => {
    console.log('\n' + chalk.magenta.bold('═'.repeat(60)));
    console.log(chalk.magenta.bold(`  ${text}`));
    console.log(chalk.magenta.bold('═'.repeat(60)) + '\n');
  },
  section: (text: string) => console.log('\n' + chalk.cyan.bold(`▶ ${text}`)),
  success: (text: string) => console.log(chalk.green(`  ✓ ${text}`)),
  error: (text: string) => console.log(chalk.red(`  ✗ ${text}`)),
  info: (text: string) => console.log(chalk.blue(`  ℹ ${text}`)),
  warn: (text: string) => console.log(chalk.yellow(`  ⚠ ${text}`)),
};

// Clean output directory
async function cleanOutput() {
  const spinner = ora('Cleaning previous builds...').start();
  try {
    if (existsSync(OUTPUT_DIR)) {
      rmSync(OUTPUT_DIR, { recursive: true, force: true });
    }
    mkdirSync(OUTPUT_DIR, { recursive: true });
    spinner.succeed('Output directory cleaned');
  } catch (error) {
    spinner.warn('Could not clean output directory (may be in use)');
  }
}

// Load target config
async function loadTargetConfig(targetName: string): Promise<TargetConfig | null> {
  const configFile = join(TARGETS_DIR, targetName, 'build.json');
  if (!existsSync(configFile)) {
    log.error(`No build.json found for target: ${targetName}`);
    return null;
  }
  try {
    const file = Bun.file(configFile);
    const content = await file.text();
    return JSON.parse(content);
  } catch (error) {
    log.error(`Invalid JSON in ${configFile}: ${error}`);
    return null;
  }
}

// Run target build script
async function runTargetScript(targetName: string, config: TargetConfig, options: BuildOptions): Promise<boolean> {
  const scriptPath = join(TARGETS_DIR, targetName, config.script);
  
  if (!existsSync(scriptPath)) {
    log.warn(`No build script found for ${targetName}, skipping...`);
    return true;
  }

  // Dynamically import and execute the build function
  const module = await import(scriptPath);
  const buildFn = module[`build${targetName.charAt(0).toUpperCase() + targetName.slice(1)}`];
  
  if (!buildFn) {
    log.error(`No build function found in ${config.script}`);
    return false;
  }

  return await buildFn({
    release: options.release,
    clean: options.clean,
    verbose: options.verbose,
    rootDir: ROOT_DIR,
    outputDir: OUTPUT_DIR
  });
}

// Copy target files based on build.json
async function copyTargetFiles(targetName: string, config: TargetConfig, options: BuildOptions) {
  const outputBase = config.output_to_root ? OUTPUT_DIR : join(OUTPUT_DIR, targetName);
  mkdirSync(outputBase, { recursive: true });

  const spinner = ora(`Packaging ${targetName} files...`).start();
  let copiedCount = 0;

  for (const target of config.targets) {
    // Skip non-release files if not in release mode
    if (target.release_only && !options.release) {
      continue;
    }

    // Resolve glob source
    let searchPath = target.glob_source;
    if (searchPath.startsWith('../')) {
      searchPath = join(ROOT_DIR, searchPath.substring(3));
    } else {
      searchPath = join(DEPLOY_DIR, searchPath);
    }

    // Find matching files
    const files = await glob(searchPath, { nodir: true, windowsPathsNoEscape: true });
    
    for (const file of files) {
      let outputPath = target.output;
      
      // Handle root output paths
      if (outputPath.startsWith('/')) {
        outputPath = join(OUTPUT_DIR, outputPath.substring(1));
      } else {
        outputPath = join(outputBase, outputPath);
      }
      
      // Create directory and copy
      const destDir = dirname(outputPath);
      if (destDir) {
        mkdirSync(destDir, { recursive: true });
      }
      
      // Handle glob patterns
      if (target.glob_source.includes('**')) {
        const basePath = target.glob_source.split('**')[0];
        const resolvedBase = basePath.startsWith('../') 
          ? join(ROOT_DIR, basePath.substring(3))
          : join(DEPLOY_DIR, basePath);
        const relativePath = file.substring(resolvedBase.length);
        const finalPath = join(outputPath, relativePath);
        mkdirSync(dirname(finalPath), { recursive: true });
        await Bun.write(finalPath, Bun.file(file));
      } else {
        await Bun.write(outputPath, Bun.file(file));
      }
      copiedCount++;
    }
  }

  spinner.succeed(`Packaged ${copiedCount} files for ${targetName}`);
}

// Create build.json for target
function createBuildInfo(targetName: string, config: TargetConfig) {
  if (config.output_to_root) {
    return; // Don't create build.json for root outputs
  }

  const outputBase = join(OUTPUT_DIR, targetName);
  const buildInfo = {
    name: config.name,
    version: config.version,
    build: config.build || new Date().toISOString().replace(/[:.]/g, '-').replace('T', '_').split('.')[0]
  };
  
  writeFileSync(join(outputBase, 'build.json'), JSON.stringify(buildInfo, null, 2));
}

// Build a single target
async function buildTarget(targetName: string, options: BuildOptions): Promise<boolean> {
  log.section(`Building ${targetName.charAt(0).toUpperCase() + targetName.slice(1)}`);
  
  const config = await loadTargetConfig(targetName);
  if (!config) return false;

  // Run build script
  const scriptSuccess = await runTargetScript(targetName, config, options);
  if (!scriptSuccess) {
    log.error(`Build script failed for ${targetName}`);
    return false;
  }

  // Copy files
  await copyTargetFiles(targetName, config, options);
  
  // Create build.json
  createBuildInfo(targetName, config);
  
  log.success(`${targetName} build completed`);
  return true;
}

// Build with dependency resolution
async function buildWithDependencies(targetName: string, options: BuildOptions, built: Set<string> = new Set()): Promise<boolean> {
  // Skip if already built
  if (built.has(targetName)) {
    return true;
  }

  const config = await loadTargetConfig(targetName);
  if (!config) return false;

  // Build dependencies first
  for (const dep of config.requires) {
    if (!built.has(dep)) {
      const success = await buildWithDependencies(dep, options, built);
      if (!success) {
        log.error(`Dependency ${dep} failed for ${targetName}`);
        return false;
      }
    }
  }

  // Build this target
  const success = await buildTarget(targetName, options);
  if (success) {
    built.add(targetName);
  }
  
  return success;
}

// Main
async function main() {
  program
    .name('build')
    .description('Oracle Build System')
    .option('-t, --target <type>', 'Build target: server, frontend, launcher, package, or all', 'all')
    .option('-r, --release', 'Create release build with executables', false)
    .option('-c, --clean', 'Clean output directory before building', false)
    .option('-v, --verbose', 'Show detailed command output', false)
    .parse();

  const options = program.opts<BuildOptions>();

  log.title('Oracle Build System');
  log.info(`Target: ${options.target}`);
  log.info(`Release: ${options.release ? 'Yes' : 'No'}`);
  log.info(`Clean: ${options.clean ? 'Yes' : 'No'}`);
  log.info(`Verbose: ${options.verbose ? 'Yes' : 'No'}`);

  try {
    // Clean if requested
    if (options.clean) {
      await cleanOutput();
    }

    // Ensure output directory exists
    mkdirSync(OUTPUT_DIR, { recursive: true });

    // Build based on target
    if (options.target === 'all') {
      // Build all except package
      const targets = ['frontend', 'server', 'launcher'];
      for (const target of targets) {
        const success = await buildTarget(target, options);
        if (!success) throw new Error(`${target} build failed`);
      }
    } else {
      // Build specific target with dependencies
      const success = await buildWithDependencies(options.target, options);
      if (!success) throw new Error(`${options.target} build failed`);
    }

    log.title('Build Completed Successfully! 🎉');
    process.exit(0);
  } catch (error) {
    log.error(`Build failed: ${error}`);
    process.exit(1);
  }
}

main();
