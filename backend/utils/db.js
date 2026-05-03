import { DataSource } from "typeorm";
import { config } from "dotenv";
import { User } from "../models/user.model.js";
import { Strategy } from "../models/stratergy.model.js";

config(); 

const sslOptions = process.env.DB_SSL === "true" ? { rejectUnauthorized: false } : undefined;

export const AppDataSource = new DataSource({
  type: "mysql",
  host: process.env.DB_HOST,
  port: parseInt(process.env.DB_PORT, 10),
  username: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
  synchronize: process.env.DB_SYNC === "true",
  ssl: sslOptions,
  entities: [User, Strategy], 
  migrations: [],
  subscribers: [],
});
