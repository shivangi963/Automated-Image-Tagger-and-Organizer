import axios from "axios";

const API_BASE = "http://localhost:8000";

const api = axios.create({
    baseURL: API_BASE,
    withCredentials: false,
});

// Add Authorization header from localStorage
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem("jwt");
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Token expired or invalid
            localStorage.removeItem("jwt");
            window.location.href = "/login";
        }
        
        if (error.response) {
            console.error("API Error:", error.response.data);
        } else {
            console.error("Network Error:", error.message);
        }
        return Promise.reject(error);
    }
);

export const getPresignedUrl = async (file) => {
    return api.post("/images/presign", {
        filename: file.name,
        mime: file.type  // Changed from content_type to mime
    });
};

export const ingestImage = async ({ filename, mime_type, storage_key }) => {
    return api.post(`/images/ingest`, {
        filename,
        mime_type,
        storage_key
    });
};

export const listImages = async () => {
    return api.get("/images/");
};

export const getImage = async (imageId) => {
    return api.get(`/images/${imageId}`);
};

export const uploadImageToMinIO = async (presignedUrl, file) => {
    return axios.put(presignedUrl, file, {
        headers: {
            "Content-Type": file.type
        }
    });
};

export default api;

