import { useMutation } from "@tanstack/react-query";
import { login, logout } from "../api/authApi";

export function useLogin(onSuccess: () => void) {
  return useMutation({
    mutationFn: (agentName: string) => login(agentName),
    onSuccess,
  });
}

export function useLogout(onDone: () => void) {
  return useMutation({ mutationFn: logout, onSettled: onDone });
}
