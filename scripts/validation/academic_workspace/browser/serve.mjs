import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const root = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../../../",
);
const frontend = path.join(root, "frontend");
const require = createRequire(path.join(frontend, "package.json"));
const { createServer } = await import(
  pathToFileURL(require.resolve("vite")).href
);
const server = await createServer({
  root: frontend,
  server: {
    host: "127.0.0.1",
    port: 5180,
    strictPort: true,
    hmr: false,
    proxy: { "/api": { target: "http://127.0.0.1:18000", changeOrigin: true } },
  },
});
await server.listen();
console.log("Academic browser test frontend: http://127.0.0.1:5180");
