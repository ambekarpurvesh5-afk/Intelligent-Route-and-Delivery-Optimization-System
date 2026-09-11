// Configuration for API endpoints
const CONFIG = {
  // Relative path allows frontend to work both when served by Flask directly
  // and when configured via reverse proxy or cloud deployment
  API_BASE_URL: window.location.origin.includes("5000") || window.location.origin.includes("localhost")
    ? "" 
    : ""
};
