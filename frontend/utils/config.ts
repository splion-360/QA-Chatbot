const ENV = process.env.NODE_ENV || "development";
const ALLOWED_ORIGINS = process.env.ALLOWED_ORIGINS || "";
const DEV_PORT = process.env.DEV_PORT || "3000";

let baseUrl = "";

if (ENV === "production") {
  if (!ALLOWED_ORIGINS) {
    throw new Error("ALLOWED_ORIGINS must be set in the production environment.");
  }
  baseUrl = ALLOWED_ORIGINS;
} else {
  baseUrl = `http://localhost:${DEV_PORT}`;
}

export const config = {
  baseUrl
};