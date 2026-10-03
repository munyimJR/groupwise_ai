import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "GroupWise AI — Shared Financial Intelligence",
    short_name: "GroupWise",
    description: "Split expenses. Understand spending. Predict what's next. Decide better together.",
    start_url: "/groups",
    scope: "/",
    display: "standalone",
    orientation: "portrait-primary",
    background_color: "#F6F8FB",
    theme_color: "#FFD429",
    categories: ["finance", "productivity"],
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
    shortcuts: [
      { name: "My groups", url: "/groups", icons: [{ src: "/icon-192.png", sizes: "192x192" }] },
    ],
  };
}
