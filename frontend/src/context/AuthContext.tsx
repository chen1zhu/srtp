import { createContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

type User = {
  username: string;
  email: string;
  full_name?: string;
  avatar_url?: string | null;
  role?: string;
} | null;

type AuthContextValue = {
  user: User;
  loading: boolean;
  login: (identifier: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string, fullName: string) => Promise<void>;
  updateAvatar: (file: File) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  login: async () => {},
  register: async () => {},
  updateAvatar: async () => {},
  changePassword: async () => {},
  logout: async () => {},
  refresh: async () => {},
});

const readErrorMessage = async (resp: Response, fallback: string) => {
  const text = await resp.text();
  try {
    const data = JSON.parse(text);
    const detail = data?.detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          const field = Array.isArray(item?.loc) ? item.loc[item.loc.length - 1] : '';
          return field ? `${field}: ${item?.msg || '请求参数不合法'}` : (item?.msg || '请求参数不合法');
        })
        .filter(Boolean);
      return messages.length > 0 ? messages.join('；') : fallback;
    }
    if (typeof detail === 'string') {
      return detail;
    }
    return fallback;
  } catch {
    return text || fallback;
  }
};

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE_URL}/auth/me`, { credentials: 'include' });
      if (resp.ok) {
        const data = await resp.json();
        setUser(data.user || null);
      } else {
        setUser(null);
      }
    } catch (e) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const login = async (identifier: string, password: string) => {
    const resp = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identifier, password }),
    });
    if (!resp.ok) {
      throw new Error(await readErrorMessage(resp, '登录失败'));
    }
    await refresh();
  };

  const register = async (username: string, email: string, password: string, fullName: string) => {
    const resp = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password, full_name: fullName }),
    });
    if (!resp.ok) {
      throw new Error(await readErrorMessage(resp, '注册失败'));
    }
    await refresh();
  };

  const updateAvatar = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const resp = await fetch(`${API_BASE_URL}/auth/me/avatar`, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    });
    if (!resp.ok) {
      throw new Error(await readErrorMessage(resp, '头像上传失败'));
    }
    const data = await resp.json();
    setUser(data.user || null);
  };

  const changePassword = async (currentPassword: string, newPassword: string) => {
    const resp = await fetch(`${API_BASE_URL}/auth/me/password`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
    if (!resp.ok) {
      throw new Error(await readErrorMessage(resp, '修改密码失败'));
    }
  };

  const logout = async () => {
    await fetch(`${API_BASE_URL}/auth/logout`, { method: 'POST', credentials: 'include' });
    setUser(null);
  };

  return <AuthContext.Provider value={{ user, loading, login, register, updateAvatar, changePassword, logout, refresh }}>{children}</AuthContext.Provider>;
};

export default AuthProvider;
