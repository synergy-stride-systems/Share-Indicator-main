import multer from "multer";
import path from "path";
import fs from "fs";
import 'dotenv/config'; // Modern way to load .env

// 1. Read upload path from env (default: uploads)
const uploadsPath = process.env.UPLOADS_PATH || "uploads";

// 2. Configure storage
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const resolvedPath = path.resolve(uploadsPath);
    // Ensure directory exists
    if (!fs.existsSync(resolvedPath)) {
      fs.mkdirSync(resolvedPath, { recursive: true });
    }
    cb(null, resolvedPath);
  },
  filename: (req, file, cb) => {
    // Generate unique filename
    const uniqueSuffix = Date.now() + "-" + Math.round(Math.random() * 1e9);
    cb(
      null,
      file.fieldname + "-" + uniqueSuffix + path.extname(file.originalname)
    );
  },
});

// 3. File filter: restrict to PDF/Images
const fileFilter = (req, file, cb) => {
  const allowedTypes = ["image/jpeg", "image/png", "application/pdf"];
  if (allowedTypes.includes(file.mimetype)) {
    cb(null, true);
  } else {
    cb(new Error("Only JPEG, PNG, or PDF files are allowed!"), false);
  }
};

// 4. Initialize Multer instance
const upload = multer({
  storage: storage,
  fileFilter: fileFilter,
  limits: { fileSize: 5 * 1024 * 1024 }, // 5MB limit
});

export default upload;