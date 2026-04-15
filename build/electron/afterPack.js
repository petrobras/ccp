const { execFileSync } = require("child_process");
const path = require("path");

exports.default = async function (context) {
  const exePath = path.join(context.appOutDir, "CCP App.exe");
  const icoPath = path.join(__dirname, "icon.ico");
  const rceditPath = path.join(
    __dirname,
    "node_modules",
    "rcedit",
    "bin",
    "rcedit-x64.exe"
  );

  console.log(`  • setting icon on ${exePath}`);
  execFileSync(rceditPath, [exePath, "--set-icon", icoPath]);
};
