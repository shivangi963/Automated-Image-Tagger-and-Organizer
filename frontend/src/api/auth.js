// src/api/auth.js
import { api } from "../store/auth";

// LOGIN
export const loginUser = async (data) => {
  return api().post("/auth/login", data);
};

// REGISTER
export const registerUser = async (data) => {
  return api().post("/auth/register", data);
};

// GET CURRENT USER
export const getCurrentUser = async () => {
  return api().get("/auth/me");
};

// LOGOUT
export const logout = () => {
  localStorage.removeItem("jwt");
  window.location.href = "/login";
};
