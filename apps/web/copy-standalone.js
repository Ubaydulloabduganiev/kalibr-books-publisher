const fs = require("fs");
const path = require("path");
const root = __dirname;
const ST = path.join(root, ".next", "standalone", "apps", "web");
function copyDir(src, dest) {
  if (!fs.existsSync(src)) return;
  fs.mkdirSync(dest, { recursive: true });
  for (const e of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, e.name), d = path.join(dest, e.name);
    if (e.isDirectory()) copyDir(s, d); else fs.copyFileSync(s, d);
  }
}
copyDir(path.join(root, ".next", "static"), path.join(ST, ".next", "static"));
copyDir(path.join(root, "public"), path.join(ST, "public"));
console.log("standalone assets copied");
