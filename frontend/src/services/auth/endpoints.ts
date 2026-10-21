export const API_BASE_URL: string = (import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')

export const LOGIN_ENDPOINT: string = `${API_BASE_URL}/v1/auth/login`

export const STUDENT_LOGIN_ENDPOINT: string = `${API_BASE_URL}/v1/auth/student/login`

export const ME_ENDPOINT: string = `${API_BASE_URL}/v1/auth/me`

export const FORGOT_PASSWORD_ENDPOINT: string = `${API_BASE_URL}/v1/auth/forgot-password`

export const RESET_PASSWORD_ENDPOINT: string = `${API_BASE_URL}/v1/auth/reset-password`

export const CHANGE_PASSWORD_ENDPOINT: string = `${API_BASE_URL}/v1/auth/change-password`

export const REFRESH_ENDPOINT: string = `${API_BASE_URL}/v1/auth/refresh`

export const LOGOUT_ENDPOINT: string = `${API_BASE_URL}/v1/auth/logout`

export const LOGOUT_ALL_ENDPOINT: string = `${API_BASE_URL}/v1/auth/logout-all`
