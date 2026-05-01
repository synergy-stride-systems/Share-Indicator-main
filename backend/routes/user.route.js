import { Router } from "express";
import {
  signup,
  login,
  listUsers,
  updateUser,
  deleteUser,
  getUserById
} from "../controllers/user.controller.js";

import authenticateToken from "../middlewares/auth.middleware.js";

const userRouter = Router();


userRouter.post("/signup", signup);
userRouter.post("/login", login);



userRouter.get("/", authenticateToken, listUsers);
userRouter.get("/:id", authenticateToken, getUserById);

userRouter.put("/update/:id", authenticateToken, updateUser);

userRouter.delete("/delete/:id", authenticateToken, deleteUser);

export default userRouter;