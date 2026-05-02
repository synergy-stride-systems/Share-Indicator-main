import express from "express";
import cors from "cors";
import { AppDataSource } from "./utils/db.js";
import { config } from "dotenv";
import userRouter from "./routes/user.route.js";
import scannerRoutes from "./routes/scanner.route.js";
import strategyRoutes from "./routes/stratergy.routes.js";

import path from "path";

config();

async function start() {
  try {
    await AppDataSource.initialize();
    console.log("AppDataSource initialized (connected to DB).");
  } catch (err) {
    console.error("Failed to initialize AppDataSource:", err);
    process.exit(1);
  }

  const app = express();

  const frontendOrigin = process.env.FRONTEND_URL || "http://localhost:3000";

  app.use(
    cors({
      origin: frontendOrigin,
      credentials: true,
    })
  );

  app.use(express.json({ limit: "2mb" }));

  // Single, correct static binding
  app.use(
    "/uploads",
    express.static(path.resolve(process.env.UPLOADS_PATH || "uploads"))
  );

  app.use("/api/users", userRouter);
  app.use("/api/scanner", scannerRoutes);
  app.use("/api/strategy", strategyRoutes);
  const PORT = process.env.PORT || process.env.SERVER_PORT || 4000;
  app.listen(PORT, () => {
    console.log(`Server is listening on port: ${PORT}`);
  });
}

start();
