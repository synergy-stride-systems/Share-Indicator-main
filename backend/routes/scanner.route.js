import { Router } from "express";
import { runScanner } from "../controllers/scanner.controller.js";

const router = Router();

router.get("/scan", runScanner);

export default router;

