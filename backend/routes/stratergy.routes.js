import express from "express";
import { saveStrategy, getStrategy } from "../controllers/stratergy.controller.js";

const router = express.Router();

// ✅ Save strategy (create/update)
router.post("/save", saveStrategy);

// ✅ Get strategy for user
router.get("/get/:userId", getStrategy);

export default router;