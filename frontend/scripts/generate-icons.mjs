// Generates PWA / favicon PNGs from the GroupWise mark. Run: node scripts/generate-icons.mjs
import { writeFileSync } from "node:fs";
import sharp from "sharp";

const mark = (pad = 0) => `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="${-pad} ${-pad} ${40 + pad * 2} ${40 + pad * 2}">
  <rect x="${-pad}" y="${-pad}" width="${40 + pad * 2}" height="${40 + pad * 2}" fill="#FFD429" ${pad ? "" : 'rx="11"'}/>
  <path d="M12.5 26.5 20 14l7.5 12.5Z" fill="none" stroke="#003B7A" stroke-width="2.4" stroke-linejoin="round"/>
  <circle cx="20" cy="14" r="4.2" fill="#0057B8"/>
  <circle cx="12.5" cy="26.5" r="4.2" fill="#0057B8"/>
  <circle cx="27.5" cy="26.5" r="4.2" fill="#003B7A"/>
  <circle cx="31" cy="9" r="2" fill="#003B7A"/>
</svg>`;

writeFileSync("src/app/icon.svg", mark().trim());
const jobs = [
  ["public/icon-192.png", 192, mark()],
  ["public/icon-512.png", 512, mark()],
  ["public/icon-maskable-512.png", 512, mark(8)], // safe-zone padding for maskable icons
  ["src/app/apple-icon.png", 180, mark(4)],
];
for (const [file, size, svg] of jobs) {
  await sharp(Buffer.from(svg)).resize(size, size).png().toFile(file);
  console.log("wrote", file);
}
