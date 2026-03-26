import { GoogleLogin } from "@react-oauth/google";

const GoogleSignIn = ({ onLoginSuccess }) => {
  const handleSuccess = (data) => {
    localStorage.setItem("token", data.token);
    localStorage.setItem("role", data.role);
    localStorage.setItem("name", data.name);
    localStorage.setItem("email", data.email);
    onLoginSuccess(data);
  };
  return (
    <div style={{ marginTop: 12 }}>
      {/* Divider */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          margin: "14px 0",
          gap: 10,
        }}
      >
        <div style={{ flex: 1, height: 1, background: "#1e293b" }} />
        <span
          style={{
            fontSize: 12,
            color: "#475569",
            fontFamily: "monospace",
            letterSpacing: 1,
          }}
        >
          OR
        </span>
        <div style={{ flex: 1, height: 1, background: "#1e293b" }} />
      </div>

      {/* Google Button Wrapper */}
      {/* <div
        style={{
          width: "100%",
          display: "flex",
          justifyContent: "center",
          background: "#020617",
          border: "1px solid #1e293b",
          borderRadius: 10,
          padding: "10px",
          cursor: "pointer",
        }}
      > */}
        <GoogleLogin
          clientId='744771510955-ftb61pp60t813o3sfeoh4hmqegi5mi3a.apps.googleusercontent.com'
          onSuccess={(credentialResponse) => {
            fetch(`${import.meta.env.VITE_BACKEND_URL}/auth/google/login`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              credentials:"include",
              body: JSON.stringify({
                token: credentialResponse.credential,
              }),
            })
              .then((res) => res.json())
              .then((data) => {
                handleSuccess(data);
              })
              .catch((err) => console.error("Google login error:", err));
          }}
          onError={() => console.log("Login Failed")}
          theme="filled_blue"
          size="xl"
          text="continue_with"
          shape="rectangular"
        />
      {/* </div> */}
    </div>
  );
};

export default GoogleSignIn;