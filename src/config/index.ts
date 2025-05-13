import path from "path";

require("dotenv").config();

const projectRoot = path.resolve(__dirname, "..", "..");

const baseConfig = {
  downloadDomain: process.env.DOWNLOAD_DOMAIN || "localhost",
  env: process.env.NODE_ENV || "dev",
  port: process.env.PORT || 3000,
  uploadDir: process.env.UPLOAD_DIR || path.join(projectRoot, "storage"),
  maxFileSizeMB: process.env.MAX_FILE_SIZE_MB || "10",
  linkExpiryMinutes: process.env.LINK_EXPIRY_MINUTES || "60",
  cleanupIntervalSeconds: process.env.CLEANUP_INTERVAL_SECONDS || "3600",
  allowedMimeTypes: /png|jpeg|jpg|gif|webp|tiff/,
  logLevel: process.env.LOG_LEVEL || "info",

  get cleanupIntervalMs(): number {
    return parseInt(this.cleanupIntervalSeconds, 10) * 1000;
  },

  get maxFileSizeBytes(): number {
    return parseInt(this.maxFileSizeMB, 10) * 1024 * 1024;
  },

  get linkExpiryMs(): number {
    return parseInt(this.linkExpiryMinutes, 10) * 60 * 1000;
  },
};

let config = { ...baseConfig };

if (process.env.NODE_ENV === "test") {
  config = {
    ...baseConfig,
    env: "test",
    logLevel: "warn",
    uploadDir:
      process.env.TEST_UPLOAD_DIR ||
      path.join(projectRoot, "/test/test-storage"),
  };
}

export default config;
