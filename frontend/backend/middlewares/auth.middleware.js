import jwt from "jsonwebtoken";

const authenticateToken = (req, res, next) => {
  const authHeader = req.headers["authorization"];
  const token = authHeader?.split(" ")[1];

  if (!token) {
    return res.status(401).json({
      error: "access_token_required",
    });
  }

  jwt.verify(token, process.env.JWT_SECRET, (err, decoded) => {
    if (err) {
      return res.status(403).json({
        error: "invalid_token",
      });
    }

    req.user = {
      id: decoded.sub,
      full_name: decoded.full_name,
      role: decoded.role,
      page_access: decoded.page_access || [], // added
    };

    next();
  });
};

export default authenticateToken;