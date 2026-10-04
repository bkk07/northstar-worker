import axios from "axios";
import { axiosClient } from "@/shared/api/axiosClient";

// 401 on any /api/ops/* call (except login itself) means the session died:
// send the operator back to login. Installed once from the ops layouts.
let installed = false;

export function installOpsAuthInterceptor() {
  if (installed) return;
  installed = true;
  axiosClient.interceptors.response.use(
    (response) => response,
    (error) => {
      const url: string = error?.config?.url ?? "";
      const isOpsCall = url.startsWith("/api/ops");
      const isLoginCall = url === "/api/ops/auth/login";
      const onLoginPage =
        typeof window !== "undefined" && window.location.pathname.startsWith("/ops/login");
      if (
        axios.isAxiosError(error) &&
        error.response?.status === 401 &&
        isOpsCall &&
        !isLoginCall &&
        !onLoginPage
      ) {
        window.location.assign("/ops/login");
      }
      return Promise.reject(error);
    },
  );
}
