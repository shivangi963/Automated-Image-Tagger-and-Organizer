import axios from "axios";

const API_BASE = "http://localhost:8000";

const api = axios.create({
    baseURL: API_BASE,
    withCredentials: false,
});

// ✅ Request interceptor: add token to EVERY request
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem("jwt");
        console.log("Request token:", token ? "✓ Present" : "✗ Missing");
        
        if (token) {
            config.headers = config.headers || {};
            config.headers.Authorization = `Bearer ${token}`;
        } else {
            console.warn("No JWT token found in localStorage!");
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// ✅ Response interceptor: handle 401
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            console.error("401 Unauthorized - token invalid or expired");
            localStorage.removeItem("jwt");
            window.location.href = "/login";
        }
        return Promise.reject(error);
    }
);

export default api;
