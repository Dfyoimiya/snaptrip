import axios from "axios"
import type {
  ApiResponse,
  ConfirmRequest,
  PlanCreateRequest,
  PlanResponse,
} from "../types/plan"

const api = axios.create({
  baseURL: "/api/v1",
  timeout: 120_000,
  headers: { "Content-Type": "application/json" },
})

export async function createPlan(
  req: PlanCreateRequest,
): Promise<ApiResponse<PlanResponse>> {
  const { data } = await api.post("/plan/create", req)
  return data
}

export async function confirmPlan(
  planId: string,
  req: ConfirmRequest,
): Promise<ApiResponse<PlanResponse>> {
  const { data } = await api.post(`/plan/${planId}/confirm`, req)
  return data
}

export async function getPlan(
  planId: string,
): Promise<ApiResponse<PlanResponse>> {
  const { data } = await api.get(`/plan/${planId}`)
  return data
}

export function sseUrl(planId: string): string {
  return `/api/v1/plan/${planId}/stream`
}
