import { api } from "@/lib/api-client";

export type StaffUser = { id: string; name: string; email: string; role: string };
export type StaffAuthBundle = { access_token: string; token_type: string; user: StaffUser };

export async function staffLoginApi(input: {
  email: string;
  password: string;
}): Promise<StaffAuthBundle> {
  const { data } = await api.post<StaffAuthBundle>("/auth/login", input);
  return data;
}

export async function staffMeApi(): Promise<StaffUser> {
  const { data } = await api.get<StaffUser>("/auth/me");
  return data;
}
