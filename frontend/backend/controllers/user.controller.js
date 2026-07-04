import { User } from "../models/user.model.js";
import { AppDataSource } from "../utils/db.js";
import bcrypt from "bcrypt";
import jwt from "jsonwebtoken"

export async function signup(req, res) {
  try {
    const userRepo = AppDataSource.getRepository(User);

    const {
      full_name,
      email,
      password,
      mobile,
      role,
      status,
      page_access,
    } = req.body;

    if (!email || !password) {
      return res.status(400).json({
        error: "email_and_password_required",
      });
    }

    // Check if user exists
    const exists = await userRepo.findOne({ where: { email } });
    if (exists) {
      return res.status(409).json({
        error: "user_already_exists",
      });
    }

    // Hash password
    const hashedPassword = await bcrypt.hash(password, 10);

    const user = userRepo.create({
      full_name: full_name ?? null,
      email,
      password: hashedPassword,
      mobile: mobile ?? null,
      role: role ?? "user",
      status: status ?? "active",
      page_access: page_access ?? ["Dashboard Home"], // default page
    });

    await userRepo.save(user);

    return res.status(201).json({
      message: "user_created_successfully",
    });
  } catch (error) {
    return res.status(500).json({
      error: "signup_failed",
      message: error.message,
    });
  }
}
export async function getUserById(req, res) {
  try {
    const userRepo = AppDataSource.getRepository(User);
    const { id } = req.params;

    const user = await userRepo.findOne({
      where: { user_id: id },
    });

    if (!user) {
      return res.status(404).json({
        error: "user_not_found",
      });
    }

    // Remove password before sending response
    const { password, ...safeUser } = user;

    return res.status(200).json(safeUser);

  } catch (error) {
    return res.status(500).json({
      error: "failed_to_get_user",
      message: error.message,
    });
  }
}

export async function login(req, res) {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({
        error: "email_and_password_required",
      });
    }

    const userRepo = AppDataSource.getRepository(User);
    const user = await userRepo.findOne({ where: { email } });

    if (!user) {
      return res.status(401).json({
        error: "invalid_credentials",
      });
    }

    // ✅ Check if user is inactive
    if (user.status === "inactive") {
      return res.status(403).json({
        error: "account_inactive",
        message: "Your account is inactive. Please contact admin.",
      });
    }

    // Check password
    const passwordMatch = await bcrypt.compare(password, user.password);
    if (!passwordMatch) {
      return res.status(401).json({
        error: "invalid_credentials",
      });
    }

    // Create JWT token
    const token = jwt.sign(
      {
        sub: user.user_id,
        full_name: user.full_name,
        role: user.role,
        page_access: user.page_access,
      },
      process.env.JWT_SECRET,
      { expiresIn: "1h" }
    );

    return res.status(200).json({
      token,
      user: {
        id: user.user_id,
        name: user.full_name,
        email: user.email,
        role: user.role,
        status: user.status,
        page_access: user.page_access,
      },
    });

  } catch (error) {
    return res.status(500).json({
      error: "login_failed",
      message: error.message,
    });
  }
}

export async function updateUser(req, res) {
  try {
    const userRepo = AppDataSource.getRepository(User);
    const { id } = req.params;

    const {
      full_name,
      email,
      password,
      mobile,
      role,
      status,
      page_access,
    } = req.body;

    const user = await userRepo.findOne({
      where: { user_id: id },
    });

    if (!user) {
      return res.status(404).json({
        error: "user_not_found",
      });
    }

    // Update fields only if provided
    if (full_name !== undefined) user.full_name = full_name;
    if (email !== undefined) user.email = email;
    if (mobile !== undefined) user.mobile = mobile;
    if (role !== undefined) user.role = role;
    if (status !== undefined) user.status = status;

    // Update page access array
    if (page_access !== undefined) {
      user.page_access = page_access; // expects array
    }

    // Hash password only if updated
    if (password) {
      user.password = await bcrypt.hash(password, 10);
    }

    await userRepo.save(user);

    return res.status(200).json({
      message: "user_updated_successfully",
      updated_user: {
        id: user.user_id,
        page_access: user.page_access,
      },
    });
  } catch (error) {
    return res.status(500).json({
      error: "update_failed",
      message: error.message,
    });
  }
}

export async function listUsers(req, res) {
  try {
    const userRepo = AppDataSource.getRepository(User);
    const { search } = req.query;

    let users;

    if (search) {
      users = await userRepo
        .createQueryBuilder("user")
        .where("user.full_name LIKE :search", {
          search: `%${search}%`,
        })
        .getMany();
    } else {
      users = await userRepo.find();
    }

    // Remove passwords before sending
    const safeUsers = users.map(({ password, ...u }) => u);

    return res.json({ users: safeUsers });
  } catch (err) {
    return res.status(500).json({ error: "failed_to_list_users" });
  }
}
  
export async function deleteUser(req, res) {
  try {
    const userRepo = AppDataSource.getRepository(User);
    const { id } = req.params;

    const user = await userRepo.findOne({ where: { user_id: id } });

    if (!user) {
      return res.status(404).json({ error: "user_not_found" });
    }

    await userRepo.remove(user);

    return res.status(200).json({
      message: "user_deleted_successfully",
    });
  } catch (error) {
    return res.status(500).json({
      error: "delete_failed",
      message: error.message,
    });
  }
}

