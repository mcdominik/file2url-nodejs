import http from "http";
import { Express } from "express";
import app from "../../src/app";
import { fileService } from "../../src/services/file.service";
import { logger } from "../../src/utils/logger";
import config from "../../src/config/index";

export interface TestApplication {
  app: Express;
  server: http.Server;
  close: () => void;
}

export function createTestApp(): TestApplication {
  const server = app.listen(config.port, () => {});

  const close = (): void => {
    logger.debug("Closing test server...");
    fileService.stopPeriodicCleanup();
    server.close();
  };

  return {
    app,
    server,
    close,
  };
}
