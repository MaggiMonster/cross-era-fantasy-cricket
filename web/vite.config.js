import { createReadStream, existsSync, statSync } from "node:fs";
import { homedir } from "node:os";
import { extname, resolve, sep } from "node:path";
import { defineConfig } from "vite";

// Photos, heads and clips stay outside git in ~/cricket-project/assets. The dev server
// serves only model and texture files from there, at /player-assets/, on this Mac only.
const ASSETS = resolve(homedir(), "cricket-project", "assets");
const TYPES = { ".glb": "model/gltf-binary", ".gltf": "model/gltf+json", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".ktx2": "image/ktx2" };

function playerAssets() {
  return {
    name: "player-assets",
    configureServer(server) {
      server.middlewares.use("/player-assets", (req, res, next) => {
        let relative;
        try {
          relative = decodeURIComponent(new URL(req.url, "http://localhost").pathname).slice(1);
        } catch {
          res.statusCode = 400;
          res.end();
          return;
        }
        const file = resolve(ASSETS, relative);
        const type = TYPES[extname(file).toLowerCase()];
        if (!file.startsWith(ASSETS + sep) || !type || !existsSync(file) || !statSync(file).isFile()) return next();
        res.setHeader("Content-Type", type);
        createReadStream(file).pipe(res);
      });
    },
  };
}

export default defineConfig({
  base: "./",
  plugins: [playerAssets()],
  server: { host: "127.0.0.1", port: 5173 },
  preview: { host: "127.0.0.1", port: 4173 },
});
