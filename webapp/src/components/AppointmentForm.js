import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { MainButton } from '@vkruglikov/react-telegram-web-app';
import WebApp from '@twa-dev/sdk';

function AppointmentForm({ user }) {
  const { serviceId } = useParams();
  const navigate = useNavigate();
  const [service, setService] = useState(null);
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedTime, setSelectedTime] = useState(null);
  const [availableTimes, setAvailableTimes] = useState([]);

  useEffect(() => {
    // Загрузка информации об услуге
    fetch(`/api/v1/services/${serviceId}`)
      .then(response => response.json())
      .then(data => setService(data))
      .catch(error => console.error('Error:', error));
  }, [serviceId]);

  const handleDateSelect = (date) => {
    setSelectedDate(date);
    // Загрузка доступного времени для выбранной даты
    fetch(`/api/v1/appointments/available-times?date=${date}&service_id=${serviceId}`)
      .then(response => response.json())
      .then(data => setAvailableTimes(data))
      .catch(error => console.error('Error:', error));
  };

  const handleTimeSelect = (time) => {
    setSelectedTime(time);
  };

  const handleSubmit = () => {
    if (!selectedDate || !selectedTime) return;

    const appointmentData = {
      service_id: parseInt(serviceId),
      appointment_time: `${selectedDate}T${selectedTime}`,
      client_telegram_id: user.id.toString(),
      client_name: user.first_name,
      client_phone: user.phone_number || ''
    };

    fetch('/api/v1/appointments', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(appointmentData),
    })
      .then(response => response.json())
      .then(data => {
        WebApp.showAlert('Запись успешно создана!');
        navigate('/');
      })
      .catch(error => {
        console.error('Error:', error);
        WebApp.showAlert('Ошибка при создании записи');
      });
  };

  return (
    <div className="appointment-form">
      {service && (
        <>
          <h2>Запись на {service.name}</h2>
          <p className="price">Стоимость: {service.price} ₽</p>
          <p className="duration">Длительность: {service.duration} мин</p>
          
          <div className="date-selector">
            <h3>Выберите дату:</h3>
            {/* Здесь будет календарь или список дат */}
          </div>

          {selectedDate && (
            <div className="time-selector">
              <h3>Выберите время:</h3>
              <div className="time-slots">
                {availableTimes.map(time => (
                  <button
                    key={time}
                    className={`time-slot ${selectedTime === time ? 'selected' : ''}`}
                    onClick={() => handleTimeSelect(time)}
                  >
                    {time}
                  </button>
                ))}
              </div>
            </div>
          )}

          {selectedDate && selectedTime && (
            <MainButton text="Подтвердить запись" onClick={handleSubmit} />
          )}
        </>
      )}
    </div>
  );
}

export default AppointmentForm;