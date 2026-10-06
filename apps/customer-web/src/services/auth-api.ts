import { api } from "@/lib/api-client";

export type User = { id: string; name: string; email: string; role: string };
export type AuthBundle = { access_token: string; token_type: string; user: User };

export async function registerApi(input: {
  name: string;
  email: string;
  password: string;
}): Promise<AuthBundle> {
  const { data } = await api.post<AuthBundle>("/auth/register", { ...input, role: "CUSTOMER" });
  return data;
}

export async function loginApi(input: { email: string; password: string }): Promise<AuthBundle> {
  const { data } = await api.post<AuthBundle>("/auth/login", input);
  return data;
}

export async function meApi(): Promise<User> {
  const { data } = await api.get<User>("/auth/me");
  return data;
}
