import { existsSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { spawn } from 'bun';
import { createHash } from 'crypto';
import ora from 'ora';
import chalk from 'chalk';

const log = {
  success: (text: string) => console.log(chalk.green(`  ✓ ${text}`)),
  error: (text: string) => console.log(chalk.red(`  ✗ ${text}`)),
  info: (text: string) => console.log(chalk.blue(`  ℹ ${text}`)),
  section: (text: string) => console.log('\n' + chalk.cyan.bold(`▶ ${text}`)),
};

interface PackageOptions {
  release: boolean;
  rootDir: string;
  outputDir: string;
}

export async function buildPackage(options: PackageOptions): Promise<boolean> {
  const DEPLOY_DIR = join(options.rootDir, 'deploy');
  const TARGETS_DIR = join(DEPLOY_DIR, 'targets');
  
  log.section('Creating Release Package');
  
  // Read package build.json to get requires
  const packageConfig = JSON.parse(await Bun.file(join(TARGETS_DIR, 'package', 'build.json')).text());
  const requires = packageConfig.requires || [];
  
  // Read version from server.json
  const versionFile = join(DEPLOY_DIR, 'server.json');
  let version = '0.1';
  if (existsSync(versionFile)) {
    const versionData = JSON.parse(await Bun.file(versionFile).text());
    version = versionData.version;
  }
  
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').replace('T', '_').split('.')[0];
  const releaseName = `Oracle-Release-v${version}-${timestamp}`;
  const packageDir = join(options.outputDir, 'package');
  const releaseDir = join(packageDir, releaseName);
  
  mkdirSync(releaseDir, { recursive: true });

  const spinner = ora('Packaging release files...').start();
  let fileCount = 0;
  
  // Process each required target
  for (const targetName of requires) {
    const targetConfigFile = join(TARGETS_DIR, targetName, 'build.json');
    if (!existsSync(targetConfigFile)) {
      log.error(`No build.json for ${targetName}`);
      continue;
    }
    
    const targetConfig = JSON.parse(await Bun.file(targetConfigFile).text());
    
    // If target outputs to root, copy files to release root
    if (targetConfig.output_to_root) {
      const targetOutputDir = options.outputDir;
      
      for (const target of targetConfig.targets || []) {
        // Handle paths starting with /
        const outputPath = target.output.startsWith('/') 
          ? target.output.substring(1) 
          : target.output;
        
        const src = join(targetOutputDir, outputPath);
        if (existsSync(src)) {
          await Bun.write(join(releaseDir, outputPath), Bun.file(src));
          fileCount++;
        }
      }
    } else {
      // Copy entire target directory
      const src = join(options.outputDir, targetName);
      if (existsSync(src)) {
        const dest = join(releaseDir, targetName);
        
        // For frontend, exclude browser directory
        if (targetName === 'frontend') {
          const proc = spawn(
            ['powershell', '-Command', `Copy-Item -Path "${src}" -Destination "${dest}" -Recurse -Force -Exclude "browser"`],
            { cwd: options.rootDir }
          );
          await proc.exited;
          
          // Remove browser directory if it was copied
          const browserDir = join(dest, 'browser');
          if (existsSync(browserDir)) {
            const removeProc = spawn(
              ['powershell', '-Command', `Remove-Item -Path "${browserDir}" -Recurse -Force`],
              { cwd: options.rootDir }
            );
            await removeProc.exited;
          }
        } else {
          const proc = spawn(
            ['powershell', '-Command', `Copy-Item -Path "${src}" -Destination "${dest}" -Recurse -Force`],
            { cwd: options.rootDir }
          );
          await proc.exited;
        }
        
        fileCount++;
      }
    }
  }
  
  spinner.succeed(`Packaged ${fileCount} targets`);
  
  // Create ZIP archive
  const zipSpinner = ora('Creating ZIP archive...').start();
  const zipName = `${releaseName}.zip`;
  const zipPath = join(packageDir, zipName);
  const proc = spawn(
    ['powershell', '-Command', `Compress-Archive -Path "${releaseDir}\\*" -DestinationPath "${zipPath}" -Force`],
    { cwd: packageDir }
  );
  await proc.exited;
  
  zipSpinner.succeed(`ZIP archive created: ${zipName}`);
  
  // Generate SHA-256 hash for integrity verification
  const hashSpinner = ora('Generating SHA-256 hash...').start();
  try {
    const zipFile = Bun.file(zipPath);
    const zipBuffer = await zipFile.arrayBuffer();
    const hash = createHash('sha256');
    hash.update(new Uint8Array(zipBuffer));
    const sha256 = hash.digest('hex');
    
    // Write hash to file
    const hashFileName = `${releaseName}.zip.sha256`;
    const hashFilePath = join(packageDir, hashFileName);
    const hashContent = `${sha256}  ${zipName}\n`;
    await Bun.write(hashFilePath, hashContent);
    
    hashSpinner.succeed(`SHA-256 hash: ${sha256.substring(0, 16)}...`);
    log.info(`Hash file: ${hashFileName}`);
  } catch (error) {
    hashSpinner.fail('Failed to generate hash');
    log.error(`Hash error: ${error}`);
  }
  
  log.success(`Release package: package/${releaseName}.zip`);
  
  return true;
}
