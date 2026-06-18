import { getToken } from './utils/auth';
import { getAdminInfoAPI } from './services/auth';

export async function getInitialState(): Promise<{
  currentUser?: API.CurrentUser;
  collapsed: boolean;
}> {
  const token = getToken();
  if (!token) return { collapsed: false };

  try {
    const res = await getAdminInfoAPI();
    return {
      currentUser: res.data,
      collapsed: false,
    };
  } catch {
    return { collapsed: false };
  }
}
