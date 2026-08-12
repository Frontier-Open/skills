#!/usr/bin/env node
import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, join, relative, resolve, sep } from "node:path";

const args = process.argv.slice(2);
const valueOf = (flag) => {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
};
const root = resolve(valueOf("--root") || ".");
const port = Number(valueOf("--port") || 4174);
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error("--port must be an integer from 1 to 65535");

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml; charset=utf-8",
  ".webp": "image/webp",
  ".xml": "application/xml; charset=utf-8",
};

function candidatePath(url) {
  const pathname = decodeURIComponent(new URL(url, "http://127.0.0.1").pathname);
  const localPath = pathname.startsWith("/drafts/")
    ? join(root, pathname.slice(1))
    : join(root, "public", pathname.replace(/^\//u, ""));
  const resolved = resolve(localPath);
  const withinRoot = resolved === root || (!relative(root, resolved).startsWith(`..${sep}`) && relative(root, resolved) !== "..");
  if (!withinRoot) throw new Error("Unsafe preview path");
  return resolved;
}

const server = createServer(async (request, response) => {
  if (!request.url || !["GET", "HEAD"].includes(request.method || "")) {
    response.writeHead(405).end();
    return;
  }
  try {
    let path = candidatePath(request.url);
    const metadata = await stat(path).catch(() => null);
    if (metadata?.isDirectory()) path = join(path, "index.html");
    const file = await stat(path);
    if (!file.isFile()) throw new Error("Not a file");
    response.writeHead(200, {
      "Content-Type": contentTypes[extname(path).toLowerCase()] || "application/octet-stream",
      "Content-Length": file.size,
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    });
    if (request.method === "HEAD") response.end();
    else createReadStream(path).pipe(response);
  } catch {
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" });
    response.end("Not found");
  }
});

server.listen(port, "127.0.0.1", () => {
  console.log(`Frontier Signals preview ready at http://127.0.0.1:${port}`);
  console.log("Web paths resolve from public/; WeChat drafts use /drafts/...");
});
