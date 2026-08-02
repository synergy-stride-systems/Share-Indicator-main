import express from "express";
import cors from "cors";
import path from "path";
import { config } from "dotenv";

import { AppDataSource } from "./utils/db.js";

import userRouter from "./routes/user.route.js";
import scannerRoutes from "./routes/scanner.route.js";
import strategyRoutes from "./routes/stratergy.routes.js";

config();

if (!process.env.JWT_SECRET) {
  console.error("JWT_SECRET is required in environment variables.");
  process.exit(1);
}

async function start() {
  try {
    await AppDataSource.initialize();
    console.log("✅ Database connected successfully.");
  } catch (err) {
    console.error("Failed to initialize AppDataSource:", err);
    process.exit(1);
  }

  const app = express();

  const allowedOrigins = [
    process.env.FRONTEND_URL,
    process.env.FRONTEND_URL_2,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
  ].filter(Boolean);

  app.use(
    cors({
      origin: (origin, callback) => {
        // Allow requests without origin (Postman, curl)
        if (!origin) {
          return callback(null, true);
        }

        console.log("Incoming Origin:", origin);

        // Localhost
        if (
          origin.startsWith("http://localhost") ||
          origin.startsWith("http://127.0.0.1")
        ) {
          return callback(null, true);
        }

        // Any Vercel deployment
        if (origin.endsWith(".vercel.app")) {
          return callback(null, true);
        }

        // Azure deployments (optional)
        if (origin.endsWith(".azurewebsites.net")) {
          return callback(null, true);
        }

        // Environment variable URLs
        if (allowedOrigins.includes(origin)) {
          return callback(null, true);
        }

        console.warn("Blocked CORS origin:", origin);

        return callback(new Error("Not allowed by CORS"));
      },

      credentials: true,

      methods: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],

      allowedHeaders: [
        "Content-Type",
        "Authorization",
        "Origin",
        "Accept",
      ],

      optionsSuccessStatus: 200,
    })
  );

  app.use(express.json({ limit: "2mb" }));

  app.use(
    "/uploads",
    express.static(path.resolve(process.env.UPLOADS_PATH || "uploads"))
  );

  app.get("/", (_, res) => {
    res.json({
      success: true,
      message: "Backend is running 🚀",
    });
  });

  app.use("/api/users", userRouter);
  app.use("/api/scanner", scannerRoutes);
  app.use("/api/strategy", strategyRoutes);

  const PORT = process.env.PORT || process.env.SERVER_PORT || 4000;

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`🚀 Server running on port ${PORT}`);
  });
}

start();