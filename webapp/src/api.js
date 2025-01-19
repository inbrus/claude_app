import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
});

// Сервисы
export const getServices = () => api.get('/services');
export const getService = (id) => api.get(`/services/${id}`);
export const createService = (data) => api.post('/services', data);
export const updateService = (id, data) => api.put(`/services/${id}`, data);
export const deleteService = (id) => api.delete(`/services/${id}`);

// Записи
export const getAppointments = () => api.get('/appointments');
export const getAppointment = (id) => api.get(`/appointments/${id}`);
export const createAppointment = (data) => api.post('/appointments', data);
export const updateAppointment = (id, data) => api.put(`/appointments/${id}`, data);
export const deleteAppointment = (id) => api.delete(`/appointments/${id}`);
export const getAvailableTimes = (date, serviceId) => 
  api.get(`/appointments/available-times?date=${date}&service_id=${serviceId}`);

// Администраторы
export const checkAdmin = (telegramId) => api.get(`/admin/check/${telegramId}`);
export const createAdmin = (data) => api.post('/admin', data);

// Обработка ошибок
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response) {
      // Обработка ошибок сервера
      console.error('API Error:', error.response.data);
    } else if (error.request) {
      // Ошибка сети
      console.error('Network Error:', error.request);
    } else {
      // Другие ошибки
      console.error('Error:', error.message);
    }
    return Promise.reject(error);
  }
);