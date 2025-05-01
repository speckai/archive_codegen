#!/usr/bin/env node
// TODO: optimize speed for this

import * as crypto from "crypto";
import ignore from "ignore";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import * as ts from "typescript";

// Remove baseDir argument
const tsConfigPath = process.argv[2];
const targetFileArg = process.argv[3];

if (!tsConfigPath || !targetFileArg) {
  console.error(
    JSON.stringify({
      error: "Missing arguments",
      usage: "npx find-imports-next <tsconfig-path> <target-file>",
    }),
  );
  process.exit(1);
}

// Load tsconfig.json using TypeScript's built-in parser to handle comments
const configFile = ts.readConfigFile(tsConfigPath, ts.sys.readFile);
if (configFile.error) {
  console.error(
    JSON.stringify({
      error: "Failed to read tsconfig: " + configFile.error.messageText,
    }),
  );
  process.exit(1);
}
const tsConfig = configFile.config;

// Add interface for path mappings
interface PathMappings {
  [key: string]: string;
}

// Resolve paths (e.g., "@/components/*" → "components/*")
const pathMappings: PathMappings = {};
if (tsConfig.compilerOptions.paths) {
  for (const alias in tsConfig.compilerOptions.paths) {
    const targetPaths = tsConfig.compilerOptions.paths[alias];
    if (targetPaths.length > 0) {
      pathMappings[alias.replace("/*", "")] = targetPaths[0].replace("/*", "");
    }
  }
}

// Add this function to load gitignore patterns
function loadGitignore(baseDir: string) {
  const ig = ignore();
  const gitignorePath = path.join(baseDir, ".gitignore");

  if (fs.existsSync(gitignorePath)) {
    const gitignoreContent = fs.readFileSync(gitignorePath, "utf8");
    ig.add(gitignoreContent);
  }

  // Always ignore node_modules regardless of gitignore
  ig.add("node_modules");

  return ig;
}

// Add these functions at the top level
function getCachePath(tsConfigPath: string) {
  const hash = crypto.createHash("md5").update(tsConfigPath).digest("hex");
  return path.join(os.tmpdir(), `ts-program-cache-${hash}.json`);
}

function isIgnored(
  filePath: string,
  baseDir: string,
  ig: ReturnType<typeof ignore>,
) {
  // Convert absolute path to relative path from baseDir
  const relativePath = path.relative(baseDir, filePath);

  return (
    relativePath.startsWith("..") || // Outside project
    ig.ignores(relativePath) // Matches gitignore
  );
}

function findImporters(targetFile: string): {
  importers: string[];
  imports: string[];
} {
  try {
    // Try load cache first
    const cachePath = getCachePath(tsConfigPath);
    const baseDir = path.dirname(tsConfigPath);
    // Load gitignore patterns
    const ig = loadGitignore(baseDir);

    if (fs.existsSync(cachePath)) {
      const cache = JSON.parse(fs.readFileSync(cachePath, "utf-8"));
      const resolvedTarget = path.resolve(targetFile);

      // If we have a valid cache with importers/imports maps
      if (cache.importers && cache.imports) {
        // Filter cached results through gitignore
        return {
          importers: (cache.importers[resolvedTarget] || []).filter(
            (file: string) => {
              const gitignoreRelativePath = path.relative(baseDir, file);
              return (
                !gitignoreRelativePath.startsWith("..") &&
                !ig.ignores(gitignoreRelativePath)
              );
            },
          ),
          imports: (cache.imports[resolvedTarget] || []).filter(
            (file: string) => {
              const gitignoreRelativePath = path.relative(baseDir, file);
              return (
                !gitignoreRelativePath.startsWith("..") &&
                !ig.ignores(gitignoreRelativePath)
              );
            },
          ),
        };
      }
    }

    // If no cache, analyze entire project
    const configFile = ts.readConfigFile(tsConfigPath, ts.sys.readFile);
    const parsedConfig = ts.parseJsonConfigFileContent(
      configFile.config,
      ts.sys,
      baseDir,
    );

    const program = ts.createProgram({
      rootNames: parsedConfig.fileNames,
      options: parsedConfig.options,
    });

    // Build complete maps for all files
    const allImports: Record<string, string[]> = {};
    const allImporters: Record<string, string[]> = {};

    // Filter source files through gitignore first
    const sourceFiles = program.getSourceFiles().filter((file) => {
      if (file.isDeclarationFile) {
        return false;
      }
      const gitignoreRelativePath = path.relative(baseDir, file.fileName);
      return (
        !gitignoreRelativePath.startsWith("..") &&
        !ig.ignores(gitignoreRelativePath)
      );
    });

    sourceFiles.forEach((sourceFile) => {
      const currentFile = path.resolve(sourceFile.fileName);
      allImports[currentFile] = [];

      ts.forEachChild(sourceFile, (node) => {
        if (
          ts.isImportDeclaration(node) &&
          node.moduleSpecifier &&
          ts.isStringLiteral(node.moduleSpecifier)
        ) {
          try {
            const { resolvedModule } = ts.resolveModuleName(
              node.moduleSpecifier.text,
              sourceFile.fileName,
              parsedConfig.options,
              ts.sys,
            );

            if (resolvedModule?.resolvedFileName) {
              const resolvedPath = path.resolve(
                resolvedModule.resolvedFileName,
              );
              allImports[currentFile].push(resolvedPath);
              if (!allImporters[resolvedPath]) {
                allImporters[resolvedPath] = [];
              }
              allImporters[resolvedPath].push(currentFile);
            }
          } catch (err) {}
        }
      });
    });

    // Save entire project graph to cache
    fs.writeFileSync(
      cachePath,
      JSON.stringify({ importers: allImporters, imports: allImports }),
    );

    const resolvedTarget = path.resolve(targetFile);
    return {
      importers: allImporters[resolvedTarget] || [],
      imports: allImports[resolvedTarget] || [],
    };
  } catch (error: any) {
    console.error(JSON.stringify({ error: error.message }));
    process.exit(1);
  }
}

// Add this function
function debugCache(tsConfigPath: string) {
  const cachePath = getCachePath(tsConfigPath);
  console.log("Cache location:", cachePath);
  if (fs.existsSync(cachePath)) {
    console.log("Cache exists");
  } else {
    console.log("No cache file exists at this location");
  }
}

// Add this before the main logic
if (process.argv.includes("--debug-cache")) {
  debugCache(tsConfigPath);
  process.exit(0);
}

// Add this function to generate the full dependency graph
function generateProjectGraph() {
  const configFile = ts.readConfigFile(tsConfigPath, ts.sys.readFile);
  const baseDir = path.dirname(tsConfigPath);
  const parsedConfig = ts.parseJsonConfigFileContent(
    configFile.config,
    ts.sys,
    baseDir,
  );
  const ig = loadGitignore(baseDir);

  const program = ts.createProgram({
    rootNames: parsedConfig.fileNames,
    options: parsedConfig.options,
  });

  // Build complete maps for all files
  const allImports: Record<string, string[]> = {};
  const allImporters: Record<string, string[]> = {};

  // Filter source files more strictly
  const sourceFiles = program.getSourceFiles().filter((file) => {
    if (file.isDeclarationFile) {
      return false;
    }
    return !isIgnored(file.fileName, baseDir, ig);
  });

  sourceFiles.forEach((sourceFile) => {
    const currentFile = path.resolve(sourceFile.fileName);
    allImports[currentFile] = [];

    ts.forEachChild(sourceFile, (node) => {
      if (
        ts.isImportDeclaration(node) &&
        node.moduleSpecifier &&
        ts.isStringLiteral(node.moduleSpecifier)
      ) {
        try {
          const { resolvedModule } = ts.resolveModuleName(
            node.moduleSpecifier.text,
            sourceFile.fileName,
            parsedConfig.options,
            ts.sys,
          );

          if (resolvedModule?.resolvedFileName) {
            const resolvedPath = path.resolve(resolvedModule.resolvedFileName);
            // Only add if not ignored
            if (!isIgnored(resolvedPath, baseDir, ig)) {
              allImports[currentFile].push(resolvedPath);
              if (!allImporters[resolvedPath]) {
                allImporters[resolvedPath] = [];
              }
              allImporters[resolvedPath].push(currentFile);
            }
          }
        } catch (err) {}
      }
    });
  });

  return { importers: allImporters, imports: allImports };
}

// Update the --dump-cache handler
if (process.argv.includes("--dump-cache")) {
  const cachePath = getCachePath(tsConfigPath);
  if (fs.existsSync(cachePath)) {
    console.log(fs.readFileSync(cachePath, "utf-8"));
  } else {
    // Generate and output fresh cache
    const graph = generateProjectGraph();
    console.log(JSON.stringify(graph));
  }
  process.exit(0);
}

try {
  const { importers, imports } = findImporters(targetFileArg);

  // Output clean JSON result
  console.log(
    JSON.stringify({
      importers: importers.map((p) => path.relative(process.cwd(), p)),
      imports: imports.map((p) => path.relative(process.cwd(), p)),
    }),
  );
} catch (error: any) {
  console.error(JSON.stringify({ error: error.message }));
  process.exit(1);
}
