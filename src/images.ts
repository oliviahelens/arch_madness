import fs from "node:fs";
import path from "node:path";
import { ASSETS_DIR } from "./config.js";

export type LoadedImage = {
  name: string;
  mediaType: "image/png" | "image/jpeg" | "image/gif" | "image/webp";
  data: string; // base64
};

function inferMediaType(file: string): LoadedImage["mediaType"] {
  const ext = path.extname(file).toLowerCase();
  if (ext === ".jpg" || ext === ".jpeg") return "image/jpeg";
  if (ext === ".gif") return "image/gif";
  if (ext === ".webp") return "image/webp";
  return "image/png";
}

export function loadImage(filename: string): LoadedImage {
  const full = path.join(ASSETS_DIR, filename);
  if (!fs.existsSync(full)) {
    throw new Error(
      `Missing image asset: ${full}\n` +
        `Place the puzzle images in assets/ — see assets/README.md.`,
    );
  }
  return {
    name: filename,
    mediaType: inferMediaType(filename),
    data: fs.readFileSync(full).toString("base64"),
  };
}
