import express from "express";
import cors from "cors";
import { AppDataSource } from "./utils/db.js";
import { config } from "dotenv";
import userRouter from "./routes/user.route.js";
import scannerRoutes from "./routes/scanner.route.js";
import strategyRoutes from "./routes/stratergy.routes.js";

import path from "path";

config();

if (!process.env.JWT_SECRET) {
  console.error("JWT_SECRET is required in environment variables.");
  process.exit(1);
}

async function start() {
  try {
    await AppDataSource.initialize();
    console.log("AppDataSource initialized (connected to DB).");
  } catch (err) {
    console.error("Failed to initialize AppDataSource:", err);
    process.exit(1);
  }

  const app = express();

  const allowedOrigins = [
    process.env.FRONTEND_URL,
    process.env.FRONTEND_URL_2,
    "http://localhost:3000",
  ].filter(Boolean);

  app.use(
    cors({
      origin: (origin, callback) => {
        const isAllowed =
          !origin ||
          allowedOrigins.includes(origin) ||
          origin.endsWith(".azurewebsites.net");

        if (isAllowed) {
          callback(null, true);
        } else {
          console.warn("Blocked CORS origin:", origin);
          callback(new Error("Not allowed by CORS"));
        }
      },
      credentials: true,
      optionsSuccessStatus: 200,
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
