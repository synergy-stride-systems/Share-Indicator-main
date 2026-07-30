import express from "express";
import { saveStrategy, getStrategy } from "../controllers/stratergy.controller.js";
import { parseConditionsFromText } from "../controllers/nlp.controller.js";
import authenticateToken from "../middlewares/auth.middleware.js";

const router = express.Router();

// ✅ Save strategy (create/update)
router.post("/save", saveStrategy);

// ✅ Get strategy for user
router.get("/get/:userId", getStrategy);

// ✅ Convert natural language into conditions (calls Groq API — auth required
// since each call costs money and we don't want it open to the public internet)
router.post("/parse-nl", authenticateToken, parseConditionsFromText);

export default router;