import { DataSource } from "typeorm";
import { config } from "dotenv";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

import { User } from "../models/user.model.js";
import { Strategy } from "../models/stratergy.model.js";

config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const ssl =
  process.env.DB_SSL === "true"
    ? {
        ca: fs.readFileSync(
          path.join(__dirname, "../certs/DigiCertGlobalRootG2.crt.pem")
        ),
      }
    : undefined;

export const AppDataSource = new DataSource({
  type: "mysql",
  host: process.env.DB_HOST,
  port: Number(process.env.DB_PORT),
  username: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,

  synchronize: process.env.DB_SYNC === "true",

  ssl,

  entities: [User, Strategy],
  migrations: [],
  subscribers: [],

  extra: {
    connectTimeout: 30000,
  },
});