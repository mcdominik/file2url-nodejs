import config from "@config/index";
import app from "./app";
import { logger } from "@utils/logger";
import { fileService } from "@services/file.service";
import fs from "fs/promises";

const server = app.listen(config.port, async () => {
  logger.info(`Environment: ${config.env}`);
  logger.info(`Server running on port: ${config.port}`);
  logger.info(`Storage (uploads) directory: ${config.uploadDir}`);
  logger.info(`Maximum file size: ${config.maxFileSizeMB} MB`);
  logger.info(`Link expiry time: ${config.linkExpiryMinutes}min`);
  logger.info(`Allowed mime types: ${config.allowedMimeTypes}`);
  logger.info(`Cleanup interval: ${config.cleanupIntervalSeconds}s`);
  await fs.mkdir(config.uploadDir, { recursive: true });
  logger.info(`Initialized storage`);
});

// graceful shutdown handling
const signals: NodeJS.Signals[] = ["SIGINT", "SIGTERM"];

signals.forEach((signal) => {
  process.on(signal, async () => {
    logger.warn(`Received ${signal}. Shutting down gracefully...`);

    await fs.rm(config.uploadDir, { recursive: true, force: true });
    fileService.stopPeriodicCleanup(); // stop background tasks

    server.close((err) => {
      if (err) {
        logger.error("Error during server shutdown:", err);
        process.exit(1); // exit with error code
      } else {
        logger.info("Server closed successfully.");
        process.exit(0); // exit cleanly
      }
    });

    // force shutdown if server doesn't close within a timeout (10s)
    setTimeout(() => {
      logger.error("Could not close connections in time, forcing shutdown.");
      process.exit(1);
    }, 10000);
  });
});

process.on("unhandledRejection", (reason: any, promise) => {
  logger.error("Unhandled Rejection at:", promise, "reason:", reason);
  process.exit(1);
});

process.on("uncaughtException", (error: Error) => {
  logger.error("Uncaught Exception:", error);
  process.exit(1);
});
