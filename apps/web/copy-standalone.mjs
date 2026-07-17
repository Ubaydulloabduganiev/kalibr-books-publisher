import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const standaloneRoot = path.join(root, ".next", "standalone", "apps", "web");

function copyDirectory(source, destination) {
  if (!fs.existsSync(source)) return;
  fs.mkdirSync(destination, { recursive: true });
  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    const sourcePath = path.join(source, entry.name);
    const destinationPath = path.join(destination, entry.name);
    if (entry.isDirectory()) {
      copyDirectory(sourcePath, destinationPath);
    } else {
      fs.copyFileSync(sourcePath, destinationPath);
    }
  }
}

copyDirectory(path.join(root, ".next", "static"), path.join(standaloneRoot, ".next", "static"));
copyDirectory(path.join(root, "public"), path.join(standaloneRoot, "public"));
console.log("Standalone assets copied");
