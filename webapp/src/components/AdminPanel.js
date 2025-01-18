import React, { useState, useEffect } from 'react';
import { MainButton } from '@vkruglikov/react-telegram-web-app';
import WebApp from '@twa-dev/sdk';

function AdminPanel() {
  const [services, setServices] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [activeTab, setActiveTab] = useState('services');

  useEffect(() => {
    loadServices();
    loadAppointments();
  }, []);

  const loadServices = () => {
    fetch('/api/v1/services')
      .then(response => response.json())
      .then(data => setServices(data))
      .catch(error => console.error('Error:', error));
  };

  const loadAppointments = () => {
    fetch('/api/v1/appointments')
      .then(response => response.json())
      .then(data => setAppointments(data))
      .catch(error => console.error('Error:', error));
  };

  const handleAddService = () => {
    WebApp.showPopup({
      title: 'Добавить услугу',
      message: 'Введите данные услуги',
      buttons: [
        { id: 'cancel', type: 'cancel', text: 'Отмена' },
        { id: 'ok', type: 'ok', text: 'Добавить' }
      ]
    });
  };

  const handleEditService = (service) => {
    // Реализация редактирования услуги
  };

  const handleDeleteService = (serviceId) => {
    if (window.confirm('Вы уверены, что хотите удалить эту услугу?')) {
      fetch(`/api/v1/services/${serviceId}`, {
        method: 'DELETE',
      })
        .then(() => {
          loadServices();
          WebApp.showAlert('Услуга удалена');
        })
        .catch(error => {
          console.error('Error:', error);
          WebApp.showAlert('Ошибка при удалении услуги');
        });
    }
  };

  return (
    <div className="admin-panel">
      <div className="tabs">
        <button
          className={activeTab === 'services' ? 'active' : ''}
          onClick={() => setActiveTab('services')}
        >
          Услуги
        </button>
        <button
          className={activeTab === 'appointments' ? 'active' : ''}
          onClick={() => setActiveTab('appointments')}
        >
          Записи
        </button>
      </div>

      {activeTab === 'services' && (
        <div className="services-panel">
          <MainButton text="Добавить услугу" onClick={handleAddService} />
          <div className="services-list">
            {services.map(service => (
              <div key={service.id} className="service-item">
                <h3>{service.name}</h3>
                <p>{service.price} ₽</p>
                <div className="actions">
                  <button onClick={() => handleEditService(service)}>
                    Редактировать
                  </button>
                  <button onClick={() => handleDeleteService(service.id)}>
                    Удалить
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'appointments' && (
        <div className="appointments-panel">
          <div className="appointments-list">
            {appointments.map(appointment => (
              <div key={appointment.id} className="appointment-item">
                <p>
                  {new Date(appointment.appointment_time).toLocaleString('ru-RU')}
                </p>
                <p>{appointment.client_name}</p>
                <p>{appointment.service.name}</p>
                <p>Статус: {appointment.status}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminPanel;