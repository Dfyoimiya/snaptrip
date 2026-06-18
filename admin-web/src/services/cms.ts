import request from '@/utils/request';

// ── Banners ──────────────────────────────────────────────────────────────

const BANNER_BASE = '/admin/cms/banners';

export const getBannerListAPI = (params?: Record<string, unknown>) =>
  request.get<API.ApiResponse<API.Banner[]>>(BANNER_BASE, { params });

export const createBannerAPI = (data: API.BannerCreate) =>
  request.post<API.ApiResponse<API.Banner>>(BANNER_BASE, data);

export const updateBannerAPI = (id: string, data: API.BannerUpdate) =>
  request.put<API.ApiResponse<API.Banner>>(`${BANNER_BASE}/${id}`, data);

export const deleteBannerAPI = (id: string) =>
  request.delete(`${BANNER_BASE}/${id}`);

export const toggleBannerStatusAPI = (id: string, status: number) =>
  request.patch(`${BANNER_BASE}/${id}/status`, null, { params: { status } });

export const updateBannerSortAPI = (id: string, sort: number) =>
  request.patch(`${BANNER_BASE}/${id}/sort`, null, { params: { sort } });

// ── Subjects ─────────────────────────────────────────────────────────────

const SUBJECT_BASE = '/admin/cms/subjects';

export const getSubjectListAPI = (params?: Record<string, unknown>) =>
  request.get<API.ApiResponse<API.PaginatedResponse<API.Subject>>>(SUBJECT_BASE, { params });

export const getSubjectCategoriesAPI = () =>
  request.get<API.ApiResponse<string[]>>(`${SUBJECT_BASE}/categories`);

export const createSubjectAPI = (data: API.SubjectCreate) =>
  request.post<API.ApiResponse<API.Subject>>(SUBJECT_BASE, data);

export const updateSubjectAPI = (id: string, data: API.SubjectUpdate) =>
  request.put<API.ApiResponse<API.Subject>>(`${SUBJECT_BASE}/${id}`, data);

export const deleteSubjectAPI = (id: string) =>
  request.delete(`${SUBJECT_BASE}/${id}`);

// ── Helps ────────────────────────────────────────────────────────────────

const HELP_BASE = '/admin/cms/helps';

export const getHelpListAPI = (params?: Record<string, unknown>) =>
  request.get<API.ApiResponse<API.PaginatedResponse<API.Help>>>(HELP_BASE, { params });

export const createHelpAPI = (data: API.HelpCreate) =>
  request.post<API.ApiResponse<API.Help>>(HELP_BASE, data);

export const updateHelpAPI = (id: string, data: Partial<API.HelpCreate>) =>
  request.put<API.ApiResponse<API.Help>>(`${HELP_BASE}/${id}`, data);

export const deleteHelpAPI = (id: string) =>
  request.delete(`${HELP_BASE}/${id}`);
