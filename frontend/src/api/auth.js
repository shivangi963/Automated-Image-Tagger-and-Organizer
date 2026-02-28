import api from "./axiosClient";

// LOGIN
export const loginUser = (data) => api.post("/auth/login", data);

// REGISTER
export const registerUser = (data) => api.post("/auth/register", data);

// GET CURRENT USER
export const getCurrentUser = () => api.get("/auth/me");

// LOGOUT
export const logout = () => {
  localStorage.removeItem("jwt");
  window.location.href = "/login";
};