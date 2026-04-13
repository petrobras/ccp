const { app, BrowserWindow } = require("electron");
const { spawn } = require("child_process");
const path = require("path");

let mainWindow;
let streamlitProcess;

function getResourcePath() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "ccp_streamlit");
  }
  return path.join(__dirname, "..", "pyinstaller_build", "ccp_streamlit");
}

function startStreamlit() {
  const exePath = path.join(getResourcePath(), "ccp_streamlit.exe");

  streamlitProcess = spawn(exePath, [], {
    cwd: getResourcePath(),
    env: { ...process.env, CCP_STANDALONE: "1" },
  });

  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      reject(new Error("Streamlit server did not start within 60 seconds"));
    }, 60000);

    streamlitProcess.stdout.on("data", (data) => {
      const output = data.toString().trim();
      console.log("Streamlit:", output);

      // Look for the JSON port output
      try {
        const parsed = JSON.parse(output);
        if (parsed.port) {
          clearTimeout(timeout);
          resolve(parsed.port);
        }
      } catch {
        // Not JSON, continue waiting
      }
    });

    streamlitProcess.stderr.on("data", (data) => {
      console.error("Streamlit stderr:", data.toString());
    });

    streamlitProcess.on("error", (err) => {
      clearTimeout(timeout);
      reject(err);
    });

    streamlitProcess.on("close", (code) => {
      if (code !== 0) {
        clearTimeout(timeout);
        reject(new Error(`Streamlit exited with code ${code}`));
      }
    });
  });
}

function createWindow(port) {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    icon: path.join(__dirname, "icon.ico"),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
    autoHideMenuBar: true,
  });

  mainWindow.loadURL(`http://localhost:${port}`);

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.on("ready", async () => {
  try {
    const port = await startStreamlit();
    createWindow(port);
  } catch (err) {
    console.error("Failed to start:", err);
    app.quit();
  }
});

app.on("window-all-closed", () => {
  if (streamlitProcess) {
    streamlitProcess.kill();
  }
  app.quit();
});

app.on("before-quit", () => {
  if (streamlitProcess) {
    streamlitProcess.kill();
  }
});
